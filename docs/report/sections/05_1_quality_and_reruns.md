<!--
Section 5.1 Quality thresholds, reconciliation and rerun evidence
Owner: Joseph Nasr
Target: 350 words | Draft due: Wed 25 Nov
To cover: The six dimensions with thresholds, which failures stop a run and which only warn, reconciliation counts, the known bad records caught (defect D-005), idempotency proof (same window run twice).
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 5.1 Quality thresholds, reconciliation and rerun evidence

Every run writes a quality report (`quality/run_id=<id>/quality_report.json`, also stored in MongoDB) that checks six dimensions against thresholds fixed before any result was seen.

| Dimension | Rule | On breach |
|---|---|---|
| Uniqueness | complaint_id not null and unique in curated data | FAIL |
| Completeness | required fields (complaint_id, date_received, product, issue, company) at least 99.5% filled; optional fields reported; an empty sub_issue is "not applicable" when the issue has no sub-issues | FAIL for required fields |
| Validity | dates parse, timely response is Yes or No, state in the reference list, processing lag not negative | WARN above 0.5%, FAIL above 2% |
| Consistency | every product and sub-product combination maps to a standard sub-product | WARN |
| Freshness | latest date received at most 3 days before the run | WARN |
| Reconciliation | raw = curated + quarantined + out of domain + duplicates removed; curated = MongoDB count | FAIL |

A failure stops the run: Spark exits with code 1, no curated data is published and the load does not start. A warning is recorded and shown on the dashboard. A development-only option can override the gate, and the report then records `quality_gate: overridden`.

**Known bad records.** The test fixtures contain deliberate problems: a missing complaint_id, an impossible date, an invalid state, a negative processing lag and a duplicate. The gate fails on them as intended while the counts still reconcile (defect log D-005).

**Full load.** 19,397,176 raw records = 205,271 curated + 112 quarantined + 19,191,793 out of domain + 0 duplicates removed, and MongoDB holds 205,271 complaints. The status was PASS, with the newest complaint one day old (`docs/evidence/full_load.md`). The same file processed independently on two more machines gave identical counts.

**Reruns.** A real API window (20 to 22 October 2026, 468 complaints) was processed and loaded twice. The curated total and the MongoDB count stayed at 468, no complaint_id appeared twice and `agg_monthly` summed to 468; a second machine gave the same result (`docs/evidence/idempotency.md`). Reruns are safe because curated data is merged by complaint_id, MongoDB documents are upserted on the same key, and aggregates are rebuilt in staging collections before they replace the published ones.