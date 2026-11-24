
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.components.db import cached_query
from dashboard.components.filters import show_filters
from database.queries import freshness


# --------------------------------------------------
# PAGE HEADER AND FILTERS
# --------------------------------------------------

st.title("Data Quality and Limitations")

st.subheader("Money Transfers and Digital Payments")

st.write(
    "Understand the quality of the CFPB complaint data, "
    "when it was last updated, and the limitations "
    "that apply to our analysis."
)

selected_filters = show_filters()

st.caption(
    "Quality and freshness results describe the latest "
    "successful pipeline load, not the selected dashboard filters."
)

st.divider()


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def load_content(filename):
    """Read explanatory text from Loutchiana's files."""
    path = (
        Path(__file__).resolve().parents[1]
        / "content"
        / filename
    )

    if path.exists():
        return path.read_text(encoding="utf-8")

    return "Content is currently unavailable."


def display_value(value):
    """Show N/A when a value has not been recorded."""
    if value is None or value == "":
        return "N/A"

    return str(value)


def display_count(value):
    """Format recorded counts without inventing values."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:,.0f}"

    return "N/A"


def show_no_report():
    st.info(
        "No quality report is currently available "
        "for the latest successful MongoDB load. "
        "The report will appear after the data pipeline "
        "has completed and saved its quality results."
    )


def read_latest_quality_report(database, _filters):
    """
    Read the quality report associated with the latest
    successful MongoDB pipeline load.

    This is an aggregate pipeline report, not a complaint record.
    """
    run = database.pipeline_runs.find_one(
        {"mongo_load_status": "success"},
        {"_id": 1},
        sort=[("mongo_loaded_at", -1)]
    )

    if run is None:
        return None

    report = database.quality_reports.find_one(
        {"_id": run["_id"]},
        {"_id": 0}
    )

    return report


# --------------------------------------------------
# LOAD FRESHNESS AND QUALITY REPORTS
# --------------------------------------------------

freshness_data = cached_query(
    "freshness",
    {},
    lambda database, _filters: freshness(database)
)

quality_data = cached_query(
    "latest_quality_report",
    {},
    read_latest_quality_report
)

if not isinstance(freshness_data, dict):
    freshness_data = {}

if not isinstance(quality_data, dict):
    quality_data = {}


# --------------------------------------------------
# SECTION 1: DATA FRESHNESS
# --------------------------------------------------

st.header("Data Freshness")

st.write(
    "Freshness tells us the latest complaint receipt date "
    "and when the database was last successfully updated."
)

latest_date = display_value(
    freshness_data.get("latest_date_received")
)

last_load = display_value(
    freshness_data.get("last_successful_run_at")
)

last_run = display_value(
    freshness_data.get("last_successful_run_id")
)

quality_status = display_value(
    freshness_data.get("last_quality_status")
)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Latest Complaint Date",
        latest_date
    )

    st.metric(
        "Last Successful Pipeline Run",
        last_run
    )

with col2:
    st.metric(
        "Last Successful MongoDB Load",
        last_load
    )

    st.metric(
        "Last Quality Status",
        quality_status
    )

if (
    not freshness_data.get("latest_date_received")
    and not freshness_data.get("last_successful_run_at")
):
    st.info(
        "No successful data load or complaint date "
        "is currently recorded."
    )

st.caption(
    "A successful database load does not necessarily mean "
    "that the newest complaints are available."
)

st.divider()


# --------------------------------------------------
# SECTION 2: DATA QUALITY CHECKS
# --------------------------------------------------

st.header("Data Quality Checks")

st.write(
    "The project evaluates six quality dimensions:"
)

st.markdown(
    """
    - **Uniqueness:** Checks for duplicate complaint IDs.
    - **Completeness:** Identifies missing data.
    - **Validity:** Checks required fields and valid values.
    - **Consistency:** Checks standardized categories.
    - **Freshness:** Examines how recently data was received.
    - **Reconciliation:** Compares record counts across stages.
    """
)

if not quality_data:
    show_no_report()

else:
    overall_status = display_value(
        quality_data.get("overall_status")
    )

    quality_gate = display_value(
        quality_data.get("quality_gate")
    )

    if isinstance(quality_data.get("quality_gate"), dict):
        gate_info = quality_data["quality_gate"]
        quality_gate = display_value(
            gate_info.get("status", gate_info.get("state"))
        )

    report_col1, report_col2 = st.columns(2)

    with report_col1:
        st.metric(
            "Overall Quality Status",
            overall_status
        )

        st.metric(
            "Report Run ID",
            display_value(quality_data.get("run_id"))
        )

    with report_col2:
        st.metric(
            "Quality Gate",
            quality_gate
        )

        st.metric(
            "Report Generated At",
            display_value(quality_data.get("generated_at"))
        )

    if overall_status == "FAIL":
        st.error(
            "The latest quality report indicates a failed check."
        )
    elif overall_status == "WARN":
        st.warning(
            "The latest quality report contains warnings."
        )
    elif overall_status == "PASS":
        st.success(
            "The latest quality report has an overall PASS status."
        )

    # ----------------------------------------------
    # INDIVIDUAL QUALITY CHECKS
    # ----------------------------------------------

    st.subheader("Individual Quality Check Results")

    checks = quality_data.get("checks", [])

    if isinstance(checks, dict):
        checks = [
            {"rule": key, **value}
            if isinstance(value, dict)
            else {"rule": key, "status": value}
            for key, value in checks.items()
        ]

    if isinstance(checks, list) and checks:
        checks_df = pd.DataFrame(checks)

        preferred_columns = [
            "dimension",
            "rule",
            "metric",
            "threshold",
            "status"
        ]

        display_columns = [
            column
            for column in preferred_columns
            if column in checks_df.columns
        ]

        if display_columns:
            st.dataframe(
                checks_df[display_columns],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.dataframe(
                checks_df,
                use_container_width=True,
                hide_index=True
            )

    else:
        st.info(
            "No individual quality checks are recorded "
            "in the latest report."
        )

    # ----------------------------------------------
    # FIELD COMPLETENESS
    # ----------------------------------------------

    st.subheader("Field Completeness")

    st.write(
        "Completeness measures the percentage of records "
        "where each reported field has a populated value."
    )

    completeness = quality_data.get("completeness", {})

    if isinstance(completeness, dict) and completeness:
        completeness_rows = []

        for field, value in completeness.items():
            if isinstance(value, (int, float)):
                completeness_rows.append({
                    "Field": field,
                    "Completeness (%)": value
                })

            elif isinstance(value, dict):
                percentage = value.get(
                    "percentage",
                    value.get(
                        "pct",
                        value.get("completeness_pct")
                    )
                )

                if percentage is not None:
                    completeness_rows.append({
                        "Field": field,
                        "Completeness (%)": percentage
                    })

        if completeness_rows:
            completeness_df = pd.DataFrame(
                completeness_rows
            )

            completeness_df[
                "Completeness (%)"
            ] = pd.to_numeric(
                completeness_df["Completeness (%)"],
                errors="coerce"
            )

            st.dataframe(
                completeness_df,
                use_container_width=True,
                hide_index=True
            )

            chart_df = completeness_df.dropna(
                subset=["Completeness (%)"]
            ).set_index("Field")

            if not chart_df.empty:
                st.bar_chart(
                    chart_df["Completeness (%)"]
                )

        else:
            st.info(
                "The completeness report is available, "
                "but no numeric field percentages were found."
            )

    else:
        st.info(
            "Field completeness results are not yet available."
        )

    st.caption(
        "Missing optional fields may reflect CFPB reporting "
        "rules and do not automatically mean data is invalid."
    )

    # ----------------------------------------------
    # QUARANTINE REASONS
    # ----------------------------------------------

    st.subheader("Quarantined Record Reasons")

    quarantine_reasons = quality_data.get(
        "quarantine_reasons", {}
    )

    if isinstance(quarantine_reasons, dict) and quarantine_reasons:
        quarantine_df = pd.DataFrame(
            [
                {
                    "Reason": reason,
                    "Count": count
                }
                for reason, count in quarantine_reasons.items()
            ]
        )

        st.dataframe(
            quarantine_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "No quarantine-reason breakdown is available "
            "in the latest report."
        )

st.divider()


# --------------------------------------------------
# SECTION 3: RECORD COUNT RECONCILIATION
# --------------------------------------------------

st.header("Record Count Reconciliation")

st.write(
    "Reconciliation checks whether the input records "
    "are accounted for after filtering, deduplication, "
    "quarantine, and curation."
)

counts = quality_data.get("counts", {})

if isinstance(counts, dict) and counts:

    raw_input = counts.get("raw_input")
    out_of_domain = counts.get("out_of_domain")
    duplicates = counts.get("duplicates_removed")
    quarantined = counts.get("quarantined")
    curated = counts.get("curated")

    count_col1, count_col2, count_col3 = st.columns(3)

    with count_col1:
        st.metric(
            "Raw Input Records",
            display_count(raw_input)
        )

        st.metric(
            "Out-of-Domain Records",
            display_count(out_of_domain)
        )

    with count_col2:
        st.metric(
            "Duplicates Removed",
            display_count(duplicates)
        )

        st.metric(
            "Quarantined Records",
            display_count(quarantined)
        )

    with count_col3:
        st.metric(
            "Curated Records",
            display_count(curated)
        )

        st.metric(
            "MongoDB Records After Last Load",
            display_count(
                freshness_data.get("mongo_count_after")
            )
        )

    st.markdown(
        """
        **Expected reconciliation rule**

        Raw Input = Curated + Quarantined
        + Out-of-Domain + Duplicates Removed
        """
    )

    required_values = [
        raw_input,
        curated,
        quarantined,
        out_of_domain,
        duplicates
    ]

    if all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        for value in required_values
    ):
        accounted_for = (
            curated
            + quarantined
            + out_of_domain
            + duplicates
        )

        difference = raw_input - accounted_for

        st.metric(
            "Reconciliation Difference",
            display_count(difference)
        )

        if difference == 0:
            st.success(
                "Reconciliation passed: all raw input "
                "records are accounted for."
            )

        else:
            st.error(
                "Reconciliation does not balance. "
                "Review the latest pipeline quality report."
            )

    else:
        st.info(
            "Some required reconciliation counts "
            "are missing from the quality report."
        )

else:
    st.info(
        "No pipeline reconciliation counts are available yet."
    )


# --------------------------------------------------
# SECTION 4: DATA LIMITATIONS
# --------------------------------------------------

st.divider()

st.header("Important Data Limitations")

st.warning(
    "CFPB complaint records are not a representative "
    "sample of all consumers or financial transactions. "
    "Reported issues do not establish proven harm, "
    "fraud, market share, or company service quality."
)

st.markdown(
    load_content("limitations.md")
)


# --------------------------------------------------
# SECTION 5: MEASURE DEFINITIONS
# --------------------------------------------------

with st.expander("How Are the Dashboard Measures Defined?"):
    st.markdown(
        load_content("kpi_definitions.md")
    )


# --------------------------------------------------
# SECTION 6: DATA QUALITY CAUTIONS
# --------------------------------------------------

with st.expander("Additional Interpretation Cautions"):
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

st.caption(
    "Quality information is based on the latest "
    "available successful pipeline load and is "
    "not recalculated by dashboard filters."
)
