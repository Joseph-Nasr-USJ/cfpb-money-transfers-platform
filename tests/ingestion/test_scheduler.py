"""Tests for ingestion/scheduler.py: collector choice, catch-up after a missed run, job settings."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from ingestion import scheduler

NOW = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)


def put_log(fake_minio, run_id, started_at, outcome="success"):
    fake_minio.objects[f"logs/ingestion/run_id={run_id}.json"] = json.dumps(
        {"run_id": run_id, "outcome": outcome, "started_at": started_at}).encode()


def test_no_previous_collection_runs_now(fake_minio):
    assert scheduler.first_collection_time(24, NOW) == NOW


def test_missed_run_while_the_computer_was_off_runs_now(fake_minio):
    put_log(fake_minio, "20261121T020000Z_api", "2026-11-21T02:00:00Z")     # 58 hours ago
    assert scheduler.first_collection_time(24, NOW) == NOW


def test_recent_collection_waits_until_it_is_due(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api", "2026-11-23T02:00:00Z")     # 10 hours ago
    assert scheduler.first_collection_time(24, NOW) == datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)


def test_failed_collections_do_not_count_as_done(fake_minio):
    put_log(fake_minio, "20261123T020000Z_api", "2026-11-23T02:00:00Z", outcome="failed")
    assert scheduler.first_collection_time(24, NOW) == NOW


def test_nifi_mode_only_processes_collected_runs(fake_minio, monkeypatch):
    monkeypatch.setenv("COLLECTOR", "nifi")
    jobs = {job.id: job for job in scheduler.build_scheduler().get_jobs()}
    assert set(jobs) == {"process_pending"}


def test_python_mode_also_collects_every_schedule_hours(fake_minio, monkeypatch):
    monkeypatch.setenv("COLLECTOR", "python")
    monkeypatch.setenv("SCHEDULE_HOURS", "24")
    sched = scheduler.build_scheduler(BackgroundScheduler)
    sched.start(paused=True)                    # jobs get their final settings when the scheduler starts
    try:
        jobs = {job.id: job for job in sched.get_jobs()}
        assert set(jobs) == {"process_pending", "python_collection"}
        assert jobs["python_collection"].trigger.interval == timedelta(hours=24)
        assert jobs["python_collection"].coalesce is True                   # missed runs merged into one
        assert jobs["python_collection"].max_instances == 1                 # never two at once
    finally:
        sched.shutdown(wait=False)


def test_unknown_collector_is_refused(fake_minio, monkeypatch):
    monkeypatch.setenv("COLLECTOR", "kafka")
    with pytest.raises(ValueError):
        scheduler.build_scheduler()
