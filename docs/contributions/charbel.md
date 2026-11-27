# Contribution log: Charbel Mazraani

Role: Delivery lead (README, runbook, testing evidence, demo, presentation). Updated every Sunday.

## Week of Tue 10 to Sun 15 Nov 2026

**Date:** Thu 12 Nov 2026

**What I did**
- Set up my machine following the setup steps: Docker Desktop, make (installed with winget), `.env` from `.env.example`, `make up`, `make test`.
- Replaced the placeholder README with the full setup guide: prerequisites, setup, every Makefile command, Docker services, project status, folder structure, team and roles, troubleshooting, links to the documentation.
- Wrote the test plan: the six test levels of the brief with owners, file paths and statuses, the inventory of the 26 existing tests, the planned tests per owner, the deliberate failing test and the manual checks.
- Started the defect log with D-001 to D-004 (Docker and MinIO defects found and fixed by Joseph).
- Saved the first test evidence file (`docs/evidence/test_results_2026-11-12.txt`).

**Pull Requests**
- README skeleton, test plan, defect log: to be opened from branch `charbel/readme-skeleton`.

**Problems**
- `make` was not recognised after installing it with winget until a new terminal was opened (inside VS Code, until VS Code itself was restarted). Added to the README troubleshooting table.
- The first `make up` took 64 minutes on my connection (about 22 minutes pulling the base images, 25 minutes for the PySpark download, 14 minutes for the S3A jars), much longer than the 25 minutes we expected. No error: the README now gives the real range and says to leave the build running.
- `make up` then gave the expected result: `minio` and `mongo` healthy, `minio-init` exited with code 0 (bucket `cfpb-lake` created), `pipeline` exited with code 1 until the scheduler is merged. `make test`: 26 passed.

**Next step**
- Clean-machine check #1 on Sun 15 Nov: fresh clone, follow only the README, report every gap as a GitHub Issue.
- Runbook draft by Wed 18 Nov (details from Marwa, Christopher and Joseph).

## Week of Mon 16 to Sun 22 Nov 2026

**Date:** Sat 21 Nov 2026

**What I did**
- Pushed my branch `charbel/readme-skeleton` to GitHub for the first time after merging the latest `main` into it (the Pull Request is not opened yet).
- Ran `make test`: 42 passed in 76 seconds. Saved the result as `docs/evidence/test_results_2026-11-21.txt`; it contains the known bad record test (`test_csv_fixture_fails_the_quality_gate`) and the idempotent rerun test.
- Added defect D-005 (known bad fixture records caught by the quality gate) to the defect log.
- Updated the test plan: real data quality and Spark job tests, the machine learning tests (planned, Perla), the deliberate-failure section and the run history.
- Wrote the runbook draft (`docs/runbook.md`) with start, stop, reset, loads, schedule, logs, data quality, recovery and troubleshooting. NiFi, Redis and the collector recovery details are marked TODO until the other components are merged.
- Updated the README for the new plan (NiFi, Redis, Spark MLlib, memory, test count, status table).
- Wrote the first draft of `docs/demo_script.md` with the 8 steps, presenters, timing and backups.
- Read the task files of my teammates.

**Pull Requests**
- README, test plan, defect log, runbook, demo script: to be opened from `charbel/readme-skeleton`.

**Problems**
- Docker Desktop was not running at first (`npipe ... dockerDesktopLinuxEngine` not found): started it and ran `docker context use desktop-linux`.
- The `redis` and `nifi` services are not on `main` yet, so I could not check them: `service "redis" is not running`. Waiting for Joseph's Pull Request.
- My teammates' task files describe the older plan (Python collector, no Redis, different demo step numbers). The demo step numbers must be agreed with everyone.
- Marwa's task file and the Session 4.1 slides are missing from my folder.
- The clean-machine check #1 planned for Sun 15 Nov was not done: I will do it as part of check #2.

**Next step**
- Ask Joseph for the date of the `nifi` and `redis` Pull Request; update the README and runbook when it is merged.
- Collect the scheduling and recovery details from Marwa and the MongoDB steps from Christopher (Mon 23 Nov).
- Write the end-to-end test with Joseph and the dashboard checklist with Perla.
- Clean-machine check #2 and the final demo script on Tue 24 Nov; report part 5.3 to Loutchiana on Wed 25 Nov.

## Week of Mon 23 to Sun 29 Nov 2026

**Date:** Fri 27 Nov 2026

**What I did**
- Reviewed Joseph's real-data rerun evidence (`docs/evidence/idempotency.md`) with Claude and linked it from the test plan.
- Pulled and merged the latest `main`.
- Prepared report section 5.3 (tests, deployment and recovery), with Claude's help.
- Updated the runbook with the scheduler and collector choice, resume, high-water mark reset, MongoDB reload, Redis and the full-load time, with Claude's help.
- Updated the demo script commands and the step 8 supporting facts.
- Rewrote the test plan inventory with the real test names.

**Pull Requests**
- [#17](https://github.com/Joseph-Nasr-USJ/cfpb-money-transfers-platform/pull/17): README, runbook, test plan, defect log and demo script (merged).
- Second Pull Request with the updates above: to be opened.

**Problems**
- The NiFi flow is not exported yet, so section 9 of the runbook is not verified.
- The end-to-end test, the clean-machine check and the dashboard checklist are not done yet.

**Next step**
- Clean-machine check, dashboard checklist with Perla, rehearsals on Sat 28 and Sun 29 Nov.
