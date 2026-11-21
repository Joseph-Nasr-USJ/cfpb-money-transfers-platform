"""Data-quality report for one Spark run: six dimensions, fixed thresholds, one overall status.

The thresholds below were fixed before looking at any results (team plan, quality thresholds).
spark_job.py builds the report after the transforms and stops with exit code 1 when
overall_status is FAIL (the quality gate).

Inputs (all produced by processing/transforms.py):
    checked_df    in-domain records after deduplication and derive_fields, BEFORE quarantine
    curated_df    clean records conformed to CURATED_SCHEMA
    quarantine_df rejected records with their reject_reason
"""
import json
from datetime import datetime, timezone

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

THRESHOLDS = {
    "uniqueness_max_problems": 0,          # null or duplicate complaint_id in curated data
    "completeness_required_min_pct": 99.5,  # required fields filled
    "validity_warn_above_pct": 0.5,         # invalid records per rule
    "validity_fail_above_pct": 2.0,
    "timeliness_max_age_days": 3,           # age of the latest date_received
}

REQUIRED_FIELDS = ["complaint_id", "date_received", "product", "issue", "company"]
OPTIONAL_FIELDS = [
    "date_sent_to_company", "sub_product", "sub_issue", "company_public_response",
    "company_response", "timely_response", "state", "zip_code", "submitted_via",
]
# Optional fields the CFPB leaves mostly or fully empty for our product: reported, never a warning.
EXPECTED_SPARSE_FIELDS = {"sub_issue", "company_public_response"}
VALIDITY_RULES = {
    "invalid_date": "dates parse (yyyy-MM-dd, MM/dd/yyyy, MM/dd/yy) and are real calendar dates",
    "invalid_timely": "timely response is Yes or No",
    "invalid_state": "state is in config/state_codes.csv",
    "negative_lag": "date sent to company is not before date received",
}

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 3) if total else 0.0


def validity_status(invalid_pct: float) -> str:
    if invalid_pct > THRESHOLDS["validity_fail_above_pct"]:
        return FAIL
    if invalid_pct > THRESHOLDS["validity_warn_above_pct"]:
        return WARN
    return PASS


def overall_status(checks: list) -> str:
    statuses = {c["status"] for c in checks}
    if FAIL in statuses:
        return FAIL
    if WARN in statuses:
        return WARN
    return PASS


def _check(dimension: str, rule: str, metric, threshold: str, status: str) -> dict:
    return {"dimension": dimension, "rule": rule, "metric": metric, "threshold": threshold, "status": status}


def _quarantine_reason_counts(quarantine_df: DataFrame) -> dict:
    rows = (
        quarantine_df.select(F.explode(F.split("reject_reason", ";")).alias("reason"))
        .groupBy("reason").count().collect()
    )
    return {r["reason"]: r["count"] for r in rows}


def build_quality_report(
    run_id: str,
    source_type: str,
    raw_input: int,
    out_of_domain: int,
    duplicates_removed: int,
    checked_df: DataFrame,
    curated_df: DataFrame,
    quarantine_df: DataFrame,
    generated_at: datetime = None,
) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc)
    checks = []

    # One pass over the checked records: total, filled values per field, invalid timely values.
    filled = [F.count(F.col(f)).alias(f) for f in REQUIRED_FIELDS + OPTIONAL_FIELDS]
    stats = checked_df.agg(
        F.count(F.lit(1)).alias("_total"),
        F.sum(F.col("invalid_timely_flag").cast("int")).alias("_invalid_timely"),
        *filled,
    ).collect()[0]
    checked_total = stats["_total"]

    cur = curated_df.agg(
        F.count(F.lit(1)).alias("rows"),
        F.countDistinct("complaint_id").alias("distinct_ids"),
        F.sum(F.col("complaint_id").isNull().cast("int")).alias("null_ids"),
        F.max("date_received").alias("latest"),
    ).collect()[0]
    curated = cur["rows"]
    quarantined = quarantine_df.count()
    reasons = _quarantine_reason_counts(quarantine_df) if quarantined else {}

    # 1. Uniqueness (curated data)
    null_ids = cur["null_ids"] or 0
    duplicate_ids = curated - null_ids - cur["distinct_ids"]
    uniqueness_problems = null_ids + duplicate_ids
    checks.append(_check(
        "uniqueness", "complaint_id is not null and unique in curated data",
        {"null_ids": null_ids, "duplicate_ids": duplicate_ids}, "0 problems",
        PASS if uniqueness_problems <= THRESHOLDS["uniqueness_max_problems"] else FAIL,
    ))

    # 2. Completeness (checked records, before quarantine)
    completeness = {f: _pct(stats[f], checked_total) for f in REQUIRED_FIELDS + OPTIONAL_FIELDS}
    minimum = THRESHOLDS["completeness_required_min_pct"]
    for field in REQUIRED_FIELDS:
        checks.append(_check(
            "completeness", f"required field {field} is filled", completeness[field],
            f">= {minimum}%", PASS if completeness[field] >= minimum else FAIL,
        ))
    always_empty = [
        f for f in OPTIONAL_FIELDS
        if f not in EXPECTED_SPARSE_FIELDS and checked_total and stats[f] == 0
    ]
    checks.append(_check(
        "completeness", "optional fields are reported; a field that is always empty suggests a source change",
        {"always_empty": always_empty}, "no optional field 100% empty", WARN if always_empty else PASS,
    ))

    # 3. Validity (checked records, before quarantine)
    invalid_counts = {
        "invalid_date": reasons.get("invalid_date", 0),
        "invalid_timely": stats["_invalid_timely"] or 0,
        "invalid_state": reasons.get("invalid_state", 0),
        "negative_lag": reasons.get("negative_lag", 0),
    }
    for name, rule in VALIDITY_RULES.items():
        pct = _pct(invalid_counts[name], checked_total)
        checks.append(_check(
            "validity", rule, {"invalid": invalid_counts[name], "invalid_pct": pct},
            f"WARN above {THRESHOLDS['validity_warn_above_pct']}%, FAIL above {THRESHOLDS['validity_fail_above_pct']}%",
            validity_status(pct),
        ))

    # 4. Consistency (curated data): every in-domain record has a standard sub-product
    combos = (
        curated_df.groupBy("product", "sub_product", "sub_product_std").count()
        .orderBy(F.desc("count")).collect()
    )
    unmapped = [
        {"product": r["product"], "sub_product": r["sub_product"], "count": r["count"]}
        for r in combos if r["sub_product_std"] is None
    ]
    checks.append(_check(
        "consistency", "every product and sub-product combination maps to a standard sub-product",
        {"unmapped_combinations": len(unmapped)}, "0 unmapped (listed when present)",
        WARN if unmapped else PASS,
    ))

    # 5. Timeliness (curated data)
    latest = cur["latest"]
    age_days = (generated_at.date() - latest).days if latest else None
    max_age = THRESHOLDS["timeliness_max_age_days"]
    checks.append(_check(
        "timeliness", "latest date_received is recent", age_days, f"<= {max_age} days",
        PASS if age_days is not None and age_days <= max_age else WARN,
    ))

    # 6. Integrity (counts reconcile; the MongoDB count is compared later by the loader)
    accounted = curated + quarantined + out_of_domain + duplicates_removed
    checks.append(_check(
        "integrity", "raw = curated + quarantined + out_of_domain + duplicates_removed",
        {"raw_input": raw_input, "accounted": accounted}, "exact",
        PASS if accounted == raw_input else FAIL,
    ))

    return {
        "run_id": run_id,
        "generated_at": generated_at.isoformat(),
        "source_type": source_type,
        "counts": {
            "raw_input": raw_input,
            "out_of_domain": out_of_domain,
            "duplicates_removed": duplicates_removed,
            "quarantined": quarantined,
            "curated": curated,
        },
        "quarantine_reasons": reasons,
        "checks": checks,
        "completeness": completeness,
        "freshness": {
            "latest_date_received": latest.isoformat() if latest else None,
            "ingestion_lag_days": age_days,
        },
        "consistency": {
            "unmapped_combinations": unmapped,
            "domain_combinations": [
                {"product": r["product"], "sub_product": r["sub_product"],
                 "sub_product_std": r["sub_product_std"], "count": r["count"]}
                for r in combos
            ],
        },
        "thresholds": THRESHOLDS,
        "overall_status": overall_status(checks),
    }


def report_to_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)
