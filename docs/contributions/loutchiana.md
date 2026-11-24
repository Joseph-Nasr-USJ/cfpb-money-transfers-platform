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

**What I did**
- Merged the latest `main` into my branch `loutchiana/delivery-docs`. It now includes Marwa's collectors, scheduler and pipeline chain (PR #33), Perla's dashboard and analytics (PR #28) and Joseph's changes to the curated path (PR #31) and to the quality dimension names (PR #32).
- Updated the architecture document (section 12), the data dictionary (section 6.2), the runbook and the test plan. The curated path is now `option=5` and the quality report uses `freshness` and `reconciliation`; it also has a `sub_issue_applicability` section (filled, missing, not applicable) and `ingested_at`.
- Updated the README status table and the "Expected today" notes, which still said the collectors, the services and the dashboard were not merged.
- Corrected the two lines above that said the paths and names were still different (21 Nov and 23 Nov). They were true on those days, so I left the earlier entries as they were.
- I keep all my work on this one branch only. I used an AI assistant to help with the wording of these updates and I checked them against the files on `main`.

**Problems**
- The `nifi` service is on `main` but `ingestion/nifi/` is still empty, so the flow is not exported yet.
- I have not run `make test` or the stack on the merged `main`. The test counts (42 on 21 Nov, 57 on 22 Nov) are old; Joseph wrote 127 passed and 1 skipped in PR #32, but I will only quote a number from my own run.
- The collector, database and dashboard rows of the test plan are written but not run by me, so I did not mark them as passing.

**Next step**
- Run `make test` on the merged code, then update the counts in the README, the test plan, the architecture document and the demo script.
- Add the new curated path to my report text once the team confirms that no run still uses `domain=`.
