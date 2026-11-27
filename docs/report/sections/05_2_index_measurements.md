<!--
Section 5.2 Index measurements
Owner: Christopher Al Hassrouty
Target: 200 words | Draft due: Wed 25 Nov
To cover: Before and after indexing for the same queries and data: median time, documents examined, winning plan; what the comparison shows (docs/evidence/benchmark.md).
Use descriptive and diagnostic language only: no causal claims or company quality rankings.
-->

### 5.2 Index measurements

To evaluate MongoDB query performance, we benchmarked three representative query patterns against 205,782 curated complaints loaded on November 26, 2026. For each query, we selected frequently occurring filter values from the actual dataset and executed ten repetitions using MongoDB's `explain("executionStats")`. The same queries and dataset were tested with the five planned secondary indexes removed and subsequently restored.

| Query | Before indexing | After indexing | Documents examined (before → after) | Execution plan |
|---|---:|---:|---:|---|
| A1: Monthly volume by sub-product | 105.5 ms | 5.0 ms | 205,782 → 0 | COLLSCAN → IXSCAN |
| A8: State issue profile | 98.0 ms | 36.0 ms | 205,782 → 24,660 | COLLSCAN → IXSCAN |
| Company and date-range filter | 72.0 ms | 13.0 ms | 205,782 → 9,982 | COLLSCAN → IXSCAN |

Without the indexes, all three queries performed full collection scans, examining 205,782 documents each. After indexing, MongoDB selected index scans and reduced the number of documents examined.

The observed median execution times improved by approximately 21.1 times for A1, 2.7 times for A8, and 5.5 times for the company and date-range query. A1 examined no documents after indexing, consistent with an index-supported execution that avoided fetching complaint documents.

These measurements demonstrate improved query access for the selected filters, not guaranteed performance across every workload. They represent server-reported execution times rather than end-to-end dashboard latency and may vary with hardware, caching, data distribution, and query selectivity.

The complete measurements and selected filter values are documented in `docs/evidence/benchmark.md`. All five compound indexes were verified after benchmarking.