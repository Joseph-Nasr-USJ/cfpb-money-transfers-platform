<!--
Section 8. References and appendices (not counted in the 4,000 to 5,000 words)
Owner: Loutchiana (from every owner) | First draft: Sat 21 Nov; complete on Fri 27 Nov.
Each appendix points to a file of the repository that its owner maintains. Excerpts are pasted in the final export only.
-->

## 8. References and appendices

### References

**Official CFPB sources** (accessed 21 November 2026)

1. Consumer Financial Protection Bureau. *Consumer Complaint Database.* https://www.consumerfinance.gov/data-research/consumer-complaints/ (page last modified 29 October 2026).
2. Consumer Financial Protection Bureau. *Consumer Complaint Database API.* https://cfpb.github.io/api/ccdb/api.html
3. Consumer Financial Protection Bureau. *Consumer Complaint Database field reference.* https://cfpb.github.io/api/ccdb/fields.html
4. Consumer Financial Protection Bureau. *Consumer Complaint Database release notes* (releases 20 to 24, 2023 to 2026). https://cfpb.github.io/api/ccdb/release-notes.html
5. Consumer Financial Protection Bureau. *Full complaint data, CSV ZIP.* https://files.consumerfinance.gov/ccdb/complaints.csv.zip

**Other sources**

6. United States Postal Service. *Publication 28, Postal Addressing Standards*, Appendix B, Two-Letter State and Possession Abbreviations. https://pe.usps.com/text/pub28/28apb.htm

**Course and brief**

7. Haque, R. *Session 1: Enterprise Data Science, methodologies, principles and practices.* 020IABDM2, ESIB, USJ. Value of big data; descriptive, diagnostic, predictive and prescriptive analytics; exploratory and inferential analytics.
8. Haque, R. *Session 2: Building an end-to-end big data solution.* Conceptual Big Data Framework; data collection tools (Apache NiFi, Kafka, Flume, Sqoop).
9. Haque, R. *Session 3.1: Data storage tools and storage formats.* Storage systems; compression; ORC and Parquet.
10. Haque, R. *Session 4.1: NoSQL and MongoDB, Redis, Apache Spark.* Document model, CAP, indexes and aggregation, replication and sharding; Redis as a cache; Spark and its libraries.
11. Haque, R. *Class project: Public Banking Complaints Data Platform*, version 2. 020IABDM2 Big Data Frameworks.

### Appendices

| ID | Appendix | Where | Owner |
|---|---|---|---|
| A | Architecture document and diagram | `docs/architecture.md`, `docs/images/architecture.png` | Loutchiana |
| B | Data dictionary, product mapping and state list | `docs/data_dictionary.md`, `config/product_mapping.csv`, `config/state_codes.csv` | Loutchiana, Joseph |
| C | Raw manifest of the historical load and a sample run log | `docs/images/minio_raw_full_load.png` (manifest in MinIO, run of 24 Nov); `docs/evidence/run_20261124T135857Z_full/manifest.json` and `run_log.json` | Marwa |
| D | Sample quality report and the reconciliation of one run | `docs/images/minio_quality_report.png`; `docs/evidence/run_20261124T135857Z_full/quality_report.json` (run of 24 Nov) | Joseph |
| E | Sample curated output | `docs/images/minio_curated_parquet.png`; `docs/evidence/curated_sample_2025-10.csv` (20 curated complaints received in October 2025, every curated field including the lineage columns) | Joseph |
| F | MongoDB model, indexes and the aggregation queries A1 to A8 | `docs/mongodb_model.md`, `database/queries.py`, `docs/images/mongodb_collections_indexes.png` | Christopher |
| G | Index benchmark before and after | `docs/evidence/benchmark.md` [TO COMPLETE] | Christopher |
| H | Metric definitions and findings | `docs/metrics.md`, `docs/findings.md` | Perla |
| I | Test plan, test results and defect log | `docs/test_plan.md`, `docs/evidence/test_results_*.txt`, `docs/defect_log.md` | Charbel |
| J | Rerun (idempotency) evidence | `docs/evidence/idempotency.md` | Joseph |
| K | Demonstration script and runbook | `docs/demo_script.md`, `docs/runbook.md` | Charbel |
| L | Checkpoint notes and contribution logs | `docs/checkpoints/`, `docs/contributions/` | Loutchiana, everyone |
