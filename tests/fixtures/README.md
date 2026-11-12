# Test fixtures (Spark transformation and quality tests)

Small, hand-made files that imitate the real CFPB inputs, so the Spark transforms and the quality gate can be tested without the full dataset. All companies, ZIP codes and Complaint IDs (9000001 and up) are invented. Owner: Joseph Nasr.

- `mini_complaints.csv`: 22 rows with the real CSV headers of the full export (`complaints.csv`).
- `mini_api_page.json`: one page of the CFPB search API (`hits.hits[]._source`) with 8 records.

If Marwa's API notes or the real CSV show different headers, keys or date formats, update these files first, then the tests.

## mini_complaints.csv: expected outcome per row

| Complaint ID | Case being tested | Expected outcome |
|---|---|---|
| 9000001 | Valid, current label, Domestic (US) money transfer, same-day send | Curated, `processing_lag_days` = 0 |
| 9000002 | Valid, International money transfer, tag "Older American" | Curated, lag 2, `is_older_american` = true |
| 9000003 | Valid, Mobile or digital wallet, issue text containing commas | Curated, `is_servicemember` = true |
| 9000004 | Valid, Virtual currency, both tags, timely "No", empty ZIP | Curated, `timely_response` = false, both flags true, lag 3 |
| 9000005 | Valid, response "In progress", timely empty | Curated, `timely_response` = null |
| 9000006 | Valid, non-core sub-product (Check cashing service) | Curated, `is_core_payment` = false |
| 9000007 | Valid, dates in `MM/dd/yy` format | Curated, `date_received` = 2024-03-22 |
| 9000008 | Valid, territory PR | Curated, lag 1 |
| 9000009 | Valid, military code AE | Curated |
| 9000010 | Valid, **empty state** | Curated or quarantined: rule to be decided from the profiling (completeness gap vs invalid) |
| 9000011 | State "XX" not in `config/state_codes.csv` | Quarantine, reason `invalid_state` |
| 9000012 (row 1) | Duplicate ID, response "In progress" | Removed by deduplication |
| 9000012 (row 2) | Duplicate ID, response "Closed with explanation" | Kept (tie-break: not "In progress" wins) |
| 9000014 | Impossible date 2024-02-30 | Quarantine, reason `invalid_date` |
| 9000015 | Sent to company before received | Quarantine, reason `negative_lag` |
| 9000016 | Legacy label "Money transfers" (2016, `MM/dd/yy`) | Curated, `product_std` = current label |
| 9000017 | Legacy label "Virtual currency", no sub-product | Curated, `sub_product_std` = Virtual currency |
| 9000018 | Legacy "Prepaid card" / "Mobile wallet" | Curated, `sub_product_std` = Mobile or digital wallet |
| 9000019 | "Prepaid card" / "General-purpose prepaid card" | Out of domain |
| 9000020 | "Credit card" | Out of domain |
| (empty) | Missing Complaint ID | Quarantine, reason `null_id` |
| 9000022 | Leading/trailing spaces, blank ZIP " " | Curated, values trimmed, ZIP = null, timely = true, lag 1 |

**Expected counts:** raw_input 22 = curated 15 + quarantined 4 + out_of_domain 2 + duplicates_removed 1 (with 9000010 counted as curated; if the profiling decides empty states go to quarantine, curated 14 and quarantined 5).

## mini_api_page.json: expected outcome per record

| Complaint ID | Case being tested | Expected outcome |
|---|---|---|
| 9000101 | Valid new complaint, ISO datetime with offset | Curated |
| 9000005 | Update of a CSV complaint (now closed, timely "Yes") | Curated; after union with the full load, the API version wins (later `ingested_at`) |
| 9000102 (first) | Duplicate inside the page, "In progress" | Removed by deduplication |
| 9000102 (second) | Duplicate inside the page, closed | Kept |
| 9000103 | Unparseable `date_received` | Quarantine, reason `invalid_date` |
| 9000104 | Sent to company before received | Quarantine, reason `negative_lag` |
| 9000105 | Legacy label "Money transfers" | Curated, `product_std` = current label |
| 9000106 | "Credit card" | Out of domain |

**Expected counts:** raw_input 8 = curated 4 + quarantined 2 + out_of_domain 1 + duplicates_removed 1.
