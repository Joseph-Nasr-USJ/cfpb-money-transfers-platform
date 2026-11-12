"""Tests for processing/transforms.py on the hand-made fixtures (expected outcomes: tests/fixtures/README.md)."""
import pytest
from pyspark.sql import functions as F

from processing import schema
from processing import transforms as t

RUN_FULL = "20261110T000000Z_full"
RUN_API = "20261112T000000Z_api"
INGESTED_FULL = "2026-11-10 00:00:00"
INGESTED_API = "2026-11-12 00:00:00"


@pytest.fixture(scope="module")
def mapping_df(spark, config_dir):
    return t.read_reference_csv(spark, str(config_dir / "product_mapping.csv"))


@pytest.fixture(scope="module")
def state_codes_df(spark, config_dir):
    return t.read_reference_csv(spark, str(config_dir / "state_codes.csv"))


@pytest.fixture(scope="module")
def csv_std(spark, fixtures_dir):
    raw = schema.read_csv(spark, str(fixtures_dir / "mini_complaints.csv"))
    return t.add_lineage(t.standardise_columns(raw, schema.CSV_TO_STANDARD), "full_load", RUN_FULL, INGESTED_FULL)


@pytest.fixture(scope="module")
def api_std(spark, fixtures_dir):
    raw = schema.read_api_pages(spark, str(fixtures_dir / "mini_api_page.json"))
    return t.add_lineage(t.standardise_columns(raw, schema.API_TO_STANDARD), "api", RUN_API, INGESTED_API)


def run_pipeline(df, mapping_df, state_codes_df):
    typed = t.normalise_values(t.parse_dates(df))
    in_domain, out_of_domain = t.apply_domain(typed, mapping_df)
    deduped = t.deduplicate(in_domain)
    clean, quarantine = t.split_quarantine(t.derive_fields(deduped), state_codes_df)
    return {
        "raw": df.count(),
        "out_of_domain": out_of_domain.count(),
        "duplicates_removed": in_domain.count() - deduped.count(),
        "quarantine": quarantine,
        "clean": clean,
    }


def by_id(df, complaint_id):
    rows = df.filter(F.col("complaint_id") == complaint_id).collect()
    assert len(rows) == 1, f"expected one row for {complaint_id}, got {len(rows)}"
    return rows[0]


def test_standardise_trims_and_nulls_empty_values(csv_std):
    row = by_id(csv_std, "9000022")
    assert row.sub_product == "Mobile or digital wallet"
    assert row.company == "Example Wallet Co."
    assert row.submitted_via == "Web" and row.timely_response == "Yes"
    assert row.zip_code is None                                  # " " became null
    assert by_id(csv_std, "9000005").timely_response is None     # empty became null


def test_parse_dates_handles_both_formats_and_flags_invalid(csv_std, api_std):
    csv = t.parse_dates(csv_std)
    assert str(by_id(csv, "9000007").date_received) == "2024-03-22"     # MM/dd/yy
    assert str(by_id(csv, "9000016").date_received) == "2016-05-10"
    assert by_id(csv, "9000001").invalid_date_flag is False
    bad = by_id(csv, "9000014")
    assert bad.invalid_date_flag is True and bad.date_received is None   # 2024-02-30
    api = t.parse_dates(api_std)
    assert str(by_id(api, "9000101").date_received) == "2024-06-20"     # ISO datetime with offset
    assert by_id(api, "9000103").invalid_date_flag is True


def test_normalise_values_types_and_tags(csv_std):
    df = t.normalise_values(t.parse_dates(csv_std))
    assert dict(df.dtypes)["complaint_id"] == "bigint"
    row = by_id(df, 9000004)
    assert row.timely_response is False
    assert row.tags == ["Older American", "Servicemember"]
    assert row.is_older_american is True and row.is_servicemember is True
    plain = by_id(df, 9000001)
    assert plain.tags == [] and plain.is_older_american is False
    assert by_id(df, 9000005).timely_response is None
    assert df.filter(F.col("complaint_id").isNull()).count() == 1


def test_apply_domain_keeps_current_and_legacy_labels(csv_std, mapping_df):
    typed = t.normalise_values(t.parse_dates(csv_std))
    in_domain, out_of_domain = t.apply_domain(typed, mapping_df)
    assert {r.complaint_id for r in out_of_domain.collect()} == {9000019, 9000020}
    assert in_domain.count() == 20
    current = "Money transfer, virtual currency, or money service"
    assert by_id(in_domain, 9000016).product_std == current
    assert by_id(in_domain, 9000017).sub_product_std == "Virtual currency"
    assert by_id(in_domain, 9000018).sub_product_std == "Mobile or digital wallet"
    assert by_id(in_domain, 9000001).is_core_payment is True
    assert by_id(in_domain, 9000006).is_core_payment is False


def test_deduplicate_prefers_closed_record(csv_std, mapping_df):
    typed = t.normalise_values(t.parse_dates(csv_std))
    in_domain, _ = t.apply_domain(typed, mapping_df)
    deduped = t.deduplicate(in_domain)
    assert deduped.count() == 19
    assert by_id(deduped, 9000012).company_response == "Closed with explanation"
    assert deduped.filter(F.col("complaint_id").isNull()).count() == 1   # null IDs are not merged


def test_deduplicate_latest_ingestion_and_api_win(csv_std, api_std, mapping_df):
    both = csv_std.unionByName(api_std)
    in_domain, _ = t.apply_domain(t.normalise_values(t.parse_dates(both)), mapping_df)
    row = by_id(t.deduplicate(in_domain), 9000005)
    assert row.source_type == "api" and row.timely_response is True
    # Same ingestion time: the API record still wins over the full load.
    same_time = csv_std.unionByName(api_std.withColumn("ingested_at", F.to_timestamp(F.lit(INGESTED_FULL))))
    in_domain, _ = t.apply_domain(t.normalise_values(t.parse_dates(same_time)), mapping_df)
    assert by_id(t.deduplicate(in_domain), 9000005).source_type == "api"


def test_derive_fields(csv_std):
    df = t.derive_fields(t.normalise_values(t.parse_dates(csv_std)))
    row = by_id(df, 9000002)
    assert (row.year, row.month, row.year_month, row.processing_lag_days) == (2024, 3, "2024-03", 2)
    assert by_id(df, 9000015).processing_lag_days == -5


def test_split_quarantine_reasons(csv_std, mapping_df, state_codes_df):
    result = run_pipeline(csv_std, mapping_df, state_codes_df)
    reasons = {r.complaint_id: r.reject_reason for r in result["quarantine"].collect()}
    assert reasons == {
        None: "null_id",
        9000011: "invalid_state",
        9000014: "invalid_date",
        9000015: "negative_lag",
    }
    assert by_id(result["clean"], 9000010).state is None                 # empty state kept by default


def test_empty_state_can_be_quarantined(csv_std, mapping_df, state_codes_df):
    typed = t.derive_fields(t.normalise_values(t.parse_dates(csv_std)))
    _, quarantine = t.split_quarantine(typed, state_codes_df, quarantine_empty_state=True)
    assert by_id(quarantine, 9000010).reject_reason == "missing_state"


def test_csv_counts_balance(csv_std, mapping_df, state_codes_df):
    r = run_pipeline(csv_std, mapping_df, state_codes_df)
    counts = (r["clean"].count(), r["quarantine"].count(), r["out_of_domain"], r["duplicates_removed"])
    assert counts == (15, 4, 2, 1)
    assert sum(counts) == r["raw"] == 22


def test_api_counts_balance(api_std, mapping_df, state_codes_df):
    r = run_pipeline(api_std, mapping_df, state_codes_df)
    counts = (r["clean"].count(), r["quarantine"].count(), r["out_of_domain"], r["duplicates_removed"])
    assert counts == (4, 2, 1, 1)
    assert sum(counts) == r["raw"] == 8


def test_conform_to_curated_matches_schema(csv_std, api_std, mapping_df, state_codes_df):
    csv_out = t.conform_to_curated(run_pipeline(csv_std, mapping_df, state_codes_df)["clean"])
    api_out = t.conform_to_curated(run_pipeline(api_std, mapping_df, state_codes_df)["clean"])
    expected = [(f.name, f.dataType) for f in schema.CURATED_SCHEMA.fields]
    assert [(f.name, f.dataType) for f in csv_out.schema.fields] == expected
    assert [(f.name, f.dataType) for f in api_out.schema.fields] == expected


def test_product_mapping_has_no_ambiguous_rows(mapping_df):
    rows = mapping_df.collect()
    wildcard_products = {r.source_product for r in rows if r.source_sub_product == t.WILDCARD}
    exact_products = {r.source_product for r in rows if r.source_sub_product != t.WILDCARD}
    assert not (wildcard_products & exact_products)
