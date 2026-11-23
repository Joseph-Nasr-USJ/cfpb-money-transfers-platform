
"""Verify that dashboard queries handle empty results safely."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pymongo import MongoClient

from database import queries


QUERY_FUNCTIONS = [
    queries.a1_monthly_volume,
    queries.a2_issue_subissue_share,
    queries.a3_fraud_share,
    queries.a4_channel_share_by_year,
    queries.a5_response_and_timeliness,
    queries.a6_processing_lag_distribution,
    queries.a7_company_cumulative_share,
    queries.a8_state_issue_profile,
]


@pytest.fixture
def db():
    client = MongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
    )
    client.admin.command("ping")
    name = f"cfpb_empty_queries_test_{uuid4().hex}"

    try:
        yield client[name]
    finally:
        client.drop_database(name)
        client.close()


def test_empty_collections_return_empty_lists(db):
    for query_function in QUERY_FUNCTIONS:
        result = query_function(db, {})
        assert result == [], query_function.__name__


def test_impossible_filters_return_empty_lists(db):
    db.complaints.insert_one({
        "_id": 1001,
        "date_received": datetime(
            2026, 11, 20, tzinfo=timezone.utc
        ),
        "year": 2026,
        "sub_product_std": "Domestic money transfer",
        "issue": "Fraud or scam",
        "state": "NY",
        "company": "Example Bank",
        "submitted_via": "Web",
        "is_core_payment": True,
        "processing_lag_days": 1,
    })

    # No complaint exists in the selected state.
    impossible_filter = {"state": ["ZZ"]}

    for query_function in QUERY_FUNCTIONS:
        result = query_function(db, impossible_filter)
        assert result == [], query_function.__name__
