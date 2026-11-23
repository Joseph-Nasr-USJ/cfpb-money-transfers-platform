
"""
Q4: Company responses and processing lag analysis.

Uses MongoDB aggregation functions provided by database/queries.py.

Outputs:
- q4_response_categories.csv
- q4_timely_responses.csv
- q4_processing_lag.csv
- q4_summary.csv
- q4_response_categories.png
- q4_timely_responses.png
- q4_processing_lag.png
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient

from database.queries import (
    a5_response_and_timeliness,
    a6_processing_lag_distribution,
    kpi_summary,
)


OUTPUT_DIR = Path("analytics/output")

RESPONSE_COLUMNS = [
    "sub_product_std",
    "company_response",
    "complaint_count",
    "response_share_pct",
    "closed_response_share_pct",
    "timely_pct",
    "timely_yes_count",
    "timely_known_count",
]

TIMELY_COLUMNS = [
    "sub_product_std",
    "total_complaints",
    "timely_yes_count",
    "timely_no_count",
    "missing_invalid_count",
    "timely_pct",
]

LAG_COLUMNS = [
    "bucket_label",
    "sort_order",
    "complaint_count",
    "share_pct",
]

SUMMARY_COLUMNS = [
    "total_complaints",
    "timely_pct",
    "median_processing_lag_days",
]


def save_chart(fig, filename):
    """Save a PNG chart in the analytics output folder."""
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def prepare_response_data(records):
    """Organize response-category aggregates."""
    df = pd.DataFrame(records, columns=RESPONSE_COLUMNS)

    if df.empty:
        return df

    df["sub_product_std"] = (
        df["sub_product_std"]
        .fillna("Unknown")
        .replace("", "Unknown")
    )

    df["company_response"] = (
        df["company_response"]
        .fillna("Unknown")
        .replace("", "Unknown")
    )

    return df.sort_values(
        ["sub_product_std", "company_response"]
    ).reset_index(drop=True)


def prepare_timely_data(response_df):
    """
    Calculate Yes, No, and missing counts per sub-product.

    Christopher's query repeats the total timely counts
    for each company response category. We must use each
    sub-product's repeated totals only once.
    """
    if response_df.empty:
        return pd.DataFrame(columns=TIMELY_COLUMNS)

    # Sum complaint counts across different response categories.
    totals = (
        response_df.groupby("sub_product_std", as_index=False)
        ["complaint_count"]
        .sum()
        .rename(
            columns={"complaint_count": "total_complaints"}
        )
    )

    # Keep one copy of the repeated timely totals.
    timely = response_df[
        [
            "sub_product_std",
            "timely_yes_count",
            "timely_known_count",
            "timely_pct",
        ]
    ].drop_duplicates(subset=["sub_product_std"])

    timely = timely.merge(
        totals,
        on="sub_product_std",
        how="left"
    )

    timely["timely_no_count"] = (
        timely["timely_known_count"]
        - timely["timely_yes_count"]
    )

    timely["missing_invalid_count"] = (
        timely["total_complaints"]
        - timely["timely_known_count"]
    )

    return timely[TIMELY_COLUMNS].sort_values(
        "sub_product_std"
    )


def prepare_lag_data(records):
    """Organize processing-lag bucket aggregates."""
    df = pd.DataFrame(records, columns=LAG_COLUMNS)

    if df.empty:
        return df

    return df.sort_values("sort_order")


def create_response_chart(df):
    """Show the distribution of response categories."""

    pivot = df.pivot_table(
        index="sub_product_std",
        columns="company_response",
        values="complaint_count",
        aggfunc="sum",
        fill_value=0
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    pivot.plot(
        kind="bar",
        stacked=True,
        ax=ax
    )

    ax.set_title("Company Response Categories by Sub-Product")
    ax.set_xlabel("Sub-Product")
    ax.set_ylabel("Published Complaint Count")

    ax.tick_params(axis="x", labelrotation=30)

    ax.legend(
        title="Company Response",
        bbox_to_anchor=(1.02, 1),
        loc="upper left"
    )

    save_chart(fig, "q4_response_categories.png")


def create_timely_chart(df):
    """Show timely-response percentages by sub-product."""

    chart_df = df.dropna(subset=["timely_pct"])

    if chart_df.empty:
        return

    fig, ax = plt.subplots(figsize=(11, 6))

    ax.bar(
        chart_df["sub_product_std"],
        chart_df["timely_pct"]
    )

    ax.set_title("Timely Response Percentage by Sub-Product")
    ax.set_xlabel("Sub-Product")
    ax.set_ylabel("Timely Response (%)")
    ax.set_ylim(0, 100)

    ax.tick_params(axis="x", labelrotation=30)

    save_chart(fig, "q4_timely_responses.png")


def create_lag_chart(df):
    """Show valid receipt-to-referral time buckets."""

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(
        df["bucket_label"],
        df["complaint_count"]
    )

    ax.set_title("CFPB Receipt-to-Referral Processing Lag")
    ax.set_xlabel("Processing Lag")
    ax.set_ylabel("Published Complaint Count")

    save_chart(fig, "q4_processing_lag.png")


def run():
    """Execute Q4 and export CSV and PNG results."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting Q4: Company Response Analysis")

    mongo_uri = os.getenv(
        "MONGO_URI",
        "mongodb://mongo:27017"
    )

    database_name = os.getenv(
        "MONGO_DB",
        "cfpb_money_transfers"
    )

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")

        database = client[database_name]

        response_records = a5_response_and_timeliness(
            database, {}
        )

        lag_records = a6_processing_lag_distribution(
            database, {}
        )

        summary = kpi_summary(database, {})

    finally:
        client.close()

    # Remove previous charts to prevent stale results.
    for filename in [
        "q4_response_categories.png",
        "q4_timely_responses.png",
        "q4_processing_lag.png",
    ]:
        path = OUTPUT_DIR / filename

        if path.exists():
            path.unlink()

    response_df = prepare_response_data(
        response_records
    )

    timely_df = prepare_timely_data(
        response_df
    )

    lag_df = prepare_lag_data(
        lag_records
    )

    # Export all aggregated tables.
    response_df.to_csv(
        OUTPUT_DIR / "q4_response_categories.csv",
        index=False
    )

    timely_df.to_csv(
        OUTPUT_DIR / "q4_timely_responses.csv",
        index=False
    )

    lag_df.to_csv(
        OUTPUT_DIR / "q4_processing_lag.csv",
        index=False
    )

    summary_df = pd.DataFrame(
        [{
            "total_complaints": summary.get(
                "total_complaints"
            ),
            "timely_pct": summary.get("timely_pct"),
            "median_processing_lag_days": summary.get(
                "median_processing_lag_days"
            ),
        }],
        columns=SUMMARY_COLUMNS
    )

    summary_df.to_csv(
        OUTPUT_DIR / "q4_summary.csv",
        index=False
    )

    if response_df.empty:
        print("No company response records available.")
    else:
        create_response_chart(response_df)

    if timely_df.empty:
        print("No timely-response records available.")
    else:
        create_timely_chart(timely_df)

    if lag_df.empty:
        print("No processing-lag records available.")
    else:
        create_lag_chart(lag_df)

    print("Q4 completed.")
    print("Results saved in analytics/output/")

    print(
        "Important: timely response is not customer "
        "satisfaction, and processing lag is not "
        "company resolution time."
    )


if __name__ == "__main__":
    run()
