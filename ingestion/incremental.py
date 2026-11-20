"""Incremental collection: new and changed complaints from the official CFPB API, saved raw to MinIO.

Usage (inside the pipeline container):
    python -m ingestion.incremental                          scheduled run: window from the high-water mark
    python -m ingestion.incremental --start 2026-11-01 --end 2026-11-10    bounded run (demo)
    python -m ingestion.incremental --resume <run_id>        continue a failed run from its last saved page
Also: make ingest-incremental. The last line printed is the run_id.

Design decisions (tested against the live API on 20 Nov 2026, see docs/api_notes.md):
- Window = [high-water mark date - OVERLAP_DAYS, today]. The CFPB publishes a complaint only after the
  company responds or after 15 days, and responses change later, so a 21-day overlap catches late and
  updated complaints. Repeats are removed downstream by de-duplication on complaint_id.
- One request series for all our product labels (the API accepts the product parameter several times).
- Pagination uses search_after (the sort values of the last hit, joined with "_"). The frm offset is
  NOT used: frm=100 silently returned the same 100 complaints as page 1. A guard stops the run if a
  page brings no new complaint, so a broken pagination can never loop forever.
- date_received_max is sent as end + 1 day: the API's real boundary behaviour differs from its spec,
  and asking one extra day guarantees the end day is included (the overlap makes extra days harmless).
- Every page is saved unchanged before any transformation, and the run log (with pagination state)
  is rewritten after each page, so a failed run can resume where it stopped.
- Timeouts, connection errors, HTTP 429 and 5xx are retried with backoff 2, 4, 8 s (Retry-After is
  respected), at most API_MAX_RETRIES times per request. Other 4xx fail the run at once.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from ingestion import minio_utils

# No custom User-Agent: the CFPB firewall (Akamai) accepts the requests default and blocks custom agents.
MAPPING_FILE = Path("config/product_mapping.csv")
HWM_KEY = "state/high_water_mark.json"
FULL_LOAD_PREFIX = "raw/cfpb/full_load/"
BACKOFF_SECONDS = [2, 4, 8]
RETRY_STATUS = {429, 500, 502, 503, 504}
SUB_PRODUCT_SEPARATOR = "•"      # "•": the API's product•sub-product syntax
WILDCARD = "*"


class CollectorError(Exception):
    """A failure that ends the run (after bounded retries, or a non-retryable answer)."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def settings() -> dict:
    return {
        "url": os.environ["CFPB_API_URL"],
        "page_size": int(os.environ.get("API_PAGE_SIZE", "100")),
        "timeout": float(os.environ.get("API_TIMEOUT_SECONDS", "30")),
        "max_retries": int(os.environ.get("API_MAX_RETRIES", "3")),
        "overlap_days": int(os.environ.get("OVERLAP_DAYS", "21")),
    }


def product_filters(path: Path = MAPPING_FILE) -> list:
    """Product filter values for our domain, from the same mapping file the Spark job uses."""
    values = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            product, sub = row["source_product"], row["source_sub_product"]
            value = product if sub == WILDCARD else f"{product}{SUB_PRODUCT_SEPARATOR}{sub}"
            if value not in values:
                values.append(value)
    return values


# ---------------------------------------------------------------- window and high-water mark

def bootstrap_high_water_mark() -> dict:
    """First incremental run: start from the latest date in the most recent historical load."""
    manifests = [k for k in minio_utils.list_keys(FULL_LOAD_PREFIX) if k.endswith("/manifest.json")]
    if not manifests:
        raise CollectorError("No high-water mark and no historical load: run 'make ingest-full' first, "
                             "or give an explicit window with --start and --end.")
    manifest = minio_utils.read_json(manifests[-1])
    return {"date_received_max": manifest["max_date_received"],
            "complaint_id_max": manifest.get("max_complaint_id"),
            "run_id": manifest["run_id"], "source": "bootstrap from historical manifest"}


def compute_window(hwm: dict, today: date, overlap_days: int) -> tuple:
    """[high-water date - overlap, today], both days included."""
    start = date.fromisoformat(hwm["date_received_max"]) - timedelta(days=overlap_days)
    return start, today


# ---------------------------------------------------------------- HTTP

def get_with_retries(session, url, params, timeout, max_retries, http_log, sleep=None) -> requests.Response:
    """One GET with bounded retries. http_log (last_status, retries, errors) is updated in place."""
    sleep = sleep or time.sleep
    attempt = 0
    while True:
        try:
            response = session.get(url, params=params, timeout=(10, timeout))
            http_log["last_status"] = response.status_code
            if response.status_code in RETRY_STATUS:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            if response.status_code != 200:
                raise CollectorError(f"HTTP {response.status_code} is not retryable: {response.text[:200]}")
            return response
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            http_log["errors"].append(f"{iso(utc_now())} {type(exc).__name__}: {exc}")
            if attempt >= max_retries:
                raise CollectorError(f"gave up after {max_retries} retries: {exc}") from exc
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
            if retry_after and str(retry_after).isdigit():
                wait = int(retry_after)
            attempt += 1
            http_log["retries"] += 1
            print(f"Request problem ({exc}); retry {attempt}/{max_retries} in {wait} s", flush=True)
            sleep(wait)


# ---------------------------------------------------------------- run

def new_log(run_id, cfg, params, start, end, hwm) -> dict:
    return {
        "run_id": run_id, "run_type": "api", "started_at": iso(utc_now()), "finished_at": None,
        "endpoint": cfg["url"], "params": params,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "pagination": {"method": "search_after", "page_size": cfg["page_size"], "pages_fetched": 0,
                       "last_offset": 0, "search_after": None, "expected_total": None},
        "http": {"last_status": None, "retries": 0, "errors": []},
        "outcome": "running", "raw_paths": [], "record_count": 0, "sha256": None, "page_sha256": [],
        "source_meta": None, "seen_ids": [],
        "high_water_mark_used": hwm, "high_water_mark_next": None,
    }


def log_key(run_id: str) -> str:
    return f"logs/ingestion/run_id={run_id}.json"


def save_log(log: dict) -> None:
    minio_utils.write_json(log, log_key(log["run_id"]), overwrite=True)


def collect(log: dict, cfg: dict, raw_prefix: str, session=None, sleep=None) -> dict:
    """Fetch every page of the window, saving each one raw, until the last page."""
    session = session or requests.Session()
    pag = log["pagination"]
    seen = set(log["seen_ids"])
    max_date = (log["high_water_mark_next"] or {}).get("date_received_max")
    max_id = (log["high_water_mark_next"] or {}).get("complaint_id_max")
    while True:
        # No "format" parameter: with a format the API switches to export mode and ignores size.
        params = dict(log["params"], size=cfg["page_size"], sort="created_date_desc",
                      no_aggs="true", no_highlight="true")
        if pag["search_after"]:
            params["search_after"] = pag["search_after"]
        response = get_with_retries(session, cfg["url"], params, cfg["timeout"], cfg["max_retries"],
                                    log["http"], sleep)
        body = response.json()
        hits = body.get("hits", {}).get("hits", [])
        if pag["expected_total"] is None:
            total = body.get("hits", {}).get("total", {})
            pag["expected_total"] = total.get("value") if isinstance(total, dict) else total
            meta = body.get("_meta", {})
            log["source_meta"] = {k: meta.get(k) for k in ("last_updated", "last_indexed",
                                                         "total_record_count", "is_data_stale")}
        if not hits and pag["pages_fetched"] > 0:
            break                                            # previous page was exactly the last one
        page_number = pag["pages_fetched"] + 1
        key = f"{raw_prefix}response_{page_number}.json"
        if minio_utils.object_exists(key):
            # A crash after saving this page but before saving the log: keep the first copy untouched
            # (raw is immutable) and store the new answer beside it; duplicates are removed by complaint_id.
            key = f"{raw_prefix}response_{page_number}_again_{utc_now().strftime('%H%M%S')}.json"
        minio_utils.upload_bytes(response.content, key, content_type="application/json")
        new_ids = 0
        for hit in hits:
            source = hit.get("_source", {})
            cid = str(source.get("complaint_id", "")).strip()
            if cid and cid not in seen:
                seen.add(cid)
                new_ids += 1
            day = (source.get("date_received") or "")[:10]
            if day and (max_date is None or day > max_date):
                max_date = day
            if cid.isdigit() and (max_id is None or int(cid) > max_id):
                max_id = int(cid)
        pag["pages_fetched"] = page_number
        pag["last_offset"] += len(hits)
        log["raw_paths"].append(key)
        log["page_sha256"].append(hashlib.sha256(response.content).hexdigest())
        log["seen_ids"] = sorted(seen, key=lambda x: (len(x), x))
        log["record_count"] = len(seen)
        log["high_water_mark_next"] = {"date_received_max": max_date, "complaint_id_max": max_id,
                                       "note": "candidate only; set by ingestion.update_hwm after "
                                               "Spark and the MongoDB load succeed"}
        if hits:
            pag["search_after"] = "_".join(_sort_value(v) for v in hits[-1].get("sort", []))
        save_log(log)                                        # pagination state saved after every page
        print(f"  page {page_number}: {len(hits)} hits, {len(seen):,} unique so far", flush=True)
        if not hits:
            break                                            # empty window
        if hits and new_ids == 0:
            raise CollectorError(f"pagination is not advancing: page {page_number} brought no new "
                                 "complaint (the same page was returned again)")
        if len(hits) < cfg["page_size"]:
            break                                            # a short page is the last page
        limit = math.ceil((pag["expected_total"] or 0) / cfg["page_size"]) + 2
        if page_number >= limit:
            raise CollectorError(f"more pages than expected ({page_number} for {pag['expected_total']} "
                                 "complaints): stopping instead of looping")
    return log


def _sort_value(value) -> str:
    """1792669710000 -> '1792669710000' (never '1.79e12'); strings unchanged."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def run(start: date = None, end: date = None, resume_run_id: str = None, session=None, sleep=None) -> dict:
    cfg = settings()
    log = None
    try:
        if resume_run_id:
            previous = minio_utils.read_json(log_key(resume_run_id))
            if previous.get("outcome") not in ("failed", "running"):
                # Checked before taking the log over, so a finished run's log is never rewritten.
                raise CollectorError(f"run {resume_run_id} ended with '{previous.get('outcome')}': nothing to resume")
            log = previous
            log["outcome"] = "running"
            log.setdefault("resumed_at", []).append(iso(utc_now()))
            ingest_date = log["run_id"][:8]
            ingest_date = f"{ingest_date[:4]}-{ingest_date[4:6]}-{ingest_date[6:8]}"
            print(f"[{log['run_id']}] resuming after page {log['pagination']['pages_fetched']}", flush=True)
        else:
            now = utc_now()
            run_id = now.strftime("%Y%m%dT%H%M%SZ") + "_api"
            ingest_date = now.strftime("%Y-%m-%d")
            if start and end:
                hwm = {"source": "explicit window (--start/--end)"}
            else:
                hwm = minio_utils.read_json(HWM_KEY) if minio_utils.object_exists(HWM_KEY) \
                    else bootstrap_high_water_mark()
                start, end = compute_window(hwm, now.date(), cfg["overlap_days"])
            if start > end:
                raise CollectorError(f"empty window: start {start} is after end {end}")
            params = {"product": product_filters(),
                      "date_received_min": start.isoformat(),
                      "date_received_max": (end + timedelta(days=1)).isoformat()}
            log = new_log(run_id, cfg, params, start, end, hwm)
            print(f"[{run_id}] window {start} to {end}, products {params['product']}", flush=True)
            save_log(log)
        raw_prefix = f"raw/cfpb/api/ingest_date={ingest_date}/run_id={log['run_id']}/"
        collect(log, cfg, raw_prefix, session, sleep)
        log["outcome"] = "success" if log["record_count"] else "empty"
        log["sha256"] = hashlib.sha256("".join(log["page_sha256"]).encode()).hexdigest() if log["page_sha256"] else None
        expected = log["pagination"]["expected_total"]
        if expected is not None and expected != log["record_count"]:
            log["note"] = (f"API announced {expected} complaints, {log['record_count']} unique collected "
                           "(the index can change during a run; the next overlapping window catches up)")
        return log
    except Exception as exc:
        if log is None:
            log = {"run_id": utc_now().strftime("%Y%m%dT%H%M%SZ") + "_api", "run_type": "api",
                   "started_at": iso(utc_now()), "http": {"last_status": None, "retries": 0, "errors": []},
                   "raw_paths": [], "record_count": 0}
        log["outcome"] = "failed"
        log["http"]["errors"].append(f"{iso(utc_now())} {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return log
    finally:
        if log is not None:
            log["finished_at"] = iso(utc_now())
            try:
                save_log(log)
            except Exception as exc:
                print(f"could not write the run log to MinIO: {exc}", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Collect new and changed complaints from the CFPB API.")
    parser.add_argument("--start", type=date.fromisoformat, help="first day of the window (YYYY-MM-DD)")
    parser.add_argument("--end", type=date.fromisoformat, help="last day of the window, included")
    parser.add_argument("--resume", metavar="RUN_ID", help="continue a failed run from its last saved page")
    args = parser.parse_args(argv)
    if bool(args.start) != bool(args.end):
        parser.error("--start and --end go together")
    log = run(args.start, args.end, args.resume)
    print(f"Outcome: {log['outcome']}  records: {log.get('record_count')}  pages: "
          f"{log.get('pagination', {}).get('pages_fetched')}")
    print(log["run_id"])
    return 0 if log["outcome"] in ("success", "empty") else 1


if __name__ == "__main__":
    sys.exit(main())
