# Demo script

Owner: Charbel Mazraani (coordinator). The live demonstration of the Banking Complaints Data Platform, option 5 (Money Transfers and Digital Payments): **15 minutes plus 5 minutes of questions**, on **Monday 30 November 2026**. Eight steps, one presenter each, as in brief V2 section 11.

**Updated Fri 27 Nov 2026.** Open points are listed at the end. Every step needs a backup screenshot in `docs/evidence/demo/` in case the live step fails.

## Rules of the demo

- Use a **saved manifest** for the full historical load. A small repeatable run is enough to show the processing path live; the full load is never run live.
- The demo includes **one controlled rerun** (steps 3 and 5): the same window runs twice and the counts do not change.
- Everything starts from a stack that is already running (`make up` done before the session) and a terminal opened in the repository root.
- Each presenter says what the step shows, what the evidence is and what could go wrong, in their own words. **Everyone must be able to explain the whole platform.**
- Stay inside the time. The coordinator (Charbel) keeps the clock and cuts a step at its limit.

## Timeline

| Step | What is shown | Presenter | Time |
|---|---|---|---|
| 1 | Architecture and financial scope | Loutchiana | 2:00 |
| 2 | Historical ingestion evidence: the saved raw manifest | Marwa | 1:30 |
| 3 | Bounded incremental run: raw output and run metadata | Marwa | 2:30 |
| 4 | Spark transformations, quality checks, count reconciliation | Joseph | 2:30 |
| 5 | Rerun: counts and dashboard measures not inflated | Joseph | 1:30 |
| 6 | MongoDB collections, indexes and one aggregation | Christopher | 2:00 |
| 7 | Dashboard answers Q1 and Q2 | Perla | 2:00 |
| 8 | Two limitations and one improvement | Charbel | 1:30 |
| | **Total** | | **15:30** (trim 30 seconds in rehearsal) |

## Before the demo (Charbel, 30 minutes before)

```
git checkout main
git pull
make up
docker compose ps
make test
```

Expected: `minio` and `mongo` healthy (plus `nifi` and `redis` once merged), `minio-init` exited with 0, `make test` ends with `passed` and no failures. Open in browser tabs: MinIO console http://localhost:9001, NiFi (address in the README), the dashboard http://localhost:8501. Check that the saved manifest, the run to be repeated and the dashboard data exist. Clear the Redis cache only if the data changed.

---

## Step 1. Architecture and financial scope (Loutchiana, 2:00)

- **Show:** the architecture diagram (`docs/images/architecture.png`, also in the README) and the product mapping `config/product_mapping.csv`.
- **Say:** "We chose option 5, Money Transfers and Digital Payments, about 195,000 complaints. The platform follows the course's framework from collection to visualisation: Apache NiFi collects, MinIO keeps raw files unchanged, Spark cleans and checks quality, MongoDB serves, Redis caches and Streamlit presents. It is a batch platform that runs every 24 hours, because the CFPB publishes daily and the brief rules out streaming. The analysis is descriptive and diagnostic only."
- **Expected result:** the audience knows the scope, the seven layers and why each tool was chosen.
- **Backup:** `docs/images/architecture.png`.

## Step 2. Evidence of the historical ingestion (Marwa, 1:30)

- **Show:** the saved raw manifest of the full load in MinIO: `raw/cfpb/full_load/ingest_date=YYYY-MM-DD/manifest.json` (record count, checksum, source URL, timestamps), next to the ZIP and CSV.
- **Say:** "The full CSV was downloaded once and stored exactly as received; raw files are never edited or overwritten. The manifest records the source, the time, the record count and the checksum, so anyone can verify the file."
- **Command:** open http://localhost:9001, bucket `cfpb-lake`, path above, on the demo laptop (the folder date is the day its full load ran). A saved copy from the run of 24 Nov is in `docs/evidence/run_20261124T135857Z_full/manifest.json`.
- **Expected result:** `manifest.json` with record count and checksum.
- **Backup:** screenshot of the manifest in `docs/evidence/demo/step2_manifest.png`.

## Step 3. Bounded incremental run (Marwa, 2:30)

- **Show:** trigger one bounded run (a short date window) and inspect its raw output and run log.
- **Command** (Python collector; NiFi is the planned scheduler, its flow is not exported yet). Collect a short window and note the `run_id` printed on the last line:
  ```
  docker compose run --rm pipeline python -m ingestion.incremental --start 2026-10-20 --end 2026-10-21
  ```
- **Say:** "The run uses a bounded date window starting at the high-water mark minus the overlap, pagination, timeouts and bounded retries. Each response is stored in MinIO before it is processed. The run log records the run id, window, HTTP status, retries, outcome, record count and checksum. The high-water mark moves only after a successful run, and an empty success is different from a failed request."
- **Expected result:** a new `raw/cfpb/api/ingest_date=.../run_id=.../response_*.json` and `logs/ingestion/run_id=<run_id>.json` in MinIO; note the `run_id`.
- **Backup:** screenshots of the raw folder and the run log: `docs/evidence/demo/step3_*.png`.

## Step 4. Spark, quality checks and reconciliation (Joseph, 2:30)

- **Show:** the Spark job on the run from step 3 and its quality report.
- **Command:** `make process SOURCE=api RUN_ID=<run_id from step 3>` then open `quality/run_id=<run_id>/quality_report.json`.
- **Say:** "Spark uses an explicit schema, standardises names, parses dates, normalises Yes and No, keeps only our domain and deduplicates by Complaint ID. Bad records go to quarantine with a reason. The quality report covers six dimensions with thresholds fixed in advance: uniqueness, completeness, validity, consistency, freshness and reconciliation. Reconciliation: raw equals curated plus quarantined plus out of domain plus duplicates removed. A failure exits with code 1 and publishes nothing."
- **Known bad record:** show that the test fixtures (invalid date, invalid state, negative interval, missing ID) are caught: `tests/processing/test_quality.py` (defect D-005).
- **Expected result:** `overall_status` PASS (or WARN) and a reconciliation that balances exactly.
- **Backup:** `docs/evidence/demo/step4_quality_report.png`.

## Step 5. Rerun: counts not inflated (Joseph, 1:30)

- **Show:** run the same window again and compare the counts before and after.
- **Command:** repeat step 3's run (or replay the same response), after step 4 run `make load RUN_ID=<run_id>`, note `db.complaints.countDocuments({})` in `mongosh`, then run `make process SOURCE=api RUN_ID=<run_id>` and `make load RUN_ID=<run_id>` a second time and count again.
- **Say:** "Deduplication by Complaint ID in Spark and upserts in MongoDB make the run idempotent: the curated count and the dashboard measures do not change."
- **Expected result:** identical counts before and after.
- **Backup:** `docs/evidence/idempotency.md` (Joseph) and `docs/evidence/demo/step5_counts.png`.

## Step 6. MongoDB collections, indexes, one aggregation (Christopher, 2:00)

- **Show:** the collections, the indexes and one aggregation, in `mongosh` or MongoDB Compass (`mongodb://localhost:27017`).
- **Command:**
  ```
  docker compose exec mongo mongosh
  use cfpb_money_transfers
  show collections
  db.complaints.getIndexes()
  ```
  then one of the aggregations A1 to A8 from `database/queries.py` (Christopher to confirm which one and the exact line to paste). The before-and-after index measurement is in `docs/evidence/benchmark.md`.
- **Say:** "One document per complaint with the Complaint ID as `_id` and native dates. Compound indexes match the dashboard filters, equality field first and then the date. Every aggregation starts with `$match` so the indexes are used."
- **Expected result:** the collections listed, the indexes shown and a result in a fraction of a second.
- **Backup:** `docs/evidence/demo/step6_*.png`.

## Step 7. Dashboard: Q1 and Q2 (Perla, 2:00)

- **Show:** the dashboard at http://localhost:8501 answering the two pre-declared questions, including the emerging-issues result from Spark MLlib.
  - **Q1:** which sub-products and issues grew fastest over 2021 to 2025, and how the mobile or digital wallet share changed.
  - **Q2:** how the "Fraud or scam" share changed across the four core sub-products since 2018.
- **Say:** the answer, the denominator (raw counts and percentages within each group), the partial-period label, and the caution: growth in complaints is not growth in usage or harm, a trend is not a forecast, the issue is chosen by the consumer.
- **Expected result:** the charts and the freshness indicator; the dashboard reads MongoDB only and shows no individual records. Open the dashboard before the demo and check it loads.
- **Backup:** `docs/evidence/demo/step7_*.png` and `docs/findings.md`.

## Step 8. Two limitations and one improvement (Charbel, 1:30)

- **Two limitations**
  1. **The data is not a random sample.** Complaints are filed by people who chose to complain, so the results describe complaints, not all consumers or the whole market; we do not generalise (course Session 1, inferential analytics). It has no transactions, balances, confirmed fraud labels or resolution durations, and company figures are shares, never a quality ranking.
  - Supporting facts if asked: about 5% of complaints have no state, so geography results cover the other 95%; no complaint in the domain has a sub-issue.
  2. **Single-node MongoDB and a local, batch platform.** If the database container is lost, recovery means rerunning the idempotent pipeline. There is no replication, and the data is refreshed once every 24 hours, not in real time (the brief rules streaming out).
- **One improvement to prioritise: a MongoDB replica set** with automatic primary election (course Session 4.1), for availability, majority writes and reads from the primary. Sharding is not needed at about 205,000 documents.
- **Say:** the three points above in your own words, plus how the tests and the defect log give confidence in what exists today (159 passing tests, known bad records caught).
- **Backup:** `docs/evidence/test_results_2026-11-24.txt` (update it before the demo).

## After the demo: questions (5 minutes)

Each presenter answers questions on their own step; anyone can be asked about any part of the platform. Before the demo, each member reads the other steps of this script.

## Open items

| Item | From | Due |
|---|---|---|
| Try the commands of steps 3 and 5 once on the demo laptop | Marwa, Joseph | rehearsals |
| Aggregation chosen and live query (step 6) | Christopher | Sat 28 Nov |
| Check the dashboard answers Q1 and Q2 (step 7) | Perla | Sat 28 Nov |
| Backup screenshots for every step in `docs/evidence/demo/` | each presenter | Fri 27 Nov |
| Timing check and trim to 15:00 | Charbel, all | rehearsals Sat 28 and Sun 29 Nov |
