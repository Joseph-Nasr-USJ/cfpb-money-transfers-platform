"""The curated path contract: one definition shared by the Spark job, the loader and the ML scripts."""
import pytest

from processing import paths


def test_curated_dir_follows_the_option_5_contract():
    assert paths.CURATED_DIR == "curated/complaints/option=5"


def test_partition_folders_have_four_digit_year_and_two_digit_month():
    assert paths.curated_partition(2024, 3) == "curated/complaints/option=5/year=2024/month=03"
    assert paths.curated_partition(2026, 11) == "curated/complaints/option=5/year=2026/month=11"
    with pytest.raises(ValueError):
        paths.curated_partition(2024, 13)


def test_spark_job_and_loader_use_the_same_paths():
    pytest.importorskip("pyarrow")
    pytest.importorskip("pymongo")
    from database import load
    from processing import spark_job

    assert spark_job.CURATED_DIR == load.CURATED_COMPLAINTS == paths.CURATED_DIR
    assert load.AGGREGATE_PATHS == {
        "agg_monthly": spark_job.AGG_MONTHLY_DIR,
        "agg_company_year": spark_job.AGG_COMPANY_YEAR_DIR,
    }
