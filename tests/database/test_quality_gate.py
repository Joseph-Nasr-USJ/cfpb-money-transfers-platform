"""Contract tests for the MongoDB loader's Spark quality gate.

These tests verify the decision before any database connection is opened.
No MinIO or MongoDB data is read or changed.
"""

import pytest

from database import load as loader


RUN_ID = "20261121T120000Z_api"


def _mock_run_metadata(monkeypatch, quality_gate, overall_status):
    """Supply valid run metadata without connecting to MinIO."""
    monkeypatch.setattr(loader, "get_filesystem", lambda: object())

    def fake_read_json_object(_filesystem, path):
        if path == f"logs/ingestion/run_id={RUN_ID}.json":
            return {"run_id": RUN_ID, "outcome": "success"}
        if path == f"quality/run_id={RUN_ID}/quality_report.json":
            return {
                "run_id": RUN_ID,
                "quality_gate": quality_gate,
                "overall_status": overall_status,
            }
        raise AssertionError(f"Unexpected MinIO object path: {path}")

    monkeypatch.setattr(loader, "read_json_object", fake_read_json_object)


def test_stopped_quality_gate_aborts_before_mongodb(monkeypatch):
    # An apparently passing overall status must not override a stopped gate.
    _mock_run_metadata(monkeypatch, "stopped", "PASS")

    def forbid_connection(*_args, **_kwargs):
        raise AssertionError("MongoDB must not be contacted for a stopped run")

    monkeypatch.setattr(loader, "MongoClient", forbid_connection)

    with pytest.raises(ValueError, match="quality gate stopped"):
        loader.load(RUN_ID)


@pytest.mark.parametrize(
    ("quality_gate", "overall_status"),
    [
        ("passed", "PASS"),
        ("overridden", "FAIL"),
    ],
)
def test_allowed_quality_gates_reach_mongodb(monkeypatch, quality_gate, overall_status):
    _mock_run_metadata(monkeypatch, quality_gate, overall_status)

    class ConnectionReached(Exception):
        """Signal that the quality gate allowed loading to proceed."""

    def stop_at_connection(*_args, **_kwargs):
        raise ConnectionReached

    monkeypatch.setattr(loader, "MongoClient", stop_at_connection)

    with pytest.raises(ConnectionReached):
        loader.load(RUN_ID)
