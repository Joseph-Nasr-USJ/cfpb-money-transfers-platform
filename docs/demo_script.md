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
docker compose stop pipeline
```

Expected: `minio` and `mongo` healthy (plus `nifi` and `redis` once merged), `minio-init` exited with 0, `make test` ends with `passed` and no failures. `docker compose stop pipeline` pauses the 24-hour scheduler so it does not process the run of step 3 on its own before step 4; every `make` command still works. Restart it after the demo (end of step 5). Open in browser tabs: MinIO console http://localhost:9001, NiFi (address in the README), the dashboard http://localhost:8501. Check that the saved manifest, the run to be repeated and the dashboard data exist. Clear the Redis cache only if the data changed.

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
- **Command** (Python collector; NiFi is the planned scheduler, its flow is not exported yet). Collect a short window and note the `run_id` printed on the last line. Collection only: do not use `make pipeline-incremental` here, because it also runs Spark and the load and step 4 needs the run still unprocessed:
  ```
  docker compose run --rm pipeline python -m ingestion.incremental --start 2026-10-20 --end 2026-10-21
  ```
- **Say:** "The run uses a bounded date window starting at the high-water mark minus the overlap, pagination, timeouts and bounded retries. Each response is stored in MinIO before it is processed. The run log records the run id, window, HTTP status, retries, outcome, record count and checksum. The high-water mark moves only after a successful run, and an empty success is different from a failed request."
- **Expected result:** a new `raw/cfpb/api/ingest_date=.../run_id=.../response_*.json` and `logs/ingestion/run_id=<run_id>.json` in MinIO; note the `run_id`.
- **Backup:** screenshots of the raw folder and the run log: `docs/evidence/demo/step3_*.png`.

## Step 4. Spark, quality checks and reconciliation (Joseph, 2:30)

- **Before the session (Joseph):** open one PowerShell window in the repository root for steps 4 and 5 and paste these two helper functions once. They only read data.

~~~
function Show-Counts {
    docker compose exec mongo mongosh cfpb_money_transfers --quiet --eval "print('complaints in MongoDB:  ' + db.complaints.countDocuments()); print('agg_monthly total:      ' + db.agg_monthly.aggregate([{`$group:{_id:null,t:{`$sum:'`$complaint_count'}}}]).toArray()[0].t); print('duplicate complaint_id: ' + db.complaints.aggregate([{`$group:{_id:'`$complaint_id',n:{`$sum:1}}},{`$match:{n:{`$gt:1}}}]).toArray().length)"
}
function Show-Quality([string]$RunId) {
    $py = @(
        "import os",
        "from ingestion import minio_utils as m",
        "r = m.read_json('quality/run_id=' + os.environ['RUN_ID'] + '/quality_report.json')",
        "print('overall_status:', r['overall_status'], '| quality_gate:', r['quality_gate'])",
        "print('counts:', r['counts'])",
        "for c in r['checks']: print(c['status'].ljust(5), c['dimension'].ljust(15), c['rule'], '| measured:', c['metric'], '| threshold:', c['threshold'])"
    ) -join "`n"
    $py | docker compose run --rm -T -e RUN_ID=$RunId pipeline python -
}
~~~

- **0:00, start Spark at once** with the run_id printed in step 3 (Spark takes about 20 seconds: start talking and finish the sentence when the summary line appears). The run is still unprocessed because the scheduler was stopped before the demo, whether step 3 used NiFi or the Python collector.

~~~
$r = "<run_id from step 3>"
make process SOURCE=api RUN_ID=$r
~~~

- **Show while Spark runs:** `tests/processing/test_quality.py`, test `test_csv_fixture_fails_the_quality_gate`.
- **Say while Spark runs:** "This is the Spark job on the run Marwa just collected. It reads the raw API pages with an explicit schema, never an inferred one, standardises the column names, parses the dates, normalises Yes and No, maps every product and sub-product to our standard sub-products and keeps only our domain. Duplicates are removed by Complaint ID with a fixed tie-break, so every run gives the same result. A record that breaks a rule is not dropped silently: it goes to quarantine with its reason. Before anything is published, a quality gate runs six checks with thresholds we fixed before seeing the data: uniqueness, completeness, validity, consistency, freshness and reconciliation. A warning is recorded; a failure makes Spark exit with code 1 and nothing is published. This test proves it: our fixture file contains an invalid date, an invalid state, a negative processing lag and a missing ID, and the gate stops the run while the counts still reconcile."
- **When Spark prints its summary line** (`overall_status`, `quality_gate`, `counts`, `curated_total`), **say:** "Reconciliation: raw input equals curated plus quarantined plus out of domain plus duplicates removed, exactly. On the full historical file that was 19,397,176 records: 205,271 curated, 112 quarantined, 19,191,793 outside our domain and no duplicates, identical on three machines. `curated_total` is the whole curated dataset: this run was merged into it by Complaint ID, not appended."
- **Then show the report:** `Show-Quality $r`. **Say:** "Here are the six dimensions with the measured value and the threshold for each. The report is stored in the lake at `quality/run_id=<run_id>/quality_report.json`, next to the quarantined records. A freshness warning is normal for a window in the past."
- **Then load:** `make load RUN_ID=$r 2>$null | Select-Object -Last 5` (the loader prints one progress line per batch for the whole curated dataset; this keeps only its last five lines). **Say:** "The loader only runs when the gate passed. MongoDB now holds exactly the curated total: the last reconciliation, curated equals MongoDB."
- **Expected result:** `quality_gate` `passed`, `overall_status` PASS or WARN, the counts adding up exactly, and the `Load completed` number equal to `curated_total`.
- **If Spark has not finished at 1:30:** show `docs/evidence/full_load.md` and the backup screenshot, and finish the step while it completes.
- **Backup:** `docs/evidence/demo/step4_quality_report.png` and `docs/evidence/full_load.md`.

## Step 5. Rerun: counts not inflated (Joseph, 1:30)

- **0:00, counts before:** `Show-Counts`
- **Then rerun Spark and the load on exactly the same input:**

~~~
make process SOURCE=api RUN_ID=$r 2>$null | Select-Object -Last 1; make load RUN_ID=$r 2>$null | Select-Object -Last 5
~~~

- **Say while it runs:** "Now the same run again, Spark and the load, on exactly the same input. Three things stop anything from doubling. Spark merges curated data by Complaint ID and replaces the affected partitions through a staging folder instead of appending. MongoDB writes every complaint as an upsert keyed by Complaint ID, so a second load updates the same documents. And the two aggregate collections the dashboard reads are rebuilt in staging and then swapped in, so the dashboard never sees a half-written or doubled total."
- **Then counts after:** `Show-Counts`. **Say:** "The loader just upserted every curated row again, all of them, not only this run's, and nothing moved. Same number of complaints, same aggregate total behind the dashboard, zero duplicate IDs, and Spark printed the same `curated_total`. That is what lets the scheduler retry a failed run safely every day."
- **Expected result:** the three lines of `Show-Counts` identical before and after, and the same `curated_total` in both Spark summaries.
- **If the rerun has not finished at 1:10:** show the results table of `docs/evidence/idempotency.md` (the same proof recorded on real data, 468 complaints, two machines).
- **Rehearsal of Fri 27 Nov (office PC):** run `20261127T120713Z_api`, 36 complaints; Spark about 20 seconds; the whole of step 5 about 35 seconds; `Show-Counts` 205,707, 205,707 and 0, identical before and after.
- **Backup:** `docs/evidence/idempotency.md` and `docs/evidence/demo/step5_counts.png`.
- **After the demo:** `docker compose start pipeline` restarts the scheduler. It will process the run of step 3 once more and move the high-water mark, which changes nothing because the run is idempotent.

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
- **Say:** the three points above in your own words, plus how the tests and the defect log give confidence in what exists today (162 passing tests and 1 skipped on 27 Nov, known bad records caught).
- **Backup:** `docs/evidence/test_results_2026-11-27.txt` (update it before the demo).

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
