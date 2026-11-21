
"""Tests for MongoDB ML result readers."""

import mongomock
import pytest

from database.queries import ml_emerging_issues, ml_state_clusters


@pytest.fixture
def db():
    return mongomock.MongoClient().cfpb


def test_empty_collections(db):
    assert ml_emerging_issues(db, {}) == []
    assert ml_state_clusters(db) == []


def test_emerging_issues_filters(db):
    db.ml_emerging_issues.insert_many([
        {
            "_id": "1",
            "sub_product_std": "Domestic money transfer",
            "issue": "Fraud or scam",
            "slope_pp_per_month": 0.3,
        },
        {
            "_id": "2",
            "sub_product_std": "International money transfer",
            "issue": "Other",
            "slope_pp_per_month": 0.1,
        },
    ])

    results = ml_emerging_issues(
        db,
        {
            "sub_product_std": ["Domestic money transfer"],
            "issue": ["Fraud or scam"],
        },
    )

    assert len(results) == 1
    assert results[0]["issue"] == "Fraud or scam"
    assert results[0]["slope_pp_per_month"] == 0.3
    assert "_id" not in results[0]


def test_state_clusters(db):
    db.ml_state_clusters.insert_many([
        {"_id": "NY", "state": "NY", "cluster": 1},
        {"_id": "CA", "state": "CA", "cluster": 0},
    ])

    results = ml_state_clusters(db)

    assert len(results) == 2
    assert [row["state"] for row in results] == ["CA", "NY"]
    assert "_id" not in results[0]


def test_unsupported_filter(db):
    with pytest.raises(ValueError, match="Unsupported filters"):
        ml_emerging_issues(db, {"company": ["Example Bank"]})
