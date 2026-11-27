# MongoDB index benchmark

- Generated: 2026-11-27 10:38 UTC
- Database: `cfpb_money_transfers`; collection: `complaints`; documents: 205,782
- Repetitions: 10 per query per condition using `explain` at `executionStats` verbosity
- Comparison: with planned secondary indexes removed versus restored
- Times are server-reported `executionTimeMillis` (integer-millisecond resolution).

| Query | Condition | Median time (ms) | Median docs examined | Median keys examined | Access plan |
|---|---|---:|---:|---:|---|
| A1 monthly volume: one sub-product, 12 months | Before indexes | 105.5 | 205782 | 0 | COLLSCAN |
| A1 monthly volume: one sub-product, 12 months | After indexes | 5.0 | 0 | 8460 | IXSCAN |
| A8 state issue profile: one state | Before indexes | 98.0 | 205782 | 0 | COLLSCAN |
| A8 state issue profile: one state | After indexes | 36.0 | 24660 | 24660 | IXSCAN |
| Company and date-range filter | Before indexes | 72.0 | 205782 | 0 | COLLSCAN |
| Company and date-range filter | After indexes | 13.0 | 9982 | 9982 | IXSCAN |

## Query selections

- **A1 monthly volume: one sub-product, 12 months:** sub-product: Domestic (US) money transfer; window: 2025-12-01 to 2026-11-30
- **A8 state issue profile: one state:** state: CA
- **Company and date-range filter:** company: Block, Inc.; window: 2025-12-01 to 2026-11-30

## Interpretation and limitations

- Compare documents and index keys examined alongside reported execution time.
- An index does not guarantee `IXSCAN`: MongoDB may select `COLLSCAN` based on selectivity and dataset size.
- This measures representative query shapes, not end-to-end Streamlit render latency.
- Avoid concurrent pipeline/dashboard workloads during the benchmark.
- Results reflect this local data snapshot and computer, not all possible workloads.
