# Data dictionary

**Owner:** Loutchiana Marie, with Joseph Nasr (schema and mappings) | **Status:** written Sat 21 Nov 2026 from `processing/schema.py`, `processing/transforms.py`, `processing/quality.py`, `config/` and `docs/mongodb_model.md` on `main`. Items marked **to confirm** need a check against the quality report of the full load.

This document describes every field of the curated record, the reference lists that define the domain, the aggregate collections and the supporting records (quarantine, quality report, run log). The curated schema is **identical in Parquet and in MongoDB** (`complaints`), and the historical CSV and the API feed the same schema. Source: official CFPB [field reference](https://cfpb.github.io/api/ccdb/fields.html).

## 1. Conventions

| Topic | Rule |
|---|---|
| Names | Standard `snake_case`. CSV headers (for example `Timely response?`) and API keys (for example `timely`) are both mapped to these names in `processing/schema.py` (`CSV_TO_STANDARD`, `API_TO_STANDARD`). |
| Reading | Both sources are read with every column as a string, so a malformed value never makes the read fail; types are cast afterwards (`processing/transforms.py`) and the output is checked against `CURATED_SCHEMA`. |
| Missing values | Empty strings and the tokens `N/A`, `NA`, `None`, `null` become **null**. Strings are trimmed. The dashboard shows null categories as `Unknown`; the data itself keeps null. |
| Types | Parquet type, then the MongoDB type: `long` is BSON `Int64`; `date` is BSON `Date` at 00:00:00 UTC; `timestamp` is BSON `Date` (UTC); `array<string>` is an array. |
| Dates | Formats tried in this order: `yyyy-MM-dd`, `MM/dd/yyyy`, `MM/dd/yy`. API dates are UTC timestamps (`2026-10-22T23:57:30.000Z`); only the first 10 characters are used. An impossible date (for example 2024-02-30) becomes null and the record is quarantined. |
| Scope | Only records of option 5 (money transfers and digital payments) are kept, using `config/product_mapping.csv` (section 3). |
| Original labels | The source labels `product` and `sub_product` are kept next to our standard categories `product_std` and `sub_product_std`. |

## 2. Curated complaint record (`complaints`)

One document per distinct `complaint_id`. 27 fields, in contract order.

### 2.1 Identifier and dates

| Field | Type | Source (CSV header / API key) | Description and rule | Allowed values | Example | Known issues |
|---|---|---|---|---|---|---|
| `complaint_id` | long (Int64, MongoDB `_id`) | `Complaint ID` / `complaint_id` | Unique identifier assigned by the CFPB. Used for deduplication and traceability. Must be present and unique. | positive integer | `9000001` (test data) | A missing or non-numeric ID is quarantined (`null_id`). |
| `date_received` | date | `Date received` / `date_received` | Date the CFPB received the complaint. All date filters and trends use it. | a real calendar date | `2024-03-15` | Unparseable or impossible dates are quarantined (`invalid_date`). The CSV mixes `yyyy-MM-dd` and `MM/dd/yy`. |
| `date_sent_to_company` | date | `Date sent to company` / `date_sent_to_company` | Date the CFPB sent the complaint to the company. | a real calendar date, or null | `2024-03-17` | Present but unparseable means quarantine (`invalid_date`). Null is allowed and gives a null lag. |
| `year` | int | derived from `date_received` | Calendar year of receipt. | 2011 to current year | `2024` | Null only if the date is invalid, and then the record is quarantined. |
| `month` | int | derived from `date_received` | Calendar month of receipt. | 1 to 12 | `3` | The Parquet folder uses a two-digit month (`month=03`). |
| `year_month` | string | derived from `date_received` | `YYYY-MM`, used for monthly aggregates. | `YYYY-MM` | `2024-03` | The current month is incomplete and must be labelled as partial. |
| `processing_lag_days` | int | derived | `date_sent_to_company` minus `date_received`, in days. **This is not the company's resolution time**: it only measures how long the CFPB took to send the complaint to the company. | 0 or more, or null | `2` | A negative value is quarantined (`negative_lag`). Null when `date_sent_to_company` is missing. |

### 2.2 Product

| Field | Type | Source | Description and rule | Allowed values | Example | Known issues |
|---|---|---|---|---|---|---|
| `product` | string | `Product` / `product` | Original CFPB product label, unchanged. | `Money transfer, virtual currency, or money service`, and the legacy labels `Money transfers`, `Virtual currency`, `Prepaid card` (section 3) | `Money transfer, virtual currency, or money service` | Product labels changed in 2017; historical records keep the label the consumer selected. |
| `sub_product` | string | `Sub-product` / `sub_product` | Original CFPB sub-product label, unchanged. | CFPB values; null allowed | `Domestic (US) money transfer` | Not every product has sub-products. The legacy `Virtual currency` label has none. |
| `product_std` | string | from `config/product_mapping.csv` | Our standard product for the domain. | `Money transfer, virtual currency, or money service` | same | Only records that match the mapping are kept. |
| `sub_product_std` | string | from `config/product_mapping.csv` | Our standard sub-product. `*` in the mapping means "keep the original sub-product". | `Domestic (US) money transfer`, `International money transfer`, `Mobile or digital wallet`, `Virtual currency`, and other CFPB sub-products of the product | `Mobile or digital wallet` | The legacy `Prepaid card` / `Mobile wallet` is renamed to `Mobile or digital wallet`. Mapping of legacy labels is **to confirm** with the lecturer. |
| `is_core_payment` | boolean | derived | True when `sub_product_std` is one of the four core sub-products. All other sub-products are grouped as "Other money services" in comparisons. | true, false | `true` | The "Other money services" group is a dashboard grouping; it is not stored as a value. |

### 2.3 Issue

| Field | Type | Source | Description and rule | Allowed values | Example | Known issues |
|---|---|---|---|---|---|---|
| `issue` | string | `Issue` / `issue` | Issue the consumer selected. Possible values depend on the product. Required. | CFPB values | `Fraud or scam` | The issue is chosen by the consumer; it does not establish confirmed fraud. |
| `sub_issue` | string | `Sub-issue` / `sub_issue` | Sub-issue, where the CFPB defines one. | CFPB values; null allowed | `null` | **Mostly empty** for this product: not every issue has a sub-issue. The quality report treats it as expected sparse, never a warning. |

### 2.4 Company and response

| Field | Type | Source | Description and rule | Allowed values | Example | Known issues |
|---|---|---|---|---|---|---|
| `company` | string | `Company` / `company` | Company the complaint is about. Required. | free text | `Example Pay Inc.` (test data) | Company counts are shares of complaints, not a quality ranking: there is no customer or transaction denominator. Name variants of one company may exist (**to confirm** from the profiling). |
| `company_public_response` | string | `Company public response` / `company_public_response` | Optional public response chosen by the company, up to 180 days after referral. | CFPB values; null allowed | `Company has responded to the consumer and the CFPB and chooses not to provide a public response` | Mostly empty for this product. |
| `company_response` | string | `Company response to consumer` / `company_response` | How the company responded. | for example `Closed with explanation`, `Closed with monetary relief`, `Closed with non-monetary relief`, `In progress`; full list **to confirm** from the profiling | `Closed with explanation` | `In progress` complaints change later, which is one reason for the 21-day overlap of incremental runs. Response categories do not measure satisfaction. |
| `timely_response` | boolean | `Timely response?` / `timely` | Whether the company responded on time. | true (Yes), false (No), null | `true` | A value that is neither Yes nor No becomes null and is counted as invalid in the quality report. The flag does not measure how long the issue took to resolve. |

### 2.5 Geography, channel and tags

| Field | Type | Source | Description and rule | Allowed values | Example | Known issues |
|---|---|---|---|---|---|---|
| `state` | string | `State` / `state` | Consumer's state, as a two-letter code. State is the default geographic level of the dashboard. | one of the 62 codes of `config/state_codes.csv`, or null | `NY` | A value not in the list is quarantined (`invalid_state`). An **empty state is kept as null** (a completeness gap, reported, not rejected); the dashboard shows it as `Unknown`. |
| `zip_code` | string | `ZIP code` / `zip_code` | ZIP code as published by the CFPB. | 5 digits, a masked form such as `750XX`, or null | `100XX` | **Partly suppressed or masked** by the CFPB for areas with small populations (a three-digit form or none). Kept as published; a missing optional ZIP is a warning at most. Not used for analysis. |
| `submitted_via` | string | `Submitted via` / `submitted_via` | How the consumer submitted the complaint to the CFPB. | observed in the test data: `Web`, `Phone`, `Referral`; other CFPB values are kept as published (**to confirm** the full list) | `Web` | A change in channel mix may reflect how complaints were routed, not consumer preference. |
| `tags` | array of string | `Tags` / `tags` | Source tags split on a comma and a space. Empty array when none. | `Older American`, `Servicemember` | `["Older American"]` | Older American means age 62 or more; Servicemember covers active duty, National Guard, Reservists, veterans and retirees (CFPB definitions). Small subgroups need care. |
| `is_older_american` | boolean | derived from `tags` | True when `tags` contains `Older American`. | true, false | `false` | |
| `is_servicemember` | boolean | derived from `tags` | True when `tags` contains `Servicemember`. | true, false | `false` | |

### 2.6 Lineage

| Field | Type | Source | Description and rule | Allowed values | Example | Known issues |
|---|---|---|---|---|---|---|
| `source_type` | string | set by the pipeline | Which path produced the record. | `full_load`, `api` | `api` | When the same ID comes from both paths, the deduplication tie-break decides (section 5). |
| `ingest_run_id` | string | set by the pipeline | The run that produced the record: `YYYYMMDDTHHMMSSZ_<full\|api>` in UTC. Leads to the raw objects, run log and quality report. | run id format | `20261110T020000Z_api` | |
| `ingested_at` | timestamp | set by the pipeline | UTC time of the ingestion, taken from the run id. | UTC timestamp | `2026-11-10 02:00:00` | |

MongoDB documents may also contain a `lineage` sub-document that repeats the three fields above; the flat fields stay canonical (`docs/mongodb_model.md`).

### 2.7 Source fields that are ignored

The CFPB no longer publishes the complaint narrative (removed September 2026), consumer consent and consumer disputed. If an older export still contains them (`Consumer complaint narrative`, `Consumer consent provided?`, `Consumer disputed?`, and the API keys `complaint_what_happened`, `consumer_consent_provided`, `consumer_disputed`, `has_narrative`), they are ignored and never loaded. The brief rules out NLP.

## 3. Reference lists

### 3.1 Domain filter and category mapping: `config/product_mapping.csv`

Required data artefact of the brief. Columns: `source_product`, `source_sub_product`, `product_std`, `sub_product_std`. A row matches a record on the product and either the exact sub-product or `*` (any). `*` in `sub_product_std` means "keep the original sub-product". A record that matches no row is out of domain and only counted.

| Source product | Sub-product | `product_std` | `sub_product_std` | Meaning |
|---|---|---|---|---|
| Money transfer, virtual currency, or money service | any | same label | original sub-product | current CFPB label (199,152 records on 20 Nov 2026 in the API; 199,354 in the full file of 22 Nov) |
| Money transfers | any | `Money transfer, virtual currency, or money service` | original sub-product | legacy label used before April 2017 (**to confirm** with the lecturer) |
| Virtual currency | any | `Money transfer, virtual currency, or money service` | `Virtual currency` | legacy label |
| Prepaid card | Mobile wallet | `Money transfer, virtual currency, or money service` | `Mobile or digital wallet` | legacy label; other prepaid sub-products stay out of domain |

The four **core sub-products** (`is_core_payment` = true) are domestic (US) money transfer, international money transfer, mobile or digital wallet and virtual currency. An initial profile of the API on 22 Oct 2026 gave 44.1%, 7.6%, 31.9% and 11.4% of the current label.

### 3.2 State reference list: `config/state_codes.csv`

Columns `code`, `name`, `category`. Source: USPS Publication 28, Postal Addressing Standards, Appendix B "Two-Letter State and Possession Abbreviations" (https://pe.usps.com/text/pub28/28apb.htm), plus the three military codes AA, AE and AP. **62 codes:** 50 states, DC, 5 territories (AS, GU, MP, PR, VI), 3 freely associated states (FM, MH, PW) and 3 military codes (AA, AE, AP). It is used for the validity check of `state`.

## 4. Aggregate collections

Both are rebuilt by Spark from **all** curated data, then loaded into MongoDB by replacing the collection.

**`agg_monthly`**: grain `year_month`, `sub_product_std`, `issue`, `state`, `submitted_via`, `company_response`.

| Field | Type | Meaning |
|---|---|---|
| `complaint_count` | long | complaints in the group |
| `timely_yes_count` | long | complaints with `timely_response` = true |
| `timely_known_count` | long | complaints with a known (Yes or No) `timely_response`, the denominator of the timely percentage |
| `lag_sum_days` | long | sum of `processing_lag_days` |
| `lag_count` | long | complaints with a known lag |

It has no `sub_issue` and no `company`; queries that need them read `complaints`.

**`agg_company_year`**: grain `year`, `company`, `sub_product_std`; measure `complaint_count`. Used for company shares of complaints, never a quality ranking.

## 5. Deduplication rule (one record per `complaint_id`)

When the same ID appears more than once, the retained record is chosen in this order: the latest `ingested_at`; then `source_type` = `api` over `full_load`; then a record whose `company_response` is not `In progress`; then the latest `date_sent_to_company`; then a stable hash, so the result is deterministic. A record without an ID is never merged; it goes to quarantine.

## 6. Supporting records

### 6.1 Quarantine (`quarantine/run_id=<run_id>/`, Parquet)

The rejected records with all their columns and a `reject_reason`. Several reasons can apply, joined with `;`.

| Reason | Meaning |
|---|---|
| `null_id` | Complaint ID missing or not numeric |
| `invalid_date` | date received missing or unparseable, or date sent present but unparseable |
| `negative_lag` | date sent to company before date received |
| `invalid_state` | a state value that is not in `config/state_codes.csv` |

### 6.2 Quality report (`quality/run_id=<run_id>/quality_report.json`, copied to `quality_reports`)

| Key | Content |
|---|---|
| `run_id`, `generated_at`, `source_type` | which run, when, which path |
| `counts` | `raw_input`, `out_of_domain`, `duplicates_removed`, `quarantined`, `curated` (they reconcile exactly: raw = curated + quarantined + out of domain + duplicates removed) |
| `quarantine_reasons` | count per reject reason |
| `checks` | one entry per check: `dimension`, `rule`, `metric`, `threshold`, `status` (PASS, WARN, FAIL) |
| `completeness` | percentage filled per field |
| `freshness` | `latest_date_received`, `ingestion_lag_days` |
| `consistency` | unmapped and mapped product combinations with counts |
| `thresholds` | the thresholds used (fixed in advance) |
| `overall_status` | PASS, WARN or FAIL; FAIL stops the run |

Example, full run of 22 Nov 2026 (`20261122T183046Z_full`): `overall_status` PASS; `counts` raw_input 19,371,701, out_of_domain 19,166,525, duplicates_removed 0, quarantined 112, curated 205,064; `quarantine_reasons` invalid_state 32, negative_lag 80; `freshness` latest_date_received 2026-11-20, ingestion_lag_days 2.
| `quality_gate` | `passed`, `stopped` or `overridden` (development only) |

The six dimensions of brief V2 are uniqueness, completeness, validity, consistency, freshness and reconciliation. On 21 Nov the code still labels two of them `timeliness` and `integrity`; the rename is open with Joseph.

### 6.3 Raw manifest and run log

| Object | Content |
|---|---|
| `raw/cfpb/full_load/ingest_date=.../manifest.json` | run id, source URL, download start and end, ZIP size and SHA-256 checksum, size and SHA-256 of the extracted CSV, record count |
| `logs/ingestion/run_id=<run_id>.json` | run id, run type, start and end time, endpoint, non-secret parameters, date window, pagination state (method `search_after`, page size, pages fetched), HTTP status and retries, outcome (`running`, `success`, `empty`, `failed`, or `skipped_identical` for a repeated full load), raw paths, record count, checksum of the pages, the CFPB's own freshness fields (`source_meta`), high-water mark used and next |
| `state/high_water_mark.json` | the latest `date_received` already collected and the run that set it; advanced only after a fully successful run |

## 7. Known data issues, summarised

- `sub_issue` and `company_public_response` are mostly empty for this product.
- ZIP codes are partly masked or suppressed by the CFPB.
- Legacy product labels (before April 2017) are mapped to the current domain; the mapping is to be confirmed with the lecturer.
- The CSV mixes two date formats; API dates are UTC timestamps (the day should be checked against the CSV once both are loaded).
- Recent months are provisional: a complaint is published only after the company responds or after 15 days, and responses change later.
- The data is not a random sample and contains no transactions, balances, confirmed fraud labels or resolution durations.
