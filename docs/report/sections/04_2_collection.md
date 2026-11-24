<!--
Section 4.2 Collection, scheduling and raw storage
Owner: Marwa Zeineddine
Target: 450 words | Draft due: Wed 25 Nov
To cover: NiFi flow and Python fallback, bounded window and overlap (date_received), high-water mark, bounded retries, run log fields, raw layout in MinIO, NiFi provenance, how older revised records can be reconciled (re-run the full CSV load).
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 4.2 Collection, scheduling and raw storage

**Two collection paths, one contract.** The historical load downloads the official CFPB CSV ZIP once with a script (`make ingest-full`). On 24 November 2026 it fetched 371,218,594 bytes, computed their SHA-256 while streaming, extracted 19,397,176 records and wrote a manifest with the source URL, download times, size, checksum and record count. New and changed complaints come from the CFPB API every 24 hours through Apache NiFi; a Python collector (`ingestion/incremental.py`, 17 tests) is the tested fallback, selected with `COLLECTOR=python`. Both write the same raw paths, run_id format and run log, so Spark and the loader do not depend on the collector. [TO CONFIRM when the NiFi flow is exported: processor chain in one sentence.]

**Window, overlap and high-water mark.** Each incremental window runs from the high-water mark minus 21 days to the current day, on `date_received`. The overlap is needed because the CFPB publishes a complaint only after the company responds or after 15 days, and responses change later: our first API run found 190 complaints for 10 to 17 November, about 24 per day against about 125 per day in October. Repeated records are removed downstream by `complaint_id`. The high-water mark (`state/high_water_mark.json`) moves only forward and only after Spark and the MongoDB load succeed; every change is kept in `state/hwm_history/`, and a manual reset requires a reason.

**Tested API behaviour.** Probing the live API on 20 November showed three differences from its specification (`docs/api_notes.md`). The CDN answered HTTP 403 to a custom User-Agent and to a browser imitation, but 200 to the default `python-requests` agent. Offset paging (`frm=100`) returned the same 100 complaints as page 1 without any error, while `search_after` returned the next page. The end date was included although documented as exclusive. The collector therefore pages with `search_after`, stops if a page brings no new complaint, and requests one extra day.

**Failures and reruns.** Timeouts, connection errors, HTTP 429 and 5xx are retried after 2, 4 and 8 seconds (or the server's `Retry-After`), at most three times; other 4xx answers fail at once. A real failure shaped this rule: on 20 November the ZIP transfer broke after 104 MB and was not retried; downloads now resume with an HTTP Range request while each attempt makes progress. A same-day rerun with an identical file uploads nothing (`skipped_identical`), and one that finds a partial upload verifies the stored copy by SHA-256 before completing it.

**Run logs and raw layout.** Every run, successful or not, writes `logs/ingestion/run_id=<id>.json`: run type, window, parameters, pagination state, HTTP status, retries, errors, outcome, raw paths, record count, checksums and the CFPB's own `last_indexed` time. Raw files sit in MinIO under `raw/cfpb/full_load/ingest_date=…/` and `raw/cfpb/api/ingest_date=…/run_id=…/`, stored exactly as received; the helper module refuses to overwrite any object under `raw/`. [TO CONFIRM: how NiFi provenance complements these logs.]

**Reconciling older revisions.** The 21-day overlap only refreshes recent complaints. Older records that the CFPB revises are reconciled by running the full CSV load again, which Spark merges with the existing curated data by `complaint_id`.
