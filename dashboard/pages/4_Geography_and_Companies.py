
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.db import cached_query
from dashboard.components.filters import show_filters

from database.queries import (
    a7_company_cumulative_share,
    a8_state_issue_profile,
    ml_state_clusters,
)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def clean_label(value):
    """Replace missing category values with Unknown."""
    if value is None or str(value).strip() == "":
        return "Unknown"

    return str(value)


def show_no_data():
    """Show a message when no matching records exist."""
    st.info(
        "No complaint data is currently available for "
        "the selected filters. Results will appear when "
        "matching records are loaded into MongoDB."
    )


def show_caution(section_title):
    """Display a caution from Loutchiana's content file."""
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


# US states and Washington DC.
# Only actual two-letter state codes are plotted on the map.
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT",
    "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY", "DC"
}


# --------------------------------------------------
# PAGE HEADER AND FILTERS
# --------------------------------------------------

st.title("Geography and Companies")

st.subheader("Money Transfers and Digital Payments")

st.write(
    "Compare published complaint patterns across "
    "US states and companies, and explore the "
    "results of Spark MLlib state clustering."
)

selected_filters = show_filters()

st.divider()


# --------------------------------------------------
# LOAD STATE ISSUE DATA
# --------------------------------------------------

state_data = cached_query(
    "a8_state_issue_profile",
    selected_filters,
    a8_state_issue_profile
)

if isinstance(state_data, list) and state_data:
    state_df = pd.DataFrame(state_data)

    state_df["state"] = (
        state_df["state"].apply(clean_label)
    )

    state_df["issue"] = (
        state_df["issue"].apply(clean_label)
    )

else:
    state_df = pd.DataFrame()


# --------------------------------------------------
# SECTION 1: GEOGRAPHIC COMPLAINT DISTRIBUTION
# --------------------------------------------------

st.header("Geographic Complaint Distribution")

st.write(
    "This map displays the number of published "
    "complaints recorded for each US state."
)

if state_df.empty:
    show_no_data()

else:
    # state_total is repeated for every issue in a state.
    # Keep only one copy of each state's total.
    state_totals = (
        state_df[
            ["state", "state_total"]
        ]
        .drop_duplicates(subset=["state"])
        .sort_values(
            "state_total",
            ascending=False
        )
        .copy()
    )

    total_complaints = int(
        state_totals["state_total"].sum()
    )

    state_totals["share_pct"] = (
        100 * state_totals["state_total"] / total_complaints
        if total_complaints > 0
        else 0
    )

    state_totals["share_pct"] = (
        state_totals["share_pct"].round(2)
    )

    # Use only recognized US state codes for the map.
    map_df = state_totals[
        state_totals["state"].isin(US_STATE_CODES)
    ].copy()

    if not map_df.empty:

        fig_map = px.choropleth(
            map_df,
            locations="state",
            locationmode="USA-states",
            color="state_total",
            scope="usa",
            title="Published Complaints by US State",
            labels={
                "state": "State",
                "state_total": "Complaint Count"
            },
            hover_data={
                "share_pct": ":.2f"
            },
            color_continuous_scale="Blues"
        )

        fig_map.update_layout(
            geo=dict(
                scope="usa",
                projection_type="albers usa"
            )
        )

        st.plotly_chart(
            fig_map,
            use_container_width=True
        )

    else:
        st.info(
            "No recognized US state codes are available "
            "for the geographic map."
        )

    # Show missing or unsupported states separately.
    other_states = state_totals[
        ~state_totals["state"].isin(US_STATE_CODES)
    ]

    if not other_states.empty:
        st.info(
            "Some complaints have Unknown, missing, "
            "or non-state geographic values. "
            "These records remain included in the table "
            "but cannot be placed on the US state map."
        )

    with st.expander("View All State Complaint Counts"):
        st.dataframe(
            state_totals.rename(
                columns={
                    "state": "State",
                    "state_total": "Complaint Count",
                    "share_pct": "Share of Selected Complaints (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

st.caption(
    "State complaint counts describe published complaints. "
    "They are not normalized by population, customers, "
    "or transaction volumes."
)


# --------------------------------------------------
# SECTION 2: ISSUE COMPOSITION BY STATE
# --------------------------------------------------

st.divider()
st.header("Issue Composition by State")

st.write(
    "Explore the issue categories reported within "
    "each state and their shares of that state's complaints."
)

if state_df.empty:
    show_no_data()

else:
    available_states = sorted(
        state_df["state"].unique().tolist()
    )

    chosen_state = st.selectbox(
        "Choose a state",
        available_states,
        key="geography_selected_state"
    )

    selected_state_df = (
        state_df[
            state_df["state"] == chosen_state
        ]
        .copy()
        .sort_values(
            "complaint_count",
            ascending=False
        )
    )

    fig_issues = px.bar(
        selected_state_df,
        x="issue",
        y="complaint_count",
        title=f"Reported Issues in {chosen_state}",
        labels={
            "issue": "Issue",
            "complaint_count": "Complaint Count"
        },
        hover_data={
            "issue_share_within_state_pct": ":.2f"
        }
    )

    fig_issues.update_layout(
        xaxis_tickangle=-35
    )

    st.plotly_chart(
        fig_issues,
        use_container_width=True
    )

    st.caption(
        "Issue share = complaints for an issue "
        "divided by all complaints in the chosen state "
        "within the selected filters."
    )

    st.subheader("Issue Share Within the Selected State")

    fig_share = px.bar(
        selected_state_df,
        x="issue",
        y="issue_share_within_state_pct",
        title=f"Issue Composition in {chosen_state}",
        labels={
            "issue": "Issue",
            "issue_share_within_state_pct": "Issue Share (%)"
        }
    )

    fig_share.update_layout(
        xaxis_tickangle=-35,
        yaxis_ticksuffix="%"
    )

    st.plotly_chart(
        fig_share,
        use_container_width=True
    )

    with st.expander("View State Issue Data"):
        st.dataframe(
            selected_state_df[
                [
                    "state",
                    "issue",
                    "complaint_count",
                    "state_total",
                    "issue_share_within_state_pct"
                ]
            ].rename(
                columns={
                    "state": "State",
                    "issue": "Issue",
                    "complaint_count": "Issue Complaints",
                    "state_total": "State Total",
                    "issue_share_within_state_pct": "Issue Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

show_caution("Q5. Issue profiles by state")


# --------------------------------------------------
# SECTION 3: COMPANY COMPLAINT SHARES
# --------------------------------------------------

st.divider()
st.header("Company Complaint Shares")

st.write(
    "Compare complaint counts and complaint shares "
    "across companies in the selected scope."
)

company_data = cached_query(
    "a7_company_cumulative_share",
    selected_filters,
    a7_company_cumulative_share
)

if not isinstance(company_data, list) or not company_data:
    show_no_data()

else:
    company_df = pd.DataFrame(company_data)

    company_df["company"] = (
        company_df["company"].apply(clean_label)
    )

    company_df = company_df.sort_values(
        ["complaint_count", "company"],
        ascending=[False, True]
    )

    # Display only the largest 20 complaint-volume
    # categories in the chart for readability.
    top_companies = company_df.head(20).copy()

    fig_companies = px.bar(
        top_companies,
        x="company",
        y="complaint_count",
        title="20 Companies with the Most Published Complaints",
        labels={
            "company": "Company",
            "complaint_count": "Complaint Count"
        },
        hover_data={
            "share_pct": ":.2f",
            "cumulative_share_pct": ":.2f"
        }
    )

    fig_companies.update_layout(
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        fig_companies,
        use_container_width=True
    )

    st.caption(
        "This chart shows the 20 companies with the "
        "largest complaint counts in the selected scope. "
        "It does not rank company quality."
    )

    st.subheader("Cumulative Company Complaint Share")

    cumulative_df = company_df.head(20).copy()

    fig_cumulative = px.line(
        cumulative_df,
        x="company",
        y="cumulative_share_pct",
        markers=True,
        title="Cumulative Complaint Share",
        labels={
            "company": "Company",
            "cumulative_share_pct": "Cumulative Share (%)"
        }
    )

    fig_cumulative.update_layout(
        xaxis_tickangle=-45,
        yaxis_ticksuffix="%"
    )

    st.plotly_chart(
        fig_cumulative,
        use_container_width=True
    )

    st.caption(
        "Cumulative share measures the percentage of "
        "selected complaint records accounted for by "
        "the companies shown in descending complaint-count order."
    )

    with st.expander("View All Company Complaint Data"):
        st.dataframe(
            company_df[
                [
                    "company",
                    "complaint_count",
                    "share_pct",
                    "cumulative_count",
                    "cumulative_share_pct"
                ]
            ].rename(
                columns={
                    "company": "Company",
                    "complaint_count": "Complaint Count",
                    "share_pct": "Complaint Share (%)",
                    "cumulative_count": "Cumulative Count",
                    "cumulative_share_pct": "Cumulative Share (%)"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

st.warning(
    "Complaint volume is not a measure of company "
    "service quality. The CFPB data does not contain "
    "the number of customers or transactions needed "
    "to calculate company complaint rates."
)


# --------------------------------------------------
# SECTION 4: STATE SEGMENTATION (SPARK MLLIB)
# --------------------------------------------------

st.divider()

st.header("State Segmentation (Machine Learning)")

st.write(
    "Apache Spark MLlib KMeans groups states with "
    "similar complaint issue mixes and submission "
    "channel distributions."
)

st.markdown(
    """
    **Method and classification rules**

    - Use state-level issue and channel shares as features.
    - Include states with at least **100 complaints**.
    - Evaluate **K = 2 through 6**.
    - Choose K using the **silhouette score**.
    - Use random seed **42** for reproducibility.
    - Report smaller states separately.
    """
)

# This function accepts only the database argument.
# Use a lambda to adapt it for cached_query().
cluster_data = cached_query(
    "ml_state_clusters",
    {},
    lambda database, _filters: ml_state_clusters(database)
)

if isinstance(cluster_data, list) and cluster_data:

    cluster_df = pd.DataFrame(cluster_data)

    st.success(
        "Precomputed state-clustering results "
        "are available in MongoDB."
    )

    # Show the actual stored ML fields rather than
    # assuming that training has a particular output schema.
    st.dataframe(
        cluster_df,
        use_container_width=True,
        hide_index=True
    )

    # Display a cluster map when the stored results
    # contain recognizable state and cluster fields.
    cluster_column = None

    for candidate in ["cluster", "cluster_id", "prediction"]:
        if candidate in cluster_df.columns:
            cluster_column = candidate
            break

    if (
        "state" in cluster_df.columns
        and cluster_column is not None
    ):
        map_clusters = cluster_df.copy()

        map_clusters["state"] = (
            map_clusters["state"].apply(clean_label)
        )

        map_clusters = map_clusters[
            map_clusters["state"].isin(US_STATE_CODES)
        ].copy()

        if not map_clusters.empty:
            map_clusters["Cluster"] = (
                map_clusters[cluster_column]
                .astype(str)
            )

            fig_clusters = px.choropleth(
                map_clusters,
                locations="state",
                locationmode="USA-states",
                color="Cluster",
                scope="usa",
                title="State Complaint-Profile Clusters",
                labels={
                    "state": "State"
                }
            )

            st.plotly_chart(
                fig_clusters,
                use_container_width=True
            )

    else:
        st.info(
            "The precomputed results are available, "
            "but a state-cluster map cannot be drawn "
            "until the stored output contains compatible "
            "state and cluster fields."
        )

else:
    st.info(
        "State-clustering results are not available yet. "
        "The cluster table and map will appear after "
        "the Spark MLlib KMeans analysis has been executed "
        "and its output loaded into MongoDB."
    )

st.caption(
    "State clusters are precomputed using their fixed "
    "analysis scope. The dashboard's date, issue, company, "
    "and channel filters do not retrain or change the clusters."
)

show_caution("State groups (Spark MLlib)")

st.caption(
    "Clusters describe similarities in complaint patterns. "
    "They do not measure state risk, consumer behaviour, "
    "company quality, or future outcomes."
)


# --------------------------------------------------
# DATA SOURCE
# --------------------------------------------------

st.divider()

st.caption(
    "Source: CFPB Consumer Complaint Database. "
    "Geographic and company comparisons describe "
    "published complaint records only."
)
