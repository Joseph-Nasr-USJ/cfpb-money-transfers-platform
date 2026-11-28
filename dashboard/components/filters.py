
from datetime import date

import streamlit as st

from dashboard.components.db import cached_query


def get_filter_options():
    """Retrieve available category values from MongoDB."""

    fields = [
        "sub_product_std",
        "issue",
        "state",
        "submitted_via",
        "company"
    ]

    def query_options(database, filters):
        options = {}

        for field in fields:
            values = database.complaints.distinct(field)

            options[field] = sorted(
                str(value)
                for value in values
                if value is not None and str(value).strip()
            )

        return options

    return cached_query(
        "dashboard_filter_options",
        {},
        query_options
    )

# Provides shared filter controls for all dashboard pages.
# Keeping filters centralized ensures consistent selections
# when comparing trends, issues, and geographic results.
def show_filters(options=None):
    """Display filters using Christopher's MongoDB query contract."""

    if options is None:
        options = get_filter_options()

    if not isinstance(options, dict):
        options = {}

    st.sidebar.header("Dashboard Filters")

    selected_dates = st.sidebar.date_input(
        "Date received (from / to)",
        value=(date(2018, 1, 1), date.today()),
        key="filter_dates"
    )

    if len(selected_dates) != 2:
        st.sidebar.warning("Please select a start and end date.")
        st.stop()

    start_date, end_date = selected_dates

    if start_date > end_date:
        st.sidebar.error("Start date must be before end date.")
        st.stop()

    # These names match database/queries.py
    selected = {
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat()
    }

    fields = {
        "sub_product_std": "Sub-product",
        "issue": "Issue",
        "state": "State",
        "submitted_via": "Submission Channel",
        "company": "Company"
    }

    for field, label in fields.items():
        values = options.get(field, [])

        choices = ["All"] + sorted({
            str(value)
            for value in values
            if value is not None
            and str(value).strip()
            and str(value) != "All"
        })

        choice = st.sidebar.selectbox(
            label,
            choices,
            key=f"filter_{field}"
        )

        if choice != "All":
            selected[field] = [choice]

    st.sidebar.caption(
        "Filters apply to published CFPB complaints "
        "within the money-transfer and digital-payment domain."
    )

    return selected
