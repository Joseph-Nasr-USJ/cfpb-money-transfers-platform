"""Tests for ingestion/update_hwm.py: the high-water mark moves only forward, from successful runs."""
import json

import pytest

from ingestion import update_hwm


def put_log(fake_minio, run_id, **fields):
    log = {"run_id": run_id, "run_type": "api", "outcome": "success",
           "high_water_mark_next": {"date_received_max": "2026-11-18", "complaint_id_max": 30700000}}
    log.update(fields)
    fake_minio.objects[f"logs/ingestion/run_id={run_id}.json"] = json.dumps(log).encode()


def hwm(fake_minio):
    return json.loads(fake_minio.objects["state/high_water_mark.json"])


def test_first_successful_run_creates_the_mark(fake_minio):
    put_log(fake_minio, "20261120T160927Z_api")

    update_hwm.advance("20261120T160927Z_api")

    mark = hwm(fake_minio)
    assert mark["date_received_max"] == "2026-11-18" and mark["run_id"] == "20261120T160927Z_api"
    assert mark["previous_date_received_max"] is None
    assert any(k.startswith("state/hwm_history/") for k in fake_minio.objects)      # history kept


def test_mark_moves_forward(fake_minio):
    put_log(fake_minio, "20261120T000000Z_api")
    update_hwm.advance("20261120T000000Z_api")
    put_log(fake_minio, "20261121T000000Z_api",
            high_water_mark_next={"date_received_max": "2026-11-20", "complaint_id_max": 30710000})

    update_hwm.advance("20261121T000000Z_api")

    assert hwm(fake_minio)["date_received_max"] == "2026-11-20"
    assert hwm(fake_minio)["previous_date_received_max"] == "2026-11-18"


def test_mark_never_moves_backwards(fake_minio):
    put_log(fake_minio, "20261121T000000Z_api",
            high_water_mark_next={"date_received_max": "2026-11-20", "complaint_id_max": 30710000})
    update_hwm.advance("20261121T000000Z_api")
    put_log(fake_minio, "20261122T000000Z_api",                       # e.g. a rerun of an older window
            high_water_mark_next={"date_received_max": "2026-11-10", "complaint_id_max": 30600000})

    update_hwm.advance("20261122T000000Z_api")

    assert hwm(fake_minio)["date_received_max"] == "2026-11-20"


@pytest.mark.parametrize("outcome", ["failed", "empty", "running"])
def test_unsuccessful_runs_do_not_move_the_mark(fake_minio, outcome):
    put_log(fake_minio, "20261120T000000Z_api", outcome=outcome)
    with pytest.raises(ValueError):
        update_hwm.advance("20261120T000000Z_api")
    assert "state/high_water_mark.json" not in fake_minio.objects
    assert update_hwm.main(["--run-id", "20261120T000000Z_api"]) == 1


def test_same_day_full_rerun_takes_values_from_the_manifest(fake_minio):
    manifest = "raw/cfpb/full_load/ingest_date=2026-11-20/manifest.json"
    fake_minio.objects[manifest] = json.dumps({"max_date_received": "2026-11-19", "max_complaint_id": 30705000}).encode()
    put_log(fake_minio, "20261120T180000Z_full", run_type="full", outcome="skipped_identical",
            high_water_mark_next=None, raw_paths=[manifest])

    update_hwm.advance("20261120T180000Z_full")

    assert hwm(fake_minio)["date_received_max"] == "2026-11-19"


def test_manual_reset_is_recorded_with_its_reason(fake_minio, capsys):
    put_log(fake_minio, "20261121T000000Z_api")
    update_hwm.advance("20261121T000000Z_api")

    assert update_hwm.main(["--reset", "2026-11-01", "--reason", "collect November again for the demo"]) == 0

    mark = hwm(fake_minio)
    assert mark["date_received_max"] == "2026-11-01" and mark["run_type"] == "manual_reset"
    assert mark["previous_date_received_max"] == "2026-11-18"
    assert mark["reason"] == "collect November again for the demo"
    assert update_hwm.main(["--show"]) == 0 and "2026-11-01" in capsys.readouterr().out


def test_reset_without_reason_is_refused(fake_minio):
    with pytest.raises(SystemExit):
        update_hwm.main(["--reset", "2026-11-01"])
