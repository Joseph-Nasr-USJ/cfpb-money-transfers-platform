
"""Verify that MongoDB complaint upserts are idempotent."""

import os
from uuid import uuid4

import pytest
from pymongo import MongoClient

from database.load import upsert_complaints


class FakeBatch:
    def __init__(self, rows):
        self.rows = rows

    def to_pylist(self):
        return [dict(row) for row in self.rows]


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

    # Use a unique temporary database, never the real project data.
    name = f"cfpb_idempotency_test_{uuid4().hex}"

    try:
        yield client[name]
    finally:
        client.drop_database(name)
        client.close()


def sample_rows():
    return [
        {
            "complaint_id": 1001,
            "date_received": "2026-11-20",
            "issue": "Fraud or scam",
        },
        {
            "complaint_id": 1002,
            "date_received": "2026-11-21",
            "issue": "Other",
        },
    ]


def test_loading_twice_does_not_create_duplicates(db):
    rows = sample_rows()

    assert upsert_complaints(db, FakeScanner(rows)) == 2
    assert db.complaints.count_documents({}) == 2

    # Run the exact same load again.
    assert upsert_complaints(db, FakeScanner(rows)) == 2

    # Two unique complaints must remain.
    assert db.complaints.count_documents({}) == 2


def test_upsert_updates_existing_complaint(db):
    rows = sample_rows()
    upsert_complaints(db, FakeScanner(rows))

    # The source corrects an existing complaint.
    updated = [dict(rows[0])]
    updated[0]["issue"] = "Incorrect information"

    upsert_complaints(db, FakeScanner(updated))

    # Existing document updated, not duplicated.
    assert db.complaints.count_documents({}) == 2

    complaint = db.complaints.find_one({"_id": 1001})
    assert complaint["issue"] == "Incorrect information"
