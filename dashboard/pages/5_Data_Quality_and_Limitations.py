
import streamlit as st
from dashboard.components.filters import show_filters

selected_filters = show_filters()

st.title("Data Quality and Limitations")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "Understand how the complaint data is checked, "
    "when it was last updated, and what conclusions "
    "can reasonably be drawn from it."
)

st.divider()

# Section 1: Data freshness
st.header("Data Freshness")

st.info(
    "The latest complaint receipt date and last successful "
    "data load timestamp will appear here."
)

st.caption(
    "A recent successful load does not necessarily mean "
    "that the latest published complaints are recent."
)

# Section 2: Quality checks
st.header("Data Quality Checks")

st.write(
    "The data pipeline checks six dimensions of quality:"
)

st.markdown(
    """
    - **Uniqueness:** Check for duplicate complaint IDs.
    - **Completeness:** Identify missing values and fields
      that do not apply.
    - **Validity:** Check date formats, required fields,
      and allowed values.
    - **Consistency:** Check whether standardised fields
      follow the same rules.
    - **Freshness:** Check how recently the data was updated.
    - **Reconciliation:** Compare counts between pipeline stages.
    """
)

st.info(
    "Quality check results and field completeness percentages "
    "will appear here after the quality report is connected."
)

# Section 3: Reconciliation
st.header("Record Count Reconciliation")

st.info(
    "This section will show record counts at each pipeline "
    "stage and explain differences caused by filtering, "
    "deduplication, or quarantined records."
)

st.divider()

# Section 4: Limitations
st.header("Important Data Limitations")

st.warning(
    "CFPB complaint records represent complaints submitted "
    "to and published by the CFPB. They do not represent "
    "all customers, transactions, or financial harm."
)

st.markdown(
    """
    **Important interpretation rules**

    - Complaint counts do not measure market share.
    - A reported fraud-or-scam issue is not proof of fraud.
    - Timely response does not mean customer satisfaction.
    - Receipt-to-referral time is not resolution time.
    - Missing fields can reflect CFPB reporting rules.
    - Product categories changed over time, so standardised
      labels are needed for historical comparisons.
    """
)

st.caption(
    "Data source: Consumer Financial Protection Bureau (CFPB) "
    "Consumer Complaint Database."
)
