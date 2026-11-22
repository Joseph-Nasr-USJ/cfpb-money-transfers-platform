
import streamlit as st
from dashboard.components.filters import show_filters

selected_filters = show_filters()

st.title("Geography and Companies")
st.subheader("Money Transfers and Digital Payments")

st.write(
    "Compare published consumer complaints across US states "
    "and companies, and explore patterns identified by "
    "Spark MLlib clustering."
)

st.divider()

# Section 1: Geographic complaint distribution
st.header("Geographic Complaint Distribution")

st.info(
    "A US state map will show complaint counts and percentages "
    "for the selected issue and reporting period."
)

st.caption(
    "Counts represent published complaints, not the number "
    "of customers or transactions in each state."
)

# Section 2: State issue profiles
st.header("Issue Composition by State")

st.info(
    "This section will compare issue counts and shares "
    "within each state. Missing state values will be "
    "reported separately."
)

st.divider()

# Section 3: Company comparisons
st.header("Company Complaint Shares")

st.info(
    "This section will compare complaint counts and "
    "percentages across companies."
)

st.warning(
    "Company complaint share is not a company quality "
    "ranking. Complaint counts cannot be interpreted "
    "without considering factors such as company size "
    "and number of customers."
)

st.divider()

# Section 4: Machine learning state clustering
st.header("State Segmentation (Machine Learning)")

st.write(
    "Spark MLlib KMeans will group states according to "
    "similarities in their issue-mix and submission-channel shares."
)

st.markdown(
    """
    **Method and classification rule**

    - Use state-level issue and channel percentages as features.
    - Test values of K from 2 to 6.
    - Select K using the silhouette score.
    - Use random seed 42 for reproducibility.
    - Report states with fewer than 100 complaints separately.
    """
)

st.info(
    "The state cluster map and cluster profiles will appear "
    "after the Spark MLlib analysis is complete and the "
    "results have been loaded into MongoDB."
)

st.caption(
    "Clusters describe similarities in published complaint "
    "patterns. They do not measure state risk levels, "
    "predict future complaints, or establish causation."
)
