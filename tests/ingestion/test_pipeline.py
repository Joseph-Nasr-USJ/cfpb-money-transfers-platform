"""Tests for ingestion/pipeline.py: step order, stop on failure, pending runs, retries, lock.

The real steps (spark-submit, database.load, update_hwm) are replaced by a fake runner that
records the commands and returns chosen exit codes, so no Spark or MongoDB is needed.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from ingestion import pipeline


class FakeRunner:
    def __init__(self, fail_on=None, collector_last_line="20261123T020000Z_api"):
        self.calls, self.fail_on, self.collector_last_line = [], fail_on, collector_last_line

    def __call__(self, args):
        self.calls.append(args)
        text = " ".join(args)
        if self.fail_on and self.fail_on in text:
            return 1, "something broke"
        if "ingestion.incremental" in text or "ingestion.historical" in text:
            return 0, self.collector_last_line
        return 0, "ok"

    def steps(self):
        names = []
        for args in self.calls:
            text = " ".join(args)
            names.append("spark" if "spark_job.py" in text else "load" if "database.load" in text
                         else "hwm" if "update_hwm" in text else "collect")
        return names


def put_log(fake_minio, run_id, outcome="success", run_type="api", collector=None):
    log = {"run_id": run_id, "run_type": run_type, "outcome": outcome}
    if collector:
        log["collector"] = collector
    fake_minio.objects[f"logs/ingestion/run_id={run_id}.json"] = json.dumps(log).encode()


def state(fake_minio, run_id):
    return json.loads(fake_minio.objects[f"state/processing/run_id={run_id}.json"])


def test_steps_run_in_order_spark_load_then_high_water_mark(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api", collector="nifi")
    runner = FakeRunner()

    assert pipeline.main(["--mode", "process", "--run-id", "20261123T020000Z_api"], runner) == 0

    assert runner.steps() == ["spark", "load", "hwm"]
    assert runner.calls[0][-4:] == ["--source", "api", "--run-id", "20261123T020000Z_api"]
    done = state(fake_minio, "20261123T020000Z_api")
    assert done["status"] == "done" and done["collector"] == "nifi" and done["attempts"] == 1


def test_full_load_run_uses_the_full_load_source(fake_minio):
    put_log(fake_minio, "20261120T150000Z_full", run_type="full")
    runner = FakeRunner()
    pipeline.main(["--mode", "process", "--run-id", "20261120T150000Z_full"], runner)
    assert runner.calls[0][-4:] == ["--source", "full_load", "--run-id", "20261120T150000Z_full"]


def test_failed_spark_stops_the_chain_before_load_and_high_water_mark(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api")
    runner = FakeRunner(fail_on="spark_job.py")

    assert pipeline.main(["--mode", "process", "--run-id", "20261123T020000Z_api"], runner) == 1

    assert runner.steps() == ["spark"]                         # no load, no high-water mark
    failed = state(fake_minio, "20261123T020000Z_api")
    assert failed["status"] == "failed" and "spark" in failed["error"]


def test_failed_load_stops_before_the_high_water_mark(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api")
    runner = FakeRunner(fail_on="database.load")
    pipeline.main(["--mode", "process", "--run-id", "20261123T020000Z_api"], runner)
    assert runner.steps() == ["spark", "load"]


def test_pending_processes_unprocessed_runs_oldest_first(fake_minio):
    put_log(fake_minio, "20261122T020000Z_api", collector="nifi")
    put_log(fake_minio, "20261121T020000Z_api", collector="nifi")
    put_log(fake_minio, "20261120T020000Z_api", outcome="failed")          # collection failed: ignored
    put_log(fake_minio, "20261119T020000Z_api", outcome="empty")           # nothing collected
    runner = FakeRunner()

    assert pipeline.main(["--mode", "pending"], runner) == 0

    spark_runs = [args[-1] for args in runner.calls if "spark_job.py" in " ".join(args)]
    assert spark_runs == ["20261121T020000Z_api", "20261122T020000Z_api"]
    assert state(fake_minio, "20261119T020000Z_api")["status"] == "skipped_empty"

    runner2 = FakeRunner()
    pipeline.main(["--mode", "pending"], runner2)
    assert runner2.calls == []                                             # nothing processed twice


def test_same_day_identical_full_load_is_not_processed_twice(fake_minio):
    put_log(fake_minio, "20261120T150000Z_full", run_type="full")
    put_log(fake_minio, "20261120T180000Z_full", run_type="full", outcome="skipped_identical")
    runner = FakeRunner()
    pipeline.main(["--mode", "pending"], runner)
    spark_runs = [args[-1] for args in runner.calls if "spark_job.py" in " ".join(args)]
    assert spark_runs == ["20261120T150000Z_full"]


def test_a_failing_run_is_retried_at_most_max_attempts(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api")
    for _ in range(pipeline.MAX_ATTEMPTS):
        assert pipeline.main(["--mode", "pending"], FakeRunner(fail_on="spark_job.py")) == 1
    runner = FakeRunner()
    assert pipeline.main(["--mode", "pending"], runner) == 0
    assert runner.calls == []                                              # left for a person
    assert state(fake_minio, "20261123T020000Z_api")["attempts"] == pipeline.MAX_ATTEMPTS


def test_incremental_mode_collects_with_python_then_processes(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api")                            # what the collector writes
    runner = FakeRunner(collector_last_line="20261123T020000Z_api")

    assert pipeline.main(["--mode", "incremental"], runner) == 0

    assert runner.steps() == ["collect", "spark", "load", "hwm"]
    assert runner.calls[0][-2:] == ["-m", "ingestion.incremental"]


def test_failed_collection_processes_nothing(fake_minio):
    runner = FakeRunner(fail_on="ingestion.incremental")
    assert pipeline.main(["--mode", "incremental"], runner) == 1
    assert runner.steps() == ["collect"]


def test_running_lock_blocks_a_second_chain(fake_minio):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fake_minio.objects["state/pipeline.lock"] = json.dumps({"owner": "scheduler", "acquired_at": now}).encode()
    put_log(fake_minio, "20261123T020000Z_api")
    runner = FakeRunner()

    assert pipeline.main(["--mode", "pending"], runner) == 0

    assert runner.calls == []


def test_abandoned_lock_is_replaced(fake_minio):
    old = (datetime.now(timezone.utc) - timedelta(hours=pipeline.LOCK_STALE_HOURS + 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fake_minio.objects["state/pipeline.lock"] = json.dumps({"owner": "killed container", "acquired_at": old}).encode()
    put_log(fake_minio, "20261123T020000Z_api")
    runner = FakeRunner()
    pipeline.main(["--mode", "pending"], runner)
    assert runner.steps() == ["spark", "load", "hwm"]


def test_lock_is_released_even_after_a_failure(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api")
    pipeline.main(["--mode", "pending"], FakeRunner(fail_on="spark_job.py"))
    assert json.loads(fake_minio.objects["state/pipeline.lock"]).get("released_at")


def test_process_mode_requires_a_run_id(fake_minio):
    with pytest.raises(SystemExit):
        pipeline.main(["--mode", "process"], FakeRunner())
