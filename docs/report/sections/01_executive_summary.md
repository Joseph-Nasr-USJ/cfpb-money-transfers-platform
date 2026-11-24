<!--
Section 1. Executive summary
Owner: Loutchiana | Target: 300 words | First draft: Sat 21 Nov; FINAL on Fri 27 Nov after docs/findings.md (Perla, Tue 24 Nov)
Every number must match docs/findings.md and the dashboard. Replace each visible [TO COMPLETE ...] marker before submission;
"python docs/report/build_report.py --check" lists the markers that are left.
-->

## 1. Executive summary

We built a batch data platform that turns the public CFPB Consumer Complaint Database into evidence for one financial domain, money transfers and digital payments (option 5). It loads the full historical file once and collects new complaints from the CFPB API every 24 hours with Apache NiFi, with a tested Python collector as the fallback. Raw files are kept unchanged in MinIO. Apache Spark validates, cleans and deduplicates the records, quarantines bad ones with a reason and stops a run when a quality threshold fixed in advance is breached. MongoDB serves the curated records and aggregates, indexed for the dashboard filters, and a Streamlit dashboard with a Redis cache presents them. Two Spark MLlib analyses describe emerging issues and groups of states. The whole stack starts with one Docker Compose command, and rerunning the same window does not create duplicates. On the full CFPB file of 24 November 2026 the chain read 19,397,176 records, kept 205,271 complaints in the domain and quarantined 112 with a stated reason (32 invalid state, 80 sent to the company before they were received), and the quality report passed with an exact reconciliation. The automated tests give 159 passed and 1 skipped.

**What we found.** [TO COMPLETE: three or four principal findings from docs/findings.md, each with its number, its denominator, the period and its caution. Include the answer to Q1 (fastest-growing sub-products and issues, and the wallet share) and to Q2 (the fraud-or-scam share by core sub-product).]

**What the findings do not show.** The CFPB database is not a statistical sample, so the results describe published complaints and not all consumers. A complaint is not confirmed fraud or harm, company figures are shares of complaints and not a quality ranking, and a trend is not a forecast: the analysis is descriptive and diagnostic only.

**Implication for the user.** [TO COMPLETE: one or two sentences on what a payments policy analyst or an operations manager can do with these results, taken from the findings.]
