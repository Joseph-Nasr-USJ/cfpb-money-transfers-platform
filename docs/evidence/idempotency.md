# Idempotency evidence: rerunning Spark and the MongoDB load changes nothing

This file shows that the processing and serving steps can be run again on the same input without
creating duplicates or changing totals. It was produced on real CFPB data, not on test fixtures.

## Run

| Item | Value |
|---|---|
| run_id | `20261124T084259Z_api` (24 Nov 2026, 08:42:59 UTC) |
| Source | CFPB complaint API, incremental collector (`ingestion/incremental.py`) |
| Window | requested `date_received` 2026-10-20 to 2026-10-21; the collector sends the API an end date one day later because the API's end bound proved inclusive (`docs/api_notes.md`, finding 4), so complaints received on 2026-10-22 are included |
| Products | Money transfer, virtual currency, or money service; Money transfers; Virtual currency; Prepaid card / Mobile wallet |
| Stack | Docker Compose on Windows (WSL2), Spark 3.5.9 with Java 17, MinIO, MongoDB 7.0 |
| Code | `main` after the merge of PR #29 |

The same window was collected and processed on a second machine the day before
(run_id `20261123T184745Z_api`) with identical results: 468 raw, 468 curated, 468 in MongoDB,
323 `agg_monthly` rows and 105 `agg_company_year` rows.

## Commands

Run from the repository root, in this order (macOS or Linux shell):

~~~
docker compose run --rm pipeline python -m ingestion.incremental --start 2026-10-20 --end 2026-10-21
make process SOURCE=api RUN_ID=20261124T084259Z_api
make load RUN_ID=20261124T084259Z_api
docker compose exec mongo mongosh cfpb_money_transfers --quiet --eval "db.complaints.countDocuments()"
make load RUN_ID=20261124T084259Z_api
docker compose exec mongo mongosh cfpb_money_transfers --quiet --eval "db.complaints.countDocuments()"
docker compose exec mongo mongosh cfpb_money_transfers --quiet --eval "db.complaints.aggregate([{\$group:{_id:'\$complaint_id',n:{\$sum:1}}},{\$match:{n:{\$gt:1}}},{\$count:'duplicates'}]).toArray()"
docker compose exec mongo mongosh cfpb_money_transfers --quiet --eval "db.agg_monthly.aggregate([{\$group:{_id:null,total:{\$sum:'\$complaint_count'}}}]).toArray()"
make process SOURCE=api RUN_ID=20261124T084259Z_api
~~~

In PowerShell, replace each `\$` with a backtick followed by `$`.

## Results

| Step | Result |
|---|---|
| Spark, first run | raw_input 468, out_of_domain 0, duplicates_removed 0, quarantined 0, curated 468; quality gate `passed` |
| MongoDB load, first run | 468 unique complaints; `agg_monthly` 323 rows (468 complaints); `agg_company_year` 105 rows (468 complaints) |
| `complaints` count after the first load | **468** |
| MongoDB load, second run (same run_id) | 468 unique complaints; same 323 and 105 aggregate rows |
| `complaints` count after the second load | **468** (unchanged) |
| `complaint_id` values present more than once | **none** (`[]`) |
| Sum of `complaint_count` in `agg_monthly` | **468** (matches the `complaints` count) |
| Spark, second run (same run_id) | same counts; `curated_total` **468** (unchanged) |

## Why the reruns are safe

- **Spark:** curated data is merged by `complaint_id`. A rerun replaces the affected partitions
  through a staging folder instead of appending, so the curated total stays the same.
- **MongoDB complaints:** every curated row is written as an upsert keyed by `complaint_id`, so a
  second load updates the same documents instead of inserting new ones.
- **MongoDB aggregates:** `agg_monthly` and `agg_company_year` are rebuilt in a staging collection
  and then published, so the dashboard never sees a half-written or doubled aggregate.
- The loader line `Upserted N curated rows` counts rows sent to MongoDB, not rows changed. That is
  why the document count and the duplicate check above are the actual proof.
- Each aggregate rename is atomic, but the two renames together are not one transaction. For a
  moment `agg_monthly` can already be the new version while `agg_company_year` is still the old
  one. Both are rebuilt from the same curated snapshot, so they agree again after the second rename.

## Quality report for this run

Overall status `WARN`, quality gate `passed`. All checks are `PASS` except freshness:

| Dimension | Rule | Measured | Threshold | Status |
|---|---|---|---|---|
| Uniqueness | `complaint_id` not null and unique in curated data | 0 null, 0 duplicate | 0 problems | PASS |
| Completeness | required fields filled (complaint_id, date_received, product, issue, company) | 100% each | >= 99.5% | PASS |
| Completeness | no optional field always empty | none always empty | none | PASS |
| Validity | dates parse; timely response Yes/No; valid state; date sent not before date received | 0 invalid each | WARN > 0.5%, FAIL > 2.0% | PASS |
| Consistency | every product and sub-product combination maps to a standard sub-product | 0 unmapped | 0 | PASS |
| Freshness | latest `date_received` is recent | 33 days | <= 3 days | WARN |
| Reconciliation | raw = curated + quarantined + out_of_domain + duplicates_removed | 468 = 468 | exact | PASS |

The freshness warning is expected: the window was chosen a month in the past. The newest complaint
was received on 22 Oct 2026, 33 days before the run on 24 Nov 2026. A warning is recorded and
shown on the dashboard. Only a failure stops publication.

Note: in the report of this run, freshness is still named `timeliness` and reconciliation is still
named `integrity`. The rename to the brief's names is a separate change.
