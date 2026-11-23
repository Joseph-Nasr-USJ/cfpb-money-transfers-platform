
"""
Tests for the two required Spark MLlib models.

All data below is synthetic TEST data only.
It must not be interpreted as real CFPB findings.
"""

import pytest

from pyspark.ml.feature import VectorAssembler
from pyspark.sql import SparkSession

from analytics.ml_emerging_issues import (
    fit_issue_model,
    MIN_SLOPE,
    MIN_R2,
    MIN_COMPLAINTS,
)

from analytics.ml_state_clusters import (
    select_best_model,
    RANDOM_SEED,
)


@pytest.fixture(scope="module")
def spark():
    """Create a local Spark session for ML tests."""

    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("cfpb-analytics-ml-tests")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )

    session.sparkContext.setLogLevel("ERROR")

    yield session

    session.stop()


def test_linear_regression_detects_increasing_share(spark):
    """
    Test a clear upward issue-share trend.

    Each month has 100 complaints.
    The issue count rises from 10 to 33.
    Expected slope: 1 percentage point per month.
    """

    monthly_totals = [100] * 24

    monthly_counts = {
        month: 10 + month
        for month in range(24)
    }

    slope, r2 = fit_issue_model(
        spark,
        monthly_counts,
        monthly_totals
    )

    assert slope == pytest.approx(1.0, abs=0.0001)
    assert r2 == pytest.approx(1.0, abs=0.0001)

    complaint_count = sum(monthly_counts.values())

    assert complaint_count >= MIN_COMPLAINTS
    assert slope >= MIN_SLOPE
    assert r2 >= MIN_R2


def test_linear_regression_rejects_flat_share(spark):
    """
    A constant issue share should not be
    considered an increasing trend.
    """

    monthly_totals = [100] * 24

    monthly_counts = {
        month: 20
        for month in range(24)
    }

    slope, r2 = fit_issue_model(
        spark,
        monthly_counts,
        monthly_totals
    )

    assert slope == pytest.approx(0.0, abs=0.0001)
    assert slope < MIN_SLOPE


def test_kmeans_selects_valid_state_clusters(spark):
    """
    Create six artificial state profiles.

    The three profile types are intentionally
    distinct so KMeans can find meaningful groups.

    These values are testing fixtures only.
    """

    rows = [
        ("CA", 150, 0.90, 0.10),
        ("NY", 150, 0.90, 0.10),
        ("TX", 150, 0.10, 0.90),
        ("FL", 150, 0.10, 0.90),
        ("WA", 150, 0.50, 0.50),
        ("OR", 150, 0.50, 0.50),
    ]

    dataframe = spark.createDataFrame(
        rows,
        [
            "state",
            "complaint_count",
            "issue_a_share",
            "issue_b_share",
        ]
    )

    assembler = VectorAssembler(
        inputCols=[
            "issue_a_share",
            "issue_b_share"
        ],
        outputCol="features"
    )

    feature_data = assembler.transform(
        dataframe
    ).select(
        "state",
        "complaint_count",
        "features"
    )

    model, best_k, best_score = select_best_model(
        feature_data
    )

    assert model is not None
    assert best_k in range(2, 7)
    assert best_score is not None
    assert -1 <= best_score <= 1

    predictions = model.transform(
        feature_data
    )

    assert predictions.count() == 6

    cluster_count = (
        predictions
        .select("prediction")
        .distinct()
        .count()
    )

    assert cluster_count == best_k


def test_kmeans_uses_required_seed():
    """Ensure our model remains reproducible."""
    assert RANDOM_SEED == 42
