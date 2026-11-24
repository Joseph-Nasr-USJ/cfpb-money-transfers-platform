# Slides outline and speaker notes for step 1

**Owners:** Loutchiana Marie and Charbel Mazraani | **Status:** outline written Sat 21 Nov 2026. The presentation is on **Monday 30 November 2026**: 15 minutes of live demonstration plus 5 minutes of questions ([demo_script.md](../demo_script.md)). The slides support the demonstration; they must never take its time.

**Tool:** to decide with Charbel. Proposal: Google Slides, because all six members can edit the same deck. Export the final deck to PDF and save it in this folder by Fri 27 Nov (`docs/presentation/slides.pdf`).

## 1. Slide list

One slide per step of the brief's 8-step demonstration, plus the framing slides. The timings come from the demo script; the total is 15:30 and is trimmed to 15:00 in rehearsal.

| # | Slide | Content | Presenter | Time | Source |
|---|---|---|---|---|---|
| 1 | Title | Project name, option 5, course, team of six, date | Loutchiana | 0:00 | |
| 2 | Problem and users | The organisation, the three users, the project question | Loutchiana | step 1 | report section 2 |
| 3 | Scope | Option 5 and the product mapping (current label plus legacy labels); core sub-products | Loutchiana | step 1 | `config/product_mapping.csv` |
| 4 | Architecture | The diagram: seven layers, one purpose each | Loutchiana | step 1 (2:00) | `docs/images/architecture.png` |
| 5 | Why these tools | NiFi, MinIO, Spark, Parquet, MongoDB, Redis, MLlib: one line each, with the alternative rejected | Loutchiana | step 1 | `docs/architecture.md`, section 7 |
| 6 | Step 2. Historical ingestion | The saved manifest: source, time, size, checksum, record count | Marwa | 1:30 | `manifest.json` |
| 7 | Step 3. Bounded incremental run | Window, overlap, pagination, retries, run log, high-water mark | Marwa | 2:30 | run log |
| 8 | Step 4. Spark, quality, reconciliation | Six dimensions, thresholds, quarantine, the reconciliation equation | Joseph | 2:30 | quality report |
| 9 | Step 5. Rerun | Same window twice: counts before and after are identical | Joseph | 1:30 | `docs/evidence/idempotency.md` |
| 10 | Step 6. MongoDB | Collections, indexes, one aggregation, before and after indexing | Christopher | 2:00 | `docs/evidence/benchmark.md` |
| 11 | Step 7. Dashboard | Q1 and Q2, including the Spark MLlib emerging-issues result | Perla | 2:00 | dashboard, `docs/findings.md` |
| 12 | Findings | Three or four findings with number, denominator, period and caution | Perla, Loutchiana | (inside step 7) | `docs/findings.md` |
| 13 | Step 8. Two limitations | Not a random sample; single node and daily batch | Charbel | 1:30 | |
| 14 | Next improvement | MongoDB replica set | Charbel | (inside step 8) | |
| 15 | Team | Who owns what, and the tests and defects that give confidence | Charbel | | contribution logs, test plan |

**Rules for the slides:** one message per slide; the diagram and the evidence screenshots do the talking; no text that the presenter only reads; numbers identical to the dashboard and `docs/findings.md`; every chart with its caution. Every step also needs a backup screenshot in `docs/evidence/demo/` in case the live step fails.

## 2. Step 1 script (Loutchiana, 2 minutes, about 260 words)

*Slide 4 on screen; point at each layer while you speak.*

"Good morning. We are Group 5 and we chose option 5: money transfers and digital payments. That covers domestic and international transfers, mobile or digital wallets and virtual currency, about 200,000 complaints in the CFPB Consumer Complaint Database. Our users are policy analysts, service managers and the person who maintains the platform.

The platform follows the course's framework from collection to visualisation, in seven layers. One: Apache NiFi collects the data every 24 hours and keeps the provenance of every run; a tested Python collector is our fallback. Two: MinIO stores every raw file unchanged. Three: Spark cleans, deduplicates and checks quality, and a failing check stops the run. Four: the trusted data is kept as Parquet, with the rejected records in quarantine. Five: MongoDB serves the data to the dashboard. Six: our analysis scripts and two Spark MLlib models describe the data. Seven: a Streamlit dashboard presents it, with Redis caching the queries.

It is a batch platform, refreshed every 24 hours, because the CFPB publishes daily and the brief rules out streaming. The analysis is descriptive and diagnostic: it says what was reported, not why, and it does not predict. Everything starts with one Docker Compose command. Now Marwa will show how the data comes in."

**Facts you must be able to defend:** the number of records (full load of 24 Nov: 19,397,176 raw, 205,271 curated; 199,561 of them under the current label, 199,152 on 20 Nov in the API), the layer names, why batch, why descriptive.

## 3. Questions you may be asked on the architecture

| Question | Short answer |
|---|---|
| Why NiFi, and why keep Python? | NiFi is the course's ingestion tool: scheduling, routing and a provenance repository that records every run. The Python collector is tested and uses the same raw paths and run log, so the demo cannot depend on one tool. |
| Why not Kafka or Flume? | Kafka and Flume serve streaming and log collection. The brief rules out real-time and simulated streaming, and the CFPB publishes daily. Sqoop moves relational data, and it cannot be paused and resumed. |
| Why MinIO, and why keep raw separate? | Raw files are whole objects written once, which is the object-storage role. Keeping them unchanged means we can reprocess with new rules and trace any figure back to its source. HDFS or Ceph need a cluster that 200,000 records do not justify. |
| Why Parquet? | Columnar, compressed, schema in the footer, and a reader fetches only the columns it needs. CSV is slow and compressed text cannot be split. ORC is the comparable alternative. |
| Why MongoDB, and what is the CAP position? | The dashboard filters complaint-shaped records on several fields at once, which suits the document model. Key-value stores cannot filter like that. Our single node has no network partition; a replica set would favour consistency. |
| Why Spark in local mode? | The same DataFrame code runs on a cluster, but here the driver and executors run in one container. Transformations are lazy, so the job caches the DataFrame that the checks and aggregates reuse. |
| Why not Spark Streaming? | It works in micro-batches on a live stream. There is no live stream: the CFPB publishes daily. |
| What does Redis do? | It caches dashboard query results, cache-aside, key = query plus filters, time-to-live 600 seconds, so repeated views do not re-run the same aggregation. |
| Why does the dashboard not read the raw layer? | Raw is unvalidated and not indexed. MongoDB holds curated data and aggregates with indexes on the dashboard filters, and the dashboard must not show individual records. |
| How is MLlib used, and why does it not predict? | Linear regression on each issue's monthly share gives a slope (emerging issues); K-means groups states by complaint profile. Rules are fixed in advance. Brief V2 keeps predictive modelling out of scope, so both describe past data. |
| How do you trace a dashboard figure to its source? | Query in `database/queries.py` reads MongoDB; each document carries `source_type`, `ingest_run_id` and `ingested_at`; the run id leads to the raw objects, the run log, the manifest and the quality report. |
| Why the legacy product labels? | Before April 2017 the CFPB used other labels (Money transfers, Virtual currency, Prepaid card with Mobile wallet). The mapping keeps the original label next to the standard one; approval is pending with the lecturer. |
| What happened with the MinIO image? | MinIO stopped publishing official images in October 2025. We pin a community rebuild of its last release to an exact tag, ports on 127.0.0.1, and the lecturer was informed (defects D-001, D-002). |
