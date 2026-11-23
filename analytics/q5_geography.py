
"""
Q5: Geographic complaint analysis.

Uses Christopher's MongoDB query:
a8_state_issue_profile()

Outputs:
- q5_state_issue_profiles.csv
- q5_state_totals.csv
- q5_state_counts.png
- q5_issue_share_heatmap.png

The analysis describes published complaints.
It does not calculate population-adjusted risk.
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient

from database.queries import a8_state_issue_profile


OUTPUT_DIR = Path("analytics/output")

ISSUE_COLUMNS = [
    "state",
    "issue",
    "complaint_count",
    "state_total",
    "issue_share_within_state_pct"
]

STATE_COLUMNS = [
    "state",
    "total_complaints",
    "share_of_all_complaints_pct"
]


def save_chart(fig, filename):
    """Save a PNG chart and close the figure."""
    fig.tight_layout()
    fig.savefig(
        OUTPUT_DIR / filename,
        dpi=150,
        bbox_inches="tight"
    )
    plt.close(fig)


def clean_label(value):
    """Represent missing categories as Unknown."""
    if value is None or str(value).strip() == "":
        return "Unknown"

    return str(value)


def prepare_issue_data(records):
    """Convert MongoDB aggregated results into a table."""
    df = pd.DataFrame(records, columns=ISSUE_COLUMNS)

    if df.empty:
        return df

    df["state"] = df["state"].apply(clean_label)
    df["issue"] = df["issue"].apply(clean_label)

    df["complaint_count"] = pd.to_numeric(
        df["complaint_count"]
    )

    df["state_total"] = pd.to_numeric(
        df["state_total"]
    )

    df["issue_share_within_state_pct"] = pd.to_numeric(
        df["issue_share_within_state_pct"],
        errors="coerce"
    )

    return df.sort_values(
        ["state", "complaint_count"],
        ascending=[True, False]
    ).reset_index(drop=True)


def prepare_state_totals(issue_df):
    """
    Obtain one total per state.

    Christopher's query repeats state_total for
    each issue, so we must not sum that column.
    """
    if issue_df.empty:
        return pd.DataFrame(columns=STATE_COLUMNS)

    state_df = (
        issue_df[
            ["state", "state_total"]
        ]
        .drop_duplicates(subset=["state"])
        .rename(
            columns={
                "state_total": "total_complaints"
            }
        )
        .copy()
    )

    all_complaints = state_df[
        "total_complaints"
    ].sum()

    if all_complaints > 0:
        state_df[
            "share_of_all_complaints_pct"
        ] = (
            100
            * state_df["total_complaints"]
            / all_complaints
        ).round(2)

    else:
        state_df[
            "share_of_all_complaints_pct"
        ] = None

    return state_df.sort_values(
        "total_complaints",
        ascending=False
    ).reset_index(drop=True)


def create_state_chart(state_df):
    """Chart the 15 largest state complaint counts."""

    # Keep Unknown in the CSV, but not on the
    # geographic state comparison chart.
    chart_df = state_df[
        state_df["state"] != "Unknown"
    ].head(15)

    if chart_df.empty:
        return

    fig, ax = plt.subplots(figsize=(11, 7))

    ax.barh(
        chart_df["state"],
        chart_df["total_complaints"]
    )

    ax.invert_yaxis()

    ax.set_title(
        "15 States with the Most Published Complaints"
    )

    ax.set_xlabel("Complaint Count")
    ax.set_ylabel("State")

    save_chart(
        fig,
        "q5_state_counts.png"
    )


def create_issue_heatmap(issue_df, state_df):
    """
    Show the within-state issue percentages.

    Select the 15 largest state categories and
    the 8 most common issues for readability.
    """

    selected_states = (
        state_df[
            state_df["state"] != "Unknown"
        ]
        .head(15)["state"]
        .tolist()
    )

    if not selected_states:
        return

    selected_rows = issue_df[
        issue_df["state"].isin(selected_states)
    ].copy()

    if selected_rows.empty:
        return

    # Counts are already aggregated by MongoDB.
    top_issues = (
        selected_rows.groupby("issue")[
            "complaint_count"
        ]
        .sum()
        .sort_values(ascending=False)
        .head(8)
        .index
        .tolist()
    )

    selected_rows = selected_rows[
        selected_rows["issue"].isin(top_issues)
    ]

    heatmap = selected_rows.pivot(
        index="state",
        columns="issue",
        values="issue_share_within_state_pct"
    )

    heatmap = heatmap.reindex(
        index=selected_states,
        columns=top_issues
    ).fillna(0)

    if heatmap.empty:
        return

    fig, ax = plt.subplots(figsize=(13, 8))

    image = ax.imshow(
        heatmap.to_numpy(),
        aspect="auto",
        vmin=0,
        vmax=100
    )

    ax.set_xticks(range(len(heatmap.columns)))
    ax.set_xticklabels(
        heatmap.columns,
        rotation=45,
        ha="right"
    )

    ax.set_yticks(range(len(heatmap.index)))
    ax.set_yticklabels(heatmap.index)

    ax.set_title(
        "Issue Share Within Each State (%)"
    )

    ax.set_xlabel("Issue")
    ax.set_ylabel("State")

    fig.colorbar(
        image,
        ax=ax,
        label="Share of State Complaints (%)"
    )

    save_chart(
        fig,
        "q5_issue_share_heatmap.png"
    )


def run():
    """Execute Q5 and export CSV and PNG results."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("Starting Q5: Geography Analysis")

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

        # MongoDB computes the actual counts
        # and percentages for each state and issue.
        records = a8_state_issue_profile(
            database,
            {}
        )

    finally:
        client.close()

    # Remove previous charts to prevent
    # stale PNG files from being displayed.
    for filename in [
        "q5_state_counts.png",
        "q5_issue_share_heatmap.png"
    ]:
        previous = OUTPUT_DIR / filename

        if previous.exists():
            previous.unlink()

    issue_df = prepare_issue_data(records)

    state_df = prepare_state_totals(
        issue_df
    )

    # Save the aggregated data tables.
    issue_df.to_csv(
        OUTPUT_DIR / "q5_state_issue_profiles.csv",
        index=False
    )

    state_df.to_csv(
        OUTPUT_DIR / "q5_state_totals.csv",
        index=False
    )

    if issue_df.empty:
        print("No geographic complaint data available.")
        print("Created empty Q5 CSV files with headers.")
        print("No PNG charts were generated.")
        return

    create_state_chart(state_df)

    create_issue_heatmap(
        issue_df,
        state_df
    )

    # Report the number of complaints with
    # missing geographic information.
    unknown_rows = state_df[
        state_df["state"] == "Unknown"
    ]

    if not unknown_rows.empty:
        unknown_count = int(
            unknown_rows["total_complaints"].iloc[0]
        )

        print(
            "Complaints with Unknown state:",
            unknown_count
        )

    print("Q5 completed successfully.")
    print("Results saved in analytics/output/")

    print(
        "Interpretation: geographic complaint counts "
        "are not normalized by population or usage."
    )


if __name__ == "__main__":
    run()
