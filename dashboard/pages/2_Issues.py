
import streamlit as st
from dashboard.components.filters import show_filters

selected_filters = show_filters()

st.title("Issues and Fraud Trends")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "Explore the issues reported by consumers, compare "
    "fraud-or-scam complaint shares, and identify emerging issues."
)

st.divider()

# Section 1: Issue composition
st.header("Issue Composition")

st.info(
    "This section will display complaint counts and percentages "
    "for each reported issue within the selected sub-product."
)

# Section 2: Sub-issue composition
st.header("Sub-Issue Composition")

st.info(
    "This section will display sub-issue counts and percentages, "
    "including complaints where no sub-issue was recorded."
)

# Section 3: Fraud-or-scam trends
st.header("Fraud or Scam Share")

st.info(
    "This section will compare fraud-or-scam complaint shares "
    "across the four core payment sub-products, including "
    "their 12-month rolling shares."
)

st.warning(
    "Fraud or scam is an issue category selected by the "
    "person submitting the complaint. It is not proof "
    " that fraud occurred."
)

st.divider()

# Section 4: Machine learning
st.header("Emerging Issues (Machine Learning)")

st.write(
    "This analysis will use Apache Spark MLlib LinearRegression "
    "to identify issues whose share of complaints has been "
    "increasing over the last 24 complete months."
)

st.markdown(
    """
    **Method and classification rule**

    An issue is classified as emerging when:

    - Its monthly share increases by at least 0.2 percentage
      points per month.
    - The regression has an R-squared value of at least 0.5.
    - The issue has at least 50 complaints in the analysis period.
    """
)

st.info(
    "Emerging issue results will appear after the Spark MLlib "
    "analysis has been executed and loaded into MongoDB."
)

st.caption(
    "This method describes historical complaint trends. "
    "It does not predict future complaints or confirm "
    " that an issue will continue growing."
)
