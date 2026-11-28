# Perla Boustany - Contribution Log

## Role

Analytics Lead and Visualisation

## Contributions

| Date | What I did | Pull Request / Evidence | Problems encountered | Next step |
|---|---|---|---|---|
| 14 Nov 2026 | Defined the analytical measures and KPI definitions used by the dashboard and Q1-Q5 analysis. | `docs/metrics.md` | Needed to make the measures consistent with MongoDB queries and dashboard terminology. | Use the definitions in the analytical scripts and dashboard. |
| 18-21 Nov 2026 | Built and connected the Streamlit dashboard structure, including Overview, Trends, Issues, Responses and Channels, Geography and Companies, and Data Quality and Limitations. Added shared filters and MongoDB query integration. | Dashboard files under `dashboard/` | Needed consistent filters and reliable handling when Redis or MongoDB was unavailable. | Complete dashboard analytics and robustness checks. |
| 22-25 Nov 2026 | Implemented and executed Q1-Q5 analytics, generated charts, and documented the analytical findings. | `analytics/`, `analytics/output/`, `docs/findings.md` | Generated CSV outputs were initially tracked even though they are reproducible build outputs. | Keep generated CSV files local and commit only the required chart evidence. |
| 25-26 Nov 2026 | Implemented the two descriptive Spark MLlib analyses: emerging-issue detection using Linear Regression and state segmentation using KMeans. | `analytics/ml_emerging_issues.py`, `analytics/ml_state_clusters.py` | The emerging-issue rule produced no qualifying issue; this had to be reported as a valid result rather than forcing a positive result. | Explain the methods, fixed rules, results and cautions in the findings and report. |
| 25-27 Nov 2026 | Completed `docs/findings.md`, including Q1-Q5 numbers, cautions, chart references, ML interpretation and the analytical snapshot. | PR #40 | The analytical MongoDB snapshot had grown beyond the reference full load because scheduled API runs continued adding complaints. | Clearly distinguish the 24 Nov reference full load from the 25 Nov analytical snapshot. |
| 27 Nov 2026 | Drafted report sections 4.5 Dashboard and 6 Findings, including dashboard architecture, Redis cache-aside behaviour, MongoDB fallback, analytical results and limitations. | `docs/report/sections/04_5_dashboard.md`, `docs/report/sections/06_findings.md` | Needed to keep all report figures consistent with the same analytical snapshot. | Run the report checker and final validation before merge. |
| 27 Nov 2026 | Addressed PR #40 review feedback: snapshot clarification, generated CSV references, UTF-8 encoding, report sections and documentation cleanup. | PR #40 | The repository initially contained ambiguous wording between the full load and the later MongoDB analytical snapshot. | Verify curated and MongoDB counts and complete final project checks. |

## Current status

The analytics, dashboard findings and owned report sections are complete. PR #40 contains the analytical work and reviewer fixes. Remaining work is final validation, contribution evidence, rehearsals and the live Q1/Q2 dashboard demonstration.