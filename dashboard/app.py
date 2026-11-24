
from pathlib import Path

import streamlit as st

from dashboard.components.filters import show_filters
from dashboard.components.db import cached_query
from database.queries import kpi_summary, freshness


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Banking Complaints Dashboard",
    page_icon=":bar_chart:",
    layout="wide"
)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def load_content(filename):
    """Read the explanatory text written by Loutchiana."""
    content_path = (
        Path(__file__).resolve().parent
        / "content"
        / filename
    )

    if content_path.exists():
        return content_path.read_text(encoding="utf-8")

    return "Content is currently unavailable."


def display_value(value):
    """Display missing values clearly."""
    if value is None or value == "":
        return "N/A"

    return str(value)


# --------------------------------------------------
# SHARED SIDEBAR FILTERS
# --------------------------------------------------

selected_filters = show_filters()


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("Banking Complaints Dashboard")

st.subheader("Money Transfers and Digital Payments")

st.markdown(load_content("overview.md"))

st.caption(
    f"Selected period: "
    f"{selected_filters.get('date_from', 'All dates')} "
    f"to "
    f"{selected_filters.get('date_to', 'All dates')}"
)

st.divider()


# --------------------------------------------------
# OVERVIEW KPIs
# --------------------------------------------------

st.header("Overview")

# Redis cache first; MongoDB on cache miss.
summary = cached_query(
    "kpi_summary",
    selected_filters,
    kpi_summary
)

has_data = (
    isinstance(summary, dict)
    and summary.get("total_complaints", 0) > 0
)

if has_data:
    total = f"{summary['total_complaints']:,}"

    yoy = summary.get("yoy_pct")
    yoy_text = (
        f"{yoy:+.2f}%"
        if yoy is not None
        else "N/A"
    )

    timely = summary.get("timely_pct")
    timely_text = (
        f"{timely:.2f}%"
        if timely is not None
        else "N/A"
    )

    lag = summary.get("median_processing_lag_days")
    lag_text = (
        f"{lag:.1f} days"
        if lag is not None
        else "N/A"
    )

else:
    total = "N/A"
    yoy_text = "N/A"
    timely_text = "N/A"
    lag_text = "N/A"

    st.info(
        "No complaint records are currently available "
        "for the selected filters, or the database "
        "could not return the requested results."
    )


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Complaints",
        total
    )
    st.caption(
        "Number of published complaints matching "
        "the selected filters."
    )

with col2:
    st.metric(
        "Year-on-Year Change",
        yoy_text
    )
    st.caption(
        "Change between the two complete calendar years "
        "used by the database query."
    )

with col3:
    st.metric(
        "Timely Responses",
        timely_text
    )
    st.caption(
        "Yes responses divided by known Yes or No responses."
    )

with col4:
    st.metric(
        "Median Processing Lag",
        lag_text
    )
    st.caption(
        "Approximate days between CFPB receipt "
        "and referral to the company."
    )


# --------------------------------------------------
# DATA FRESHNESS
# --------------------------------------------------

st.divider()

st.header("Data Freshness")

# freshness() accepts only the database argument.
# The lambda adapts it to cached_query().
freshness_data = cached_query(
    "freshness",
    {},
    lambda database, _filters: freshness(database)
)

if isinstance(freshness_data, dict):

    latest_date = display_value(
        freshness_data.get("latest_date_received")
    )

    last_load = display_value(
        freshness_data.get("last_successful_run_at")
    )

    quality_status = display_value(
        freshness_data.get("last_quality_status")
    )

    latest_count = freshness_data.get("mongo_count_after")

    count_text = (
        f"{latest_count:,}"
        if isinstance(latest_count, int)
        else "N/A"
    )

    fresh_col1, fresh_col2 = st.columns(2)

    with fresh_col1:
        st.metric(
            "Latest Complaint Date",
            latest_date
        )

        st.metric(
            "Records After Last Successful Load",
            count_text
        )

    with fresh_col2:
        st.metric(
            "Last Successful MongoDB Load",
            last_load
        )

        st.metric(
            "Last Quality Status",
            quality_status
        )

    run_id = freshness_data.get("last_successful_run_id")

    if run_id:
        st.caption(
            f"Last successful pipeline run: {run_id}"
        )

    if (
        freshness_data.get("latest_date_received") is None
        and freshness_data.get("last_successful_run_at") is None
    ):
        st.info(
            "No successful data load or complaint date "
            "is currently recorded."
        )

else:
    st.info(
        "Freshness information is currently unavailable."
    )

st.caption(
    "A successful database load does not necessarily "
    "mean the newest complaints have been published. "
    "Always check the latest complaint date."
)


# --------------------------------------------------
# KPI DEFINITIONS
# --------------------------------------------------

st.divider()

with st.expander("How Are These Measures Calculated?"):
    st.markdown(
        load_content("kpi_definitions.md")
    )


# --------------------------------------------------
# IMPORTANT LIMITATIONS
# --------------------------------------------------

st.header("Important Limitations")

st.warning(
    "CFPB complaints are not a representative sample "
    "of all consumers or transactions. Complaint counts "
    "do not prove fraud, establish market share, "
    "or measure company service quality."
)

with st.expander("Read All Data Limitations"):
    st.markdown(
        load_content("limitations.md")
    )


# --------------------------------------------------
# INTERPRETATION CAUTIONS
# --------------------------------------------------

with st.expander("Interpretation Cautions"):
    st.markdown(
        load_content("cautions.md")
    )


# --------------------------------------------------
# DATA SOURCE
# --------------------------------------------------

st.divider()

st.caption(
    "Source: Consumer Financial Protection Bureau "
    "(CFPB) Consumer Complaint Database."
)
