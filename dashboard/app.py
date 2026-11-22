
import streamlit as st

from dashboard.components.filters import show_filters
from dashboard.components.db import cached_query
from database.queries import kpi_summary


st.set_page_config(
    page_title="Banking Complaints Dashboard",
    page_icon=":bar_chart:",
    layout="wide"
)

# Shared filters
selected_filters = show_filters()

st.title("Banking Complaints Dashboard")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "This dashboard analyses public consumer complaints "
    "published by the Consumer Financial Protection Bureau (CFPB)."
)

st.caption(
    f"Selected period: {selected_filters['date_from']} "
    f"to {selected_filters['date_to']}"
)

st.divider()

# Overview KPIs
st.header("Overview")

# Try Redis first, then MongoDB on a cache miss.
# If Redis is unavailable, query MongoDB directly.
summary = cached_query(
    "kpi_summary",
    selected_filters,
    kpi_summary
)

# Only display results when the database has matching records.
has_data = (
    isinstance(summary, dict)
    and summary.get("total_complaints", 0) > 0
)

if has_data:
    total = f"{summary['total_complaints']:,}"

    yoy = summary.get("yoy_pct")
    yoy_text = f"{yoy:.2f}%" if yoy is not None else "N/A"

    timely = summary.get("timely_pct")
    timely_text = (
        f"{timely:.2f}%" if timely is not None else "N/A"
    )

    lag = summary.get("median_processing_lag_days")
    lag_text = f"{lag:.1f} days" if lag is not None else "N/A"

else:
    total = "N/A"
    yoy_text = "N/A"
    timely_text = "N/A"
    lag_text = "N/A"

    st.info(
        "No complaint records are currently available for "
        "the selected filters, or the data service is unavailable."
    )

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Complaints", total)
    st.caption("Published complaints within the selected filters.")

with col2:
    st.metric("Year-on-Year Change", yoy_text)
    st.caption("Comparison of two complete calendar years.")

with col3:
    st.metric("Timely Responses", timely_text)
    st.caption("Valid Yes / (Valid Yes + Valid No).")

with col4:
    st.metric("Median Processing Lag", lag_text)
    st.caption("Approximate median receipt-to-referral interval.")

st.divider()

st.header("Important Limitations")

st.warning(
    "CFPB complaint counts represent published complaints, "
    "not all financial transactions or consumers. "
    "Complaint volume does not establish market share, "
    "confirmed fraud, or company service quality."
)

st.caption("Data source: CFPB Consumer Complaint Database")
