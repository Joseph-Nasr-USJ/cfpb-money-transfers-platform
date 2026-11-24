# Full historical load: evidence (24 Nov 2026)

The complete CFPB complaint database was collected, processed by Spark, checked by the quality
gate and loaded into MongoDB in one run of the pipeline chain.

## Run

| Item | Value |
|---|---|
| run_id | `20261124T134839Z_full` |
| Command | `make pipeline-full` (runs `python -m ingestion.pipeline --mode full`) |
| Source | CFPB complaint database, `complaints.csv.zip` downloaded on 24 Nov 2026 (371,218,594 bytes) |
| Machine | Windows with Docker (WSL2); Spark 3.5.9 in local mode, driver memory 4 GB; the `nifi` and `dashboard` containers were stopped during the run |
| Code | `main` after PR #34 |

## Timings (UTC)

| Step | Finished | Duration |
|---|---|---|
| Download, upload of the ZIP and CSV to MinIO, record count, manifest | 13:55:43 | about 7 min |
| Spark job: read, domain filter, de-duplication, quality report, curated Parquet and aggregates | 13:58:21 | 2 min 38 s |
| MongoDB load: upsert 205,271 complaints, rebuild both aggregate collections | 13:58:33 | 12 s |
| High-water mark update | 13:58:33 | under 1 s |
| **Whole chain** (measured around `make pipeline-full`) | | **9.9 min** |

During the Parquet write Spark logged `Total allocation exceeds 95.00% of heap memory` and scaled
the row group size down for 31 parallel writers. This is a warning, not an error: it shows that a
4 GB driver is close to the minimum for the full file.

## Counts and reconciliation

| Measure | Value |
|---|---|
| Records in the CSV (all CFPB products) | 19,397,176 |
| Out of domain (other products) | 19,191,793 |
| Duplicates removed | 0 |
| Checked records in the domain | 205,383 |
| Quarantined | 112 (invalid state 32, date sent before date received 80) |
| Curated | **205,271** |
| Reconciliation | 205,271 + 112 + 19,191,793 + 0 = 19,397,176 (exact) |
| MongoDB `complaints` after the load | **205,271** (equal to curated) |
| `agg_monthly` | 73,597 rows covering 205,271 complaints |
| `agg_company_year` | 8,078 rows covering 205,271 complaints |
| High-water mark | 2026-10-22 moved to **2026-11-23** |

## Quality report

Overall status **PASS**, quality gate passed. Every check passed:

| Dimension | Result |
|---|---|
| Uniqueness | no null or duplicate `complaint_id` in curated data |
| Completeness (required) | `complaint_id`, `date_received`, `product`, `issue`, `company`: 100% |
| Completeness (optional, reported) | `state` 95.013%, `zip_code` 99.694%, `company_public_response` 14.175% (expected to be sparse); all other optional fields 100% |
| Completeness (`sub_issue`) | not applicable for all 205,383 records: no record of the four product labels has a sub-issue |
| Validity | invalid state 32 (0.016%), negative lag 80 (0.039%): both far below the 0.5% warning level |
| Consistency | every product and sub-product combination maps to a standard sub-product (0 unmapped) |
| Freshness | newest complaint received on 2026-11-23, 1 day before the run (threshold 3 days); ingested at 2026-11-24 13:48:39 UTC |
| Reconciliation | raw = curated + quarantined + out of domain + duplicates removed, exact |

## Analyses run on this data (`make ml`, 24 Nov 2026)

- **Emerging issues** (Spark MLlib `LinearRegression` on each issue's monthly share): 43 issues
  modelled over the 24 complete months from 2024-11-01 to 2026-10-31. None met all three
  thresholds together (slope at least +0.2 percentage points per month, R² at least 0.5, at least
  50 complaints), so no issue is flagged as emerging in this window.
- **State clusters** (Spark MLlib `KMeans` on each state's issue profile): 51 states with at
  least 100 complaints (50 states and DC). The silhouette score was highest for k = 2 (0.696;
  k = 6 gave 0.444). Cluster 0 has 15 states (AL, AR, GA, IL, IN, KY, LA, MI, MS, NC, OK, SC,
  TN, TX, WI) and cluster 1 the other 36. The clusters describe similar complaint issue profiles,
  not geographic risk.

## How to reproduce

~~~
make up
docker compose stop nifi dashboard
make pipeline-full
docker compose start nifi dashboard
make ml
~~~
