
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.db import cached_query
from dashboard.components.filters import show_filters

from database.queries import (
    a2_issue_subissue_share,
    a3_fraud_share,
    ml_emerging_issues,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("Issues and Fraud Trends")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "Explore reported issues, compare fraud-or-scam "
    "complaint shares, and identify emerging issues."
)

selected_filters = show_filters()

st.divider()


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def show_caution(section_title):
    """Display the relevant caution from Loutchiana's file."""
    path = (
        Path(__file__).resolve().parents[1]
        / "content"
        / "cautions.md"
    )

    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    for index, line in enumerate(lines):
        if section_title in line:
            for next_line in lines[index + 1:]:
                if next_line.strip():
                    if next_line.startswith("**"):
                        break
                    st.caption(next_line.strip())
                    return


def get_label(value):
    """Replace missing category names with Unknown."""
    if value is None or str(value).strip() == "":
        return "Unknown"

    return str(value)


def show_no_data():
    st.info(
        "No complaint data is available for the selected "
        "filters. Charts will appear when matching records "
        "are available in MongoDB."
    )


# --------------------------------------------------
# LOAD ISSUE AND SUB-ISSUE DATA
# --------------------------------------------------

issue_data = cached_query(
    "a2_issue_subissue_share",
    selected_filters,
    a2_issue_subissue_share
)

if isinstance(issue_data, list) and issue_data:
    issue_df = pd.DataFrame(issue_data)

    for column in [
        "sub_product_std",
        "issue",
        "sub_issue"
    ]:
        issue_df[column] = issue_df[column].apply(get_label)

else:
    issue_df = pd.DataFrame()


# --------------------------------------------------
# SECTION 1: ISSUE COMPOSITION
# --------------------------------------------------

st.header("Issue Composition")

st.write(
    "Complaint counts and issue shares within each "
    "selected sub-product."
)

if issue_df.empty:
    show_no_data()

else:
    # Christopher's query returns one row per sub-issue.
    # The issue total is repeated on those rows.
    # Keep only one row per sub-product and issue.
    issue_summary = (
        issue_df[
            [
                "sub_product_std",
                "issue",
                "issue_total_count",
                "issue_share_pct"
            ]
        ]
        .drop_duplicates(
            subset=["sub_product_std", "issue"]
        )
        .sort_values(
            "issue_total_count",
            ascending=False
        )
    )

    fig_issues = px.bar(
        issue_summary,
        x="issue",
        y="issue_total_count",
        color="sub_product_std",
        barmode="group",
        title="Complaints by Issue and Sub-Product",
        labels={
            "issue": "Issue",
            "issue_total_count": "Complaint Count",
            "sub_product_std": "Sub-Product"
        },
        hover_data={
            "issue_share_pct": ":.2f"
        }
    )

    fig_issues.update_layout(
        xaxis_tickangle=-35,
        legend_title_text="Sub-Product"
    )

    st.plotly_chart(
        fig_issues,
        use_container_width=True
    )

    st.caption(
        "Issue share is calculated within each "
        "sub-product and the selected filters."
    )

    with st.expander("View Issue Counts and Percentages"):
        st.dataframe(
            issue_summary.rename(
                columns={
                    "sub_product_std": "Sub-Product",
                    "issue": "Issue",
                    "issue_total_count": "Complaint Count",
                    "issue_share_pct": "Issue Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# SECTION 2: SUB-ISSUE COMPOSITION
# --------------------------------------------------

st.divider()
st.header("Sub-Issue Composition")

st.write(
    "Sub-issue counts and their shares within "
    "the corresponding parent issue."
)

if issue_df.empty:
    show_no_data()

else:
    # Select which issue to inspect.
    available_issues = sorted(
        issue_df["issue"].unique().tolist()
    )

    chosen_issue = st.selectbox(
        "Choose an issue to inspect its sub-issues",
        available_issues,
        key="sub_issue_parent"
    )

    subissue_df = issue_df[
        issue_df["issue"] == chosen_issue
    ].copy()

    subissue_summary = (
        subissue_df.groupby(
            ["sub_product_std", "sub_issue"],
            as_index=False
        )
        .agg(
            complaint_count=("complaint_count", "sum")
        )
    )

    # Calculate shares separately within each sub-product.
    totals = subissue_summary.groupby(
        "sub_product_std"
    )["complaint_count"].transform("sum")

    subissue_summary["share_pct"] = (
        100 * subissue_summary["complaint_count"] / totals
    ).round(2)

    fig_subissues = px.bar(
        subissue_summary,
        x="sub_issue",
        y="complaint_count",
        color="sub_product_std",
        barmode="group",
        title=f"Sub-Issues Within: {chosen_issue}",
        labels={
            "sub_issue": "Sub-Issue",
            "complaint_count": "Complaint Count",
            "sub_product_std": "Sub-Product"
        },
        hover_data={
            "share_pct": ":.2f"
        }
    )

    fig_subissues.update_layout(
        xaxis_tickangle=-35
    )

    st.plotly_chart(
        fig_subissues,
        use_container_width=True
    )

    st.caption(
        "Missing sub-issue categories are shown as Unknown. "
        "Percentages use the parent issue's complaints "
        "within each sub-product as the denominator."
    )

    with st.expander("View Sub-Issue Counts and Percentages"):
        st.dataframe(
            subissue_summary.rename(
                columns={
                    "sub_product_std": "Sub-Product",
                    "sub_issue": "Sub-Issue",
                    "complaint_count": "Complaint Count",
                    "share_pct": "Share Within Issue (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# SECTION 3: FRAUD OR SCAM SHARE
# --------------------------------------------------

st.divider()
st.header("Fraud or Scam Share")

st.write(
    "Monthly fraud-or-scam complaint shares "
    "across the core payment sub-products."
)

fraud_data = cached_query(
    "a3_fraud_share",
    selected_filters,
    a3_fraud_share
)

if not isinstance(fraud_data, list) or not fraud_data:
    show_no_data()

else:
    fraud_df = pd.DataFrame(fraud_data)

    fraud_df["sub_product_std"] = (
        fraud_df["sub_product_std"].apply(get_label)
    )

    fraud_df = fraud_df.sort_values(
        ["year_month", "sub_product_std"]
    )

    # Monthly share chart
    fig_monthly = px.line(
        fraud_df,
        x="year_month",
        y="fraud_share_pct",
        color="sub_product_std",
        markers=True,
        title="Monthly Fraud-or-Scam Complaint Share",
        labels={
            "year_month": "Month",
            "fraud_share_pct": "Fraud-or-Scam Share (%)",
            "sub_product_std": "Sub-Product"
        }
    )

    fig_monthly.update_layout(
        yaxis_ticksuffix="%"
    )

    st.plotly_chart(
        fig_monthly,
        use_container_width=True
    )

    st.caption(
        "Monthly share = complaints classified as "
        "Fraud or scam / all complaints in that "
        "sub-product and month."
    )

    # Rolling 12-month share chart
    st.subheader("Rolling 12-Month Fraud-or-Scam Share")

    fig_rolling = px.line(
        fraud_df,
        x="year_month",
        y="rolling_12m_share_pct",
        color="sub_product_std",
        title="Rolling 12-Month Fraud-or-Scam Share",
        labels={
            "year_month": "Month",
            "rolling_12m_share_pct": "Rolling Share (%)",
            "sub_product_std": "Sub-Product"
        }
    )

    fig_rolling.update_layout(
        yaxis_ticksuffix="%"
    )

    st.plotly_chart(
        fig_rolling,
        use_container_width=True
    )

    st.caption(
        "The rolling share uses the sum of fraud-or-scam "
        "complaints divided by all complaints in the "
        "preceding 12-month window. At the start of "
        "the selected range, fewer months may be available."
    )

    with st.expander("View Fraud-or-Scam Data"):
        st.dataframe(
            fraud_df[
                [
                    "year_month",
                    "sub_product_std",
                    "complaint_count",
                    "fraud_count",
                    "fraud_share_pct",
                    "rolling_12m_share_pct"
                ]
            ].rename(
                columns={
                    "year_month": "Month",
                    "sub_product_std": "Sub-Product",
                    "complaint_count": "Total Complaints",
                    "fraud_count": "Fraud-or-Scam Complaints",
                    "fraud_share_pct": "Monthly Share (%)",
                    "rolling_12m_share_pct": "Rolling 12M Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

show_caution(
    "Q2. Fraud-or-scam share across the four core sub-products"
)


# --------------------------------------------------
# SECTION 4: MACHINE LEARNING
# --------------------------------------------------

st.divider()

st.header("Emerging Issues (Machine Learning)")

st.write(
    "The emerging-issues analysis uses Apache Spark MLlib "
    "LinearRegression to examine issue shares over "
    "the last 24 complete months."
)

st.markdown(
    """
    **Classification rules**

    An issue is classified as emerging when:

    - Its monthly share rises by at least **0.2 percentage points per month**.
    - Its regression **R-squared is at least 0.5**.
    - It has at least **50 complaints** in the analysis window.
    """
)

# The ML query only supports sub-product and issue filters.
# Other sidebar filters must not be passed to this query.
ml_filters = {
    key: value
    for key, value in selected_filters.items()
    if key in ("sub_product_std", "issue")
    and value not in (None, [], "")
}

emerging_data = cached_query(
    "ml_emerging_issues",
    ml_filters,
    ml_emerging_issues
)

if isinstance(emerging_data, list) and emerging_data:

    emerging_df = pd.DataFrame(emerging_data)

    st.success(
        "Precomputed emerging-issues results are available."
    )

    # Display the actual result fields returned by MongoDB.
    # No model output values are invented.
    st.dataframe(
        emerging_df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info(
        "No emerging-issue results are currently available "
        "for the selected ML filters. Results will appear "
        "after the Spark MLlib analysis has run and "
        "its output has been loaded into MongoDB."
    )

st.caption(
    "ML results use their fixed historical analysis window. "
    "The dashboard date, state, channel, and company filters "
    "do not change these precomputed results."
)

show_caution("Emerging issues (Spark MLlib)")

st.caption(
    "This analysis describes historical complaint patterns. "
    "It does not forecast future complaint volume."
)
