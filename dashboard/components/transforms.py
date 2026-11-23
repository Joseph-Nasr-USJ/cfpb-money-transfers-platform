
"""Reusable pandas transformations for the Streamlit dashboard."""

import pandas as pd


def prepare_monthly_data(rows):
    """
    Prepare monthly complaint totals for the Trends page.

    Accepts MongoDB query rows or a pandas DataFrame.
    Groups all sub-products by calendar month.
    """
    df = pd.DataFrame(rows).copy()

    if df.empty:
        return pd.DataFrame(
            columns=["month", "complaint_count"]
        )

    required_columns = {"year_month", "complaint_count"}

    if not required_columns.issubset(df.columns):
        raise ValueError(
            "Monthly data requires year_month and complaint_count."
        )

    df["month"] = pd.to_datetime(
        df["year_month"],
        format="%Y-%m",
        errors="coerce"
    )

    df["complaint_count"] = pd.to_numeric(
        df["complaint_count"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["month", "complaint_count"]
    )

    monthly = (
        df.groupby("month", as_index=False)["complaint_count"]
        .sum()
        .sort_values("month")
        .reset_index(drop=True)
    )

    return monthly
