"""Tests for processing/schema.py: both sources map to the same standard input columns."""
from pyspark.sql.types import StringType

from processing import schema


def test_both_mappings_produce_the_same_standard_columns():
    assert sorted(schema.CSV_TO_STANDARD.values()) == sorted(schema.STANDARD_INPUT_COLUMNS)
    assert sorted(schema.API_TO_STANDARD.values()) == sorted(schema.STANDARD_INPUT_COLUMNS)


def test_csv_fixture_maps_to_standard_columns(spark, fixtures_dir):
    raw = schema.read_csv(spark, str(fixtures_dir / "mini_complaints.csv"))
    std = schema.to_standard_columns(raw, schema.CSV_TO_STANDARD)
    assert std.columns == schema.STANDARD_INPUT_COLUMNS
    assert std.count() == 22
    assert all(field.dataType == StringType() for field in std.schema.fields)
    row = std.filter("complaint_id = '9000003'").first()
    assert row.issue == "Managing, opening, or closing your mobile wallet account"   # quoted commas kept
    assert row.timely_response == "Yes"


def test_api_fixture_maps_to_standard_columns(spark, fixtures_dir):
    raw = schema.read_api_pages(spark, str(fixtures_dir / "mini_api_page.json"))
    std = schema.to_standard_columns(raw, schema.API_TO_STANDARD)
    assert std.columns == schema.STANDARD_INPUT_COLUMNS
    assert std.count() == 8
    row = std.filter("complaint_id = '9000005'").first()
    assert row.timely_response == "Yes"                 # API key "timely" renamed
    assert row.date_received.startswith("2024-04-09")


def test_csv_and_api_give_identical_standard_schema(spark, fixtures_dir):
    csv_std = schema.to_standard_columns(
        schema.read_csv(spark, str(fixtures_dir / "mini_complaints.csv")), schema.CSV_TO_STANDARD)
    api_std = schema.to_standard_columns(
        schema.read_api_pages(spark, str(fixtures_dir / "mini_api_page.json")), schema.API_TO_STANDARD)
    assert csv_std.schema == api_std.schema


def test_removed_and_missing_columns_do_not_fail(spark):
    # A CSV without the removed narrative/consent/dispute columns and without "Tags".
    df = spark.createDataFrame(
        [("9000001", "2024-03-15", "CA")], ["Complaint ID", "Date received", "State"])
    std = schema.to_standard_columns(df, schema.CSV_TO_STANDARD)
    assert std.columns == schema.STANDARD_INPUT_COLUMNS
    row = std.first()
    assert row.complaint_id == "9000001" and row.state == "CA" and row.tags is None


def test_curated_schema_matches_the_shared_contract():
    assert [f.name for f in schema.CURATED_SCHEMA.fields] == [
        "complaint_id", "date_received", "date_sent_to_company", "product", "sub_product",
        "product_std", "sub_product_std", "is_core_payment", "issue", "sub_issue", "company",
        "company_public_response", "company_response", "timely_response", "state", "zip_code",
        "tags", "is_older_american", "is_servicemember", "submitted_via", "year", "month",
        "year_month", "processing_lag_days", "source_type", "ingest_run_id", "ingested_at",
    ]
