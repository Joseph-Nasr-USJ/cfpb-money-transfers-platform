
import pandas as pd


def prepare_monthly_data(rows):
    """Prepare the monthly totals used by the Trends page."""

    df = pd.DataFrame(rows)

    df["month"] = pd.to_datetime(
        df["year_month"],
        format="%Y-%m"
    )

    df["complaint_count"] = pd.to_numeric(
        df["complaint_count"]
    )

    monthly = (
        df.groupby("month", as_index=False)["complaint_count"]
        .sum()
        .sort_values("month")
    )

    return monthly


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
