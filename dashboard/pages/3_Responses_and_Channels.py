
import streamlit as st
from dashboard.components.filters import show_filters

selected_filters = show_filters()

st.title("Company Responses and Submission Channels")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "Explore how companies respond to published consumer "
    "complaints and how complaints reach the CFPB."
)

st.divider()

# Section 1: Company response categories
st.header("Company Response Categories")

st.info(
    "This section will display complaint counts and "
    "percentages for each company response category."
)

st.caption(
    "Closed-outcome percentages exclude complaints marked "
    "'In progress' and records with unknown response categories."
)

# Section 2: Timely responses
st.header("Timely Response Percentage")

st.write(
    "Timely response percentage is calculated as:"
)

st.code(
    "Timely Yes / (Timely Yes + Timely No) * 100",
    language="text"
)

st.info(
    "The percentage and separate counts of missing or invalid "
    "missing or invalid will appear here after MongoDB integration."
)

st.caption(
    "Timely response measures the CFPB timeliness flag. "
    "It does not establish customer satisfaction."
)

st.divider()

# Section 3: Receipt-to-referral interval
st.header("Receipt-to-Referral Interval")

st.write(
    "This measures the number of calendar days between "
    "the CFPB receiving a complaint and sending it to the company."
)

st.info(
    "The median interval, distribution of days, and counts "
    "of missing or invalid dates will appear here."
)

st.warning(
    "The receipt-to-referral interval is not the time "
    "a company took to resolve a complaint."
)

# Section 4: Submission channels
st.header("Submission Channels")

st.info(
    "This section will display complaint counts and percentages "
    "by submission channel and calendar year."
)

st.caption(
    "Changes in submission-channel shares may reflect differences "
    "in reporting behaviour or CFPB intake processes."
)
