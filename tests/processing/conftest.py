"""Shared pytest fixtures for the Spark processing tests."""
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from processing.transforms import REQUIRED_SPARK_CONF

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
CONFIG = REPO / "config"


@pytest.fixture(scope="session")
def spark():
    """One small local Spark session for the whole test run."""
    builder = (
        SparkSession.builder
        .master("local[1]")
        .appName("cfpb-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
    )
    for key, value in REQUIRED_SPARK_CONF.items():
        builder = builder.config(key, value)
    session = builder.getOrCreate()
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def fixtures_dir():
    return FIXTURES


@pytest.fixture(scope="session")
def config_dir():
    return CONFIG
