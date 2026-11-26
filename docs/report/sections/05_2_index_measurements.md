<!--
Section 5.2 Index measurements
Owner: Christopher Al Hassrouty
Target: 200 words | Draft due: Wed 25 Nov
To cover: Before and after indexing for the same queries and data: median time, documents examined, winning plan; what the comparison shows (docs/evidence/benchmark.md).
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 5.2 Index measurements

To evaluate MongoDB query performance, we benchmarked three query patterns against 205,782 curated complaints loaded on November 26, 2026. Each query was executed ten times using MongoDB's `explain("executionStats")`, first without the five secondary indexes and then with them restored. The same dataset and query filters were used in both conditions.

| Query | Before indexing | After indexing | Documents examined (before → after) | Execution plan |
|---|---:|---:|---:|---|
| A1: Monthly volume by sub-product | 86.0 ms | 0.0 ms | 205,782 → 0 | COLLSCAN → IXSCAN |
| A8: State issue profile | 77.0 ms | 0.0 ms | 205,782 → 6 | COLLSCAN → IXSCAN |
| Company and date-range filter | 53.5 ms | 0.0 ms | 205,782 → 0 | COLLSCAN → IXSCAN |

Before indexing, all three queries performed full collection scans, examining 205,782 documents each. After indexing, MongoDB selected index scans, substantially reducing document examinations. For A1, the indexed execution examined 491 index keys without fetching documents, demonstrating the benefit of an index-supported query.

The reported 0.0 ms values reflect integer-millisecond measurement resolution, not zero execution time. Additionally, the selected state had only six matching documents, and the company filter examined no index keys. Therefore, these measurements demonstrate reduced scanning for the tested filters rather than a universal performance improvement. They also exclude dashboard rendering and network overhead.

The complete benchmark results are recorded in `docs/evidence/benchmark.md`. All five project indexes were successfully restored and verified after benchmarking.