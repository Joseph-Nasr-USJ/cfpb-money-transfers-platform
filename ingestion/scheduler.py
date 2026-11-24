"""Scheduler of the pipeline container (its default command): keeps the platform up to date.

Two collectors exist, chosen with COLLECTOR in .env:
- COLLECTOR=nifi (default): Apache NiFi collects from the CFPB API on its own schedule and writes
  raw pages and a run log to MinIO. This scheduler only checks every PENDING_CHECK_MINUTES for
  collected runs that are not processed yet, and sends them through Spark, the load and the
  high-water mark (python -m ingestion.pipeline --mode pending).
- COLLECTOR=python (fallback, when NiFi is not available): this scheduler also runs the Python
  collector every SCHEDULE_HOURS (python -m ingestion.pipeline --mode incremental).

If the computer was off at the scheduled time, the run is not lost: at start-up the scheduler
looks at the last successful collection, and if it is older than SCHEDULE_HOURS it collects at once.
Missed runs are merged into one (coalesce) and two runs never overlap (max_instances=1, plus the
lock in ingestion.pipeline). Nothing is lost by a late run: the window starts from the
high-water mark minus OVERLAP_DAYS, whatever the date.

Usage: python -m ingestion.scheduler        (started by "make up"; logs: docker compose logs pipeline)
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from ingestion import minio_utils, pipeline

LOG_PREFIX = "logs/ingestion/"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def last_successful_collection(run_type: str = "api"):
    """Start time of the newest successful collection of that type, or None."""
    newest = None
    for key in minio_utils.list_keys(LOG_PREFIX):
        if not key.endswith(f"_{run_type}.json"):
            continue
        log = minio_utils.read_json(key)
        if log.get("outcome") in ("success", "empty") and log.get("started_at"):
            started = datetime.strptime(log["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            newest = started if newest is None or started > newest else newest
    return newest


def first_collection_time(schedule_hours: float, now: datetime = None):
    """Now if the last successful collection is too old (missed run), else when it is next due."""
    now = now or utc_now()
    last = last_successful_collection("api")
    if last is None or now - last >= timedelta(hours=schedule_hours):
        return now
    return last + timedelta(hours=schedule_hours)


def run_pending() -> None:
    try:
        pipeline.main(["--mode", "pending"])
    except Exception as exc:                 # a failed pass is logged; the next pass tries again
        print(f"Processing pass failed: {exc}", file=sys.stderr, flush=True)


def run_python_collection() -> None:
    try:
        pipeline.main(["--mode", "incremental"])
    except Exception as exc:
        print(f"Python collection failed: {exc}", file=sys.stderr, flush=True)


def build_scheduler(scheduler_class=BlockingScheduler):
    collector = os.environ.get("COLLECTOR", "nifi").strip().lower()
    schedule_hours = float(os.environ.get("SCHEDULE_HOURS", "24"))
    check_minutes = float(os.environ.get("PENDING_CHECK_MINUTES", "15"))
    if collector not in ("nifi", "python"):
        raise ValueError(f"COLLECTOR must be 'nifi' or 'python', not {collector!r}")
    scheduler = scheduler_class(timezone="UTC", job_defaults={"coalesce": True, "max_instances": 1})
    scheduler.add_job(run_pending, "interval", minutes=check_minutes, next_run_time=utc_now(),
                      id="process_pending", name="process collected runs")
    if collector == "python":
        scheduler.add_job(run_python_collection, "interval", hours=schedule_hours,
                          next_run_time=first_collection_time(schedule_hours),
                          id="python_collection", name="Python fallback collection")
    print(f"Scheduler started: COLLECTOR={collector}, processing check every {check_minutes:g} min"
          + (f", Python collection every {schedule_hours:g} h" if collector == "python" else
             ", collection by NiFi"), flush=True)
    return scheduler


def main() -> int:
    build_scheduler().start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
