
import streamlit as st
from dashboard.components.filters import show_filters

selected_filters = show_filters()

st.title("Complaint Trends")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "Explore how consumer complaint volumes change over time "
    "and compare trends across payment sub-products."
)

st.divider()

st.header("Monthly Complaint Volume")

st.info(
    "Monthly complaint trends will appear here "
    "after the MongoDB connection is implemented."
)

st.header("Yearly Growth by Sub-Product")

st.info(
    "This section will compare yearly complaint growth "
    "across the different payment sub-products."
)

st.header("Mobile or Digital Wallet Share")

st.info(
    "This section will show how mobile or digital wallet "
    "complaints have changed as a percentage of all "
    "complaints within the selected domain."
)

st.divider()

st.warning(
    "Complaint volume represents published CFPB complaints. "
    "An increase does not necessarily mean more transactions, "
    "more customers, or a higher rate of financial harm."
)
