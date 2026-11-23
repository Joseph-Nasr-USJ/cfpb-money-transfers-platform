
"""
Q2: Fraud-or-scam complaint share analysis.

Uses Christopher's MongoDB aggregation:
a3_fraud_share()

Outputs:
- q2_fraud_monthly.csv
- q2_fraud_summary.csv
- q2_fraud_monthly.png
- q2_fraud_rolling_12m.png

All results come from genuine MongoDB aggregates.
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient

from database.queries import a3_fraud_share


# -----------------------------------------------
# OUTPUT SETTINGS
# -----------------------------------------------

OUTPUT_DIR = Path("analytics/output")

MONTHLY_COLUMNS = [
    "year_month",
    "sub_product_std",
    "complaint_count",
    "fraud_count",
    "fraud_share_pct",
    "rolling_12m_share_pct"
]

SUMMARY_COLUMNS = [
    "sub_product_std",
    "total_complaints",
    "fraud_complaints",
    "overall_fraud_share_pct"
]


# -----------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------

def percentage(part, total):
    """Calculate a percentage with a valid denominator."""
    if total is None or total == 0:
        return None

    return round(100 * part / total, 2)


def save_chart(fig, filename):
    """Save a chart to the analytics output folder."""
    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / filename,
        dpi=150
    )

    plt.close(fig)


def plot_fraud_trends(df, value_column, title, filename):
    """Plot the monthly trend for each sub-product."""

    fig, ax = plt.subplots(figsize=(12, 6))

    for product, group in df.groupby("sub_product_std"):
        group = group.sort_values("year_month")

        ax.plot(
            group["year_month"],
            group[value_column],
            marker="o",
            markersize=2,
            label=product
        )

    ax.set_title(title)
    ax.set_xlabel("Month")
    ax.set_ylabel("Fraud-or-Scam Complaint Share (%)")

    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    # Keep month labels readable.
    months = sorted(df["year_month"].unique())
    step = max(1, len(months) // 12)

    selected_months = months[::step]

    ax.set_xticks(selected_months)
    ax.set_xticklabels(
        selected_months,
        rotation=45,
        ha="right"
    )

    ax.legend(
        title="Sub-Product",
        loc="best"
    )

    save_chart(fig, filename)


# -----------------------------------------------
# MAIN Q2 ANALYSIS
# -----------------------------------------------

def run():
    """Run Q2 and export the results."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("Starting Q2: Fraud-or-Scam Analysis")

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

        # MongoDB calculates the monthly counts,
        # monthly shares and rolling 12-month shares.
        records = a3_fraud_share(
            database,
            {}
        )

    finally:
        client.close()

    # Remove old charts so that previously generated
    # results cannot be confused with the current run.
    for filename in [
        "q2_fraud_monthly.png",
        "q2_fraud_rolling_12m.png"
    ]:
        old_file = OUTPUT_DIR / filename

        if old_file.exists():
            old_file.unlink()

    monthly_df = pd.DataFrame(
        records,
        columns=MONTHLY_COLUMNS
    )

    # -------------------------------------------
    # HANDLE EMPTY MONGODB DATA
    # -------------------------------------------

    if monthly_df.empty:

        monthly_df.to_csv(
            OUTPUT_DIR / "q2_fraud_monthly.csv",
            index=False
        )

        pd.DataFrame(
            columns=SUMMARY_COLUMNS
        ).to_csv(
            OUTPUT_DIR / "q2_fraud_summary.csv",
            index=False
        )

        print("No fraud-or-scam analysis data available.")
        print("Created empty Q2 CSV files with headers.")
        print("No PNG charts were generated.")

        return

    # -------------------------------------------
    # CLEAN AGGREGATED RESULTS
    # -------------------------------------------

    monthly_df["sub_product_std"] = (
        monthly_df["sub_product_std"]
        .fillna("Unknown")
    )

    monthly_df["complaint_count"] = pd.to_numeric(
        monthly_df["complaint_count"]
    )

    monthly_df["fraud_count"] = pd.to_numeric(
        monthly_df["fraud_count"]
    )

    monthly_df = monthly_df.sort_values(
        ["year_month", "sub_product_std"]
    )

    # -------------------------------------------
    # EXPORT MONTHLY DATA
    # -------------------------------------------

    monthly_df.to_csv(
        OUTPUT_DIR / "q2_fraud_monthly.csv",
        index=False
    )

    # -------------------------------------------
    # OVERALL FRAUD SHARE BY SUB-PRODUCT
    # -------------------------------------------

    summary_df = (
        monthly_df.groupby(
            "sub_product_std",
            as_index=False
        )
        .agg(
            total_complaints=(
                "complaint_count",
                "sum"
            ),
            fraud_complaints=(
                "fraud_count",
                "sum"
            )
        )
    )

    summary_df["overall_fraud_share_pct"] = [
        percentage(fraud, total)
        for fraud, total in zip(
            summary_df["fraud_complaints"],
            summary_df["total_complaints"]
        )
    ]

    summary_df = summary_df.sort_values(
        "total_complaints",
        ascending=False
    )

    summary_df.to_csv(
        OUTPUT_DIR / "q2_fraud_summary.csv",
        index=False
    )

    # -------------------------------------------
    # MONTHLY FRAUD SHARE CHART
    # -------------------------------------------

    plot_fraud_trends(
        monthly_df,
        "fraud_share_pct",
        "Monthly Fraud-or-Scam Complaint Share",
        "q2_fraud_monthly.png"
    )

    # -------------------------------------------
    # ROLLING 12-MONTH FRAUD SHARE CHART
    # -------------------------------------------

    plot_fraud_trends(
        monthly_df,
        "rolling_12m_share_pct",
        "Rolling 12-Month Fraud-or-Scam Share",
        "q2_fraud_rolling_12m.png"
    )

    print("Q2 completed successfully.")
    print("Results saved to analytics/output/")

    print(
        "Important: Fraud or scam is a consumer-selected "
        "complaint category, not verified fraud."
    )


if __name__ == "__main__":
    run()
