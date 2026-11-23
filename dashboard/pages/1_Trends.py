
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.filters import show_filters
from dashboard.components.db import cached_query
from database.queries import a1_monthly_volume


# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.title("Complaint Trends")
st.subheader("Money Transfers and Digital Payments")

selected_filters = show_filters()

st.write(
    "Explore how consumer complaint volumes change over time "
    "and compare trends across payment sub-products."
)

st.caption(
    f"Selected period: {selected_filters['date_from']} "
    f"to {selected_filters['date_to']}"
)

st.divider()


# --------------------------------------------------
# GET DATA FROM MONGODB THROUGH REDIS CACHE
# --------------------------------------------------

rows = cached_query(
    "a1_monthly_volume",
    selected_filters,
    a1_monthly_volume
)

if not isinstance(rows, list) or not rows:
    st.info(
        "No complaint trend data is available for the selected filters. "
        "Data may not have been loaded into MongoDB yet."
    )

    st.warning(
        "Complaint volume represents published CFPB complaints. "
        "An increase does not necessarily mean more transactions, "
        "more customers, or a higher rate of financial harm."
    )

    st.stop()


# --------------------------------------------------
# PREPARE DATA
# --------------------------------------------------

df = pd.DataFrame(rows)

required_columns = {
    "year_month",
    "sub_product_std",
    "complaint_count",
    "yoy_pct"
}

if not required_columns.issubset(df.columns):
    st.error(
        "The MongoDB query returned an unexpected format. "
        "Please check database/queries.py."
    )
    st.stop()

df["month"] = pd.to_datetime(
    df["year_month"],
    format="%Y-%m",
    errors="coerce"
)

df["complaint_count"] = pd.to_numeric(
    df["complaint_count"],
    errors="coerce"
)

df["yoy_pct"] = pd.to_numeric(
    df["yoy_pct"],
    errors="coerce"
)

df = df.dropna(subset=["month", "complaint_count"])

if df.empty:
    st.info("No valid monthly complaint records are available.")
    st.stop()

df = df.sort_values(["month", "sub_product_std"])


# --------------------------------------------------
# CHART 1: MONTHLY COMPLAINT VOLUME
# --------------------------------------------------

st.header("Monthly Complaint Volume")

monthly = (
    df.groupby("month", as_index=False)["complaint_count"]
    .sum()
    .sort_values("month")
)

fig_monthly = px.line(
    monthly,
    x="month",
    y="complaint_count",
    markers=True,
    labels={
        "month": "Month",
        "complaint_count": "Number of Complaints"
    },
    title="Published Complaints Over Time"
)

fig_monthly.update_layout(
    hovermode="x unified",
    xaxis_title="Month",
    yaxis_title="Complaint Count"
)

st.plotly_chart(
    fig_monthly,
    use_container_width=True
)

st.caption(
    "Monthly counts are aggregated from published CFPB "
    "complaints matching the selected filters."
)


# --------------------------------------------------
# CHART 2: YEAR-ON-YEAR GROWTH BY SUB-PRODUCT
# --------------------------------------------------

st.header("Year-on-Year Growth by Sub-Product")

growth = df.dropna(subset=["yoy_pct"]).copy()

if growth.empty:
    st.info(
        "Year-on-year growth cannot be calculated for the "
        "selected period because comparable monthly data "
        "is unavailable."
    )

else:
    fig_growth = px.line(
        growth,
        x="month",
        y="yoy_pct",
        color="sub_product_std",
        markers=True,
        labels={
            "month": "Month",
            "yoy_pct": "Year-on-Year Change (%)",
            "sub_product_std": "Sub-Product"
        },
        title="Monthly Year-on-Year Complaint Growth"
    )

    fig_growth.update_layout(
        hovermode="x unified",
        xaxis_title="Month",
        yaxis_title="Year-on-Year Change (%)",
        legend_title="Sub-Product"
    )

    st.plotly_chart(
        fig_growth,
        use_container_width=True
    )

st.caption(
    "Each year-on-year value compares a month's complaint "
    "count with the same month of the previous year for "
    "the same sub-product. Missing comparisons are excluded."
)


# --------------------------------------------------
# CHART 3: MOBILE OR DIGITAL WALLET SHARE
# --------------------------------------------------

st.header("Mobile or Digital Wallet Share")

wallet_name = "Mobile or digital wallet"

if "sub_product_std" in selected_filters:
    st.info(
        "Wallet share of the full domain is not shown when "
        "a sub-product filter is selected, because the "
        "denominator would no longer represent all "
        "sub-products."
    )

else:
    wallet = (
        df[df["sub_product_std"] == wallet_name]
        .groupby("month", as_index=False)["complaint_count"]
        .sum()
        .rename(columns={
            "complaint_count": "wallet_complaints"
        })
    )

    wallet_share = monthly.merge(
        wallet,
        on="month",
        how="left"
    )

    wallet_share["wallet_complaints"] = (
        wallet_share["wallet_complaints"].fillna(0)
    )

    wallet_share["wallet_share_pct"] = (
        wallet_share["wallet_complaints"]
        / wallet_share["complaint_count"]
        * 100
    )

    if wallet_share["wallet_complaints"].sum() == 0:
        st.info(
            "No complaints classified as 'Mobile or digital wallet' "
            "were found in the current selection."
        )

    else:
        fig_wallet = px.line(
            wallet_share,
            x="month",
            y="wallet_share_pct",
            markers=True,
            labels={
                "month": "Month",
                "wallet_share_pct": "Wallet Share (%)"
            },
            title="Mobile or Digital Wallet Share of Complaints"
        )

        fig_wallet.update_layout(
            hovermode="x unified",
            xaxis_title="Month",
            yaxis_title="Percentage of Complaints",
            yaxis_range=[0, 100]
        )

        st.plotly_chart(
            fig_wallet,
            use_container_width=True
        )

    st.caption(
        "Wallet share = mobile or digital wallet complaints "
        "divided by total complaints in the selected domain "
        "for each month. Other selected category filters "
        "still apply."
    )


# --------------------------------------------------
# LIMITATIONS
# --------------------------------------------------

st.divider()

st.warning(
    "Complaint volume represents published CFPB complaints. "
    "An increase does not necessarily mean more transactions, "
    "more customers, or a higher rate of financial harm."
)
