"""End-to-end tests for processing/spark_job.py on the fixtures, with a local folder as the data lake."""
import json

import pytest

from processing import paths
from processing import schema
from processing import spark_job as job

RUN_FULL = "20261110T000000Z_full"
RUN_API = "20261112T000000Z_api"


@pytest.fixture
def lake(tmp_path):
    return str(tmp_path / "lake")


def curated(spark, lake):
    path = f"{lake}/{job.CURATED_DIR}"
    return spark.read.schema(schema.CURATED_SCHEMA).option("basePath", path).parquet(path)


def read_report(lake, run_id):
    with open(f"{lake}/quality/run_id={run_id}/quality_report.json", encoding="utf-8") as handle:
        return json.load(handle)


def test_parse_run_id():
    assert job.parse_run_id(RUN_FULL, "full_load") == ("2026-11-10", "2026-11-10 00:00:00")
    assert job.parse_run_id("20261112T020500Z_api", "api") == ("2026-11-12", "2026-11-12 02:05:00")
    with pytest.raises(ValueError):
        job.parse_run_id(RUN_FULL, "api")                 # suffix does not match the source
    with pytest.raises(ValueError):
        job.parse_run_id("2026-11-10_full", "full_load")  # wrong format


def test_wrong_arguments_exit_with_code_2():
    assert job.main(["--source", "api", "--run-id", RUN_FULL]) == 2


def test_quality_gate_failure_writes_evidence_but_no_curated_data(spark, fixtures_dir, lake):
    code, report = job.run(spark, "full_load", RUN_FULL, str(fixtures_dir / "mini_complaints.csv"), lake)
    assert code == 1
    assert read_report(lake, RUN_FULL)["quality_gate"] == "stopped"
    assert spark.read.parquet(f"{lake}/quarantine/run_id={RUN_FULL}").count() == 4
    assert not job.path_exists(spark, f"{lake}/curated")


def test_full_load_writes_curated_aggregates_and_report(spark, fixtures_dir, lake):
    code, report = job.run(spark, "full_load", RUN_FULL, str(fixtures_dir / "mini_complaints.csv"), lake,
                           ignore_quality_gate=True)
    assert code == 0
    df = curated(spark, lake)
    assert df.count() == 15
    assert set(df.columns) == {f.name for f in schema.CURATED_SCHEMA.fields}
    assert job.CURATED_DIR == "curated/complaints/option=5"
    assert job.path_exists(spark, f"{lake}/{paths.curated_partition(2024, 3)}")     # month=03
    assert not job.path_exists(spark, f"{lake}/{job.CURATED_DIR}/year=2024/month=3")
    assert {row.month for row in df.select("month").distinct().collect()} <= set(range(1, 13))
    assert not job.path_exists(spark, f"{lake}/curated/_staging")
    monthly = spark.read.parquet(f"{lake}/{job.AGG_MONTHLY_DIR}")
    company = spark.read.parquet(f"{lake}/{job.AGG_COMPANY_YEAR_DIR}")
    assert monthly.groupBy().sum("complaint_count").collect()[0][0] == 15
    assert company.groupBy().sum("complaint_count").collect()[0][0] == 15
    saved = read_report(lake, RUN_FULL)
    assert saved["quality_gate"] == "overridden"
    assert saved["counts"] == {"raw_input": 22, "out_of_domain": 2, "duplicates_removed": 1, "quarantined": 4, "curated": 15}
    assert saved["curated_snapshot"] == {"total_records": 15, "distinct_complaint_ids": 15}


def test_api_run_merges_with_curated_and_rerun_changes_nothing(spark, fixtures_dir, lake):
    job.run(spark, "full_load", RUN_FULL, str(fixtures_dir / "mini_complaints.csv"), lake, ignore_quality_gate=True)
    api_input = str(fixtures_dir / "mini_api_page.json")
    code, report = job.run(spark, "api", RUN_API, api_input, lake, ignore_quality_gate=True)
    assert code == 0
    df = curated(spark, lake)
    # 15 from the CSV + 4 from the API, minus 9000005 which the API updates
    assert df.count() == 18
    updated = df.filter("complaint_id = 9000005").collect()
    assert len(updated) == 1 and updated[0].source_type == "api" and updated[0].timely_response is True

    # Idempotency: the same run again leaves curated data and aggregates unchanged
    code, report = job.run(spark, "api", RUN_API, api_input, lake, ignore_quality_gate=True)
    assert code == 0
    assert report["curated_snapshot"] == {"total_records": 18, "distinct_complaint_ids": 18}
    monthly = spark.read.parquet(f"{lake}/{job.AGG_MONTHLY_DIR}")
    assert monthly.groupBy().sum("complaint_count").collect()[0][0] == 18


def test_missing_input(spark, lake):
    assert job.run(spark, "api", "20261113T000000Z_api", None, lake) == (0, None)        # empty API window
    assert job.run(spark, "full_load", "20261113T000000Z_full", None, lake) == (1, None)  # no raw CSV
