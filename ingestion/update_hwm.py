"""High-water mark: the latest complaint date that has been collected, processed AND loaded.

The next incremental run starts from this date minus OVERLAP_DAYS. It is stored in MinIO at
state/high_water_mark.json and moves only forward, and only after Spark and the MongoDB load of a
run have succeeded (ingestion.pipeline calls this module last). Every change is also kept in
state/hwm_history/, so any value can be traced back to the run that set it.

Usage (inside the pipeline container):
    python -m ingestion.update_hwm --run-id <run_id>                     advance from a successful run
    python -m ingestion.update_hwm --show                                print the current value
    python -m ingestion.update_hwm --reset 2026-11-01 --reason "..."     manual reset (runbook)
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone

from ingestion import minio_utils

HWM_KEY = "state/high_water_mark.json"
HISTORY_PREFIX = "state/hwm_history/"
ACCEPTED_OUTCOMES = ("success", "skipped_identical")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current() -> dict:
    return minio_utils.read_json(HWM_KEY) if minio_utils.object_exists(HWM_KEY) else None


def _write(new: dict) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    minio_utils.write_json(new, f"{HISTORY_PREFIX}{stamp}.json")      # history is append-only
    minio_utils.write_json(new, HWM_KEY, overwrite=True)
    return new


def candidate_from_run(run_id: str) -> dict:
    """The newest complaint date (and highest ID) seen by a successful run."""
    log = minio_utils.read_json(f"logs/ingestion/run_id={run_id}.json")
    if log.get("outcome") not in ACCEPTED_OUTCOMES:
        raise ValueError(f"run {run_id} ended with '{log.get('outcome')}': the high-water mark does not move")
    candidate = log.get("high_water_mark_next") or {}
    if not candidate.get("date_received_max") and log.get("run_type") == "full":
        # A same-day rerun of the full load uploads nothing, so take the values from its manifest.
        manifest_key = next((p for p in log.get("raw_paths", []) if p.endswith("manifest.json")), None)
        if manifest_key:
            manifest = minio_utils.read_json(manifest_key)
            candidate = {"date_received_max": manifest.get("max_date_received"),
                         "complaint_id_max": manifest.get("max_complaint_id")}
    if not candidate.get("date_received_max"):
        raise ValueError(f"run {run_id} has no candidate date (high_water_mark_next is missing)")
    date.fromisoformat(candidate["date_received_max"])                  # must be YYYY-MM-DD
    return {"date_received_max": candidate["date_received_max"],
            "complaint_id_max": candidate.get("complaint_id_max"),
            "run_type": log.get("run_type"), "collector": log.get("collector", "python")}


def advance(run_id: str) -> dict:
    """Move the mark forward to the run's candidate. Never moves it backwards."""
    candidate = candidate_from_run(run_id)
    old = current()
    if old and old.get("date_received_max") and candidate["date_received_max"] < old["date_received_max"]:
        print(f"High-water mark kept at {old['date_received_max']} "
              f"(run {run_id} only reached {candidate['date_received_max']})")
        return old
    old_id = (old or {}).get("complaint_id_max")
    new_id = candidate["complaint_id_max"]
    new = {
        "date_received_max": candidate["date_received_max"],
        "complaint_id_max": max(x for x in (old_id, new_id) if x is not None) if (old_id or new_id) else None,
        "run_id": run_id,
        "run_type": candidate["run_type"],
        "collector": candidate["collector"],
        "updated_at": utc_now_iso(),
        "previous_date_received_max": (old or {}).get("date_received_max"),
        "reason": "advanced after a successful collection, Spark run and MongoDB load",
    }
    _write(new)
    print(f"High-water mark: {new['previous_date_received_max']} -> {new['date_received_max']} (run {run_id})")
    return new


def reset(day: str, reason: str) -> dict:
    """Manual reset, for example to collect an older window again. Kept in the history."""
    date.fromisoformat(day)
    old = current()
    new = {
        "date_received_max": day,
        "complaint_id_max": None,
        "run_id": None,
        "run_type": "manual_reset",
        "collector": None,
        "updated_at": utc_now_iso(),
        "previous_date_received_max": (old or {}).get("date_received_max"),
        "reason": reason,
    }
    _write(new)
    print(f"High-water mark reset: {new['previous_date_received_max']} -> {day} ({reason})")
    return new


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Show, advance or reset the high-water mark.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", help="advance from this successful, processed and loaded run")
    group.add_argument("--show", action="store_true", help="print the current high-water mark")
    group.add_argument("--reset", metavar="YYYY-MM-DD", help="set the mark by hand (needs --reason)")
    parser.add_argument("--reason", help="why the mark is reset (stored in the history)")
    args = parser.parse_args(argv)
    try:
        if args.show:
            print(json.dumps(current(), indent=2) if current() else "No high-water mark yet.")
        elif args.reset:
            if not args.reason:
                parser.error("--reset needs --reason")
            reset(args.reset, args.reason)
        else:
            advance(args.run_id)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
