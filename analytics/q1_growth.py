
"""
Q1: Growth of money transfers and digital payment complaints.

Data source: MongoDB curated complaints.
Outputs: CSV tables and PNG charts in analytics/output/.

No fabricated complaints or statistics are used.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient

from database.queries import a1_monthly_volume, build_match


OUTPUT_DIR = Path("analytics/output")

MONTHLY_COLUMNS = [
    "year_month", "sub_product_std",
    "complaint_count", "mom_pct", "yoy_pct"
]

ISSUE_COLUMNS = [
    "year_month", "issue", "complaint_count"
]


def save_chart(fig, filename):
    """Save a figure and close it."""
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def calculate_growth(current, previous):
    """Percentage change when the previous count is positive."""
    if previous is None or previous == 0:
        return None

    return round(100 * (current - previous) / previous, 2)


def load_issue_monthly(db):
    """Aggregate monthly complaint counts by issue in MongoDB."""
    pipeline = [
        {"$match": build_match({})},
        {
            "$group": {
                "_id": {
                    "month": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$date_received",
                            "timezone": "UTC"
                        }
                    },
                    "issue": {
                        "$ifNull": ["$issue", "Unknown"]
                    }
                },
                "complaint_count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "year_month": "$_id.month",
                "issue": "$_id.issue",
                "complaint_count": 1
            }
        },
        {
            "$sort": {
                "year_month": 1,
                "issue": 1
            }
        }
    ]

    return list(db.complaints.aggregate(pipeline))


def run():
    """Execute Q1 and export reproducible results."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting Q1: Complaint Growth Analysis")

    uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
    database_name = os.getenv(
        "MONGO_DB", "cfpb_money_transfers"
    )

    client = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")
        db = client[database_name]

        # Christopher's aggregation calculates monthly
        # counts, month-on-month and year-on-year changes.
        monthly_records = a1_monthly_volume(db, {})

        monthly_df = pd.DataFrame(
            monthly_records,
            columns=MONTHLY_COLUMNS
        )

        # Issue counts are also aggregated in MongoDB.
        issue_records = load_issue_monthly(db)

        issue_df = pd.DataFrame(
            issue_records,
            columns=ISSUE_COLUMNS
        )

    finally:
        client.close()

    # Remove old Q1 charts so they cannot be mistaken
    # for results from this execution.
    for filename in [
        "q1_monthly_growth.png",
        "q1_wallet_share.png"
    ]:
        old_chart = OUTPUT_DIR / filename

        if old_chart.exists():
            old_chart.unlink()

    # Save the raw aggregated tables.
    monthly_df.to_csv(
        OUTPUT_DIR / "q1_monthly_subproducts.csv",
        index=False
    )

    issue_df.to_csv(
        OUTPUT_DIR / "q1_monthly_issues.csv",
        index=False
    )

    if monthly_df.empty:
        pd.DataFrame(
            columns=[
                "year_month",
                "total_complaints",
                "wallet_complaints",
                "wallet_share_pct"
            ]
        ).to_csv(
            OUTPUT_DIR / "q1_wallet_share.csv",
            index=False
        )

        pd.DataFrame(
            columns=[
                "year",
                "issue",
                "complaint_count",
                "previous_year_count",
                "yoy_pct"
            ]
        ).to_csv(
            OUTPUT_DIR / "q1_issue_yearly_growth.csv",
            index=False
        )

        print("No complaint records found in MongoDB.")
        print("Created empty Q1 CSV files with headers.")
        print("No statistical charts were generated.")
        return

    # --------------------------------------------------
    # MONTHLY COMPLAINT VOLUME
    # --------------------------------------------------

    monthly_df["complaint_count"] = pd.to_numeric(
        monthly_df["complaint_count"]
    )

    monthly_totals = (
        monthly_df.groupby(
            "year_month",
            as_index=False
        )["complaint_count"]
        .sum()
        .sort_values("year_month")
    )

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        monthly_totals["year_month"],
        monthly_totals["complaint_count"],
        marker="o",
        markersize=3
    )

    ax.set_title("Monthly Complaint Volume")
    ax.set_xlabel("Month")
    ax.set_ylabel("Published Complaints")
    ax.grid(True, alpha=0.3)

    # Avoid overcrowding the month labels.
    step = max(1, len(monthly_totals) // 12)
    ax.set_xticks(
        range(0, len(monthly_totals), step)
    )
    ax.set_xticklabels(
        monthly_totals["year_month"].iloc[::step],
        rotation=45,
        ha="right"
    )

    save_chart(fig, "q1_monthly_growth.png")

    # --------------------------------------------------
    # MOBILE / DIGITAL WALLET SHARE
    # --------------------------------------------------

    # Wallet labels are identified from the standardized
    # sub-product field, not from invented records.
    wallet_rows = monthly_df[
        monthly_df["sub_product_std"]
        .fillna("")
        .str.contains("wallet", case=False, regex=False)
    ]

    wallet_counts = (
        wallet_rows.groupby("year_month")[
            "complaint_count"
        ]
        .sum()
    )

    wallet_df = monthly_totals.rename(
        columns={
            "complaint_count": "total_complaints"
        }
    ).copy()

    wallet_df["wallet_complaints"] = (
        wallet_df["year_month"]
        .map(wallet_counts)
        .fillna(0)
        .astype(int)
    )

    wallet_df["wallet_share_pct"] = (
        100
        * wallet_df["wallet_complaints"]
        / wallet_df["total_complaints"]
    ).round(2)

    wallet_df.to_csv(
        OUTPUT_DIR / "q1_wallet_share.csv",
        index=False
    )

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        wallet_df["year_month"],
        wallet_df["wallet_share_pct"],
        marker="o",
        markersize=3
    )

    ax.set_title(
        "Mobile / Digital Wallet Share of Complaints"
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("Share of Domain Complaints (%)")
    ax.set_ylim(bottom=0, top=100)
    ax.grid(True, alpha=0.3)

    step = max(1, len(wallet_df) // 12)
    ax.set_xticks(
        range(0, len(wallet_df), step)
    )
    ax.set_xticklabels(
        wallet_df["year_month"].iloc[::step],
        rotation=45,
        ha="right"
    )

    save_chart(fig, "q1_wallet_share.png")

    # --------------------------------------------------
    # YEARLY ISSUE GROWTH
    # --------------------------------------------------

    if not issue_df.empty:
        issue_df["year"] = (
            issue_df["year_month"]
            .str.slice(0, 4)
            .astype(int)
        )

        # Exclude the current incomplete calendar year.
        current_year = datetime.now(timezone.utc).year

        complete_issues = issue_df[
            issue_df["year"] < current_year
        ].copy()

        yearly_issues = (
            complete_issues.groupby(
                ["year", "issue"],
                as_index=False
            )["complaint_count"]
            .sum()
        )

        # Compare adjacent complete calendar years.
        previous = yearly_issues[
            ["year", "issue", "complaint_count"]
        ].copy()

        previous["year"] += 1
        previous = previous.rename(
            columns={
                "complaint_count": "previous_year_count"
            }
        )

        yearly_issues = yearly_issues.merge(
            previous,
            on=["year", "issue"],
            how="left"
        )

        yearly_issues["yoy_pct"] = [
            calculate_growth(current, prior)
            for current, prior in zip(
                yearly_issues["complaint_count"],
                yearly_issues["previous_year_count"]
            )
        ]

        yearly_issues.to_csv(
            OUTPUT_DIR / "q1_issue_yearly_growth.csv",
            index=False
        )

    else:
        pd.DataFrame(
            columns=[
                "year",
                "issue",
                "complaint_count",
                "previous_year_count",
                "yoy_pct"
            ]
        ).to_csv(
            OUTPUT_DIR / "q1_issue_yearly_growth.csv",
            index=False
        )

    print("Q1 completed.")
    print("CSV and PNG results saved in analytics/output/")
    print(
        "Interpretation: complaint growth does not "
        "establish growth in usage or harm."
    )


if __name__ == "__main__":
    run()
