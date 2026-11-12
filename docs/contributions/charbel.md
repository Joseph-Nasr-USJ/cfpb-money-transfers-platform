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
