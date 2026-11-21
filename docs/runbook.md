# Runbook

Owner: Charbel Mazraani. How to operate the Banking Complaints Data Platform (option 5, Money Transfers and Digital Payments): start, stop, reset, run the pipeline, find logs, check data quality, recover from failures and fix common problems.

**Draft of Sat 21 Nov 2026.** Parts marked **TODO** wait for a teammate and are listed in section 14. Every command is run from the repository root. Windows commands are for PowerShell; macOS commands are in the same code block when they differ.

Prerequisites and first-time setup are in the [README](../README.md). Environment variables are described in `.env.example`.

## 1. Start

```
make up
```

This builds the pipeline image (first time only: 10 to 25 minutes) and starts the services in the background. Expected result: `docker compose ps` shows `minio` and `mongo` as `healthy`, and `minio-init` as `Exited (0)` (it creates the bucket and stops, which is correct).

Check:
```
docker compose ps
```
Open the MinIO console at http://localhost:9001 and log in with `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` from `.env`. The bucket `cfpb-lake` must exist.

Known and expected until the scheduler is merged: the `pipeline` container exits with code 1 and restarts up to 5 times with `No module named ingestion.scheduler`. This is not an error in your setup.

All ports are bound to `127.0.0.1`: only your own computer can reach them.

## 2. Stop

```
make down
```

Stops and removes the containers. **Data is kept** in the Docker volumes `minio_data` and `mongo_data`, so `make up` brings the platform back with its data.

## 3. Reset (deletes all data)

> **Warning:** this deletes the Docker volumes: every raw file, curated file, quality report and the whole MongoDB database. Use it only for a clean start.

```
make reset
make up
```

After a reset you must run the historical load again (section 4). Reset is also the fix when MinIO credentials were changed after the first start (section 13).

## 4. Run the historical load

The full CFPB CSV is downloaded once, stored unchanged in MinIO, processed by Spark and loaded into MongoDB.

```
make pipeline-full
```

This runs, in order: collection (writes the raw ZIP, the CSV and `manifest.json` under `raw/cfpb/full_load/ingest_date=YYYY-MM-DD/`), the Spark job, the MongoDB load, and the high-water mark update. It prints a `run_id` such as `20261121T100000Z_full`. Keep it: the run log, quality report and quarantine are named after it.

To run the steps one at a time (useful when one of them failed):
```
make ingest-full
make process SOURCE=full_load RUN_ID=<run_id>
make load RUN_ID=<run_id>
```

For a quick test on the small development sample instead of the full file:
```
make sample
```
This writes `data/sample/complaints_sample.csv` (about 5,000 in-domain rows). The full dataset is never committed to Git.

## 5. Run an incremental load manually

The incremental load asks the CFPB API for complaints in a bounded date window that starts at the saved high-water mark minus `OVERLAP_DAYS` (21 days), so late changes are picked up. It uses `date_received` as the date field.

```
make pipeline-incremental
```

To run the steps one at a time:
```
make ingest-incremental
make process SOURCE=api RUN_ID=<run_id>
make load RUN_ID=<run_id>
```

Running the same window twice does **not** create duplicates: records are deduplicated by Complaint ID in Spark and loaded to MongoDB with upserts. This is the controlled rerun shown in the demo. Check it by comparing the curated count and `db.complaints.countDocuments({})` before and after the second run.

## 6. How the 24-hour schedule works

- **Primary: Apache NiFi.** The NiFi flow (`ingestion/nifi/cfpb_flow.json`) calls the CFPB API every 24 hours (`SCHEDULE_HOURS=24`), writes each response to MinIO before processing it, and keeps the provenance of every run. See section 9. **TODO:** the `nifi` service is being added by Joseph and the flow by Marwa.
- **Fallback: Python scheduler.** `python -m ingestion.scheduler` (the default command of the `pipeline` container) calls the same incremental pipeline every `SCHEDULE_HOURS`. **TODO:** confirm with Marwa how the two are selected and what happens if the computer was off at the scheduled time.
- **Manual trigger** (`make pipeline-incremental`) uses the same collector and processing chain as the schedule, as the brief allows for the demo.
- **Safety rules of every incremental run:** bounded date window, pagination, timeouts (`API_TIMEOUT_SECONDS`), bounded retries (`API_MAX_RETRIES`, never retried forever), and the high-water mark (`state/high_water_mark.json`) moves forward only after the run finished successfully. A successful empty response is recorded as such and is different from a failed request.

## 7. Where to see logs

| What | Where |
|---|---|
| Live container logs | `make logs` (stop with Ctrl+C); one service: `docker compose logs nifi` |
| Ingestion run log (run id, times, endpoint, window, pagination state, HTTP status, retries, outcome, raw path, record count, checksum, next high-water mark) | MinIO bucket `cfpb-lake`, path `logs/ingestion/run_id=<run_id>.json` |
| Quality report of a run | `quality/run_id=<run_id>/quality_report.json` |
| Rejected records and the reason for each | `quarantine/run_id=<run_id>/` (Parquet) |
| Run history and loaded counts | MongoDB collection `pipeline_runs` (section 10) |
| Redis cache | section 11 |
| NiFi history of every collection run | NiFi data provenance (section 9) |

Browse MinIO at http://localhost:9001.

## 8. How to check data quality

Each Spark run writes `quality/run_id=<run_id>/quality_report.json`. It covers six dimensions with thresholds fixed in advance:

| Dimension | Rule | On breach |
|---|---|---|
| Uniqueness | `complaint_id` not null and unique | **FAIL** |
| Completeness | required fields at least 99.5% filled | **FAIL** (optional fields: WARN) |
| Validity | invalid values at most 0.5% | WARN above 0.5%, **FAIL** above 2% |
| Consistency | product, sub-product and issue combinations exist in the mapping | WARN, listed |
| Freshness | latest `date_received` at most 3 days old | WARN |
| Reconciliation | raw = curated + quarantined + out of domain + duplicates removed; curated = MongoDB count | **FAIL** |

A FAIL makes the Spark job exit with code 1 and publish nothing: the curated data stays as it was, and the report and quarantine are still written as evidence. A WARN does not stop the run. `overall_status` in the report is `PASS`, `WARN` or `FAIL`.

The code still uses the names `timeliness` and `integrity` for freshness and reconciliation until Joseph's V2 change is merged.

## 9. Apache NiFi

**TODO** until Joseph adds the `nifi` service and Marwa adds the flow. The steps below are the plan and must be verified on the real setup.

- **Open the UI:** the address and port are in the README after Joseph's change. NiFi needs 1 to 2 minutes to start: check `docker compose logs nifi` for the started message. The browser warns about a self-signed certificate on localhost: continue to the page.
- **Log in** with `NIFI_USERNAME` and `NIFI_PASSWORD` from `.env` (password 12 characters or more).
- **Start or stop the flow:** select the process group `cfpb_flow` and use Start or Stop in the operate panel.
- **Trigger a manual run:** right-click the first processor and choose **Run once**.
- **Find a run in provenance:** menu (top right) > **Data Provenance**, search by time or by the run id attribute, open an event to see the content and attributes.
- **If NiFi is not available:** use the Python fallback (`make pipeline-incremental`).

## 10. MongoDB: inspect and rebuild indexes

Open a shell in the database container:
```
docker compose exec mongo mongosh
```
Then, in `mongosh`:
```
use cfpb_money_transfers
show collections
db.complaints.countDocuments({})
db.complaints.getIndexes()
db.pipeline_runs.find().sort({ _id: -1 }).limit(3)
db.quality_reports.find().sort({ _id: -1 }).limit(1)
```
Collections: `complaints`, `agg_monthly`, `agg_company_year`, `pipeline_runs`, `quality_reports`, `ml_emerging_issues`, `ml_state_clusters`. MongoDB Compass can connect to `mongodb://localhost:27017`.

**Rebuild the indexes** (safe to rerun; existing indexes are not duplicated):
```
docker compose run --rm pipeline python -m database.indexes
```

**TODO:** Christopher to confirm these steps and add how to reload MongoDB from the curated data (due Mon 23 Nov).

## 11. Redis cache

**TODO** until Joseph adds the `redis` service and Perla connects the dashboard. Redis caches the dashboard queries (key = query name + filters, time-to-live `CACHE_TTL_SECONDS`, 600 seconds). Cached results can be up to 10 minutes old. To clear the cache:
```
docker compose exec redis redis-cli FLUSHDB
```
After a new load, clear the cache so the dashboard shows the new data immediately.

## 12. Recovery steps

Our collector, unlike a tool such as Sqoop that must clean and restart a failed import, saves its progress: pagination state is stored, retries are bounded, every raw response is stored before it is processed, and reruns are idempotent. So recovery means running the failed step again.

| Situation | What to do |
|---|---|
| A run failed in collection | Read the run log (section 7), fix the cause (for example network), then run `make pipeline-incremental` again. The high-water mark did not move, so the same window is collected again. **TODO:** resume from saved pagination state, confirm with Marwa. |
| Spark stopped with exit code 1 (quality gate) | Open `quality/run_id=<run_id>/quality_report.json` and `quarantine/run_id=<run_id>/` to see which rule failed and which records. Nothing was published. Fix the cause, then run `make process SOURCE=<full_load or api> RUN_ID=<run_id>` again. |
| The load into MongoDB failed | Run `make load RUN_ID=<run_id>` again. Upserts make the rerun safe. |
| The high-water mark must be reset | **TODO:** Marwa to document the exact command for `state/high_water_mark.json` (the `ingestion.update_hwm` module). |
| Indexes are missing or slow | Rebuild them (section 10). |
| MongoDB data was lost | Run `make load RUN_ID=<run_id>` from the curated Parquet in MinIO; if MinIO is also empty, run the historical load again (section 4). |
| Everything is broken | `make reset`, then `make up` and the historical load. |

MongoDB runs as a single node: a failure of that container means recovery by rerunning the idempotent pipeline. A replica set with automatic primary election would give availability; it is listed as the next improvement and is not built.

## 13. Troubleshooting

| Problem | Fix |
|---|---|
| `docker` cannot connect to the engine, or `npipe ... docker_engine` is not found | Start Docker Desktop (or Rancher Desktop) and wait until it is running. With Docker Desktop also run `docker context use desktop-linux`. |
| `make` is not recognised | Open a **new** terminal after installing make (`winget install ezwinports.make` on Windows). |
| `env file ... .env not found` | Copy `.env.example` to `.env` (Windows: `Copy-Item .env.example .env`; macOS: `cp .env.example .env`) and set the MinIO values. |
| Port already in use (`port is already allocated`: 9000, 9001, 27017, 8501) | Another program uses the port, for example a local MongoDB service. Stop it, then `make up` again. |
| Docker runs out of memory (containers killed, Spark `OutOfMemoryError`, `Killed`) | In Docker Desktop > Settings > Resources, give Docker at least 8 GB (NiFi needs about 2 GB on top of Spark). Lower `SPARK_DRIVER_MEMORY` in `.env` (for example `2g`) for the sample. |
| MinIO keeps restarting, or MinIO password too short | `MINIO_ROOT_PASSWORD` must be 8 or more characters, letters and digits only (`$`, `#`, quotes and `=` break the file). |
| `InvalidAccessKeyId` or `SignatureDoesNotMatch` after changing the MinIO password | MinIO keeps the first credentials in its volume. Put the old values back in `.env`, or run `make reset` (deletes data) and `make up`. |
| Slow or interrupted image build (`Read timed out`, hash mismatch) | Run `make up` again: downloads resume automatically. Use a stable connection; the first build takes 10 to 25 minutes. |
| `pull access denied for cfpb-pipeline` during `make up` | Only a warning: Compose builds this image locally right after. |
| NiFi page does not open right after `make up` | NiFi needs 1 to 2 minutes to start. Check `docker compose logs nifi`. |
| Pushing to GitHub gives `403 ... denied to <another account>` | Run `git remote set-url origin https://<your-username>@github.com/Joseph-Nasr-USJ/cfpb-money-transfers-platform.git` and push again. |

## 14. Open items for this runbook

| Item | From | Due |
|---|---|---|
| Scheduling details, scheduler and NiFi selection, resume from pagination state, high-water mark reset | Marwa | Mon 23 Nov |
| MongoDB inspection, index rebuild and reload steps (confirm section 10) | Christopher | Mon 23 Nov |
| NiFi address, ports and credentials; Redis port; Spark memory advice | Joseph | with the `nifi` and `redis` Pull Request |
| Redis cache wiring in the dashboard | Perla | with the dashboard |
| Verify every command on a clean machine | Charbel | Tue 24 Nov |
