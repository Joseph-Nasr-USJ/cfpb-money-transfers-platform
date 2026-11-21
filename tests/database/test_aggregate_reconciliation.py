
"""Tests for MongoDB aggregate loading and reconciliation."""

import os
from uuid import uuid4

import pytest
from pymongo import MongoClient

from database import load as mongo_load


class FakeBatch:
    def __init__(self, rows):
        self.rows = rows

    def to_pylist(self):
        return self.rows


class FakeScanner:
    def __init__(self, rows):
        self.rows = rows

    def to_batches(self):
        return [FakeBatch(self.rows)]


@pytest.fixture
def db():
    client = MongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
    )
    client.admin.command("ping")
    name = f"cfpb_aggregate_test_{uuid4().hex}"

    try:
        yield client[name]
    finally:
        client.drop_database(name)
        client.close()


def test_aggregate_totals_match_complaints(db, monkeypatch):
    db.complaints.insert_many([
        {"_id": 1001},
        {"_id": 1002},
        {"_id": 1003},
    ])

    datasets = {
        "monthly": [
            {"year_month": "2026-11", "complaint_count": 2},
            {"year_month": "2026-10", "complaint_count": 1},
        ],
        "company": [
            {"year": 2026, "company": "A", "complaint_count": 2},
            {"year": 2026, "company": "B", "complaint_count": 1},
        ],
    }

    monkeypatch.setattr(
        mongo_load,
        "parquet_scanner",
        lambda fs, path: FakeScanner(datasets[path]),
    )

    curated_count = db.complaints.count_documents({})
    assert curated_count == 3

    for name, path in [
        ("agg_monthly", "monthly"),
        ("agg_company_year", "company"),
    ]:
        staging, row_count, aggregate_total = (
            mongo_load.stage_aggregate(
                db, None, name, path, "test_run"
            )
        )

        assert row_count == 2
        assert aggregate_total == curated_count

        db[staging].rename(name, dropTarget=True)

        totals = list(db[name].aggregate([
            {"$group": {
                "_id": None,
                "total": {"$sum": "$complaint_count"},
            }}
        ]))

        assert totals[0]["total"] == curated_count


def test_invalid_aggregate_count_is_rejected(
    db, monkeypatch
):
    monkeypatch.setattr(
        mongo_load,
        "parquet_scanner",
        lambda fs, path: FakeScanner([
            {"complaint_count": -1}
        ]),
    )

    with pytest.raises(
        ValueError, match="Invalid complaint_count"
    ):
        mongo_load.stage_aggregate(
            db, None, "agg_monthly", "invalid", "test_run"
        )

    assert (
        "agg_monthly_staging_test_run"
        not in db.list_collection_names()
    )
