"""MongoDB aggregation queries for the CFPB money transfers dashboard.

All A1-A8 functions accept (db, filters) and return a list of aggregated
results, never individual complaint documents. They operate on the canonical
`complaints` collection produced by database.load.

Filter contract:
  date_from, date_to: YYYY-MM-DD / date / datetime (inclusive calendar dates)
  sub_product_std, issue, state, submitted_via, company: list[str]

Send the documented return shapes to Perla before dashboard integration.
The precise KPI presentation definitions still need to be agreed with
Perla's docs/metrics.md; do not interpret these as final analytical findings.

MongoDB 7.0 is required for $setWindowFields, $densify and $median.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any


CATEGORY_FIELDS = (
    "sub_product_std",
    "issue",
    "state",
    "submitted_via",
    "company",
)


def _as_date(value: Any, name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a YYYY-MM-DD date") from exc
    raise ValueError(f"{name} must be a date or YYYY-MM-DD string")


def _midnight(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def build_match(filters: dict | None = None, *, exclude: tuple[str, ...] = ()) -> dict:
    """Build an indexed MongoDB $match using inclusive calendar-date bounds.

    date_to is converted to a *strict* next-day upper bound so records on the
    selected last day are included. Unknown filter keys are rejected to avoid
    accidentally publishing unfiltered charts.
    """
    filters = filters or {}
    supported = set(CATEGORY_FIELDS) | {"date_from", "date_to"}
    unknown = set(filters) - supported
    if unknown:
        raise ValueError(f"Unsupported dashboard filters: {sorted(unknown)}")

    match: dict[str, Any] = {}
    start = _as_date(filters["date_from"], "date_from") if filters.get("date_from") is not None else None
    end = _as_date(filters["date_to"], "date_to") if filters.get("date_to") is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("date_from cannot be after date_to")
    if "date_from" not in exclude and "date_to" not in exclude:
        bounds = {}
        if start is not None:
            bounds["$gte"] = _midnight(start)
        if end is not None:
            if end == date.max:
                raise ValueError("date_to is out of supported range")
            bounds["$lt"] = _midnight(end + timedelta(days=1))
        if bounds:
            match["date_received"] = bounds
    for field in CATEGORY_FIELDS:
        if field in exclude or filters.get(field) is None:
            continue
        values = filters[field]
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
            raise ValueError(f"{field} must be a list of strings")
        match[field] = {"$in": list(values)}
    return match


def _aggregate(db, pipeline: list[dict]) -> list[dict]:
    return list(db.complaints.aggregate(pipeline, allowDiskUse=True))


def _percent(numerator: Any, denominator: Any) -> dict:
    """A numeric percentage or null when the denominator is zero/unknown."""
    return {
        "$cond": [
            {"$gt": [denominator, 0]},
            {"$round": [{"$multiply": [{"$divide": [numerator, denominator]}, 100]}, 2]},
            None,
        ]
    }


def a1_monthly_volume(db, filters: dict) -> list[dict]:
    """Month/sub-product counts and calendar-accurate MoM and YoY percentages.

    No comparison is reported across a gap in the monthly series; the
    corresponding preceding month/year must actually exist in the selection.
    """
    return _aggregate(db, [
        {"$match": build_match(filters)},
        {"$group": {
            "_id": {
                "month": {"$dateTrunc": {"date": "$date_received", "unit": "month", "timezone": "UTC"}},
                "sub_product_std": {"$ifNull": ["$sub_product_std", "Unknown"]},
            },
            "complaint_count": {"$sum": 1},
        }},
        {"$project": {"_id": 0, "month": "$_id.month", "sub_product_std": "$_id.sub_product_std", "complaint_count": 1}},
        {"$setWindowFields": {
            "partitionBy": "$sub_product_std", "sortBy": {"month": 1},
            "output": {
                "prev_m_count": {"$shift": {"output": "$complaint_count", "by": -1}},
                "prev_m_date": {"$shift": {"output": "$month", "by": -1}},
                "prev_y_count": {"$shift": {"output": "$complaint_count", "by": -12}},
                "prev_y_date": {"$shift": {"output": "$month", "by": -12}},
            },
        }},
        {"$project": {
            "month": 1, "year_month": {"$dateToString": {"format": "%Y-%m", "date": "$month", "timezone": "UTC"}},
            "sub_product_std": 1, "complaint_count": 1,
            "mom_pct": {"$cond": [
                {"$and": [
                    {"$gt": ["$prev_m_count", 0]},
                    {"$eq": [{"$dateDiff": {"startDate": "$prev_m_date", "endDate": "$month", "unit": "month"}}, 1]},
                ]},
                _percent({"$subtract": ["$complaint_count", "$prev_m_count"]}, "$prev_m_count"), None,
            ]},
            "yoy_pct": {"$cond": [
                {"$and": [
                    {"$gt": ["$prev_y_count", 0]},
                    {"$eq": [{"$dateDiff": {"startDate": "$prev_y_date", "endDate": "$month", "unit": "month"}}, 12]},
                ]},
                _percent({"$subtract": ["$complaint_count", "$prev_y_count"]}, "$prev_y_count"), None,
            ]},
        }},
        {"$sort": {"month": 1, "sub_product_std": 1}},
    ])


def a2_issue_subissue_share(db, filters: dict) -> list[dict]:
    """Counts plus issue share within product and sub-issue share within issue.

    Uses $facet to derive both denominators from the *same filtered rows*.
    If issue is filtered down to one value, the share is of that selection.
    """
    return _aggregate(db, [
        {"$match": build_match(filters)},
        {"$group": {
            "_id": {
                "p": {"$ifNull": ["$sub_product_std", "Unknown"]},
                "i": {"$ifNull": ["$issue", "Unknown"]},
                "si": {"$ifNull": ["$sub_issue", "Unknown"]},
            },
            "n": {"$sum": 1},
        }},
        {"$facet": {
            "rows": [{"$project": {"_id": 1, "n": 1}}],
            "product_totals": [{"$group": {"_id": "$_id.p", "n": {"$sum": "$n"}}}],
            "issue_totals": [{"$group": {"_id": {"p": "$_id.p", "i": "$_id.i"}, "n": {"$sum": "$n"}}}],
        }},
        {"$unwind": "$rows"},
        {"$set": {
            "product_total": {"$first": {"$filter": {"input": "$product_totals", "as": "t", "cond": {"$eq": ["$$t._id", "$rows._id.p"]}}}},
            "issue_total": {"$first": {"$filter": {"input": "$issue_totals", "as": "t", "cond": {"$and": [
                {"$eq": ["$$t._id.p", "$rows._id.p"]}, {"$eq": ["$$t._id.i", "$rows._id.i"]},
            ]}}}},
        }},
        {"$project": {
            "_id": 0, "sub_product_std": "$rows._id.p", "issue": "$rows._id.i", "sub_issue": "$rows._id.si",
            "complaint_count": "$rows.n", "issue_total_count": "$issue_total.n",
            "sub_product_total_count": "$product_total.n",
            "issue_share_pct": _percent("$issue_total.n", "$product_total.n"),
            "sub_issue_share_within_issue_pct": _percent("$rows.n", "$issue_total.n"),
        }},
        {"$sort": {"sub_product_std": 1, "issue_total_count": -1, "issue": 1, "complaint_count": -1}},
    ])


def a3_fraud_share(db, filters: dict) -> list[dict]:
    """Consumer-classified 'Fraud or scam' share with a rolling 12-month rate.

    Ignore the selected issue filter intentionally: it would otherwise make
    the numerator and denominator both fraud-only (100%). Other filters apply.
    Months missing within a sub-product series are filled with zero counts.
    """
    match = build_match(filters, exclude=("issue",))
    match["is_core_payment"] = True
    return _aggregate(db, [
        {"$match": match},
        {"$group": {
            "_id": {
                "month": {"$dateTrunc": {"date": "$date_received", "unit": "month", "timezone": "UTC"}},
                "sub_product_std": "$sub_product_std",
            },
            "complaint_count": {"$sum": 1},
            "fraud_count": {"$sum": {"$cond": [{"$eq": ["$issue", "Fraud or scam"]}, 1, 0]}},
        }},
        {"$project": {"_id": 0, "month": "$_id.month", "sub_product_std": "$_id.sub_product_std", "complaint_count": 1, "fraud_count": 1}},
        {"$sort": {"sub_product_std": 1, "month": 1}},
        {"$densify": {"field": "month", "partitionByFields": ["sub_product_std"], "range": {"step": 1, "unit": "month", "bounds": "partition"}}},
        {"$set": {"complaint_count": {"$ifNull": ["$complaint_count", 0]}, "fraud_count": {"$ifNull": ["$fraud_count", 0]}}},
        {"$setWindowFields": {
            "partitionBy": "$sub_product_std", "sortBy": {"month": 1},
            "output": {
                "rolling_12m_total": {"$sum": "$complaint_count", "window": {"documents": [-11, "current"]}},
                "rolling_12m_fraud": {"$sum": "$fraud_count", "window": {"documents": [-11, "current"]}},
            },
        }},
        {"$project": {
            "_id": 0, "month": 1,
            "year_month": {"$dateToString": {"format": "%Y-%m", "date": "$month", "timezone": "UTC"}},
            "sub_product_std": 1, "complaint_count": 1, "fraud_count": 1,
            "fraud_share_pct": _percent("$fraud_count", "$complaint_count"),
            "rolling_12m_share_pct": _percent("$rolling_12m_fraud", "$rolling_12m_total"),
        }},
        {"$sort": {"month": 1, "sub_product_std": 1}},
    ])


def a4_channel_share_by_year(db, filters: dict) -> list[dict]:
    """Submission channel counts and shares within each selected calendar year."""
    return _aggregate(db, [
        {"$match": build_match(filters)},
        {"$group": {
            "_id": {"year": "$year", "submitted_via": {"$ifNull": ["$submitted_via", "Unknown"]}},
            "complaint_count": {"$sum": 1},
        }},
        {"$project": {"_id": 0, "year": "$_id.year", "submitted_via": "$_id.submitted_via", "complaint_count": 1}},
        {"$setWindowFields": {
            "partitionBy": "$year", "sortBy": {"submitted_via": 1},
            "output": {"year_total": {"$sum": "$complaint_count", "window": {"documents": ["unbounded", "unbounded"]}}},
        }},
        {"$project": {"year": 1, "submitted_via": 1, "complaint_count": 1, "year_total": 1,
                      "channel_share_pct": _percent("$complaint_count", "$year_total")}},
        {"$sort": {"year": 1, "complaint_count": -1}},
    ])


def a5_response_and_timeliness(db, filters: dict) -> list[dict]:
    """Response mix and timely-response rate by sub-product.

    `closed_response_share_pct` excludes 'In progress' and 'Unknown'; it is
    null for those categories. `response_share_pct` includes all categories.
    """
    return _aggregate(db, [
        {"$match": build_match(filters)},
        {"$group": {
            "_id": {"p": {"$ifNull": ["$sub_product_std", "Unknown"]},
                    "r": {"$ifNull": ["$company_response", "Unknown"]}},
            "complaint_count": {"$sum": 1},
            "timely_yes_count": {"$sum": {"$cond": [{"$eq": ["$timely_response", True]}, 1, 0]}},
            "timely_known_count": {"$sum": {"$cond": [{"$in": ["$timely_response", [True, False]]}, 1, 0]}},
        }},
        {"$project": {
            "_id": 0, "sub_product_std": "$_id.p", "company_response": "$_id.r", "complaint_count": 1,
            "timely_yes_count": 1, "timely_known_count": 1,
            "closed_count": {"$cond": [{"$in": ["$_id.r", ["In progress", "Unknown"]]}, 0, "$complaint_count"]},
        }},
        {"$setWindowFields": {
            "partitionBy": "$sub_product_std", "sortBy": {"company_response": 1},
            "output": {
                "total": {"$sum": "$complaint_count", "window": {"documents": ["unbounded", "unbounded"]}},
                "closed_total": {"$sum": "$closed_count", "window": {"documents": ["unbounded", "unbounded"]}},
                "timely_yes_total": {"$sum": "$timely_yes_count", "window": {"documents": ["unbounded", "unbounded"]}},
                "timely_known_total": {"$sum": "$timely_known_count", "window": {"documents": ["unbounded", "unbounded"]}},
            },
        }},
        {"$project": {
            "_id": 0, "sub_product_std": 1, "company_response": 1, "complaint_count": 1,
            "response_share_pct": _percent("$complaint_count", "$total"),
            "closed_response_share_pct": {"$cond": [
                {"$in": ["$company_response", ["In progress", "Unknown"]]}, None,
                _percent("$complaint_count", "$closed_total"),
            ]},
            "timely_pct": _percent("$timely_yes_total", "$timely_known_total"),
            "timely_yes_count": "$timely_yes_total", "timely_known_count": "$timely_known_total",
        }},
        {"$sort": {"sub_product_std": 1, "complaint_count": -1}},
    ])


def a6_processing_lag_distribution(db, filters: dict) -> list[dict]:
    """Non-negative processing-lag buckets: 0, 1, 2-3, 4-7, 8-14, 15+."""
    match = build_match(filters)
    match["processing_lag_days"] = {"$gte": 0}
    return _aggregate(db, [
        {"$match": match},
        {"$bucket": {
            "groupBy": "$processing_lag_days", "boundaries": [0, 1, 2, 4, 8, 15], "default": "15+",
            "output": {"complaint_count": {"$sum": 1}},
        }},
        {"$set": {"sort_order": {"$switch": {"branches": [
            {"case": {"$eq": ["$_id", 0]}, "then": 0},
            {"case": {"$eq": ["$_id", 1]}, "then": 1},
            {"case": {"$eq": ["$_id", 2]}, "then": 2},
            {"case": {"$eq": ["$_id", 4]}, "then": 3},
            {"case": {"$eq": ["$_id", 8]}, "then": 4},
        ], "default": 5}}}},
        {"$setWindowFields": {
            "sortBy": {"sort_order": 1},
            "output": {"total": {"$sum": "$complaint_count", "window": {"documents": ["unbounded", "unbounded"]}}},
        }},
        {"$project": {
            "_id": 0, "bucket_start": "$_id", "sort_order": 1, "complaint_count": 1,
            "bucket_label": {"$arrayElemAt": [["0 days", "1 day", "2-3 days", "4-7 days", "8-14 days", "15+ days"], "$sort_order"]},
            "share_pct": _percent("$complaint_count", "$total"),
        }},
        {"$sort": {"sort_order": 1}},
    ])


def a7_company_cumulative_share(db, filters: dict) -> list[dict]:
    """Cumulative company share of *complaint records*, never a quality rank."""
    return _aggregate(db, [
        {"$match": build_match(filters)},
        {"$group": {"_id": {"$ifNull": ["$company", "Unknown"]}, "complaint_count": {"$sum": 1}}},
        {"$project": {"_id": 0, "company": "$_id", "complaint_count": 1}},
        {"$setWindowFields": {"sortBy": {"complaint_count": -1, "company": 1}, "output": {
            "cumulative_count": {"$sum": "$complaint_count", "window": {"documents": ["unbounded", "current"]}},
            "total": {"$sum": "$complaint_count", "window": {"documents": ["unbounded", "unbounded"]}},
        }}},
        {"$project": {"company": 1, "complaint_count": 1, "cumulative_count": 1,
                      "share_pct": _percent("$complaint_count", "$total"),
                      "cumulative_share_pct": _percent("$cumulative_count", "$total")}},
        {"$sort": {"complaint_count": -1, "company": 1}},
    ])


def a8_state_issue_profile(db, filters: dict) -> list[dict]:
    """Issue distribution by state, including an explicit Unknown state bucket.

    No per-capita normalization is attempted unless Perla supplies an approved,
    quality-checked `state_population` enrichment source.
    """
    return _aggregate(db, [
        {"$match": build_match(filters)},
        {"$group": {"_id": {
            "state": {"$ifNull": ["$state", "Unknown"]},
            "issue": {"$ifNull": ["$issue", "Unknown"]},
        }, "complaint_count": {"$sum": 1}}},
        {"$project": {"_id": 0, "state": "$_id.state", "issue": "$_id.issue", "complaint_count": 1}},
        {"$setWindowFields": {
            "partitionBy": "$state", "sortBy": {"issue": 1},
            "output": {"state_total": {"$sum": "$complaint_count", "window": {"documents": ["unbounded", "unbounded"]}}},
        }},
        {"$project": {"state": 1, "issue": 1, "complaint_count": 1, "state_total": 1,
                      "issue_share_within_state_pct": _percent("$complaint_count", "$state_total")}},
        {"$sort": {"state": 1, "complaint_count": -1, "issue": 1}},
    ])


def kpi_summary(db, filters: dict) -> dict:
    """Filtered total, timely %, median processing lag, and a full-year YoY.

    YoY always compares two *complete calendar years* under the same category
    filters. If the selected dates don't cover both complete years, YoY is null.
    `median_processing_lag_days` uses MongoDB 7.0 approximate $median.
    """
    pipeline = [
        {"$match": build_match(filters)},
        {"$facet": {
            "totals": [{"$group": {
                "_id": None, "total_complaints": {"$sum": 1},
                "timely_yes": {"$sum": {"$cond": [{"$eq": ["$timely_response", True]}, 1, 0]}},
                "timely_known": {"$sum": {"$cond": [{"$in": ["$timely_response", [True, False]]}, 1, 0]}},
            }}],
            "lag": [
                {"$match": {"processing_lag_days": {"$gte": 0}}},
                {"$group": {"_id": None, "median": {"$median": {"input": "$processing_lag_days", "method": "approximate"}}}},
            ],
        }},
        {"$project": {
            "_id": 0, "total_complaints": {"$ifNull": [{"$first": "$totals.total_complaints"}, 0]},
            "timely_yes": {"$ifNull": [{"$first": "$totals.timely_yes"}, 0]},
            "timely_known": {"$ifNull": [{"$first": "$totals.timely_known"}, 0]},
            "median_processing_lag_days": {"$first": "$lag.median"},
        }},
    ]
    rows = _aggregate(db, pipeline)
    result = rows[0] if rows else {"total_complaints": 0, "timely_yes": 0, "timely_known": 0, "median_processing_lag_days": None}
    yes = result["timely_yes"]
    known = result["timely_known"]
    result["timely_pct"] = round(100 * yes / known, 2) if known else None

    today = datetime.now(timezone.utc).date()
    last_complete_year = today.year - 1
    if filters.get("date_to") is not None:
        to_date = _as_date(filters["date_to"], "date_to")
        last_complete_year = min(last_complete_year, to_date.year if (to_date.month, to_date.day) == (12, 31) else to_date.year - 1)
    previous_year = last_complete_year - 1
    start = _as_date(filters["date_from"], "date_from") if filters.get("date_from") is not None else None
    if start is not None and start > date(previous_year, 1, 1):
        result["yoy_pct"] = None
        result["yoy_years"] = None
        return result
    match = build_match(filters, exclude=("date_from", "date_to"))
    match["date_received"] = {
        "$gte": _midnight(date(previous_year, 1, 1)),
        "$lt": _midnight(date(last_complete_year + 1, 1, 1)),
    }
    counts = _aggregate(db, [
        {"$match": match},
        {"$group": {"_id": "$year", "count": {"$sum": 1}}},
    ])
    by_year = {row["_id"]: row["count"] for row in counts}
    earlier = by_year.get(previous_year, 0)
    later = by_year.get(last_complete_year, 0)
    result["yoy_pct"] = round(100 * (later - earlier) / earlier, 2) if earlier else None
    result["yoy_years"] = [previous_year, last_complete_year]
    return result


def freshness(db) -> dict:
    """Latest complaint date, last successful MongoDB load and quality state."""
    latest = db.complaints.find_one({}, {"date_received": 1, "_id": 0}, sort=[("date_received", -1)])
    run = db.pipeline_runs.find_one(
        {"mongo_load_status": "success"},
        {"_id": 1, "run_id": 1, "mongo_loaded_at": 1, "mongo_count_after": 1},
        sort=[("mongo_loaded_at", -1)],
    )
    quality = db.quality_reports.find_one({"_id": run["_id"]}) if run else None
    return {
        "latest_date_received": latest.get("date_received") if latest else None,
        "last_successful_run_id": (run.get("run_id") or str(run["_id"])) if run else None,
        "last_successful_run_at": run.get("mongo_loaded_at") if run else None,
        "mongo_count_after": run.get("mongo_count_after") if run else None,
        "last_quality_status": quality.get("overall_status") if quality else None,
    }


def ml_emerging_issues(db, filters: dict | None = None) -> list[dict]:
    """Read precomputed emerging-issue results from MongoDB."""
    filters = filters or {}

    unsupported = [
        key for key, value in filters.items()
        if key not in ("sub_product_std", "issue")
        and value not in (None, [], "")
    ]
    if unsupported:
        raise ValueError(
            f"Unsupported filters for precomputed ML results: {sorted(unsupported)}"
        )

    selected = {
        key: filters[key]
        for key in ("sub_product_std", "issue")
        if key in filters and filters[key] is not None
    }
    query = build_match(selected)
    return list(db.ml_emerging_issues.find(query, {"_id": 0}))


def ml_state_clusters(db) -> list[dict]:
    """Read precomputed state-clustering results from MongoDB."""
    return list(
        db.ml_state_clusters.find({}, {"_id": 0}).sort("state", 1)
    )



__all__ = [
    "build_match", "a1_monthly_volume", "a2_issue_subissue_share",
    "a3_fraud_share", "a4_channel_share_by_year",
    "a5_response_and_timeliness",
    "a6_processing_lag_distribution",
    "a7_company_cumulative_share", "a8_state_issue_profile",
    "kpi_summary", "freshness",
    "ml_emerging_issues", "ml_state_clusters",
]
