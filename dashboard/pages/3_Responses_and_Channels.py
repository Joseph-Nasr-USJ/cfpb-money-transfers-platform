
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.db import cached_query
from dashboard.components.filters import show_filters

from database.queries import (
    a4_channel_share_by_year,
    a5_response_and_timeliness,
    a6_processing_lag_distribution,
    kpi_summary,
)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def clean_label(value):
    """Display missing categories as Unknown."""
    if value is None or str(value).strip() == "":
        return "Unknown"

    return str(value)


def show_no_data():
    """Show a message when there are no matching records."""
    st.info(
        "No complaint data is available for the selected "
        "filters. Results will appear when matching "
        "records are available in MongoDB."
    )


def show_caution(section_title):
    """Read the relevant caution from Loutchiana's file."""
    path = (
        Path(__file__).resolve().parents[1]
        / "content"
        / "cautions.md"
    )

    if not path.exists():
        return

    lines = path.read_text(encoding="utf-8").splitlines()

    for index, line in enumerate(lines):
        if section_title in line:
            for next_line in lines[index + 1:]:
                if next_line.startswith("**"):
                    break

                if next_line.strip():
                    st.caption(next_line.strip())
                    return


# --------------------------------------------------
# PAGE HEADER AND FILTERS
# --------------------------------------------------

st.title("Company Responses and Submission Channels")

st.subheader("Money Transfers and Digital Payments")

st.write(
    "Explore company response categories, timely-response "
    "rates, processing lag, and how complaints reach the CFPB."
)

selected_filters = show_filters()

st.divider()


# --------------------------------------------------
# LOAD RESPONSE DATA
# --------------------------------------------------

response_data = cached_query(
    "a5_response_and_timeliness",
    selected_filters,
    a5_response_and_timeliness
)

if isinstance(response_data, list) and response_data:
    response_df = pd.DataFrame(response_data)

    response_df["sub_product_std"] = (
        response_df["sub_product_std"].apply(clean_label)
    )

    response_df["company_response"] = (
        response_df["company_response"].apply(clean_label)
    )

else:
    response_df = pd.DataFrame()


# --------------------------------------------------
# SECTION 1: COMPANY RESPONSE CATEGORIES
# --------------------------------------------------

st.header("Company Response Categories")

st.write(
    "Complaint counts and percentages for each "
    "company response category, grouped by sub-product."
)

if response_df.empty:
    show_no_data()

else:
    fig_response = px.bar(
        response_df,
        x="sub_product_std",
        y="complaint_count",
        color="company_response",
        barmode="stack",
        title="Company Response Categories by Sub-Product",
        labels={
            "sub_product_std": "Sub-Product",
            "complaint_count": "Complaint Count",
            "company_response": "Response Category"
        },
        hover_data={
            "response_share_pct": ":.2f"
        }
    )

    fig_response.update_layout(
        xaxis_tickangle=-25,
        legend_title_text="Response Category"
    )

    st.plotly_chart(
        fig_response,
        use_container_width=True
    )

    st.caption(
        "Response share uses all complaints in each "
        "sub-product, including In progress and Unknown."
    )

    # Show the closed-outcome percentages separately.
    st.subheader("Closed-Outcome Shares")

    closed_df = response_df[
        ~response_df["company_response"].isin(
            ["In progress", "Unknown"]
        )
    ].copy()

    if closed_df.empty:
        st.info(
            "No closed response categories are available "
            "for the selected filters."
        )

    else:
        fig_closed = px.bar(
            closed_df,
            x="sub_product_std",
            y="closed_response_share_pct",
            color="company_response",
            barmode="stack",
            title="Closed-Outcome Response Shares",
            labels={
                "sub_product_std": "Sub-Product",
                "closed_response_share_pct": "Closed-Outcome Share (%)",
                "company_response": "Response Category"
            }
        )

        fig_closed.update_layout(
            yaxis_ticksuffix="%",
            xaxis_tickangle=-25
        )

        st.plotly_chart(
            fig_closed,
            use_container_width=True
        )

        st.caption(
            "Closed-outcome shares exclude In progress "
            "and Unknown from the denominator."
        )

    with st.expander("View Response Category Data"):
        st.dataframe(
            response_df[
                [
                    "sub_product_std",
                    "company_response",
                    "complaint_count",
                    "response_share_pct",
                    "closed_response_share_pct"
                ]
            ].rename(
                columns={
                    "sub_product_std": "Sub-Product",
                    "company_response": "Response Category",
                    "complaint_count": "Complaint Count",
                    "response_share_pct": "Response Share (%)",
                    "closed_response_share_pct": "Closed Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


show_caution(
    "Q4. Response categories and timely-response rates"
)


# --------------------------------------------------
# SECTION 2: TIMELY RESPONSE PERCENTAGE
# --------------------------------------------------

st.divider()
st.header("Timely Response Percentage")

st.write(
    "Timely-response percentage uses only complaints "
    "where the response flag is Yes or No."
)

st.code(
    "Timely % = Timely Yes / (Timely Yes + Timely No) * 100",
    language="text"
)

if response_df.empty:
    show_no_data()

else:
    # Christopher's query repeats the sub-product's
    # timely totals for every response category.
    # Keep one row per sub-product to avoid double counting.
    timely_df = (
        response_df[
            [
                "sub_product_std",
                "timely_pct",
                "timely_yes_count",
                "timely_known_count"
            ]
        ]
        .drop_duplicates(subset=["sub_product_std"])
        .copy()
    )

    timely_df["timely_no_count"] = (
        timely_df["timely_known_count"]
        - timely_df["timely_yes_count"]
    )

    # Total complaints per sub-product must be computed
    # from its different response categories.
    product_totals = (
        response_df.groupby("sub_product_std")[
            "complaint_count"
        ]
        .sum()
        .reset_index(name="total_complaints")
    )

    timely_df = timely_df.merge(
        product_totals,
        on="sub_product_std",
        how="left"
    )

    timely_df["unknown_count"] = (
        timely_df["total_complaints"]
        - timely_df["timely_known_count"]
    )

    fig_timely = px.bar(
        timely_df,
        x="sub_product_std",
        y="timely_pct",
        title="Timely Response Percentage by Sub-Product",
        labels={
            "sub_product_std": "Sub-Product",
            "timely_pct": "Timely Responses (%)"
        },
        text="timely_pct"
    )

    fig_timely.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside"
    )

    fig_timely.update_layout(
        yaxis_range=[0, 105],
        yaxis_ticksuffix="%",
        xaxis_tickangle=-25
    )

    st.plotly_chart(
        fig_timely,
        use_container_width=True
    )

    st.caption(
        "Unknown includes missing or invalid timely-response "
        "flags. These are excluded from the percentage denominator."
    )

    with st.expander("View Timely Response Counts"):
        st.dataframe(
            timely_df[
                [
                    "sub_product_std",
                    "total_complaints",
                    "timely_yes_count",
                    "timely_no_count",
                    "unknown_count",
                    "timely_pct"
                ]
            ].rename(
                columns={
                    "sub_product_std": "Sub-Product",
                    "total_complaints": "Total Complaints",
                    "timely_yes_count": "Timely Yes",
                    "timely_no_count": "Timely No",
                    "unknown_count": "Missing / Invalid",
                    "timely_pct": "Timely (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

st.caption(
    "The timely-response flag does not measure "
    "customer satisfaction or resolution time."
)


# --------------------------------------------------
# SECTION 3: RECEIPT-TO-REFERRAL INTERVAL
# --------------------------------------------------

st.divider()
st.header("Receipt-to-Referral Interval")

st.write(
    "Processing lag measures calendar days between "
    "the CFPB receiving a complaint and referring "
    "it to the company."
)

summary = cached_query(
    "kpi_summary",
    selected_filters,
    kpi_summary
)

lag_data = cached_query(
    "a6_processing_lag_distribution",
    selected_filters,
    a6_processing_lag_distribution
)

if isinstance(summary, dict):
    lag = summary.get("median_processing_lag_days")

    if lag is not None:
        st.metric(
            "Median Processing Lag",
            f"{lag:.1f} days"
        )
    else:
        st.metric(
            "Median Processing Lag",
            "N/A"
        )
else:
    st.metric(
        "Median Processing Lag",
        "N/A"
    )


if not isinstance(lag_data, list) or not lag_data:
    show_no_data()

else:
    lag_df = pd.DataFrame(lag_data)

    lag_df = lag_df.sort_values("sort_order")

    fig_lag = px.bar(
        lag_df,
        x="bucket_label",
        y="complaint_count",
        title="Distribution of Processing Lag",
        labels={
            "bucket_label": "Processing Lag",
            "complaint_count": "Complaint Count"
        },
        text="complaint_count",
        hover_data={
            "share_pct": ":.2f"
        }
    )

    fig_lag.update_layout(
        xaxis_categoryorder="array",
        xaxis_categoryarray=[
            "0 days",
            "1 day",
            "2-3 days",
            "4-7 days",
            "8-14 days",
            "15+days"
        ]
    )

    st.plotly_chart(
        fig_lag,
        use_container_width=True
    )

    st.caption(
        "Only valid, non-negative processing-lag "
        "values are included in the distribution."
    )

    with st.expander("View Processing Lag Data"):
        st.dataframe(
            lag_df[
                [
                    "bucket_label",
                    "complaint_count",
                    "share_pct"
                ]
            ].rename(
                columns={
                    "bucket_label": "Processing Lag",
                    "complaint_count": "Complaint Count",
                    "share_pct": "Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# Calculate how many complaints were excluded from
# the valid, non-negative processing-lag distribution.
if isinstance(summary, dict):
    total_complaints = summary.get("total_complaints")

    if total_complaints is not None:
        valid_lag_count = (
            sum(row["complaint_count"] for row in lag_data)
            if isinstance(lag_data, list)
            else 0
        )

        excluded_count = (
            total_complaints - valid_lag_count
        )

        st.caption(
            f"Complaints without a valid non-negative "
            f"processing lag: {excluded_count:,}"
        )

st.warning(
    "Processing lag is not the time taken by a company "
    "to resolve a complaint."
)

show_caution("Processing lag chart")


# --------------------------------------------------
# SECTION 4: SUBMISSION CHANNELS
# --------------------------------------------------

st.divider()
st.header("Submission Channels")

st.write(
    "Explore how published complaints reached the "
    "CFPB and how the submission-channel mix changed "
    "across calendar years."
)

channel_data = cached_query(
    "a4_channel_share_by_year",
    selected_filters,
    a4_channel_share_by_year
)

if not isinstance(channel_data, list) or not channel_data:
    show_no_data()

else:
    channel_df = pd.DataFrame(channel_data)

    channel_df["submitted_via"] = (
        channel_df["submitted_via"].apply(clean_label)
    )

    channel_df = channel_df.sort_values(
        ["year", "submitted_via"]
    )

    # 100% stacked bar chart of channel shares
    fig_channels = px.bar(
        channel_df,
        x="year",
        y="channel_share_pct",
        color="submitted_via",
        barmode="stack",
        title="Submission Channel Share by Year",
        labels={
            "year": "Calendar Year",
            "channel_share_pct": "Channel Share (%)",
            "submitted_via": "Submission Channel"
        },
        hover_data={
            "complaint_count": True
        }
    )

    fig_channels.update_layout(
        yaxis_ticksuffix="%",
        legend_title_text="Submission Channel",
        xaxis_type="category"
    )

    st.plotly_chart(
        fig_channels,
        use_container_width=True
    )

    st.caption(
        "Each year's channel shares add up to 100% "
        "within the selected filters. The current year "
        "may be incomplete."
    )

    st.subheader("Submission Channel Counts")

    fig_counts = px.bar(
        channel_df,
        x="year",
        y="complaint_count",
        color="submitted_via",
        barmode="stack",
        title="Complaints by Channel and Year",
        labels={
            "year": "Calendar Year",
            "complaint_count": "Complaint Count",
            "submitted_via": "Submission Channel"
        }
    )

    fig_counts.update_layout(
        xaxis_type="category"
    )

    st.plotly_chart(
        fig_counts,
        use_container_width=True
    )

    with st.expander("View Submission Channel Data"):
        st.dataframe(
            channel_df[
                [
                    "year",
                    "submitted_via",
                    "complaint_count",
                    "channel_share_pct"
                ]
            ].rename(
                columns={
                    "year": "Year",
                    "submitted_via": "Submission Channel",
                    "complaint_count": "Complaint Count",
                    "channel_share_pct": "Channel Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

show_caution("Q3. Mix of submission channels over time")


# --------------------------------------------------
# FINAL DATA NOTE
# --------------------------------------------------

st.divider()

st.caption(
    "Source: CFPB Consumer Complaint Database. "
    "All results describe published complaints, "
    "not all transactions or consumers."
)
