# Contribution log: Loutchiana Marie

Role: Delivery lead (technical report, architecture and data documentation, dashboard content, presentation). Updated every Sunday.

## Week of Mon 16 to Sun 22 Nov 2026

**Date:** Sat 21 Nov 2026

**What I did**
- Read the brief V2, the four course sessions, my task file and the task files of my teammates, then read the repository: the Docker stack, the Spark job, the quality gate, the MongoDB model and queries, the metric definitions, the README, runbook, test plan and demo script, and Marwa's collector branch.
- Cloned the repository outside OneDrive (`C:\Dev\`), set my Git identity for this repository only and worked on branches named `loutchiana/<topic>`.
- Wrote the technical report skeleton with the 14 section files (owners, word targets, deadlines) and a small script that assembles the report and counts the words per section (`docs/report/`).
- Wrote report section 2 (problem and scope), section 3 (data source, limitations, responsible use and ethics) and section 4.1 (architecture); drafted section 1 (executive summary, findings to be added), section 7 (reflection and next steps) and the section 8 reference list with the appendix index.
- Wrote the architecture document with the diagram (PNG and Mermaid), the purpose of the seven layers, the technology chosen and the alternative considered, the trade-offs and the MinIO decision (`docs/architecture.md`).
- Wrote the data dictionary: every curated field, the product mapping and state reference list, the aggregates, the quarantine, quality report, manifest and run log (`docs/data_dictionary.md`).
- Wrote the dashboard texts: overview, measure definitions, limitations and cautions (`dashboard/content/`), consistent with Perla's `docs/metrics.md`.
- Wrote the checkpoint notes of 13 and 20 November from the repository history (`docs/checkpoints/`).
- Wrote the slides outline, the script of my demo step 1 and the likely questions on the architecture (`docs/presentation/slides_outline.md`).
- Checked the CFPB statements used in the report against the official pages and release notes (accessed 21 Nov), and Marwa's API notes (licence CC0, 199,152 records for the current label).
- Used an AI assistant (Claude Code) to draft these documents from the repository and the official sources; I review the content and must be able to explain it.

**Pull Requests**
- One Pull Request from branch `loutchiana/delivery-docs` with all of the above: report skeleton and sections, architecture document, data dictionary, dashboard texts, slides outline and this log. Reviewed and merged by Joseph.

**Problems**
- I started late: the report skeleton and section 2 were due on Sat 14 Nov, and the architecture document, data dictionary and dashboard texts on Wed 18 Nov. Perla and the others could not use my texts before today.
- My teammates' task files describe the earlier plan (no Redis in Perla's, a nine-step demo in Charbel's). I followed my own updated file and the code on `main`.
- On 21 Nov the repository differed from the shared contract in two places: the curated path (`domain=money_transfers_payments` in the Spark job, `option=5` in the contract) and the quality dimension names (`timeliness` and `integrity` instead of freshness and reconciliation). Both were written in `docs/architecture.md` (section 12). Joseph closed them on 24 Nov (PR #31 for the path, PR #32 for the names) and I updated the documents.
- The `nifi` and `redis` services and Marwa's collectors are not on `main` yet, so the architecture document marks them as target.
- `make` is not installed on my machine yet and I have not run `make up` or `make test` myself.
- The checkpoint notes are based on the repository history; I still have to check them with the team.

**Next step**
- Install `make`, run `make up` and `make test`, and check the MinIO console.
- Open the Pull Requests above for review by Charbel and tell the team where their report section files are (deadline Wed 25 Nov).
- Agree the two contract differences with Joseph and Christopher, and the Redis decision with Perla.
- Collect screenshots (MinIO, MongoDB Compass, dashboard, quality report) into `docs/images/` as they exist.
- Update the executive summary, section 7 and the appendices when `docs/findings.md` (Tue 24 Nov) and the evidence files exist.

## Update of Sun 22 Nov 2026

**What I did**
- Put all my work into one Pull Request (#26) from branch `loutchiana/delivery-docs`, for Joseph to review and merge, and closed the seven smaller Pull Requests I had opened first.
- Installed `make` and `pandoc` (for the PDF and DOCX export of the report), started Docker Desktop and created my local `.env` (not committed).
- Started `make up` to build the stack and check the MinIO console.

**Problems**
- Docker Desktop is limited to 2 GB of memory and 2 processors by my WSL configuration (laptop: 15.6 GB), while the project needs about 8 GB for Spark. It must be raised before `make test` and the Spark job can run on my machine.
- Seven small Pull Requests sent many notifications to Joseph and Charbel; one Pull Request is clearer. Lesson: agree the number of Pull Requests before opening them.
- No new work from the teammates is on `main` since Sat 21 Nov: Perla's dashboard and analysis code, Marwa's collectors and the NiFi and Redis services are still to be pushed.

**Next step**
- Raise the Docker memory, run `make test`, and take the MinIO and MongoDB screenshots.
- Message the team about the section files and the Wed 25 Nov deadline, and ask Joseph to merge #26.
- Remind the owners on Mon 23 Nov.

## Update of Mon 23 Nov 2026

**What I did**
- Raised the Docker memory from 2 GB to 8 GB (4 processors), then ran `make test` on my machine: 57 passed in 4 minutes.
- Ran the whole chain once on the real CFPB file of 22 Nov 2026, from a scratch copy of the repository that adds Marwa's collectors (they are not on `main` yet): download (19,371,701 records, 353.6 MiB zipped, 5.5 GiB CSV), Spark job (quality gate PASS; 19,166,525 out of domain, 112 quarantined, 205,064 curated, 0 duplicates; the counts reconcile exactly) and MongoDB load (205,064 complaints, 73,545 monthly and 8,074 company-year summaries), then the indexes.
- Took the MinIO console screenshots (raw files and manifest, curated Parquet, quality report, bucket) and a `mongosh` output with the collections, the five indexes and an index scan; saved in `docs/images/`.
- Explained the two record counts in the architecture document, the report (section 2), the data dictionary and the slides outline: 205,064 curated = 199,354 under the current label (199,152 on 20 Nov in the API, plus 202 published since) + 5,710 under legacy labels.
- Updated the architecture document after Joseph's PR #27 (NiFi and Redis services on `main`) and corrected the first contract difference: the Spark job and the loader both use `domain=money_transfers_payments`; only the brief's example says `option=5`.
- Built the first draft of the 15 slides with a script (`docs/presentation/build_slides.py`) and put my run's numbers on slides 6, 8 and 10 (marked as my run, for the owners to confirm or replace).
- Used an AI assistant (Claude Code) for these steps; I check the numbers against the quality report and must be able to explain them.

**Problems**
- The full file has 19.4 million records; the Spark job needs the 8 GB Docker setting. Teammates with the default 2 GB will not be able to run it.
- The two record counts (199,152 and 205,064) were not explained anywhere; now they are.
- The quality check names `timeliness` and `integrity` in `processing/quality.py` differed from brief V2 (`freshness`, `reconciliation`); resolved by Joseph's PR #32, merged 24 Nov.
- Perla's dashboard is on her branch (work in progress); her pages do not yet show my texts from `dashboard/content/`.

**Next step**
- Message the team about the section files (due Wed 25 Nov) and settle the two differences with Joseph and Christopher.
- Fill the findings, the executive summary and the remaining slide placeholders when Perla's findings arrive (Tue 24 Nov).
- Write my reflection (due Fri 27 Nov), rehearse step 1 and export the final report with `export_report.py --final`.

## Update of Tue 24 Nov 2026

**Work done**
- The latest `main` was merged into `loutchiana/delivery-docs`. It brings in the collectors, scheduler and pipeline chain (Marwa, PR #33), the dashboard and analytics (Perla, PR #28), the `option=5` curated path (Joseph, PR #31), the renamed quality dimensions (Joseph, PR #32) and the collector settings in `.env.example` (Joseph, PR #34).
- `make test` on the merged code: 159 passed, 1 skipped in 4 min 25 s (Docker 8 GB, 4 processors). The skipped module is `tests/dashboard/test_db.py`, which needs streamlit; the pipeline image does not include it. The result is saved in `docs/evidence/test_results_2026-11-24.txt`.
- The architecture document (section 12), the data dictionary (section 6.2), the runbook, the test plan and the README were updated to match the code. The curated path is `option=5`, the quality report uses `freshness` and `reconciliation`, and it contains a `sub_issue_applicability` section (filled, missing, not applicable) and `ingested_at`. The test counts and the status of the collector, database and dashboard test levels come from the run above.
- Ran the whole chain on the official CFPB file of 24 Nov (run `20261124T135857Z_full`) on the `option=5` path: 19,397,176 records, 205,271 curated, 112 quarantined, 0 duplicates, quality PASS with exact reconciliation, 205,271 complaints in MongoDB (73,597 monthly and 8,078 company-year summaries). The load first stopped at the integrity check: curated under `option=5` was built from scratch, while MongoDB still held the load of 22 Nov, which included complaint 33357934, no longer in the CFPB file; that document was deleted locally and the run resumed with `ingestion.pipeline --mode process`. The manifest, run log and quality report of this run are in `docs/evidence/run_20261124T135857Z_full/`, and the five screenshots in `docs/images/` (MinIO console and `mongosh` output) were retaken for it.
- The architecture document (full-run section), the data dictionary, the report sections 1, 2, 7 and 8, the slides outline and `build_slides.py` use the figures of this run; the report and the slides were rebuilt.
- The "Unresolved issues" paragraph of the report (section 7) was written from the repository state, and appendix J now points to the idempotency evidence.
- The entries of 21 and 23 Nov that mention the path and name differences were left unchanged, because they were accurate on those dates.
- All work stays on this single branch. An AI assistant (Claude Code) was used for the wording of these updates; the content was checked against the files on `main`.

**Problems**
- `ingestion/nifi/` is still empty, so the NiFi flow is not exported and the Python collector remains the collection path.
- Neither the Spark merge nor the MongoDB loader removes a complaint that the CFPB drops from its file; to raise with Joseph and Christopher.
- `docs/findings.md` and the report sections 4.2, 4.5 and 6 (Marwa, Perla) are not on `main` yet, so the executive summary and the slide placeholders that depend on them stay open.

**Next step**
- Fill the executive summary, the findings slide and the remaining placeholders when `docs/findings.md` is available, then rebuild the report and the slides.
