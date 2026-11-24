"""Historical batch load: download the official CFPB full CSV ZIP into the MinIO raw zone.

Usage (inside the pipeline container):  python -m ingestion.historical     (also: make ingest-full)
The last line printed is the run_id, so ingestion/pipeline.py can pass it to the Spark job.

What one run does:
1. Create a run_id (YYYYMMDDTHHMMSSZ_full, UTC).
2. Stream the ZIP to data/tmp/ in chunks (never fully in memory), computing SHA-256 and size.
   An interrupted download RESUMES from where it stopped (HTTP Range request) on the next run.
   Network errors, timeouts, HTTP 429 and 5xx are retried with bounded backoff (2, 4, 8 s).
3. If today's manifest already exists with the same SHA-256: upload nothing, log "skipped_identical".
4. Otherwise upload the original ZIP, extract complaints.csv, count its records (quoted multi-line
   fields respected) and upload the CSV next to it.
5. Write manifest.json next to the raw files and the run log to logs/ingestion/run_id=<id>.json.
Raw objects are never modified or overwritten (enforced in ingestion/minio_utils.py).
"""
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from ingestion import minio_utils

# No custom User-Agent: the CFPB sites sit behind the Akamai firewall, which answered 403 to a custom
# agent ("cfpb-course-project/1.0") and to a browser imitation, but 200 to the requests library's own
# default ("python-requests/<version>"), tested 20 Nov 2026. So we send the library default, honestly.
CHUNK_SIZE = 1024 * 1024                       # 1 MiB per read
BACKOFF_SECONDS = [2, 4, 8]                    # waits between attempts
RETRY_STATUS = {429, 500, 502, 503, 504}
# Network problems worth another attempt. ChunkedEncodingError is what requests raises when the
# connection drops in the MIDDLE of a download; it is not a ConnectionError subclass, so it must be
# listed (defect found on 20 Nov: a 370 MB download broke after 104 MB and was not retried).
RETRYABLE_ERRORS = (requests.ConnectionError, requests.Timeout, requests.HTTPError,
                    requests.exceptions.ChunkedEncodingError)
WORK_DIR = Path(os.environ.get("INGEST_WORK_DIR", "data/tmp"))   # git-ignored, survives container restarts
DATE_RECEIVED_HEADER = "Date received"
COMPLAINT_ID_HEADER = "Complaint ID"


class DownloadError(Exception):
    """The download failed after every allowed retry, or with a non-retryable HTTP status."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%SZ") + "_full"


def raw_prefix(ingest_date: str) -> str:
    return f"raw/cfpb/full_load/ingest_date={ingest_date}/"


# ---------------------------------------------------------------- download

def _hash_existing(path: Path, digest) -> int:
    """Feed the bytes already on disk into the hash (resume case) and return their size."""
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            size += len(chunk)
    return size


def download(url: str, target: Path, http_log: dict, timeout: float, max_retries: int,
             sleep=None) -> dict:
    """Stream url to target with resume and bounded retries. Returns size, sha256 and HTTP metadata.

    http_log is updated in place (last_status, retries, errors) so the run log is complete
    even when the download finally fails.
    """
    sleep = sleep or time.sleep
    target.parent.mkdir(parents=True, exist_ok=True)
    validator_file = target.with_name(target.name + ".validator.json")
    attempt = 0                     # failures in a row WITHOUT progress (bytes on disk did not grow)
    best_size = target.stat().st_size if target.exists() else 0
    while True:
        digest = hashlib.sha256()
        already = _hash_existing(target, digest) if target.exists() else 0
        headers = {}
        if already:
            headers["Range"] = f"bytes={already}-"
            # If-Range: resume only if the server still has the SAME file (the CFPB republishes it
            # daily). If it changed, the server sends the whole new file (200) and we start again.
            validator = _read_validator(validator_file)
            if validator:
                headers["If-Range"] = validator
        try:
            with requests.get(url, headers=headers, stream=True, timeout=(10, timeout)) as response:
                http_log["last_status"] = response.status_code
                if response.status_code == 416:            # we already hold every byte
                    return _result(target, digest, already, response)
                if response.status_code in RETRY_STATUS:
                    raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
                if response.status_code not in (200, 206):
                    raise DownloadError(f"HTTP {response.status_code} is not retryable")
                if already and response.status_code == 200:  # file changed or Range ignored: start again
                    digest, already, best_size = hashlib.sha256(), 0, 0
                validator = response.headers.get("ETag") or response.headers.get("Last-Modified")
                if validator and not already:
                    validator_file.write_text(json.dumps({"validator": validator}))
                mode = "ab" if already else "wb"
                with open(target, mode) as handle:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        handle.write(chunk)
                        digest.update(chunk)
                size = target.stat().st_size
                expected = _expected_size(response, already)
                if expected is not None and size != expected:
                    raise requests.ConnectionError(f"incomplete download: {size} of {expected} bytes")
                return _result(target, digest, size, response)
        except RETRYABLE_ERRORS as exc:
            http_log["errors"].append(f"{iso(utc_now())} {type(exc).__name__}: {exc}")
            size_now = target.stat().st_size if target.exists() else 0
            if size_now > best_size:
                # The broken attempt still downloaded more: resume at once and do not count it
                # against max_retries, so a slow, unstable connection can finish a large file.
                best_size, attempt = size_now, 0
                http_log["resumes"] = http_log.get("resumes", 0) + 1
                print(f"Connection dropped after {size_now:,} bytes; resuming", flush=True)
                continue
            if attempt >= max_retries:
                raise DownloadError(f"gave up after {max_retries} retries: {exc}") from exc
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = int(retry_after)
            attempt += 1
            http_log["retries"] += 1
            print(f"Download problem ({exc}); retry {attempt}/{max_retries} in {wait} s", flush=True)
            sleep(wait)


def _read_validator(validator_file: Path):
    try:
        return json.loads(validator_file.read_text())["validator"]
    except (OSError, ValueError, KeyError):
        return None


def _expected_size(response, already: int):
    """Total file size announced by the server, if any."""
    content_range = response.headers.get("Content-Range")      # e.g. bytes 100-999/1000
    if content_range and "/" in content_range:
        total = content_range.rsplit("/", 1)[1]
        return int(total) if total.isdigit() else None
    length = response.headers.get("Content-Length")
    return already + int(length) if length and length.isdigit() else None


def _result(target: Path, digest, size: int, response) -> dict:
    return {
        "size_bytes": size,
        "sha256": digest.hexdigest(),
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
    }


# ---------------------------------------------------------------- extract and count

class _HashingTee(io.RawIOBase):
    """Read from the ZIP member, copy every byte to the output file and into a SHA-256."""

    def __init__(self, source, sink):
        self.source, self.sink, self.digest, self.size = source, sink, hashlib.sha256(), 0

    def readable(self):
        return True

    def readinto(self, buffer):
        data = self.source.read(len(buffer))
        self.sink.write(data)
        self.digest.update(data)
        self.size += len(data)
        buffer[:len(data)] = data
        return len(data)


def _to_iso_date(value: str):
    """'2024-03-15', '03/15/2024' or '03/15/24' -> '2024-03-15'; anything else -> None."""
    value = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def extract_and_profile(zip_path: Path, csv_path: Path) -> dict:
    """Extract the CSV in one streaming pass and return its size, SHA-256, header and record count.

    csv.reader handles quoted fields containing commas or line breaks, so record_count is the
    number of complaints, not the number of text lines. The latest date_received and the highest
    Complaint ID are kept to bootstrap the first incremental run.
    """
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected exactly one CSV in the ZIP, found {members}")
        with archive.open(members[0]) as source, open(csv_path, "wb") as sink:
            tee = _HashingTee(source, sink)
            text = io.TextIOWrapper(io.BufferedReader(tee, CHUNK_SIZE), encoding="utf-8-sig", newline="")
            reader = csv.reader(text)
            header = next(reader)
            date_col = header.index(DATE_RECEIVED_HEADER) if DATE_RECEIVED_HEADER in header else None
            id_col = header.index(COMPLAINT_ID_HEADER) if COMPLAINT_ID_HEADER in header else None
            count, max_date, max_id = 0, None, None
            for row in reader:
                if not row:
                    continue
                count += 1
                if date_col is not None and date_col < len(row):
                    day = _to_iso_date(row[date_col])
                    if day and (max_date is None or day > max_date):
                        max_date = day
                if id_col is not None and id_col < len(row) and row[id_col].strip().isdigit():
                    value = int(row[id_col])
                    max_id = value if max_id is None or value > max_id else max_id
                if count % 1_000_000 == 0:
                    print(f"  counted {count:,} records", flush=True)
            text.read()                              # drain the rest so the copy is complete
    return {
        "member": members[0],
        "size_bytes": tee.size,
        "sha256": tee.digest.hexdigest(),
        "header": header,
        "record_count": count,
        "max_date_received": max_date,
        "max_complaint_id": max_id,
    }


# ---------------------------------------------------------------- run

def run() -> dict:
    """Execute one historical load and return its run log (also written to MinIO)."""
    started = utc_now()
    run_id = new_run_id(started)
    ingest_date = started.strftime("%Y-%m-%d")
    prefix = raw_prefix(ingest_date)
    zip_key, csv_key, manifest_key = prefix + "complaints.csv.zip", prefix + "complaints.csv", prefix + "manifest.json"
    url = os.environ["CFPB_CSV_URL"]
    timeout = float(os.environ.get("API_TIMEOUT_SECONDS", "30"))
    max_retries = int(os.environ.get("API_MAX_RETRIES", "3"))
    zip_path = WORK_DIR / "complaints.csv.zip.part"
    csv_path = WORK_DIR / "complaints.csv"

    log = {
        "run_id": run_id, "run_type": "full", "started_at": iso(started), "finished_at": None,
        "endpoint": url, "params": {}, "window": None,
        "pagination": None,
        "http": {"last_status": None, "retries": 0, "errors": []},
        "outcome": None, "raw_paths": [], "record_count": None, "sha256": None,
        "high_water_mark_used": None, "high_water_mark_next": None,
    }
    try:
        print(f"[{run_id}] downloading {url}", flush=True)
        download_started = utc_now()
        meta = download(url, zip_path, log["http"], timeout, max_retries)
        download_finished = utc_now()
        log["sha256"] = meta["sha256"]
        print(f"[{run_id}] downloaded {meta['size_bytes']:,} bytes, sha256 {meta['sha256']}", flush=True)

        if minio_utils.object_exists(manifest_key):
            existing = minio_utils.read_json(manifest_key)
            if existing.get("sha256") != meta["sha256"]:
                raise RuntimeError(
                    f"{manifest_key} already holds a different file (sha256 {existing.get('sha256')}). "
                    "Raw objects are immutable: run the historical load again on another day.")
            log.update(outcome="skipped_identical", record_count=existing.get("record_count"),
                       raw_paths=[zip_key, csv_key, manifest_key])
            print(f"[{run_id}] identical file already stored today: nothing uploaded", flush=True)
        else:
            minio_utils.upload_file(str(zip_path), zip_key, content_type="application/zip")
            print(f"[{run_id}] uploaded {zip_key}; extracting and counting records", flush=True)
            profile = extract_and_profile(zip_path, csv_path)
            minio_utils.upload_file(str(csv_path), csv_key, content_type="text/csv")
            manifest = {
                "run_id": run_id,
                "source_url": url,
                "download_started_at": iso(download_started),
                "download_finished_at": iso(download_finished),
                "size_bytes": meta["size_bytes"],
                "sha256": meta["sha256"],
                "record_count": profile["record_count"],
                "http_etag": meta["etag"],
                "http_last_modified": meta["last_modified"],
                "zip_object": zip_key,
                "csv_object": csv_key,
                "csv_member": profile["member"],
                "csv_size_bytes": profile["size_bytes"],
                "csv_sha256": profile["sha256"],
                "csv_columns": profile["header"],
                "max_date_received": profile["max_date_received"],
                "max_complaint_id": profile["max_complaint_id"],
            }
            minio_utils.write_json(manifest, manifest_key)
            log.update(outcome="success", record_count=profile["record_count"],
                       raw_paths=[zip_key, csv_key, manifest_key],
                       high_water_mark_next={"date_received_max": profile["max_date_received"],
                                             "complaint_id_max": profile["max_complaint_id"],
                                             "note": "candidate only; state/high_water_mark.json is set "
                                                     "by ingestion.update_hwm after Spark and the load succeed"})
            print(f"[{run_id}] {profile['record_count']:,} records; manifest written", flush=True)
        # Local copies are only a cache: remove them once MinIO holds the raw files.
        for path in (zip_path, csv_path, zip_path.with_name(zip_path.name + ".validator.json")):
            path.unlink(missing_ok=True)
        return log
    except Exception as exc:
        log["outcome"] = "failed"
        log["http"]["errors"].append(f"{iso(utc_now())} {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return log
    finally:
        log["finished_at"] = iso(utc_now())
        try:
            minio_utils.write_json(log, f"logs/ingestion/run_id={run_id}.json")
        except Exception as exc:                      # MinIO down: still show the log
            print(f"[{run_id}] could not write the run log to MinIO: {exc}", file=sys.stderr)


def main() -> int:
    log = run()
    print(f"Outcome: {log['outcome']}")
    print(log["run_id"])                              # last line = run_id (read by ingestion.pipeline)
    return 0 if log["outcome"] in ("success", "skipped_identical") else 1


if __name__ == "__main__":
    sys.exit(main())
