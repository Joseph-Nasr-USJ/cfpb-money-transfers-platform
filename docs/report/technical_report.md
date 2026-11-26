# Banking Complaints Data Platform: Money Transfers and Digital Payments

Technical report. Group 5, course 020IABDM2 Big Data Frameworks (Dr. Rafiqul Haque), ESIB, USJ. Marwa Zeineddine, Perla Boustany, Joseph Nasr, Christopher Al Hassrouty, Charbel Mazraani, Loutchiana Marie.

## 1. Executive summary

We built a batch data platform that turns the public CFPB Consumer Complaint Database into evidence for one financial domain, money transfers and digital payments (option 5). It loads the full history once and collects new complaints every 24 hours with Apache NiFi, with a tested Python collector as the fallback. Raw files stay unchanged in MinIO; Apache Spark validates, cleans and deduplicates the records, quarantines bad ones with a reason and stops a run when a threshold fixed in advance is breached; MongoDB serves the curated records and aggregates to a Streamlit dashboard with a Redis cache. Two Spark MLlib analyses describe emerging issues and groups of states. The stack starts with one Docker Compose command, and rerunning a window creates no duplicates. On the full file of 24 November 2026 the chain read 19,397,176 records, kept 205,271 in the domain and quarantined 112; the quality report passed with an exact reconciliation, and 159 automated tests passed (1 skipped).

**What we found.** Domestic (US) money transfer grew from 3,069 complaints in 2021 to 57,853 in 2025 and mobile or digital wallet from 6,405 to 17,149; the yearly volume of the whole domain went from 16,746 in 2024 to 84,612 in 2025, which the data does not explain. The share of "Fraud or scam" complaints is highest for virtual currency (about 34%), then mobile or digital wallet (28%), international money transfer (24%) and domestic money transfer (19%). The MLlib model found no issue that met the three thresholds fixed in advance for "emerging" (43 models). Denominators and periods are in `docs/findings.md`.

**What the findings do not show.** The database is not a statistical sample, so the results describe published complaints and not all consumers. A complaint is not confirmed fraud or harm, company figures are shares of complaints and not a quality ranking, and a trend is not a forecast.

**Implication for the user.** A payments policy analyst or an operations manager can see where complaint volume is concentrated and which sub-products carry a higher share of fraud-or-scam complaints, and decide where to look more closely.

## 2. Problem and scope

**Problem.** A public-interest organisation that monitors consumer financial complaints needs a dependable way to collect the records the CFPB publishes, check their quality and show what they say to people who do not write code. Our platform turns the CFPB Consumer Complaint Database into evidence for one financial domain and states what the records cannot tell us. The analysis is descriptive and diagnostic (Session 1); it does not predict.

**Intended users.** Policy analysts in payments oversight (which issues and sub-products are growing), service and operations managers (channels, response categories, timely-response rates) and the platform maintainer (run logs, quality reports, freshness).

**Chosen option.** Option 5, money transfers and digital payments: emerging issues, shifts in submission channels and growth rates.

**Filters.** The domain is defined by `config/product_mapping.csv`; original source labels are kept next to our standard categories.

| Source product | Sub-products kept | Standard category |
|---|---|---|
| Money transfer, virtual currency, or money service | all | same label |
| Money transfers (label used before 2017) | all | Money transfer, virtual currency, or money service |
| Virtual currency (legacy label) | all | Virtual currency |
| Prepaid card | Mobile wallet only | Mobile or digital wallet |

Four core sub-products are compared throughout: domestic (US) money transfer, international money transfer, mobile or digital wallet and virtual currency; the rest are grouped as "Other money services". The CFPB API returned 199,152 records for the current label on 20 November 2026. The full load of 24 November keeps 205,271 curated complaints: 199,561 under the current label and 5,710 under the legacy labels of the mapping.

**Reporting period.** The full history in the CFPB file, kept current by a 24-hour incremental collection. Each question's window is fixed in advance, and the current year is labelled partial.

**Analytical questions.**

| # | Question | Window |
|---|---|---|
| Q1 (demo) | Which sub-products and issues grew fastest, and how did the mobile or digital wallet share change? | 2021 to 2025 |
| Q2 (demo) | How did the "Fraud or scam" share change across the four core sub-products? | since 2018 |
| Q3 | Has the mix of submission channels changed over time? | full history |
| Q4 | How do response categories and timely-response rates differ by sub-product and among the largest companies by share? | full history |
| Q5 | Which states show different issue profiles (optionally per 100,000 residents)? | full history |

Q1 and Q5 use Spark MLlib descriptively (issue-share trends, K-means groups of states). Every answer shows raw counts and percentages within each group, with its caution next to it.

## 3. Data source and limitations

**Source and usage basis.** The platform uses the CFPB Consumer Complaint Database: the full CSV ZIP for the history and the official API for daily updates (references in section 8). The CFPB states that the complaint data it publishes is "freely available for anyone to use, analyze, and build on", and the API metadata declares the licence CC0, public domain (tested on 20 November 2026).

**Fields and coverage.** The CFPB publishes 15 fields: Complaint ID, Date received, Date sent to company, Product, Sub-product, Issue, Sub-issue, Company, Company public response, Company response to consumer, Timely response?, State, ZIP code, Tags and Submitted via. Not every product has sub-products and not every issue has sub-issues, so sub-issue is mostly empty in our domain. The database generally updates daily. Only complaints sent to companies for response are eligible, and they are published after the company responds or after 15 days, whichever comes first, so recent weeks are provisional. Complaints referred to other regulators are not published.

**Current restrictions.** Complaint narratives were removed in September 2026 (release 24), which is why the project does no text analysis; the consumer-consent and consumer-disputed fields are also gone. Since July 2026 filtered exports are limited to 100,000 complaints, so we use the full ZIP for the history and narrow API windows for updates. ZIP codes are masked or suppressed for small areas. The data contains no transactions, balances, confirmed fraud labels or resolution durations.

**Representativeness.** The CFPB states that the database "is not a statistical sample of consumers' experiences". Following Session 1, inference needs a random sample and correlation does not imply causation, so we describe the published complaints and neither generalise nor claim causes. The CFPB advises considering company size and market share when comparing companies; the data cannot provide them, so company figures are shares of complaints, never a quality ranking.

**Category changes.** The CFPB updated its product and issue forms in August 2023 and 2026 but keeps the labels the consumer selected, so history is not re-coded. In our domain three legacy labels used before April 2017 (Money transfers, Virtual currency, and Prepaid card with the sub-product Mobile wallet) are mapped to the current domain by `config/product_mapping.csv`, and the original labels are kept next to the standard ones. The mapping is to be confirmed with the lecturer.

**Responsible use and ethics.** The data is public, but the platform still limits its use. It never displays individual records or free text, makes no attempt to re-identify anyone and does not use ZIP codes. Company results carry a caution and are never rankings. No statement claims causality or confirmed fraud, and small groups are grouped or flagged. A quality failure stops a run, so bad data never reaches the dashboard. AI assistants were used for drafting and code support; every contribution was reviewed and tested by the team, who can explain it.

## 4. Architecture and implementation

### 4.1 Architecture and technology choices

![Figure 1. Architecture of the platform](../images/architecture.png)

The platform is a batch system of seven layers, following the Conceptual Big Data Framework of Session 2. Each layer has one purpose and the whole stack starts with one Docker Compose command.

**Collection.** Apache NiFi is planned to start the collection every 24 hours and keep the provenance of every run (its service is in the Docker stack; its flow is still to be exported); the tested Python collector is the working path. NiFi was chosen from the course's ingestion tools for its scheduling and provenance. Kafka and Flume serve streaming and log collection, which the brief rules out, and Sqoop moves relational data.

**Raw storage.** MinIO object storage keeps every file unchanged, by ingestion date and run, with manifests and run logs. HDFS and Ceph need a cluster that about 200,000 records do not justify.

**Processing.** Spark DataFrames in local mode validate, clean, deduplicate and aggregate. A quality gate stops a failing run. Spark Streaming is not used because the CFPB publishes daily, so there is no live stream.

**Curated storage.** Parquet is columnar, compressed and stores its schema, so the aggregates read only the columns they need. ORC would be an equivalent alternative; CSV is slower and compressed text cannot be split.

**Serving.** MongoDB's document model fits complaint-shaped records filtered on several fields; key-value, wide-column and graph stores do not. The single node has no network partition, so the CAP choice does not arise; a replica set is the first improvement.

**Analytics.** Spark MLlib describes the data with linear regression (emerging issues) and K-means (groups of states). It does not forecast, because the brief keeps predictive modelling out of scope.

**Presentation.** Streamlit reads MongoDB only, with Redis as a cache-aside layer with a ten-minute time-to-live.

**Trade-offs.** We accept data that is up to a day old, a single node and no horizontal scale, in return for a platform that is simple to test, replay and reproduce. MinIO no longer publishes official Docker images, so we pin a community rebuild of its last release to an exact tag.

### 4.2 Collection, scheduling and raw storage

**Two collection paths, one contract.** The historical load downloads the official CFPB CSV ZIP once with a script (`make ingest-full`). On 24 November 2026 it fetched 371,218,594 bytes, computed their SHA-256 while streaming, extracted 19,397,176 records and wrote a manifest with the source URL, download times, size, checksum and record count. New and changed complaints come from the CFPB API every 24 hours through Apache NiFi; a Python collector (`ingestion/incremental.py`, 17 tests) is the tested fallback, selected with `COLLECTOR=python`. Both write the same raw paths, run_id format and run log, so Spark and the loader do not depend on the collector. [TO CONFIRM when the NiFi flow is exported: processor chain in one sentence.]

**Window, overlap and high-water mark.** Each incremental window runs from the high-water mark minus 21 days to the current day, on `date_received`. The overlap is needed because the CFPB publishes a complaint only after the company responds or after 15 days, and responses change later: our first API run found 190 complaints for 10 to 17 November, about 24 per day against about 125 per day in October. Repeated records are removed downstream by `complaint_id`. The high-water mark (`state/high_water_mark.json`) moves only forward and only after Spark and the MongoDB load succeed; every change is kept in `state/hwm_history/`, and a manual reset requires a reason.

**Tested API behaviour.** Probing the live API on 20 November showed three differences from its specification (`docs/api_notes.md`). The CDN answered HTTP 403 to a custom User-Agent and to a browser imitation, but 200 to the default `python-requests` agent. Offset paging (`frm=100`) returned the same 100 complaints as page 1 without any error, while `search_after` returned the next page. The end date was included although documented as exclusive. The collector therefore pages with `search_after`, stops if a page brings no new complaint, and requests one extra day.

**Failures and reruns.** Timeouts, connection errors, HTTP 429 and 5xx are retried after 2, 4 and 8 seconds (or the server's `Retry-After`), at most three times; other 4xx answers fail at once. A real failure shaped this rule: on 20 November the ZIP transfer broke after 104 MB and was not retried; downloads now resume with an HTTP Range request while each attempt makes progress. A same-day rerun with an identical file uploads nothing (`skipped_identical`), and one that finds a partial upload verifies the stored copy by SHA-256 before completing it.

**Run logs and raw layout.** Every run, successful or not, writes `logs/ingestion/run_id=<id>.json`: run type, window, parameters, pagination state, HTTP status, retries, errors, outcome, raw paths, record count, checksums and the CFPB's own `last_indexed` time. Raw files sit in MinIO under `raw/cfpb/full_load/ingest_date=…/` and `raw/cfpb/api/ingest_date=…/run_id=…/`, stored exactly as received; the helper module refuses to overwrite any object under `raw/`. [TO CONFIRM: how NiFi provenance complements these logs.]

**Reconciling older revisions.** The 21-day overlap only refreshes recent complaints. Older records that the CFPB revises are reconciled by running the full CSV load again, which Spark merges with the existing curated data by `complaint_id`.

### 4.3. Spark processing

_Draft pending (Joseph, due Wed 25 Nov)._

### 4.4. MongoDB serving layer

_Draft pending (Christopher, due Wed 25 Nov)._

### 4.5. Dashboard

_Draft pending (Perla, due Wed 25 Nov)._

## 5. Testing and operations

### 5.1. Quality thresholds, reconciliation and rerun evidence

_Draft pending (Joseph, due Wed 25 Nov)._

### 5.2. Index measurements

_Draft pending (Christopher, due Wed 25 Nov)._

### 5.3. Tests, deployment and recovery

_Draft pending (Charbel, due Wed 25 Nov)._

## 6. Findings

_Draft pending (Perla, due Wed 25 Nov)._

## 7. Reflection and next steps

**Team process.** Six members each own a folder, so most Pull Requests touch different files. The `main` branch is protected: every change goes through a branch, a Pull Request and a review by a named teammate, merged with a merge commit. Each member keeps a weekly contribution log, and the lecturer's checkpoints were written up as short notes. The brief was updated during the project (version 2) and the lecturer asked for course tools, so NiFi, Redis and Spark MLlib were added late; the shared plan, the contracts and the task files had to be revised in one day.

**Design trade-offs.** We chose a daily batch over streaming, because the CFPB publishes daily and the brief rules streaming out. We chose MongoDB as the serving store and kept Parquet in MinIO as the trusted source. We kept the tested Python collector next to NiFi so that the demonstration does not depend on one tool. MinIO no longer publishes official images, so we pinned a community rebuild.

**Unresolved issues.** The NiFi and Redis services are merged and part of the Docker stack, but the NiFi flow is not exported to `ingestion/nifi/` yet, so the Python collector remains the collection path that the pipeline uses. The two differences between the brief and the code that were open on 21 Nov are closed: the curated data is written and read under `curated/complaints/option=5/year=YYYY/month=MM/` through one shared module, and the quality report uses the V2 names freshness and reconciliation. A full run on the new path was made on 24 Nov (19,397,176 records, 205,271 curated, quality PASS) and its figures replace those of the run of 22 Nov. Two points remain open: the lecturer's approval of the legacy product labels, which account for 5,710 of the 205,271 curated complaints, and complaints that the CFPB drops from its file: the Spark merge and the MongoDB loader only insert and update, so such a complaint stays in the curated data and in MongoDB. The first load on the new path stopped at the integrity check (205,272 documents in MongoDB for 205,271 curated) because MongoDB still held one complaint from the run of 22 Nov, written under the previous folder layout; that document was removed by hand and the run resumed.

**Next improvement.** The improvement to prioritise is a MongoDB replica set with automatic primary election, majority writes and reads from the primary, so that the loss of one node no longer means rebuilding the database. Sharding is not needed at about 200,000 documents. After that, a Spark cluster would be needed only if the data grew by orders of magnitude.

**What we would do differently.** [TO COMPLETE with Charbel after the rehearsals: one or two lessons about planning, integration and testing.]

## 8. References and appendices

### References

**Official CFPB sources** (accessed 21 November 2026)

1. Consumer Financial Protection Bureau. *Consumer Complaint Database.* https://www.consumerfinance.gov/data-research/consumer-complaints/ (page last modified 29 October 2026).
2. Consumer Financial Protection Bureau. *Consumer Complaint Database API.* https://cfpb.github.io/api/ccdb/api.html
3. Consumer Financial Protection Bureau. *Consumer Complaint Database field reference.* https://cfpb.github.io/api/ccdb/fields.html
4. Consumer Financial Protection Bureau. *Consumer Complaint Database release notes* (releases 20 to 24, 2023 to 2026). https://cfpb.github.io/api/ccdb/release-notes.html
5. Consumer Financial Protection Bureau. *Full complaint data, CSV ZIP.* https://files.consumerfinance.gov/ccdb/complaints.csv.zip

**Other sources**

6. United States Postal Service. *Publication 28, Postal Addressing Standards*, Appendix B, Two-Letter State and Possession Abbreviations. https://pe.usps.com/text/pub28/28apb.htm

**Course and brief**

7. Haque, R. *Session 1: Enterprise Data Science, methodologies, principles and practices.* 020IABDM2, ESIB, USJ. Value of big data; descriptive, diagnostic, predictive and prescriptive analytics; exploratory and inferential analytics.
8. Haque, R. *Session 2: Building an end-to-end big data solution.* Conceptual Big Data Framework; data collection tools (Apache NiFi, Kafka, Flume, Sqoop).
9. Haque, R. *Session 3.1: Data storage tools and storage formats.* Storage systems; compression; ORC and Parquet.
10. Haque, R. *Session 4.1: NoSQL and MongoDB, Redis, Apache Spark.* Document model, CAP, indexes and aggregation, replication and sharding; Redis as a cache; Spark and its libraries.
11. Haque, R. *Class project: Public Banking Complaints Data Platform*, version 2. 020IABDM2 Big Data Frameworks.

### Appendices

| ID | Appendix | Where | Owner |
|---|---|---|---|
| A | Architecture document and diagram | `docs/architecture.md`, `docs/images/architecture.png` | Loutchiana |
| B | Data dictionary, product mapping and state list | `docs/data_dictionary.md`, `config/product_mapping.csv`, `config/state_codes.csv` | Loutchiana, Joseph |
| C | Raw manifest of the historical load and a sample run log | `docs/images/minio_raw_full_load.png` (manifest in MinIO, run of 24 Nov); `docs/evidence/run_20261124T135857Z_full/manifest.json` and `run_log.json` | Marwa |
| D | Sample quality report and the reconciliation of one run | `docs/images/minio_quality_report.png`; `docs/evidence/run_20261124T135857Z_full/quality_report.json` (run of 24 Nov) | Joseph |
| E | Sample curated output | `docs/images/minio_curated_parquet.png`; `docs/evidence/` [TO COMPLETE: sample file, Joseph] | Joseph |
| F | MongoDB model, indexes and the aggregation queries A1 to A8 | `docs/mongodb_model.md`, `database/queries.py`, `docs/images/mongodb_collections_indexes.png` | Christopher |
| G | Index benchmark before and after | `docs/evidence/benchmark.md` [TO COMPLETE] | Christopher |
| H | Metric definitions and findings | `docs/metrics.md`, `docs/findings.md` | Perla |
| I | Test plan, test results and defect log | `docs/test_plan.md`, `docs/evidence/test_results_*.txt`, `docs/defect_log.md` | Charbel |
| J | Rerun (idempotency) evidence | `docs/evidence/idempotency.md` | Joseph |
| K | Demonstration script and runbook | `docs/demo_script.md`, `docs/runbook.md` | Charbel |
| L | Checkpoint notes and contribution logs | `docs/checkpoints/`, `docs/contributions/` | Loutchiana, everyone |
