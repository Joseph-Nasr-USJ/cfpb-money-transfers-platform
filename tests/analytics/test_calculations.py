
"""
Unit tests for CFPB analytics calculations.

These tests use small, explicitly defined examples.
They do not represent actual CFPB observations.
"""

from datetime import date

import pandas as pd
import pytest

from analytics.common_measures import (
    percentage,
    percentage_change,
    rolling_share,
    is_complete_month,
    is_complete_year,
)
from analytics.q3_channels import (
    prepare_yearly_data,
    create_summary,
)
from analytics.q4_responses import (
    prepare_response_data,
    prepare_timely_data,
)
from analytics.q5_geography import (
    prepare_issue_data,
    prepare_state_totals,
)
from analytics.ml_emerging_issues import (
    analysis_window,
    month_index,
)


def test_percentage():
    assert percentage(25, 100) == 25.0
    assert percentage(1, 4) == 25.0


def test_percentage_zero_denominator():
    assert percentage(5, 0) is None
    assert percentage(5, None) is None


def test_percentage_change():
    assert percentage_change(120, 100) == 20.0
    assert percentage_change(80, 100) == -20.0


def test_percentage_change_zero_previous():
    assert percentage_change(100, 0) is None


def test_rolling_share():
    result = rolling_share(
        [2, 3, 5],
        [10, 10, 20],
        window=2,
    )

    assert result == [20.0, 25.0, 26.67]


def test_rolling_share_rejects_invalid_input():
    with pytest.raises(ValueError):
        rolling_share([1, 2], [10], window=2)

    with pytest.raises(ValueError):
        rolling_share([1], [10], window=0)


def test_complete_month_excludes_current_month():
    today = date(2026, 11, 23)

    assert is_complete_month(2026, 10, today)
    assert not is_complete_month(2026, 11, today)
    assert not is_complete_month(2026, 12, today)


def test_complete_year():
    today = date(2026, 11, 23)

    assert is_complete_year(2025, today)
    assert not is_complete_year(2026, today)


def test_q3_channel_summary_uses_counts():
    rows = [
        {
            "year": 2024,
            "submitted_via": "Web",
            "complaint_count": 30,
            "year_total": 40,
            "channel_share_pct": 75.0,
        },
        {
            "year": 2024,
            "submitted_via": "Phone",
            "complaint_count": 10,
            "year_total": 40,
            "channel_share_pct": 25.0,
        },
        {
            "year": 2025,
            "submitted_via": "Web",
            "complaint_count": 20,
            "year_total": 60,
            "channel_share_pct": 33.33,
        },
        {
            "year": 2025,
            "submitted_via": "Phone",
            "complaint_count": 40,
            "year_total": 60,
            "channel_share_pct": 66.67,
        },
    ]

    yearly = prepare_yearly_data(rows)
    summary = create_summary(yearly)

    web = summary[
        summary["submitted_via"] == "Web"
    ].iloc[0]

    assert web["complaint_count"] == 50
    assert web["overall_share_pct"] == 50.0

    assert summary["complaint_count"].sum() == 100


def test_q3_empty_data():
    yearly = prepare_yearly_data([])
    summary = create_summary(yearly)

    assert yearly.empty
    assert summary.empty
    assert list(summary.columns) == [
        "submitted_via",
        "complaint_count",
        "overall_share_pct",
    ]


def test_q4_timely_counts_not_double_counted():
    """
    The MongoDB query repeats timely totals for
    every response category within a sub-product.
    """

    records = [
        {
            "sub_product_std": "Product A",
            "company_response": "Closed with explanation",
            "complaint_count": 60,
            "response_share_pct": 60.0,
            "closed_response_share_pct": 60.0,
            "timely_pct": 80.0,
            "timely_yes_count": 72,
            "timely_known_count": 90,
        },
        {
            "sub_product_std": "Product A",
            "company_response": "Closed with relief",
            "complaint_count": 40,
            "response_share_pct": 40.0,
            "closed_response_share_pct": 40.0,
            "timely_pct": 80.0,
            "timely_yes_count": 72,
            "timely_known_count": 90,
        },
    ]

    responses = prepare_response_data(records)
    timely = prepare_timely_data(responses)

    assert len(timely) == 1

    result = timely.iloc[0]

    assert result["total_complaints"] == 100
    assert result["timely_yes_count"] == 72
    assert result["timely_no_count"] == 18
    assert result["missing_invalid_count"] == 10
    assert result["timely_pct"] == 80.0


def test_q4_empty_data():
    responses = prepare_response_data([])
    timely = prepare_timely_data(responses)

    assert responses.empty
    assert timely.empty


def test_q5_state_totals_not_double_counted():
    """
    The MongoDB query repeats state_total for
    every issue in the same state.
    """

    records = [
        {
            "state": "CA",
            "issue": "Issue A",
            "complaint_count": 60,
            "state_total": 100,
            "issue_share_within_state_pct": 60.0,
        },
        {
            "state": "CA",
            "issue": "Issue B",
            "complaint_count": 40,
            "state_total": 100,
            "issue_share_within_state_pct": 40.0,
        },
        {
            "state": "NY",
            "issue": "Issue A",
            "complaint_count": 50,
            "state_total": 50,
            "issue_share_within_state_pct": 100.0,
        },
    ]

    issues = prepare_issue_data(records)
    states = prepare_state_totals(issues)

    assert states["total_complaints"].sum() == 150

    ca = states[states["state"] == "CA"].iloc[0]

    assert ca["total_complaints"] == 100
    assert ca["share_of_all_complaints_pct"] == 66.67


def test_q5_preserves_unknown_state():
    records = [
        {
            "state": None,
            "issue": "Issue A",
            "complaint_count": 5,
            "state_total": 5,
            "issue_share_within_state_pct": 100.0,
        }
    ]

    issues = prepare_issue_data(records)

    assert issues.iloc[0]["state"] == "Unknown"


def test_ml_24_complete_month_window():
    start, end = analysis_window(
        date(2026, 11, 23)
    )

    assert start == date(2024, 11, 1)
    assert end == date(2026, 11, 1)


def test_ml_month_index():
    start = date(2024, 11, 1)

    assert month_index("2024-11", start) == 0
    assert month_index("2025-11", start) == 12
    assert month_index("2026-10", start) == 23
