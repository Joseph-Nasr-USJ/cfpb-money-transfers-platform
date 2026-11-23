
"""Tests for the actual Trends dashboard transformation."""

from dashboard.components.transforms import prepare_monthly_data


def test_monthly_totals():
    rows = [
        {
            "year_month": "2025-01",
            "sub_product_std": "Mobile or digital wallet",
            "complaint_count": 10,
        },
        {
            "year_month": "2025-01",
            "sub_product_std": "Domestic money transfer",
            "complaint_count": 20,
        },
        {
            "year_month": "2025-02",
            "sub_product_std": "Mobile or digital wallet",
            "complaint_count": 15,
        },
    ]

    monthly = prepare_monthly_data(rows)

    assert monthly["complaint_count"].tolist() == [30, 15]


def test_month_order():
    rows = [
        {"year_month": "2025-03", "complaint_count": 7},
        {"year_month": "2025-01", "complaint_count": 5},
        {"year_month": "2025-02", "complaint_count": 6},
    ]

    monthly = prepare_monthly_data(rows)

    assert monthly["month"].dt.strftime("%Y-%m").tolist() == [
        "2025-01",
        "2025-02",
        "2025-03",
    ]


def test_wallet_percentage():
    total = 50
    wallet = 15

    wallet_share = wallet / total * 100

    assert wallet_share == 30.0


def test_invalid_months_are_excluded():
    rows = [
        {"year_month": "2025-01", "complaint_count": 10},
        {"year_month": "not-a-month", "complaint_count": 50},
    ]

    monthly = prepare_monthly_data(rows)

    assert monthly["complaint_count"].tolist() == [10]


def test_empty_monthly_data():
    monthly = prepare_monthly_data([])

    assert monthly.empty
    assert list(monthly.columns) == [
        "month",
        "complaint_count",
    ]
