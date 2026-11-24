
"""
Q3: CFPB complaint submission channel analysis.

Uses Christopher's MongoDB aggregation:
a4_channel_share_by_year()

Outputs:
- q3_channels_yearly.csv
- q3_channels_summary.csv
- q3_channel_shares.png
- q3_channel_counts.png

Only aggregated complaint records are used.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient

from database.queries import a4_channel_share_by_year


OUTPUT_DIR = Path("analytics/output")

YEARLY_COLUMNS = [
    "year",
    "submitted_via",
    "complaint_count",
    "year_total",
    "channel_share_pct"
]

SUMMARY_COLUMNS = [
    "submitted_via",
    "complaint_count",
    "overall_share_pct"
]


def save_chart(fig, filename):
    """Save a PNG chart and release its memory."""
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def prepare_yearly_data(records):
    """Organize MongoDB's aggregated channel results."""
    df = pd.DataFrame(records, columns=YEARLY_COLUMNS)

    if df.empty:
        return df

    df["submitted_via"] = (
        df["submitted_via"]
        .fillna("Unknown")
        .replace("", "Unknown")
    )

    df["year"] = pd.to_numeric(
        df["year"], errors="coerce"
    )

    df["complaint_count"] = pd.to_numeric(
        df["complaint_count"], errors="coerce"
    )

    df["channel_share_pct"] = pd.to_numeric(
        df["channel_share_pct"], errors="coerce"
    )

    df = df.dropna(
        subset=["year", "complaint_count"]
    )

    df["year"] = df["year"].astype(int)

    return df.sort_values(
        ["year", "submitted_via"]
    ).reset_index(drop=True)


def create_summary(df):
    """Calculate overall channel shares from yearly counts."""
    if df.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    summary = (
        df.groupby("submitted_via", as_index=False)
        ["complaint_count"]
        .sum()
    )

    total = summary["complaint_count"].sum()

    summary["overall_share_pct"] = (
        (100 * summary["complaint_count"] / total).round(2)
        if total > 0
        else None
    )

    return summary.sort_values(
        "complaint_count",
        ascending=False
    )


def create_charts(df):
    """Generate count and share charts from yearly aggregates."""

    # Use one row per calendar year and submission channel.
    share_table = df.pivot(
        index="year",
        columns="submitted_via",
        values="channel_share_pct"
    ).fillna(0)

    count_table = df.pivot(
        index="year",
        columns="submitted_via",
        values="complaint_count"
    ).fillna(0)

    # ------------------------------------------
    # CHART 1: SUBMISSION CHANNEL PERCENTAGES
    # ------------------------------------------

    fig, ax = plt.subplots(figsize=(12, 6))

    share_table.plot(
        kind="bar",
        stacked=True,
        ax=ax
    )

    ax.set_title("Complaint Submission Channels by Year")
    ax.set_xlabel("Calendar Year")
    ax.set_ylabel("Share of Complaints (%)")
    ax.set_ylim(0, 100)

    ax.legend(
        title="Submission Channel",
        bbox_to_anchor=(1.02, 1),
        loc="upper left"
    )

    save_chart(fig, "q3_channel_shares.png")

    # ------------------------------------------
    # CHART 2: SUBMISSION CHANNEL COUNTS
    # ------------------------------------------

    fig, ax = plt.subplots(figsize=(12, 6))

    count_table.plot(
        kind="bar",
        stacked=True,
        ax=ax
    )

    ax.set_title("Published Complaints by Channel and Year")
    ax.set_xlabel("Calendar Year")
    ax.set_ylabel("Complaint Count")

    ax.legend(
        title="Submission Channel",
        bbox_to_anchor=(1.02, 1),
        loc="upper left"
    )

    save_chart(fig, "q3_channel_counts.png")


def run():
    """Execute the Q3 analysis and save its outputs."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting Q3: Submission Channel Analysis")

    mongo_uri = os.getenv(
        "MONGO_URI", "mongodb://mongo:27017"
    )

    database_name = os.getenv(
        "MONGO_DB", "cfpb_money_transfers"
    )

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")

        database = client[database_name]

        # Let MongoDB calculate the actual channel shares.
        records = a4_channel_share_by_year(
            database, {}
        )

    finally:
        client.close()

    # Remove old charts from earlier runs.
    for filename in [
        "q3_channel_shares.png",
        "q3_channel_counts.png"
    ]:
        chart_path = OUTPUT_DIR / filename

        if chart_path.exists():
            chart_path.unlink()

    yearly_df = prepare_yearly_data(records)

    yearly_df.to_csv(
        OUTPUT_DIR / "q3_channels_yearly.csv",
        index=False
    )

    if yearly_df.empty:
        pd.DataFrame(
            columns=SUMMARY_COLUMNS
        ).to_csv(
            OUTPUT_DIR / "q3_channels_summary.csv",
            index=False
        )

        print("No submission channel data available.")
        print("Created empty Q3 CSV files with headers.")
        print("No PNG charts were generated.")
        return

    summary_df = create_summary(yearly_df)

    summary_df.to_csv(
        OUTPUT_DIR / "q3_channels_summary.csv",
        index=False
    )

    create_charts(yearly_df)

    # The current calendar year is incomplete.
    current_year = datetime.now(timezone.utc).year

    if current_year in yearly_df["year"].values:
        print(
            f"Note: {current_year} is a partial calendar year."
        )

    print("Q3 completed successfully.")
    print("CSV and PNG outputs saved in analytics/output/")

    print(
        "Interpretation: changes in submission channels "
        "may reflect CFPB intake procedures rather than "
        "consumer preferences."
    )


if __name__ == "__main__":
    run()
