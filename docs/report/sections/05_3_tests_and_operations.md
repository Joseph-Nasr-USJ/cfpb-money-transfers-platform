<!--
Section 5.3 Tests, deployment and recovery
Owner: Charbel Mazraani
Target: 350 words | Draft due: Wed 25 Nov
To cover: Test levels and results (docs/test_plan.md), defects found and corrected (docs/defect_log.md), Docker setup, start/stop/reset, runbook, recovery after a failed run.
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 5.3 Tests, deployment and recovery

**Test levels and results.** All automated tests run with one command, `make test`, which starts pytest inside the pipeline container so that every machine uses the same Python, Java and Spark versions. The tests cover the collector (pagination, timeouts, bounded retries, date window and high-water mark), the Spark transformations, the six data-quality dimensions, the database loader and queries, the dashboard data functions and the machine-learning calculations. On the merged code of 24 November, 159 tests passed and one module was skipped, because it needs Streamlit, which is not installed in the pipeline image. The dated output is kept in `docs/evidence/`. An automated end-to-end test and the manual dashboard checklist are not yet recorded. A repeated run on real data was recorded separately: the same API window loaded twice left 468 complaints, with no duplicate Complaint ID.

**Known bad records and defects.** Test fixtures contain an invalid date, an invalid state, a negative interval and a missing Complaint ID. The quality gate reports FAIL on them, and a Spark job test confirms that a failed gate publishes no curated data. The defect log lists five entries. Four concern the Docker setup: the official MinIO image could no longer be pulled, MinIO could not write to its volume, and two image builds failed on interrupted downloads. All four were corrected with pinned images, longer timeouts and resumable downloads. The fifth records the intended detection of the bad records.

**Deployment.** Docker Compose defines MinIO, MongoDB, the pipeline container, Apache NiFi, Redis and the Streamlit dashboard, with ports bound to the local machine and secrets kept in an untracked `.env` file. `make up` starts the stack, `make down` stops it and keeps the data, and `make reset` also deletes the data volumes. The NiFi service runs, but its flow is not yet exported to the repository, so collection currently uses the Python collector.

**Recovery.** The runbook describes recovery. A failed collection can resume from its last saved page. The processing chain stops at the first failed step, and the high-water mark moves only after both Spark and the MongoDB load succeed. Because curated records are merged by Complaint ID and loaded with upserts, running a step again does not create duplicates. MongoDB runs as a single node, so recovery relies on rerunning the pipeline rather than on replication.
