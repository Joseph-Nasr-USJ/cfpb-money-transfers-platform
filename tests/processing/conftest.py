"""Shared pytest fixtures for the Spark processing tests."""
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="session")
def spark():
    """One small local Spark session for the whole test run."""
    session = (
        SparkSession.builder
        .master("local[1]")
        .appName("cfpb-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def fixtures_dir():
    return FIXTURES
