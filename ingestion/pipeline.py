"""Processing chain: collection run -> Spark job -> MongoDB load -> high-water mark.

Usage (inside the pipeline container):
    python -m ingestion.pipeline --mode pending        process every collected run not processed yet
                                                      (how NiFi runs reach Spark and MongoDB)
    python -m ingestion.pipeline --mode incremental    Python fallback: collect from the API, then process
    python -m ingestion.pipeline --mode full           Python historical load, then process
    python -m ingestion.pipeline --mode process --run-id <run_id>     process one given run
Also: make pipeline-full, make pipeline-incremental.

Rules:
- The steps run in order and the chain stops at the first failure (non-zero exit code): the
  high-water mark therefore moves only after Spark AND the load succeeded.
- NiFi and the Python collectors write the same run log (logs/ingestion/run_id=<id>.json), so this
  chain does not care which collector produced a run.
- Each run's processing status is kept in state/processing/run_id=<id>.json. A run that fails is
  retried by the next pass, at most MAX_ATTEMPTS times, then left for a person to investigate.
- A lock (state/pipeline.lock) prevents two chains from running at the same time, for example the
  scheduler and a manual "make pipeline-incremental". A lock older than LOCK_STALE_HOURS is
  considered abandoned (container killed) and replaced.
- A run that collected nothing ("empty") is recorded and not sent to Spark.
"""
import argparse
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from ingestion import minio_utils

LOG_PREFIX = "logs/ingestion/"
STATE_PREFIX = "state/processing/"
LOCK_KEY = "state/pipeline.lock"
MAX_ATTEMPTS = 3
LOCK_STALE_HOURS = 6
SOURCE_BY_RUN_TYPE = {"full": "full_load", "api": "api"}


class PipelineError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def run_command(args: list) -> tuple:
    """Run one step, streaming its output; return (exit code, last output line)."""
    print(f"$ {' '.join(args)}", flush=True)
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    last = ""
    for line in process.stdout:
        print(line, end="", flush=True)
        if line.strip():
            last = line.strip()
    return process.wait(), last


# ---------------------------------------------------------------- lock

def acquire_lock(owner: str) -> bool:
    lock = minio_utils.read_json(LOCK_KEY) if minio_utils.object_exists(LOCK_KEY) else None
    if lock and not lock.get("released_at"):
        taken = datetime.strptime(lock["acquired_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if utc_now() - taken < timedelta(hours=LOCK_STALE_HOURS):
            print(f"Another chain is running ({lock['owner']} since {lock['acquired_at']}): nothing done.")
            return False
        print(f"Replacing an abandoned lock from {lock['acquired_at']}")
    minio_utils.write_json({"owner": owner, "acquired_at": iso(utc_now())}, LOCK_KEY, overwrite=True)
    return True


def release_lock() -> None:
    lock = minio_utils.read_json(LOCK_KEY)
    lock["released_at"] = iso(utc_now())
    minio_utils.write_json(lock, LOCK_KEY, overwrite=True)


# ---------------------------------------------------------------- processing state

def state_key(run_id: str) -> str:
    return f"{STATE_PREFIX}run_id={run_id}.json"


def read_state(run_id: str) -> dict:
    key = state_key(run_id)
    return minio_utils.read_json(key) if minio_utils.object_exists(key) else {"run_id": run_id, "attempts": 0}


def save_state(state: dict) -> None:
    minio_utils.write_json(state, state_key(state["run_id"]), overwrite=True)


def process_run(run_id: str, runner=run_command) -> dict:
    """Spark -> load -> high-water mark for one collected run."""
    log = minio_utils.read_json(f"{LOG_PREFIX}run_id={run_id}.json")
    state = read_state(run_id)
    if log.get("outcome") == "empty":
        state.update(status="skipped_empty", finished_at=iso(utc_now()))
        save_state(state)
        print(f"[{run_id}] collected nothing: not sent to Spark")
        return state
    if log.get("outcome") not in ("success", "skipped_identical"):
        raise PipelineError(f"run {run_id} ended with '{log.get('outcome')}': cannot be processed")
    source = SOURCE_BY_RUN_TYPE[log["run_type"]]
    state.update(status="running", attempts=state["attempts"] + 1, started_at=iso(utc_now()),
                 collector=log.get("collector", "python"), steps=[], error=None)
    save_state(state)
    steps = [
        ("spark", ["spark-submit", "processing/spark_job.py", "--source", source, "--run-id", run_id]),
        ("load", [sys.executable, "-m", "database.load", "--run-id", run_id]),
        ("high_water_mark", [sys.executable, "-m", "ingestion.update_hwm", "--run-id", run_id]),
    ]
    for name, args in steps:
        code, last = runner(args)
        state["steps"].append({"step": name, "exit_code": code, "finished_at": iso(utc_now())})
        if code != 0:
            state.update(status="failed", error=f"step '{name}' exited with {code}: {last}",
                         finished_at=iso(utc_now()))
            save_state(state)
            raise PipelineError(f"[{run_id}] {state['error']} (attempt {state['attempts']} of {MAX_ATTEMPTS})")
        save_state(state)
    state.update(status="done", finished_at=iso(utc_now()))
    save_state(state)
    print(f"[{run_id}] processed and loaded")
    return state


def pending_runs() -> list:
    """Collected runs (oldest first) that still need processing."""
    todo = []
    for key in minio_utils.list_keys(LOG_PREFIX):
        if not key.endswith(".json"):
            continue
        run_id = key[len(LOG_PREFIX) + len("run_id="):-len(".json")]
        state = read_state(run_id)
        if state.get("status") in ("done", "skipped_empty", "skipped_duplicate_file"):
            continue
        if state.get("attempts", 0) >= MAX_ATTEMPTS:
            print(f"[{run_id}] failed {state['attempts']} times: left for investigation ({state.get('error')})")
            continue
        log = minio_utils.read_json(key)
        if log.get("outcome") == "skipped_identical":
            state.update(status="skipped_duplicate_file", finished_at=iso(utc_now()))
            save_state(state)                       # the original run of that day carries the file
            continue
        if log.get("outcome") in ("success", "empty"):
            todo.append(run_id)
    return sorted(todo)                             # run_ids start with a UTC timestamp


def process_pending(runner=run_command) -> int:
    runs = pending_runs()
    if not runs:
        print("No collected run waiting for processing.")
        return 0
    for run_id in runs:                             # in order, so the high-water mark only moves forward
        process_run(run_id, runner)
    return 0


def collect(module: str, runner=run_command) -> str:
    code, last = runner([sys.executable, "-m", module])
    if code != 0:
        raise PipelineError(f"collection with {module} failed (exit {code}); run_id {last}")
    return last                                     # the collectors print the run_id last


def main(argv=None, runner=run_command) -> int:
    parser = argparse.ArgumentParser(description="Run the processing chain after a collection.")
    parser.add_argument("--mode", required=True, choices=["pending", "incremental", "full", "process"])
    parser.add_argument("--run-id", help="with --mode process: the run to process")
    args = parser.parse_args(argv)
    if args.mode == "process" and not args.run_id:
        parser.error("--mode process needs --run-id")
    owner = f"{socket.gethostname()} pid {os.getpid()} mode {args.mode}"
    if not acquire_lock(owner):
        return 0
    try:
        if args.mode == "pending":
            return process_pending(runner)
        if args.mode == "process":
            process_run(args.run_id, runner)
            return 0
        run_id = collect("ingestion.incremental" if args.mode == "incremental" else "ingestion.historical", runner)
        process_run(run_id, runner)
        return 0
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
