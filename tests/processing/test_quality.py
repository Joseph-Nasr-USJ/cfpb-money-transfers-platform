"""Tests for processing/quality.py: the quality gate must stop bad data and let clean data through."""
import json
from datetime import datetime, timezone

import pytest
from pyspark.sql import functions as F

from processing import quality as q
from processing import schema
from processing import transforms as t

RUN_ID = "20261116T000000Z_full"
TODAY = datetime(2026, 11, 16, tzinfo=timezone.utc)
DAY_AFTER_LATEST_CSV = datetime(2024, 6, 18, tzinfo=timezone.utc)   # latest CSV fixture date: 2024-06-17


@pytest.fixture(scope="module")
def mapping_df(spark, config_dir):
    return t.read_reference_csv(spark, str(config_dir / "product_mapping.csv"))


@pytest.fixture(scope="module")
def state_codes_df(spark, config_dir):
    return t.read_reference_csv(spark, str(config_dir / "state_codes.csv"))


@pytest.fixture(scope="module")
def csv_std(spark, fixtures_dir):
    raw = schema.read_csv(spark, str(fixtures_dir / "mini_complaints.csv"))
    return t.add_lineage(t.standardise_columns(raw, schema.CSV_TO_STANDARD), "full_load", RUN_ID, "2026-11-16 00:00:00")


@pytest.fixture(scope="module")
def api_std(spark, fixtures_dir):
    raw = schema.read_api_pages(spark, str(fixtures_dir / "mini_api_page.json"))
    return t.add_lineage(t.standardise_columns(raw, schema.API_TO_STANDARD), "api", RUN_ID, "2026-11-16 00:00:00")


def transform(std_df, mapping_df, state_codes_df):
    typed = t.normalise_values(t.parse_dates(std_df))
    in_domain, out_of_domain = t.apply_domain(typed, mapping_df)
    deduped = t.deduplicate(in_domain)
    checked = t.derive_fields(deduped)
    clean, quarantine = t.split_quarantine(checked, state_codes_df)
    return {
        "raw_input": std_df.count(),
        "out_of_domain": out_of_domain.count(),
        "duplicates_removed": in_domain.count() - deduped.count(),
        "checked": checked,
        "clean": clean,
        "quarantine": quarantine,
    }


def report_for(r, source_type="full_load", generated_at=TODAY, **overrides):
    args = {
        "run_id": RUN_ID,
        "source_type": source_type,
        "raw_input": r["raw_input"],
        "out_of_domain": r["out_of_domain"],
        "duplicates_removed": r["duplicates_removed"],
        "checked_df": r["checked"],
        "curated_df": t.conform_to_curated(r["clean"]),
        "quarantine_df": r["quarantine"],
        "generated_at": generated_at,
    }
    args.update(overrides)
    return q.build_quality_report(**args)


def statuses(report, dimension):
    return [c["status"] for c in report["checks"] if c["dimension"] == dimension]


def check(report, dimension, rule_part):
    found = [c for c in report["checks"] if c["dimension"] == dimension and rule_part in c["rule"]]
    assert len(found) == 1, f"expected one {dimension} check containing '{rule_part}'"
    return found[0]


def test_csv_fixture_fails_the_quality_gate(csv_std, mapping_df, state_codes_df):
    # The fixtures contain deliberately bad rows (1 in 19 for each problem, far above 2%),
    # so the gate must stop the run while the counts still reconcile.
    report = report_for(transform(csv_std, mapping_df, state_codes_df))
    assert report["overall_status"] == "FAIL"
    assert report["counts"] == {"raw_input": 22, "out_of_domain": 2, "duplicates_removed": 1, "quarantined": 4, "curated": 15}
    assert report["quarantine_reasons"] == {"null_id": 1, "invalid_date": 1, "invalid_state": 1, "negative_lag": 1}
    assert check(report, "reconciliation", "raw =")["status"] == "PASS"
    assert check(report, "uniqueness", "complaint_id")["status"] == "PASS"
    assert check(report, "completeness", "complaint_id")["status"] == "FAIL"     # 18 of 19 filled
    assert check(report, "completeness", "date_received")["status"] == "FAIL"    # 2024-02-30 became null
    assert check(report, "validity", "dates parse")["status"] == "FAIL"
    assert check(report, "validity", "state")["status"] == "FAIL"
    assert check(report, "validity", "not before")["status"] == "FAIL"
    assert check(report, "validity", "Yes or No")["status"] == "PASS"


def test_api_fixture_counts_and_gate(api_std, mapping_df, state_codes_df):
    report = report_for(transform(api_std, mapping_df, state_codes_df), source_type="api")
    assert report["counts"] == {"raw_input": 8, "out_of_domain": 1, "duplicates_removed": 1, "quarantined": 2, "curated": 4}
    assert check(report, "reconciliation", "raw =")["status"] == "PASS"
    assert report["overall_status"] == "FAIL"


def test_clean_records_pass(csv_std, mapping_df, state_codes_df):
    r = transform(csv_std, mapping_df, state_codes_df)
    clean_only = {
        "raw_input": r["clean"].count(), "out_of_domain": 0, "duplicates_removed": 0,
        "checked": r["clean"], "clean": r["clean"], "quarantine": r["quarantine"].limit(0),
    }
    report = report_for(clean_only, generated_at=DAY_AFTER_LATEST_CSV)
    assert report["overall_status"] == "PASS", [c for c in report["checks"] if c["status"] != "PASS"]


def test_duplicate_ids_fail_uniqueness(csv_std, mapping_df, state_codes_df):
    r = transform(csv_std, mapping_df, state_codes_df)
    curated = t.conform_to_curated(r["clean"])
    duplicated = curated.unionByName(curated.filter(F.col("complaint_id") == 9000001))
    report = report_for(r, curated_df=duplicated)
    uniqueness = check(report, "uniqueness", "complaint_id")
    assert uniqueness["status"] == "FAIL" and uniqueness["metric"]["duplicate_ids"] == 1


def test_reconciliation_fails_when_counts_do_not_add_up(csv_std, mapping_df, state_codes_df):
    r = transform(csv_std, mapping_df, state_codes_df)
    report = report_for(r, raw_input=r["raw_input"] + 1)
    assert check(report, "reconciliation", "raw =")["status"] == "FAIL"
    assert report["overall_status"] == "FAIL"


def test_freshness_warns_on_old_data_and_records_the_ingestion_time(csv_std, mapping_df, state_codes_df):
    r = transform(csv_std, mapping_df, state_codes_df)
    old = report_for(r, generated_at=TODAY)
    assert check(old, "freshness", "latest")["status"] == "WARN"
    assert old["freshness"] == {
        "latest_date_received": "2024-06-17", "ingestion_lag_days": 882, "ingested_at": "2026-11-16 00:00:00",
    }
    recent = report_for(r, generated_at=DAY_AFTER_LATEST_CSV)
    assert check(recent, "freshness", "latest")["status"] == "PASS"
    assert "timeliness_max_age_days" not in old["thresholds"]
    assert old["thresholds"]["freshness_max_age_days"] == 3


def test_empty_sub_issue_is_not_applicable_when_the_issue_has_no_sub_issues(csv_std, mapping_df, state_codes_df):
    # In the fixture no record has a sub-issue, so every empty sub_issue is "not applicable".
    r = transform(csv_std, mapping_df, state_codes_df)
    report = report_for(r)
    split = report["sub_issue_applicability"]
    assert split["applicable"] == 0 and split["missing"] == 0
    assert split["not_applicable"] == split["records"] == r["checked"].count()
    assert report["completeness"]["sub_issue"] == 100.0
    assert check(report, "completeness", "sub_issue")["status"] == "PASS"


def test_empty_sub_issue_is_missing_when_the_same_issue_has_sub_issues(csv_std, mapping_df, state_codes_df):
    # One "Fraud or scam" record gets a sub-issue: the other "Fraud or scam" records become "missing".
    with_sub_issue = csv_std.withColumn(
        "sub_issue",
        F.when(F.col("complaint_id") == "9000001", F.lit("Scam involving a seller")).otherwise(F.col("sub_issue")),
    )
    r = transform(with_sub_issue, mapping_df, state_codes_df)
    fraud = r["checked"].filter(F.col("issue") == "Fraud or scam").count()
    split = report_for(r)["sub_issue_applicability"]
    assert split["applicable"] == fraud and split["filled"] == 1 and split["missing"] == fraud - 1
    assert split["not_applicable"] == split["records"] - fraud


def test_invalid_timely_value_is_counted(csv_std, mapping_df, state_codes_df):
    odd = csv_std.withColumn(
        "timely_response",
        F.when(F.col("complaint_id") == "9000001", F.lit("Maybe")).otherwise(F.col("timely_response")),
    )
    r = transform(odd, mapping_df, state_codes_df)
    report = report_for(r)
    assert check(report, "validity", "Yes or No")["metric"]["invalid"] == 1
    row = r["clean"].filter(F.col("complaint_id") == 9000001).collect()[0]
    assert row.timely_response is None and row.invalid_timely_flag is True


def test_unmapped_sub_product_warns_consistency(csv_std, mapping_df, state_codes_df):
    r = transform(csv_std, mapping_df, state_codes_df)
    curated = t.conform_to_curated(r["clean"]).withColumn(
        "sub_product_std",
        F.when(F.col("complaint_id") == 9000001, F.lit(None).cast("string")).otherwise(F.col("sub_product_std")),
    )
    report = report_for(r, curated_df=curated)
    assert check(report, "consistency", "maps to")["status"] == "WARN"
    assert report["consistency"]["unmapped_combinations"] == [
        {"product": "Money transfer, virtual currency, or money service",
         "sub_product": "Domestic (US) money transfer", "count": 1}
    ]


def test_threshold_rules():
    assert q.validity_status(0.5) == "PASS"
    assert q.validity_status(0.6) == "WARN"
    assert q.validity_status(2.0) == "WARN"
    assert q.validity_status(2.1) == "FAIL"
    assert q.overall_status([{"status": "PASS"}, {"status": "WARN"}]) == "WARN"
    assert q.overall_status([{"status": "WARN"}, {"status": "FAIL"}]) == "FAIL"
    assert q.overall_status([{"status": "PASS"}]) == "PASS"


def test_report_is_valid_json(csv_std, mapping_df, state_codes_df):
    report = report_for(transform(csv_std, mapping_df, state_codes_df))
    parsed = json.loads(q.report_to_json(report))
    assert set(parsed) == {
        "run_id", "generated_at", "source_type", "counts", "quarantine_reasons", "checks",
        "completeness", "sub_issue_applicability", "freshness", "consistency", "thresholds", "overall_status",
    }
    assert {c["dimension"] for c in parsed["checks"]} == {
        "uniqueness", "completeness", "validity", "consistency", "freshness", "reconciliation",
    }
