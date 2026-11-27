# NiFi collection flow (`cfpb_flow.json`)

**Owner:** Marwa Zeineddine. Built and tested on Apache NiFi 2.12.0 on 26 and 27 Nov 2026.

`cfpb_flow.json` is the exported process group **CFPB API collection**. It is the primary collector for new and changed complaints. The Python collector (`ingestion/incremental.py`) is the tested fallback, selected with `COLLECTOR=python`. Both write the same raw paths, run_id format and run log, so the Spark job, the loader and the high-water mark do not depend on the collector.

## What the flow does

```
GenerateFlowFile (CRON 0 0 2 * * ?, daily 02:00 UTC)
 -> Read high-water mark (FetchS3Object state/high_water_mark.json)
 -> Read high-water mark date (EvaluateJsonPath hwm.date)
 -> Stamp run time -> Prepare run (run_id, ingest_date, window = hwm - OVERLAP_DAYS .. today)
 -> Call CFPB API page (InvokeHTTP, size=API_PAGE_SIZE, sort=created_date_desc, search_after)
 -> Save raw page (PutS3Object raw/cfpb/api/ingest_date=<d>/run_id=<id>/response_<n>.json)
 -> Read page facts -> Count page -> More pages?
       more      -> back to Call CFPB API page (next page with search_after)
       unmatched -> Build run log -> Save run log (logs/ingestion/run_id=<id>.json)
Errors:
 Call CFPB API page: Retry (5xx), Failure (timeout, connection) -> Retry API call (RetryFlowFile, API_MAX_RETRIES, 4 s penalty)
                     No Retry (4xx) -> Rate limited? (429 -> Retry API call; other 4xx -> failure)
 Retries exceeded, a response that is not JSON, or pagination not advancing
   -> Describe failure -> Build failed run log -> Save run log (outcome "failed", high_water_mark_next null)
```

Every setting comes from `.env` through NiFi expression language (`${CFPB_API_URL}`, `${MINIO_BUCKET}`, `${MINIO_ENDPOINT}`, `${OVERLAP_DAYS}`, `${API_PAGE_SIZE}`, `${API_MAX_RETRIES}`); nothing is hard-coded. The `pipeline` container (`ingestion.scheduler`, `COLLECTOR=nifi`) checks every `PENDING_CHECK_MINUTES` for new successful run logs and runs Spark, the MongoDB load and the high-water mark update.

## Design choices tested against the live API (see `docs/api_notes.md`)

- **User-Agent `python-requests/2.34.2`** (property Request User-Agent). With NiFi's default agent the CFPB firewall (Akamai) answers HTTP 403; with this agent, HTTP 200. Tested 24 and 26 Nov 2026.
- **`search_after` paging, never `frm`.** `frm=100` returns page 1 again without any error. The flow stops a run as failed if `search_after` does not change between two pages.
- **`date_received_max` = window end + 1 day**, because the API returns the end day although its specification says the bound is exclusive.
- **Timeouts:** connect 10 s, read 30 s (`API_TIMEOUT_SECONDS`).

## Import the flow on another laptop

1. `make up`, then open https://localhost:8443/nifi and log in with `NIFI_USERNAME` / `NIFI_PASSWORD` from `.env`.
2. Drag the **Process Group** icon onto the canvas, click the **upload** (import) icon in the dialog and choose `ingestion/nifi/cfpb_flow.json` from your clone. The same file is also mounted read-only in the container at `/opt/nifi/nifi-current/project-flows/`.
3. Inside the group: right-click the canvas -> **Controller Services** -> **MinIO credentials** -> Edit. NiFi never exports sensitive values, and both keys are sensitive, so type them again: **Access Key ID** = `${MINIO_ROOT_USER}`, **Secret Access Key** = `${MINIO_ROOT_PASSWORD}`. Apply, then **Enable** (the service is exported disabled).
4. Right-click the canvas -> **Start**. Nothing runs until 02:00 UTC.

A high-water mark must exist (`state/high_water_mark.json`); it is created after the first historical load is processed (`make pipeline-full`).

## Run once for the demo

Right-click **GenerateFlowFile** -> **Run Once**. About 4 seconds later the raw pages and the run log are in MinIO; within `PENDING_CHECK_MINUTES` (or at once with `docker compose run --rm pipeline python -m ingestion.pipeline --mode pending`) Spark and the load follow. Data provenance (right-click a processor -> **View data provenance**) shows every page that was fetched and saved.

## Results on 27 Nov 2026

| Run | Outcome | Evidence |
|---|---|---|
| `20261127T152439Z_api` | success: window 2026-11-02 to 2026-11-27, 20 pages, 1,931 complaints = the API's announced total; processed by Spark (quality gate passed) and loaded; high-water mark 2026-11-23 -> 2026-11-25 | run log in MinIO, pipeline output |
| `20261127T204146Z_api` | failed (test with a wrong URL): the server answered HTTP 200 with an HTML page; the run log says "HTTP 200 but the response is not valid JSON", the high-water mark did not move | run log in MinIO |
