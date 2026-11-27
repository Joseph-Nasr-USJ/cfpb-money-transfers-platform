# Contribution log: Joseph Nasr

Role: Data Engineering Lead and Repository Integrator (Docker stack, Spark processing, quality gate, integration of every component, review and merge of the team's Pull Requests).

## Week of Mon 9 to Sun 15 Nov 2026

**What I did**
- Created the repository structure, the branch protection rules and the shared files (`docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore`, `requirements-pipeline.txt`).
- Built the Docker stack: MinIO with the `cfpb-lake` bucket created by `minio-init`, MongoDB 7.0, and the pipeline image (Python 3.11, Java 17, PySpark 3.5.9, S3A jars), every port bound to 127.0.0.1.
- Added the state reference list (`config/state_codes.csv`), the shared packages and the test fixtures with deliberate bad records.

**Pull Requests**
- #1 repository skeleton, #2 Docker pipeline image, #4 pip download timeouts, #5 state codes, #6 shared packages, #7 test fixtures.

**Problems**
- Fixed the Docker and MinIO defects D-001 to D-004 (recorded by Charbel in the defect log), including package downloads that timed out during the image build.
- MinIO stopped publishing official images: pinned a community rebuild of the last release and ran it as root so it can write to its volume.

## Week of Mon 16 to Sun 22 Nov 2026

**What I did**
- Wrote the explicit schemas for the CSV and the API (`processing/schema.py`), the transformations and the product mapping (`processing/transforms.py`, `config/product_mapping.csv`).
- Wrote the quality gate (`processing/quality.py`) with six dimensions and a FAIL that stops the run, and the Spark job (`processing/spark_job.py`): domain filter, de-duplication with a fixed tie-break, quarantine with reasons, partitioned Parquet, aggregates, merge by complaint_id for API runs.
- Aligned the plan with brief V2, added Apache NiFi and Redis to the stack and wrote the updated task files for every member.
- Reviewed and merged the database layer (Christopher), the metrics and the dashboard groundwork (Perla), the README, runbook, test plan and defect log (Charbel) and the delivery documents (Loutchiana).

**Pull Requests**
- #10 schema, #11 transformations and product mapping, #13 quality gate, #15 Spark job, #27 NiFi and Redis services.
- Reviewed: #12, #14, #16, #17, #18, #26, #28, #29.

**Problems**
- The NiFi health check never passed: NiFi listens on the container hostname, not on 127.0.0.1. Fixed the health check to connect to `$(hostname):8443`.

## Week of Mon 23 to Sun 29 Nov 2026

**What I did**
- Ran the first real end-to-end chain (CFPB API to MinIO, Spark, MongoDB) and recorded the rerun proof on two machines (`docs/evidence/idempotency.md`).
- Moved curated data to the agreed path `curated/complaints/option=5/year=YYYY/month=MM/` with one shared path module for the Spark job, the loader and the ML scripts.
- Renamed the quality dimensions to freshness and reconciliation and split `sub_issue` into filled, missing and not applicable.
- Ran the full historical load: 19,397,176 records, 205,271 curated complaints, 112 quarantined, quality PASS, 9.9 minutes end to end; then ran the Spark MLlib analyses (`docs/evidence/full_load.md`, `docs/evidence/profiling.md`).
- Wrote report sections 4.3 and 5.1 and added the curated sample for appendix E.
- Reviewed and merged the processing chain, high-water mark and scheduler (Marwa), the findings and ML logging changes (Perla) and the refreshed documents (Loutchiana).

**Pull Requests**
- #30 idempotency evidence, #31 curated path, #32 quality dimension names, #34 collector settings, #35 full-load evidence and profiling, #39 report sections 4.3 and 5.1, and the curated sample with this log.
- Reviewed: #33, #36, #37, #38, #40.

**Problems**
- The commits made from my office PC used a mistyped email address, so GitHub does not credit them to my account; the address is corrected for all later commits.
- The MongoDB total grows every day once the scheduler runs, so the report uses one fixed snapshot: the full load of 24 Nov (205,271 complaints).

**Next step**
- Clean-clone check, rehearsals on 28 and 29 Nov, final `make test` and the `v1.0` tag, demo steps 4 (Spark processing) and 5 (quality gate and rerun).
