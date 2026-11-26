<!--
Section 1. Executive summary
Owner: Loutchiana | Target: 300 words | First draft: Sat 21 Nov; FINAL on Fri 27 Nov after docs/findings.md (Perla, Tue 24 Nov)
Every number must match docs/findings.md and the dashboard. Replace each visible [TO COMPLETE ...] marker before submission;
"python docs/report/build_report.py --check" lists the markers that are left.
-->

## 1. Executive summary

We built a batch data platform that turns the public CFPB Consumer Complaint Database into evidence for one financial domain, money transfers and digital payments (option 5). It loads the full history once and collects new complaints every 24 hours with Apache NiFi, with a tested Python collector as the fallback. Raw files stay unchanged in MinIO; Apache Spark validates, cleans and deduplicates the records, quarantines bad ones with a reason and stops a run when a threshold fixed in advance is breached; MongoDB serves the curated records and aggregates to a Streamlit dashboard with a Redis cache. Two Spark MLlib analyses describe emerging issues and groups of states. The stack starts with one Docker Compose command, and rerunning a window creates no duplicates. On the full file of 24 November 2026 the chain read 19,397,176 records, kept 205,271 in the domain and quarantined 112; the quality report passed with an exact reconciliation, and 159 automated tests passed (1 skipped).

**What we found.** Domestic (US) money transfer grew from 3,069 complaints in 2021 to 57,853 in 2025 and mobile or digital wallet from 6,405 to 17,149; the yearly volume of the whole domain went from 16,746 in 2024 to 84,612 in 2025, which the data does not explain. The share of "Fraud or scam" complaints is highest for virtual currency (about 34%), then mobile or digital wallet (28%), international money transfer (24%) and domestic money transfer (19%). The MLlib model found no issue that met the three thresholds fixed in advance for "emerging" (43 models). Denominators and periods are in `docs/findings.md`.

**What the findings do not show.** The database is not a statistical sample, so the results describe published complaints and not all consumers. A complaint is not confirmed fraud or harm, company figures are shares of complaints and not a quality ranking, and a trend is not a forecast.

**Implication for the user.** A payments policy analyst or an operations manager can see where complaint volume is concentrated and which sub-products carry a higher share of fraud-or-scam complaints, and decide where to look more closely.
