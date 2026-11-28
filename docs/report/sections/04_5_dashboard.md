<!--
Section 4.5 Dashboard
Owner: Perla Boustany
Target: 300 words | Draft due: Wed 25 Nov
To cover: Pages (at least four analytical views), date and categorical filters, Redis cache (key, time-to-live), freshness indicator, limitation notes, handling of empty selections and database unavailability.
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 4.5 Dashboard

The Streamlit dashboard provides six views for the Money Transfers and Digital Payments domain: Overview, Trends, Issues, Responses and Channels, Geography and Companies, and Data Quality and Limitations. The Overview page presents the selected scope, last update information, and KPI cards for total complaints, year-on-year change, timely-response rate, and median processing lag. The analytical pages answer Q1 to Q5 with time-series, issue, response, channel, company, and geographic views, while the final page presents freshness, data-quality, and limitation information.

A shared sidebar applies consistent filters across the dashboard. Users can restrict results by date range, sub-product, issue, state, submission channel, and company. Centralising these controls ensures that comparisons between pages use the same selected scope. Invalid date ranges are blocked, missing categorical values are displayed as “Unknown”, and selections with no matching complaints return a clear message instead of an error.

The dashboard reads analytical data only from MongoDB through the project query helpers; it does not query raw MinIO files or curated Parquet directly. Query results use a Redis cache-aside layer. The cache key combines the query name with the selected filters in sorted JSON, and cached entries use a 600-second time-to-live. On a cache miss, the query is executed against MongoDB and the result is stored in Redis. If Redis is unavailable, the dashboard falls back to MongoDB directly. If MongoDB is unavailable, the interface displays a warning rather than crashing.

Freshness and quality information help users understand whether the displayed data reflects the latest successful processing run. Limitation notes are displayed with the analytical results so that complaint counts and shares are interpreted correctly. Complaint shares are descriptive evidence rather than company-quality rankings, processing lag is not resolution time, and the dashboard avoids causal or predictive claims.