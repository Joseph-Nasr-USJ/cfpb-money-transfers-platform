# Test plan

Owner: Charbel Mazraani. Each test is written by the owner of its component; this file tracks every test level the brief requires, who owns it, where it lives and its current status.

**Run all automated tests:** `make test` (pytest inside the pipeline container, so every machine uses the same Python, Java and Spark versions). Each run is saved as evidence in `docs/evidence/test_results_YYYY-MM-DD.txt`.

**Status values:** `passing` (on `main`, green in the last run), `failing` (on `main`, red in the last run; a defect is open in [defect_log.md](defect_log.md)), `planned` (not written yet). Test names marked *proposed* are suggestions; the owner may rename them and this file is updated when the test is merged.

Last update: Sat 21 Nov 2026 (42 tests passing, brief V2 dimension names, machine-learning tests added).

## 1. Test levels required by the brief

| Level | What the tests must show | Owner | Location | Status |
|---|---|---|---|---|
| Collector | Pagination, timeouts, bounded retries, date window with high-water mark and overlap, complete run log, raw files never overwritten, resume after failure | Marwa Zeineddine | `tests/ingestion/` | planned |
| Transformation | Explicit schema, standard column names, trimmed strings, date parsing and invalid dates, Yes/No and missing values, domain filter, deduplication by Complaint ID with tie-break, derived fields, quarantine | Joseph Nasr | `tests/processing/` | passing (26 tests in the transformation files, plus 6 for the Spark job) |
| Data quality | Six dimensions (uniqueness, completeness, validity, consistency, freshness, reconciliation) with the fixed thresholds; the quality gate stops a bad run; the known bad fixture records are caught (defect D-005) | Joseph Nasr | `tests/processing/test_quality.py` | passing (10 tests) |
| Database | Upsert or bulk load is idempotent, `_id` = complaint_id, native dates, indexes on the dashboard filters, aggregation queries return the expected result | Christopher Al Hassrouty | `tests/database/` | planned |
| Dashboard | Query functions return aggregates only, empty selection, invalid date range, missing category, database unavailable | Perla Boustany | `tests/dashboard/` + manual checklist | planned |
| End-to-end | A small sample goes raw → curated → MongoDB → query function and the counts reconcile at every layer; a repeated run creates no duplicates | Charbel Mazraani with Joseph Nasr | `tests/e2e/test_pipeline_sample.py` | planned |

## 2. Test inventory

### Collector (Marwa Zeineddine)

| ID | Test | File | Status |
|---|---|---|---|
| C-01 | *proposed* `test_historical_writes_zip_csv_and_manifest` (record count and checksum in the manifest) | `tests/ingestion/test_historical.py` | planned |
| C-02 | *proposed* `test_incremental_follows_pagination_to_last_page` (HTTP mocked with `responses`) | `tests/ingestion/test_incremental.py` | planned |
| C-03 | *proposed* `test_retries_are_bounded` (stops after `API_MAX_RETRIES`, outcome recorded as failed) | `tests/ingestion/test_incremental.py` | planned |
| C-04 | *proposed* `test_request_uses_timeout` (`API_TIMEOUT_SECONDS`) | `tests/ingestion/test_incremental.py` | planned |
| C-05 | *proposed* `test_window_starts_at_high_water_mark_minus_overlap` (`OVERLAP_DAYS`) | `tests/ingestion/test_incremental.py` | planned |
| C-06 | *proposed* `test_run_log_has_every_required_field` (run id, start and end time, endpoint, parameters, window, pagination state, HTTP status, retry count, outcome, raw path, record count, checksum, next high-water mark) | `tests/ingestion/test_run_log.py` | planned |
| C-07 | *proposed* `test_raw_object_is_never_overwritten` | `tests/ingestion/test_incremental.py` | planned |
| C-08 | *proposed* `test_resume_from_saved_pagination_state` | `tests/ingestion/test_incremental.py` | planned |
| C-09 | *proposed* `test_run_id_format` (`YYYYMMDDTHHMMSSZ_<full\|api>`) | `tests/ingestion/test_run_log.py` | planned |

### Transformation (Joseph Nasr)

| ID | Test | File | Status |
|---|---|---|---|
| T-01 | `test_columns` | `tests/processing/test_state_codes.py` | passing |
| T-02 | `test_expected_counts` | `tests/processing/test_state_codes.py` | passing |
| T-03 | `test_codes_are_unique_two_uppercase_letters` | `tests/processing/test_state_codes.py` | passing |
| T-04 | `test_key_codes_present` | `tests/processing/test_state_codes.py` | passing |
| T-05 | `test_csv_has_real_headers_and_22_rows` | `tests/processing/test_fixtures.py` | passing |
| T-06 | `test_csv_contains_the_deliberate_cases` | `tests/processing/test_fixtures.py` | passing |
| T-07 | `test_api_page_structure_and_cases` | `tests/processing/test_fixtures.py` | passing |
| T-08 | `test_both_mappings_produce_the_same_standard_columns` | `tests/processing/test_schema.py` | passing |
| T-09 | `test_csv_fixture_maps_to_standard_columns` | `tests/processing/test_schema.py` | passing |
| T-10 | `test_api_fixture_maps_to_standard_columns` | `tests/processing/test_schema.py` | passing |
| T-11 | `test_csv_and_api_give_identical_standard_schema` | `tests/processing/test_schema.py` | passing |
| T-12 | `test_removed_and_missing_columns_do_not_fail` | `tests/processing/test_schema.py` | passing |
| T-13 | `test_curated_schema_matches_the_shared_contract` | `tests/processing/test_schema.py` | passing |
| T-14 | `test_standardise_trims_and_nulls_empty_values` | `tests/processing/test_transforms.py` | passing |
| T-15 | `test_parse_dates_handles_both_formats_and_flags_invalid` | `tests/processing/test_transforms.py` | passing |
| T-16 | `test_normalise_values_types_and_tags` | `tests/processing/test_transforms.py` | passing |
| T-17 | `test_apply_domain_keeps_current_and_legacy_labels` | `tests/processing/test_transforms.py` | passing |
| T-18 | `test_deduplicate_prefers_closed_record` | `tests/processing/test_transforms.py` | passing |
| T-19 | `test_deduplicate_latest_ingestion_and_api_win` | `tests/processing/test_transforms.py` | passing |
| T-20 | `test_derive_fields` | `tests/processing/test_transforms.py` | passing |
| T-21 | `test_split_quarantine_reasons` | `tests/processing/test_transforms.py` | passing |
| T-22 | `test_empty_state_can_be_quarantined` | `tests/processing/test_transforms.py` | passing |
| T-23 | `test_csv_counts_balance` | `tests/processing/test_transforms.py` | passing |
| T-24 | `test_api_counts_balance` | `tests/processing/test_transforms.py` | passing |
| T-25 | `test_conform_to_curated_matches_schema` | `tests/processing/test_transforms.py` | passing |
| T-26 | `test_product_mapping_has_no_ambiguous_rows` | `tests/processing/test_transforms.py` | passing |
| T-27 | `test_parse_run_id` | `tests/processing/test_spark_job.py` | passing |
| T-28 | `test_wrong_arguments_exit_with_code_2` | `tests/processing/test_spark_job.py` | passing |
| T-29 | `test_quality_gate_failure_writes_evidence_but_no_curated_data` | `tests/processing/test_spark_job.py` | passing |
| T-30 | `test_full_load_writes_curated_aggregates_and_report` | `tests/processing/test_spark_job.py` | passing |
| T-31 | `test_api_run_merges_with_curated_and_rerun_changes_nothing` (idempotent rerun, demo step 5; real-data proof in [idempotency.md](evidence/idempotency.md)) | `tests/processing/test_spark_job.py` | passing |
| T-32 | `test_missing_input` | `tests/processing/test_spark_job.py` | passing |

### Data quality (Joseph Nasr)

Thresholds are fixed before any result is seen (uniqueness 0 nulls and 0 duplicates; required fields at least 99.5% filled; invalid values WARN above 0.5% and FAIL above 2%; unmapped combinations listed; latest record at most 3 days old; raw = curated + quarantined + out_of_domain + duplicates_removed, and curated = MongoDB count). The code still uses the older dimension names `timeliness` and `integrity` until Joseph's V2 change lands; they mean freshness and reconciliation.

| ID | Test | File | Status |
|---|---|---|---|
| Q-01 | `test_csv_fixture_fails_the_quality_gate` (known bad records: invalid date, invalid state, negative interval, missing ID; defect D-005) | `tests/processing/test_quality.py` | passing |
| Q-02 | `test_api_fixture_counts_and_gate` | `tests/processing/test_quality.py` | passing |
| Q-03 | `test_clean_records_pass` | `tests/processing/test_quality.py` | passing |
| Q-04 | `test_duplicate_ids_fail_uniqueness` | `tests/processing/test_quality.py` | passing |
| Q-05 | `test_integrity_fails_when_counts_do_not_reconcile` (reconciliation) | `tests/processing/test_quality.py` | passing |
| Q-06 | `test_timeliness_warns_on_old_data` (freshness) | `tests/processing/test_quality.py` | passing |
| Q-07 | `test_invalid_timely_value_is_counted` | `tests/processing/test_quality.py` | passing |
| Q-08 | `test_unmapped_sub_product_warns_consistency` | `tests/processing/test_quality.py` | passing |
| Q-09 | `test_threshold_rules` | `tests/processing/test_quality.py` | passing |
| Q-10 | `test_report_is_valid_json` | `tests/processing/test_quality.py` | passing |

### Database (Christopher Al Hassrouty)

Unit tests use `mongomock` (in-memory MongoDB), so they run without the `mongo` container.

| ID | Test | File | Status |
|---|---|---|---|
| D-01 | `test_loading_twice_does_not_create_duplicates` (upsert is idempotent; real-data proof in [idempotency.md](evidence/idempotency.md)) | `tests/database/test_upsert_idempotency.py` | passing |
| D-01b | `test_upsert_updates_existing_complaint` | `tests/database/test_upsert_idempotency.py` | passing |
| D-02 | *proposed* `test_id_is_complaint_id` | `tests/database/test_load.py` | planned |
| D-03 | *proposed* `test_dates_are_stored_as_native_dates` | `tests/database/test_load.py` | planned |
| D-04 | *proposed* `test_indexes_cover_dashboard_filters` (product, date, state, company, issue) | `tests/database/test_indexes.py` | planned |
| D-05 | *proposed* `test_each_aggregation_returns_expected_result` (A1 to A8 on a small known dataset) | `tests/database/test_queries.py` | planned |
| D-06 | *proposed* `test_pipeline_runs_records_loaded_count` | `tests/database/test_load.py` | planned |

### Dashboard (Perla Boustany)

| ID | Test | File | Status |
|---|---|---|---|
| B-01 | *proposed* `test_queries_return_aggregates_not_individual_records` | `tests/dashboard/test_queries.py` | planned |
| B-02 | *proposed* `test_empty_selection_shows_message` | `tests/dashboard/test_filters.py` | planned |
| B-03 | *proposed* `test_invalid_date_range_is_rejected` | `tests/dashboard/test_filters.py` | planned |
| B-04 | *proposed* `test_database_unavailable_shows_error` | `tests/dashboard/test_app.py` | planned |
| B-05 | Manual checklist (section 4): empty selection, invalid date range, missing category, database stopped, mobile width | `docs/evidence/dashboard_checks.md` | planned |

### Machine learning (Perla Boustany, Spark MLlib)

The models only describe or diagnose past data; they never predict. Fixed rule for "emerging": slope of at least +0.2 points per month, R² of at least 0.5 and at least 50 complaints in the window.

| ID | Test | File | Status |
|---|---|---|---|
| M-01 | *proposed* `test_rising_series_gives_positive_slope_and_emerging_flag` (rising fixture series) | `tests/analytics/test_ml_emerging_issues.py` | planned |
| M-02 | *proposed* `test_flat_series_is_not_flagged_emerging` | `tests/analytics/test_ml_emerging_issues.py` | planned |
| M-03 | *proposed* `test_same_seed_gives_same_clusters` (KMeans seed 42) | `tests/analytics/test_ml_state_clusters.py` | planned |
| M-04 | *proposed* `test_states_below_100_complaints_are_listed_separately` | `tests/analytics/test_ml_state_clusters.py` | planned |

### End-to-end (Charbel Mazraani with Joseph Nasr)

| ID | Test | File | Status |
|---|---|---|---|
| E-01 | *proposed* `test_sample_counts_reconcile_at_every_layer`: about 1,000 sample rows go raw → curated → MongoDB → query function; raw = curated + quarantined + out_of_domain + duplicates_removed, curated = MongoDB count = query total | `tests/e2e/test_pipeline_sample.py` | planned |
| E-02 | *proposed* `test_rerun_creates_no_duplicates`: the same window processed and loaded twice gives the same counts. Manual real-data version already recorded: run `20261124T084259Z_api`, 468 complaints before and after the rerun, no duplicate Complaint IDs ([idempotency.md](evidence/idempotency.md)) | `tests/e2e/test_pipeline_sample.py` | planned |

## 3. Deliberate failing test (brief requirement)

The brief requires a known bad test record to be shown caught by the intended check during development. The final submission must have passing tests. Joseph implemented this as fixture records with deliberate problems (an invalid date, an invalid state, a negative interval, a missing Complaint ID) and a test that proves the quality gate fails on them, so the test itself passes.

| Step | What | Evidence | Status |
|---|---|---|---|
| 1 | The fixtures contain the known bad records | `tests/fixtures/mini_complaints.csv` and `tests/fixtures/README.md` | passing |
| 2 | The quality gate detects them: `overall_status` FAIL | `test_csv_fixture_fails_the_quality_gate` in [test_results_2026-11-21.txt](evidence/test_results_2026-11-21.txt) | passing |
| 3 | The gate stops the run and publishes nothing | `test_quality_gate_failure_writes_evidence_but_no_curated_data` | passing |
| 4 | A defect entry is recorded | D-005 in [defect_log.md](defect_log.md) | passing |

## 4. Manual checks

| Check | When | Who | Evidence | Status |
|---|---|---|---|---|
| Clean-machine check #1: fresh clone, follow only the README | Sun 15 Nov | Charbel | GitHub Issues + `docs/evidence/clean_machine_check_1.md` | planned |
| Dashboard checklist: empty selection, invalid date range, missing category, database stopped (`docker compose stop mongo`), mobile width (about 400 px) | after dashboard version 1 (Sat 21 Nov) | Charbel with Perla | `docs/evidence/dashboard_checks.md` with screenshots | planned |
| Clean-machine check #2 (final): fresh clone, `make up`, `make pipeline-full`, `make pipeline-incremental`, open the dashboard; total time recorded | Tue 24 Nov | Charbel | `docs/evidence/clean_machine_check_2.md` | planned |
| Controlled rerun for the demo: the same incremental window run twice, MongoDB count unchanged | rehearsals (Sat 28 and Sun 29 Nov) | Joseph, Marwa | demo script, screenshots | planned |

## 5. Test run history

| Date | Command | Result | Evidence |
|---|---|---|---|
| Thu 12 Nov 2026 | `make test` | 26 passed | [test_results_2026-11-12.txt](evidence/test_results_2026-11-12.txt) |
| Sat 21 Nov 2026 | `make test` | 42 passed | [test_results_2026-11-21.txt](evidence/test_results_2026-11-21.txt) |
