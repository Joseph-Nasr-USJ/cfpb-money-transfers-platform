<!--
Section 4.4 MongoDB serving layer
Owner: Christopher Al Hassrouty
Target: 400 words | Draft due: Wed 25 Nov
To cover: Document model and why, native dates and why, upserts and batch size, the collections, indexes, the aggregation queries A1 to A8, aggregate refresh.
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 4.4 MongoDB serving layer

MongoDB 7.0 serves as the database layer between Apache Spark and the Streamlit dashboard. Spark processes the raw CFPB complaint data and stores curated Parquet files in MinIO, while MongoDB makes the cleaned data and precomputed aggregates available for efficient querying. This separation allows the dashboard to retrieve analytical results without repeatedly processing the original dataset.

The main `complaints` collection stores one document per complaint, using the unique `complaint_id` as its `_id`. Each document contains standardized product classifications, issues, company information, geographic details, submission channels, company responses, processing lag, and ingestion metadata. MongoDB's flexible document model accommodates optional fields without requiring a rigid relational schema. Dates are stored as native BSON dates rather than strings, allowing accurate chronological comparisons, date-range filtering, and indexing. Processing lag refers to the interval between receiving a complaint and forwarding it to the company, not the time needed to resolve the complaint.

The loader implemented in `database/load.py` reads curated Parquet files from `curated/complaints/option=5/` and performs bulk upserts in batches of up to 5,000 documents. This approach ensures idempotency: rerunning the pipeline updates existing complaints instead of creating duplicates. Loading is controlled by the Spark quality gate, preventing invalid processing results from being published.

Two additional collections, `agg_monthly` and `agg_company_year`, store precomputed analytical summaries. These aggregates are built in staging collections and published through collection renaming, reducing the risk of exposing partially loaded results. However, their replacements are performed separately rather than as one atomic transaction.

Five compound indexes support commonly used filters on standardized sub-product, issue, state, company, and submission channel, each combined with `date_received`. These indexes improve access to selected records, particularly for equality filters followed by date ranges.

The query module provides eight aggregation functions (A1–A8), supporting complaint volume trends, issue distributions, fraud-related classifications, company responses, processing lag, and geographic analysis. Additional functions provide KPI summaries, data freshness indicators, and access to machine-learning results.

Two data limitations affect interpretation. Sub-issues are not applicable within this domain, so A2 primarily supports issue shares within sub-products. Additionally, approximately 5% of complaints lack state information, meaning geographic findings represent only complaints with available locations. The analysis remains descriptive and diagnostic, without making causal claims or ranking companies by service quality.