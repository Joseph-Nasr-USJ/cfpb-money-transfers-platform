# MongoDB Model — Banking Complaints Data Platform

**Team:** Group 5 — Money Transfers and Digital Payments

**Database:** `cfpb_money_transfers`

**Owner:** Christopher Al Hassrouty (Database Lead)

**Status:** Model and implementation drafted; production integration, tests and benchmarking pending

## 1. Purpose and design decisions

MongoDB is the **serving layer** between Spark's curated Parquet output in MinIO and the Streamlit dashboard. It holds individual curated complaint documents for **internal querying** and precomputed aggregates for efficient dashboards. The dashboard reads MongoDB only, **never** raw files, and must not show individual complaint records.

The authoritative transformation and field names come from Spark and the team's shared curated schema. The ingestion paths (historical CSV and incremental API) must converge on that schema. Complaint counts describe records in the CFPB database, not customer experience or financial harm across the whole market.

- **Grain:** exactly one document per unique `complaint_id` in `complaints`.
- **Identifier:** MongoDB `_id` equals `complaint_id` (numeric BSON `Int64` for the production loader). This enforces uniqueness.
- **Dates:** represent `date_received` and `date_sent_to_company` as native BSON `Date`, at 00:00:00 UTC, and `ingested_at` as a UTC timestamp. BSON Date supports correct chronological range queries, date grouping and indexing; date strings can sort incorrectly if formats differ.
- **Idempotency:** use `UpdateOne({"_id": complaint_id}, {"$set": document}, upsert=True)` in batches, so rerunning a load updates the same complaint rather than inserting a second copy.
- **Lineage:** preserve the shared canonical top-level fields `source_type`, `ingest_run_id`, and `ingested_at`. A `lineage` subdocument may additionally mirror these fields for convenient inspection but **must not replace** the top-level schema; confirm this optional addition during integration.
- **Missing values:** distinguish null/missing source fields from literal categories such as `Unknown` where the agreed processing rules require them.

## 2. Collections

### 2.1 `complaints` — curated records

**Purpose:** primary queryable, deduplicated collection for detailed descriptive analysis.

**Grain:** one document per complaint.

**Source:** Spark `curated/complaints/option=5/year=YYYY/month=MM/` in the MinIO bucket `cfpb-lake` (`MM` is two digits). This path must be deployed together with Joseph's corresponding Spark writer change.

Example (mongosh syntax; illustrative, **not** a real consumer record):

```javascript
{
  _id: NumberLong("1234567890"),
  complaint_id: NumberLong("1234567890"),
  date_received: ISODate("2026-10-01T00:00:00Z"),
  date_sent_to_company: ISODate("2026-10-03T00:00:00Z"),
  product: "Money transfer, virtual currency, or money service",
  sub_product: "Domestic (US) money transfer",
  product_std: "Money transfer, virtual currency, or money service",
  sub_product_std: "Domestic (US) money transfer",
  is_core_payment: true,
  issue: "Fraud or scam",
  sub_issue: null,
  company: "Example Company",
  company_public_response: null,
  company_response: "Closed with explanation",
  timely_response: true,
  state: "NY",
  zip_code: null,
  tags: [],
  is_older_american: false,
  is_servicemember: false,
  submitted_via: "Web",
  year: 2026,
  month: 10,
  year_month: "2026-10",
  processing_lag_days: 2,
  source_type: "api",
  ingest_run_id: "20261110T020000Z_api",
  ingested_at: ISODate("2026-11-10T02:00:00Z"),
  lineage: {
    source_type: "api",
    ingest_run_id: "20261110T020000Z_api",
    ingested_at: ISODate("2026-11-10T02:00:00Z")
  }
}
```

The source-defined `processing_lag_days` is **date sent to company minus date received**, **not** the time taken to resolve a complaint. `issue: "Fraud or scam"` is a complaint classification, **not** independently verified fraud. The legacy-to-standard product mapping remains subject to lecturer approval.

**Planned indexes:** unique automatic `{_id: 1}`, and compound `{sub_product_std: 1, date_received: 1}`, `{issue: 1, date_received: 1}`, `{state: 1, date_received: 1}`, `{company: 1, date_received: 1}`, `{submitted_via: 1, date_received: 1}`. Equality fields precede the date range. Confirm the final selection against real dashboard query patterns; extra indexes increase storage and write costs.

### 2.2 `agg_monthly` — dashboard-ready monthly summaries

**Purpose:** monthly counts and response measures for frequently used multi-dimensional charts.

**Grain:** one row per unique combination of `year_month`, `sub_product_std`, `issue`, `state`, `submitted_via`, and `company_response`.

**Source:** Spark `curated/aggregates/agg_monthly/`.

```javascript
{
  year_month: "2026-10",
  sub_product_std: "Domestic (US) money transfer",
  issue: "Fraud or scam",
  state: "NY",
  submitted_via: "Web",
  company_response: "Closed with explanation",
  complaint_count: 18,
  timely_yes_count: 17,
  timely_known_count: 18,
  lag_sum_days: 36,
  lag_count: 18
}
```

Index: `{year_month: 1, sub_product_std: 1}`. The numbers above are illustrative, not observed findings. For analyses requiring fields absent from this aggregate (such as `sub_issue` or `company`), query `complaints` rather than inventing information from the summary.

### 2.3 `agg_company_year` — annual company/sub-product counts

**Purpose:** company-share summaries, **not** company service-quality rankings.

**Grain:** `year`, `company`, `sub_product_std`.

**Source:** Spark `curated/aggregates/agg_company_year/`.

```javascript
{
  year: 2025,
  company: "Example Company",
  sub_product_std: "International money transfer",
  complaint_count: 42
}
```

Candidate index: `{year: 1, sub_product_std: 1, company: 1}`, subject to benchmark results. Company complaint totals lack denominators for customers and transaction volume.

### 2.4 `pipeline_runs` — operational audit trail

**Purpose:** record each ingestion/pipeline run and the MongoDB load reconciliation evidence.

**Grain:** one document per `run_id` (use `_id = run_id` for idempotent writes).

```javascript
{
  _id: "20261110T020000Z_api",
  run_id: "20261110T020000Z_api",
  run_type: "api",
  started_at: ISODate("2026-11-10T02:00:00Z"),
  finished_at: ISODate("2026-11-10T02:04:00Z"),
  outcome: "success",
  record_count: 120,
  mongo_count_after: 200120,
  high_water_mark_next: { date_received_max: "2026-11-09" }
}
```

Also retain the remaining non-secret collector run metadata, including endpoint, request parameters, window, pagination, HTTP status/retries, raw object paths and checksum where available. Index `_id` suffices for run-ID lookups; a chronological `finished_at` index can be added if operational queries need it.

### 2.5 `quality_reports` — data-quality evidence

**Purpose:** store Spark quality reports for monitoring and the dashboard's data-quality view.

**Grain:** one document per `run_id`, with `_id = run_id`.

```javascript
{
  _id: "20261110T020000Z_api",
  run_id: "20261110T020000Z_api",
  generated_at: ISODate("2026-11-10T02:05:00Z"),
  source_type: "api",
  counts: { raw_input: 120, out_of_domain: 0, duplicates_removed: 5,
            quarantined: 2, curated: 113 },
  checks: [{ dimension: "uniqueness", rule: "unique complaint_id", status: "PASS" }],
  completeness: { complaint_id: 100.0 },
  freshness: { latest_date_received: "2026-11-09", ingestion_lag_days: 1 },
  overall_status: "PASS",
  quality_gate: "passed"
}
```

Examples are illustrative; actual counts and quality statuses must come from the Spark job. The six required V2 quality dimensions are **uniqueness, completeness, validity, consistency, freshness and reconciliation**. Reconciliation checks the raw-to-curated accounting and, **after MongoDB loading**, the equality of curated and MongoDB complaint counts; the loader records this latter count as `pipeline_runs.mongo_count_after`.

The Spark report exposes `quality_gate` with the decisions `"passed"`, `"stopped"` and `"overridden"`. The MongoDB loader **aborts before opening MongoDB only when `quality_gate == "stopped"`**. An explicitly overridden gate can proceed even if `overall_status` reports `"FAIL"`, allowing controlled fixture testing with Spark's `--ignore-quality-gate`; this does not mean the underlying quality warnings or failures disappear. Keep the actual status and override evidence in `quality_reports`.

### 2.6 `ml_emerging_issues` — descriptive emerging-issue analysis

**Purpose:** serve Perla's **Spark MLlib** emerging-issue results to the dashboard; this collection stores *derived analytical results*, not individual complaints.

**Grain:** one result per `(sub_product_std, issue)` for the defined 24-complete-month analysis window.

**Writer:** Perla's `analytics/ml_emerging_issues.py` (the MongoDB loader does not train the models or write this collection).

**Index:** the built-in unique `{_id: 1}` is sufficient for this small collection; do not introduce additional secondary indexes without a measured query need.

Expected content: sub-product and issue labels, a slope in **percentage points per month**, R², latest observed issue share, count of complaints in the analysis window, an emerging-issue decision based on the documented thresholds, `generated_at` and the curated input record count. The agreed rule is slope >= +0.2 percentage points/month, R² >= 0.5, and at least 50 complaints in the window. This is a description of published complaint shares, **not a forecast or a claim of fraud**.

Illustrative shape **only** (field names beyond the shared contract must be finalized with Perla before dashboard integration):

```javascript
{
  _id: "Domestic (US) money transfer|Fraud or scam",
  sub_product_std: "Domestic (US) money transfer",
  issue: "Fraud or scam",
  slope_pp_per_month: 0.25,
  r_squared: 0.62,
  latest_share_pct: 23.5,
  complaints_in_window: 500,
  is_emerging: true,
  generated_at: ISODate("2026-11-21T12:00:00Z"),
  curated_count: 200000
}
```

Reader: `ml_emerging_issues(db, filters)` in `database/queries.py`, returning a list and `[]` when the collection or filtered result is empty. Use the dashboard's agreed filters and preserve the helper's return structure for Redis caching.

### 2.7 `ml_state_clusters` — descriptive state segmentation

**Purpose:** serve Perla's **Spark MLlib K-means** state-profile clusters to the dashboard.

**Grain:** one result per eligible state, with a cluster label and a documented cluster profile; states with fewer than 100 complaints are listed separately.

**Writer:** Perla's `analytics/ml_state_clusters.py`.

**Index:** the automatic `{_id: 1}` is sufficient for this small collection.

The team evaluates `k` from 2 through 6 using silhouette score, with seed 42; features describe the issue and submission-channel shares. Include the selected cluster, descriptive leading issues/channels, silhouette, `generated_at`, and curated input record count. Clusters **do not** describe individual consumers or service quality.

Illustrative shape **only** (exact field names and `_id` format to be confirmed with Perla):

```javascript
{
  _id: "NY",
  state: "NY",
  cluster: 1,
  leading_issues: ["Fraud or scam"],
  leading_channels: ["Web"],
  silhouette: 0.41,
  generated_at: ISODate("2026-11-21T12:00:00Z"),
  curated_count: 200000
}
```

Reader: `ml_state_clusters(db)` in `database/queries.py`, returning a list and `[]` if there are no results. Perla owns ML model fitting, collection output formats, and refresh after a successful curated-data load; coordinate changes to the reader contract before altering the dashboard's Redis-cached usage.

### 2.8 `state_population` — optional enrichment

**Purpose:** hold documented US state population estimates **only if** the team implements and validates this optional enrichment.

**Grain:** one document per state and reference year, with a documented source and update date. Do not create or populate it unless Perla proceeds with population-normalized analysis.

## 3. Loading and query contracts

1. `python -m database.load --run-id <id>` reads curated Parquet and the two aggregate outputs from MinIO using `pyarrow.fs.S3FileSystem` with credentials from environment variables. It never directly reads raw data to serve the dashboard.
2. Convert Parquet/Python dates to BSON `Date` before writing. Upsert `complaints` in batches of **5,000**, unordered; the same complaint ID must not create duplicates on rerun.
3. **Refresh aggregates whenever their underlying curated records change.** Replace aggregate collections safely by loading temporary collections and renaming them into place (`dropTarget=True`). Each collection rename is atomic independently; replacement of both aggregates together is **not** one transaction. Preserve relevant indexes on the replacement collections.
4. Copy the run log and quality report to `pipeline_runs` and `quality_reports`; store `mongo_count_after` in the run document for post-load **reconciliation** with the curated count. Reject a Spark `quality_gate` of `"stopped"` before opening the database; allow `"passed"` and `"overridden"`.
5. `database/queries.py` exposes shared filter-aware aggregations to Perla's dashboard, with filters including date range, sub-product, issue, state, submission channel and company. It also exposes the two ML read helpers. Return stable list/dictionary shapes, with `[]` for empty list-producing queries, and coordinate signature/shape changes with Perla **before** changing them because her Redis cache uses those results (configured TTL: 600 seconds).
6. Reconcile counts at the **same scope** (a full curated snapshot versus MongoDB, or a specific run's affected records). Rerunning an identical window must not increase unique complaint counts.

## 4. Performance and verification evidence

- Implement the planned indexes in `database/indexes.py` and record their actual names and keys.
- Compare three representative query patterns **before and after indexing** using MongoDB `explain("executionStats")`; record median execution time, `totalDocsExamined`, `totalKeysExamined`, and winning plan (typically `COLLSCAN` before, `IXSCAN` after when usable).
- Test: duplicate `_id` insertion raises `DuplicateKeyError`; upsert twice does not increase count; `date_received` is a BSON Date; aggregate totals reconcile with the same curated snapshot; impossible filters return empty results; a `quality_gate` of `"stopped"` prevents a MongoDB connection, while `"passed"` and `"overridden"` proceed; query timings meet a documented threshold.
- Save evidence in `docs/evidence/benchmark.md`, database tests in `tests/database/`, and MongoDB screenshots for the technical report and live demonstration.

## 5. Open integration decisions

- Confirm final product mapping with the lecturer and Joseph.
- Confirm with Joseph whether the optional `lineage` nested object is emitted by Spark or assembled solely by the MongoDB loader; do **not** drop the canonical flat lineage fields.
- Confirm Perla's `docs/metrics.md` and agree on query return formats before dashboard integration.
- Deploy the updated `curated/complaints/option=5` reader **in the same release as Joseph's Spark writer**; verify real MinIO partitions have two-digit months.
- Confirm the exact Spark MLlib document fields and any dashboard filters with Perla; retain the current query function names and return shapes.
