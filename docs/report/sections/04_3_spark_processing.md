<!--
Section 4.3 Spark processing
Owner: Joseph Nasr
Target: 450 words | Draft due: Wed 25 Nov
To cover: Explicit schema, transformations, domain filter and product mapping, deduplication tie-break, quarantine with reasons, partitioned Parquet, aggregates, record lineage (source_type, ingest_run_id, ingested_at).
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

### 4.3 Spark processing

The Spark job (`processing/spark_job.py`) turns one collected run into curated data, quarantine records, two aggregate tables and a quality report. It runs in local mode inside the pipeline container; on the full file of 19,397,176 records it took 2 minutes 38 seconds with a 4 GB driver.

**Explicit schema.** Both sources are read with declared schemas in which every input field is text, so a change in the source cannot silently change a type. CSV headers and API keys are renamed to one set of standard names, and a test checks that both sources produce the same curated schema.

**Transformations.** Dates are parsed from the first ten characters in three formats (yyyy-MM-dd, MM/dd/yyyy, MM/dd/yy), because API dates also carry a time; impossible dates such as 30 February become null. The timely-response field is normalised to Yes or No and any other value is flagged. Each record gains year, month, year_month and the processing lag in days between the date received and the date sent to the company.

**Domain filter.** A broadcast join with `config/product_mapping.csv` keeps the product labels of option 5, the current label and three legacy labels, and adds a standard sub-product next to the original one. Records of other products are counted as out of domain rather than dropped silently: 19,191,793 in the full load.

**De-duplication.** A complaint can arrive twice, for example in the full file and again in an API window. A window function keeps one record per complaint_id: the most recent ingestion wins, then an API record over a full-load record, then a record whose response is not "In progress", then the latest date sent to the company, and finally a hash of the whole record, so the choice is always the same.

**Quarantine.** Records without a complaint_id, with an invalid date, with a state outside the reference list or with a negative processing lag go to a quarantine folder with a reject_reason that lists every problem found. An empty state is kept and reported as a completeness gap, because removing it would remove about 5% of real complaints. The full load quarantined 112 records.

**Partitioned Parquet.** Curated data is written to `curated/complaints/option=5/year=YYYY/month=MM/`. An API run is merged with the existing curated data by complaint_id, and only the months it touches are rewritten, through a staging folder and dynamic partition overwrite, so running the same input again leaves the totals unchanged.

**Aggregates.** `agg_monthly` (year_month, standard sub-product, issue, state, channel and response category, with complaint counts, timely counts and lag sums) and `agg_company_year` (year, company and standard sub-product, with complaint counts) are always recomputed from the whole curated data set, never from the increment alone.

**Lineage.** Every curated record keeps its source_type (full_load or api), ingest_run_id and ingested_at, and every raw file stays unchanged in MinIO, so any curated value can be traced back to the run and the file it came from.