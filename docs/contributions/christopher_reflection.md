# Individual reflection: Christopher Al Hassrouty

**Role:** Database Lead — Group 5, Money Transfers and Digital Payments.

## My responsibility

My responsibility was to build the MongoDB layer that connects the processed CFPB complaint data to the dashboard. At first, I expected this part to be mainly about designing collections, writing queries and creating indexes. As the project progressed, I realized that the bigger challenge was making sure the database remained consistent with the rest of the pipeline, especially when data was reprocessed or the structure changed.

## What I implemented and learned

I designed the MongoDB document model and implemented the loading logic, indexes and aggregation queries. Each complaint uses its unique CFPB complaint ID as MongoDB's `_id`, which prevents duplicate documents. I used bulk upserts so that loading the same records again updates existing documents instead of inserting duplicates.

I also worked with native BSON dates rather than storing dates as strings. This made date filtering and chronological aggregations more reliable. Alongside the main `complaints` collection, I implemented loading for the monthly and company-year aggregates, using staging collections to avoid exposing partially loaded results.

For the analytical part, I developed the A1–A8 query functions, along with KPI summaries, freshness information and readers for the machine-learning results. One thing I learned was that building a technically correct aggregation is not enough. The results also need to be interpreted correctly. For example, our selected domain contains no applicable sub-issues, so the sub-issue breakdown in A2 is not meaningful. Similarly, approximately 5% of complaints lack state information, which limits the geographic analysis.

## Challenges and integration

The biggest difficulty was working with components that depended on other team members' implementations. My MongoDB loader required the exact Parquet structure produced by Spark, and the dashboard depended on the query functions returning consistent results.

One integration issue involved the curated data path. The Spark and MongoDB components initially referenced different locations, so the team moved to a shared path definition. This showed me why agreeing on data contracts early is important in a project involving several developers.

I also spent time implementing tests for native dates, duplicate IDs, idempotent loading, aggregate reconciliation, empty query results and quality-gate behavior. These tests helped identify potential problems before running the entire pipeline.

Running the full pipeline on my computer was another important part of the experience. On November 26, I processed the updated CFPB dataset and loaded 205,782 complaints, 73,728 monthly aggregates and 8,083 company-year aggregates. Seeing the complete workflow succeed made the relationship between ingestion, Spark, MinIO and MongoDB much clearer.

## Indexing and performance

The indexing benchmark was particularly useful because it connected the database concepts from the course to actual measurements. I tested three query patterns against the full MongoDB collection, first without the planned secondary indexes and then with them restored.

Without indexes, all three queries performed collection scans. With indexes, MongoDB used index scans and examined considerably fewer documents.

However, I also learned that performance numbers require careful interpretation. MongoDB reported some execution times as 0.0 milliseconds because of its measurement resolution, and certain filters returned very few or no matching documents. These results demonstrate more efficient access paths for the selected queries, but they do not prove that every dashboard query will be equally fast.

## What I would improve

If I worked on a similar project again, I would finalize the data schema, storage paths and query interfaces earlier. I would also prepare benchmark scenarios with more representative filter values and test the complete pipeline sooner, rather than waiting until the individual components were finished.

For a production deployment, I would consider MongoDB replication for improved availability and a more complete strategy for handling records removed from later source snapshots.

## Use of AI and final takeaway

I used ChatGPT to assist with implementation planning, troubleshooting, testing and documentation. I checked the work against the repository, automated tests and actual execution results, and I remain responsible for the submitted work.

My biggest takeaway is that a Big Data platform is not simply about processing a large dataset. Reliable results depend on consistent data contracts, quality checks, safe reruns, appropriate indexing and clear documentation. This project helped me understand how those individual decisions contribute to a working end-to-end data platform.