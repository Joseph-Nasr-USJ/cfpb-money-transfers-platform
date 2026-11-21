
"""Tests for MongoDB complaint identifiers and date types."""

from datetime import date, datetime

import mongomock
import pytest
from pymongo.errors import DuplicateKeyError

from database.load import make_complaint_document


def sample_complaint():
    return {
        "complaint_id": 12345,
        "date_received": date(2026, 11, 20),
        "date_sent_to_company": date(2026, 11, 21),
        "ingested_at": "2026-11-21T12:00:00Z",
        "source_type": "full",
        "ingest_run_id": "test_run",
    }


def test_dates_stored_as_bson_dates():
    complaint_id, document = make_complaint_document(
        sample_complaint()
    )

    db = mongomock.MongoClient().test_database
    db.complaints.insert_one({"_id": complaint_id, **document})

    stored = db.complaints.find_one({"_id": complaint_id})

    assert isinstance(stored["date_received"], datetime)
    assert isinstance(stored["date_sent_to_company"], datetime)
    assert isinstance(stored["ingested_at"], datetime)
    assert stored["date_received"].date() == date(2026, 11, 20)
    assert stored["lineage"]["ingest_run_id"] == "test_run"


def test_duplicate_complaint_id_rejected():
    complaint_id, document = make_complaint_document(
        sample_complaint()
    )

    db = mongomock.MongoClient().test_database
    db.complaints.insert_one({"_id": complaint_id, **document})

    with pytest.raises(DuplicateKeyError):
        db.complaints.insert_one({
            "_id": complaint_id,
            **document,
        })

    assert db.complaints.count_documents({}) == 1
