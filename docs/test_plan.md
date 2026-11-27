# Test plan

Owner: Charbel Mazraani. Each test is written by the owner of its component; this file tracks every test level the brief requires, who owns it, where it lives and its current status.

**Run all automated tests:** `make test` (pytest inside the pipeline container, so every machine uses the same Python, Java and Spark versions). Each run is saved as evidence in `docs/evidence/test_results_YYYY-MM-DD.txt`.

**Status values:** `passing` (on `main`, green in the last run), `failing` (on `main`, red in the last run; a defect is open in [defect_log.md](defect_log.md)), `planned` (not written yet). Test names marked *proposed* are suggestions; the owner may rename them and this file is updated when the test is merged.

Last update: Fri 27 Nov 2026 (test inventory rewritten with the real test names).

## 1. Test levels required by the brief

| Level | What the tests must show | Owner | Location | Status |
|---|---|---|---|---|
| Collector | Pagination, timeouts, bounded retries, date window with high-water mark and overlap, complete run log, raw files never overwritten, resume after failure | Marwa Zeineddine | `tests/ingestion/` | passing (7 test files, about 70 tests) |
| Transformation | Explicit schema, standard column names, trimmed strings, date parsing and invalid dates, Yes/No and missing values, domain filter, deduplication by Complaint ID with tie-break, derived fields, quarantine | Joseph Nasr | `tests/processing/` | passing (26 tests in the transformation files, plus 6 for the Spark job) |
| Data quality | Six dimensions (uniqueness, completeness, validity, consistency, freshness, reconciliation) with the fixed thresholds; the quality gate stops a bad run; the known bad fixture records are caught (defect D-005) | Joseph Nasr | `tests/processing/test_quality.py` | passing (12 tests) |
| Database | Upsert or bulk load is idempotent, `_id` = complaint_id, native dates, indexes on the dashboard filters, aggregation queries return the expected result | Christopher Al Hassrouty | `tests/database/` | passing (6 test files, about 14 tests) |
| Dashboard | Query functions return aggregates only, empty selection, invalid date range, missing category, database unavailable | Perla Boustany | `tests/dashboard/` + manual checklist | passing (2 test files; `test_db.py` is skipped in the pipeline image because streamlit is not installed there); manual checklist still to do |
| End-to-end | A small sample goes raw → curated → MongoDB → query function and the counts reconcile at every layer; a repeated run creates no duplicates | Charbel Mazraani with Joseph Nasr | `tests/e2e/test_pipeline_sample.py` | planned |

## 2. Test inventory

Test names are the ones in the test files on `main`; the statuses come from the latest recorded run (section 5).

### Collector and processing chain (Marwa Zeineddine)

| ID | Test | File | Status |
|---|---|---|---|
| C-01 | `test_successful_load_writes_raw_files_manifest_and_log` | `tests/ingestion/test_historical.py` | passing |
| C-02 | `test_server_error_then_success_is_retried` | `tests/ingestion/test_historical.py` | passing |
| C-03 | `test_persistent_server_error_stops_after_max_retries` | `tests/ingestion/test_historical.py` | passing |
| C-04 | `test_not_found_is_not_retried` | `tests/ingestion/test_historical.py` | passing |
| C-05 | `test_timeout_is_retried_then_logged` | `tests/ingestion/test_historical.py` | passing |
| C-06 | `test_interrupted_download_resumes_with_range` | `tests/ingestion/test_historical.py` | passing |
| C-07 | `test_same_day_rerun_with_identical_file_uploads_nothing` | `tests/ingestion/test_historical.py` | passing |
| C-08 | `test_same_day_rerun_with_different_file_fails_without_overwriting` | `tests/ingestion/test_historical.py` | passing |
| C-09 | `test_main_prints_run_id_last_and_returns_exit_code` | `tests/ingestion/test_historical.py` | passing |
| C-10 | `test_sends_the_default_requests_user_agent` | `tests/ingestion/test_historical.py` | passing |
| C-11 | `test_connection_dropped_mid_download_resumes_and_finishes` | `tests/ingestion/test_historical.py` | passing |
| C-12 | `test_connection_that_drops_without_progress_gives_up` | `tests/ingestion/test_historical.py` | passing |
| C-13 | `test_same_day_rerun_completes_a_partial_upload` | `tests/ingestion/test_historical.py` | passing |
| C-14 | `test_partial_upload_of_a_different_file_is_not_overwritten` | `tests/ingestion/test_historical.py` | passing |
| C-15 | `test_product_filters_come_from_the_mapping_file` | `tests/ingestion/test_incremental.py` | passing |
| C-16 | `test_window_is_high_water_mark_minus_overlap_until_today` | `tests/ingestion/test_incremental.py` | passing |
| C-17 | `test_known_window_builds_the_right_request` | `tests/ingestion/test_incremental.py` | passing |
| C-18 | `test_pagination_uses_search_after_and_stops_on_the_last_page` | `tests/ingestion/test_incremental.py` | passing |
| C-19 | `test_exact_multiple_of_page_size_ends_with_an_empty_page` | `tests/ingestion/test_incremental.py` | passing |
| C-20 | `test_raw_page_is_stored_byte_for_byte` | `tests/ingestion/test_incremental.py` | passing |
| C-21 | `test_pagination_that_repeats_the_same_page_is_detected` | `tests/ingestion/test_incremental.py` | passing |
| C-22 | `test_empty_window_gives_outcome_empty` | `tests/ingestion/test_incremental.py` | passing |
| C-23 | `test_server_error_then_success_is_retried` | `tests/ingestion/test_incremental.py` | passing |
| C-24 | `test_server_error_forever_stops_after_max_retries` | `tests/ingestion/test_incremental.py` | passing |
| C-25 | `test_rate_limit_429_respects_retry_after` | `tests/ingestion/test_incremental.py` | passing |
| C-26 | `test_timeout_is_retried` | `tests/ingestion/test_incremental.py` | passing |
| C-27 | `test_client_error_is_not_retried` | `tests/ingestion/test_incremental.py` | passing |
| C-28 | `test_failed_run_resumes_from_its_last_saved_page` | `tests/ingestion/test_incremental.py` | passing |
| C-29 | `test_a_successful_run_cannot_be_resumed` | `tests/ingestion/test_incremental.py` | passing |
| C-30 | `test_bootstrap_uses_the_latest_historical_manifest` | `tests/ingestion/test_incremental.py` | passing |
| C-31 | `test_without_high_water_mark_or_historical_load_the_run_fails_clearly` | `tests/ingestion/test_incremental.py` | passing |
| C-32 | `test_page_cut_off_mid_transfer_is_retried` | `tests/ingestion/test_incremental.py` | passing |
| C-33 | `test_object_exists` | `tests/ingestion/test_minio_utils.py` | passing |
| C-34 | `test_object_exists_raises_on_other_errors` | `tests/ingestion/test_minio_utils.py` | passing |
| C-35 | `test_write_and_read_json_round_trip` | `tests/ingestion/test_minio_utils.py` | passing |
| C-36 | `test_refuses_to_overwrite_without_flag` | `tests/ingestion/test_minio_utils.py` | passing |
| C-37 | `test_raw_objects_are_never_overwritten` | `tests/ingestion/test_minio_utils.py` | passing |
| C-38 | `test_upload_and_download_file` | `tests/ingestion/test_minio_utils.py` | passing |
| C-39 | `test_list_keys_sorted_by_prefix` | `tests/ingestion/test_minio_utils.py` | passing |
| C-40 | `test_sha256_of_object_matches_the_content` | `tests/ingestion/test_minio_utils.py` | passing |
| C-41 | `test_steps_run_in_order_spark_load_then_high_water_mark` | `tests/ingestion/test_pipeline.py` | passing |
| C-42 | `test_full_load_run_uses_the_full_load_source` | `tests/ingestion/test_pipeline.py` | passing |
| C-43 | `test_failed_spark_stops_the_chain_before_load_and_high_water_mark` | `tests/ingestion/test_pipeline.py` | passing |
| C-44 | `test_failed_load_stops_before_the_high_water_mark` | `tests/ingestion/test_pipeline.py` | passing |
| C-45 | `test_pending_processes_unprocessed_runs_oldest_first` | `tests/ingestion/test_pipeline.py` | passing |
| C-46 | `test_same_day_identical_full_load_is_not_processed_twice` | `tests/ingestion/test_pipeline.py` | passing |
| C-47 | `test_a_failing_run_is_retried_at_most_max_attempts` | `tests/ingestion/test_pipeline.py` | passing |
| C-48 | `test_incremental_mode_collects_with_python_then_processes` | `tests/ingestion/test_pipeline.py` | passing |
| C-49 | `test_failed_collection_processes_nothing` | `tests/ingestion/test_pipeline.py` | passing |
| C-50 | `test_running_lock_blocks_a_second_chain` | `tests/ingestion/test_pipeline.py` | passing |
| C-51 | `test_abandoned_lock_is_replaced` | `tests/ingestion/test_pipeline.py` | passing |
| C-52 | `test_lock_is_released_even_after_a_failure` | `tests/ingestion/test_pipeline.py` | passing |
| C-53 | `test_process_mode_requires_a_run_id` | `tests/ingestion/test_pipeline.py` | passing |
| C-54 | `test_domain_rules_follow_product_mapping` | `tests/ingestion/test_sample.py` | passing |
| C-55 | `test_allocation_is_proportional_with_a_floor_and_exact_total` | `tests/ingestion/test_sample.py` | passing |
| C-56 | `test_small_domain_is_kept_whole` | `tests/ingestion/test_sample.py` | passing |
| C-57 | `test_build_sample_filters_domain_and_spreads_years` | `tests/ingestion/test_sample.py` | passing |
| C-58 | `test_same_seed_gives_the_same_sample` | `tests/ingestion/test_sample.py` | passing |
| C-59 | `test_main_reads_latest_manifest_from_minio_and_writes_files` | `tests/ingestion/test_sample.py` | passing |
| C-60 | `test_no_previous_collection_runs_now` | `tests/ingestion/test_scheduler.py` | passing |
| C-61 | `test_missed_run_while_the_computer_was_off_runs_now` | `tests/ingestion/test_scheduler.py` | passing |
| C-62 | `test_recent_collection_waits_until_it_is_due` | `tests/ingestion/test_scheduler.py` | passing |
| C-63 | `test_failed_collections_do_not_count_as_done` | `tests/ingestion/test_scheduler.py` | passing |
| C-64 | `test_nifi_mode_only_processes_collected_runs` | `tests/ingestion/test_scheduler.py` | passing |
| C-65 | `test_python_mode_also_collects_every_schedule_hours` | `tests/ingestion/test_scheduler.py` | passing |
| C-66 | `test_unknown_collector_is_refused` | `tests/ingestion/test_scheduler.py` | passing |
| C-67 | `test_first_successful_run_creates_the_mark` | `tests/ingestion/test_update_hwm.py` | passing |
| C-68 | `test_mark_moves_forward` | `tests/ingestion/test_update_hwm.py` | passing |
| C-69 | `test_mark_never_moves_backwards` | `tests/ingestion/test_update_hwm.py` | passing |
| C-70 | `test_unsuccessful_runs_do_not_move_the_mark` | `tests/ingestion/test_update_hwm.py` | passing |
| C-71 | `test_same_day_full_rerun_takes_values_from_the_manifest` | `tests/ingestion/test_update_hwm.py` | passing |
| C-72 | `test_manual_reset_is_recorded_with_its_reason` | `tests/ingestion/test_update_hwm.py` | passing |
| C-73 | `test_reset_without_reason_is_refused` | `tests/ingestion/test_update_hwm.py` | passing |

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

Thresholds are fixed before any result is seen (uniqueness 0 nulls and 0 duplicates; required fields at least 99.5% filled; invalid values WARN above 0.5% and FAIL above 2%; unmapped combinations listed; latest record at most 3 days old; raw = curated + quarantined + out_of_domain + duplicates_removed, and curated = MongoDB count). The code uses the V2 names freshness and reconciliation since Joseph's PR #32 (24 Nov); the freshness threshold key is `freshness_max_age_days`.

| ID | Test | File | Status |
|---|---|---|---|
| Q-01 | `test_csv_fixture_fails_the_quality_gate` (known bad records: invalid date, invalid state, negative interval, missing ID; defect D-005) | `tests/processing/test_quality.py` | passing |
| Q-02 | `test_api_fixture_counts_and_gate` | `tests/processing/test_quality.py` | passing |
| Q-03 | `test_clean_records_pass` | `tests/processing/test_quality.py` | passing |
| Q-04 | `test_duplicate_ids_fail_uniqueness` | `tests/processing/test_quality.py` | passing |
| Q-05 | `test_reconciliation_fails_when_counts_do_not_add_up` | `tests/processing/test_quality.py` | passing |
| Q-06 | `test_freshness_warns_on_old_data_and_records_the_ingestion_time` | `tests/processing/test_quality.py` | passing |
| Q-07 | `test_invalid_timely_value_is_counted` | `tests/processing/test_quality.py` | passing |
| Q-08 | `test_unmapped_sub_product_warns_consistency` | `tests/processing/test_quality.py` | passing |
| Q-09 | `test_threshold_rules` | `tests/processing/test_quality.py` | passing |
| Q-10 | `test_report_is_valid_json` | `tests/processing/test_quality.py` | passing |
| Q-11 | `test_empty_sub_issue_is_not_applicable_when_the_issue_has_no_sub_issues` | `tests/processing/test_quality.py` | passing |
| Q-12 | `test_empty_sub_issue_is_missing_when_the_same_issue_has_sub_issues` | `tests/processing/test_quality.py` | passing |

### Database (Christopher Al Hassrouty)

Unit tests use `mongomock` (in-memory MongoDB), so they run without the `mongo` container. Index coverage is shown by the measurement in [benchmark.md](evidence/benchmark.md), not by a unit test.

| ID | Test | File | Status |
|---|---|---|---|
| D-01 | `test_aggregate_totals_match_complaints` | `tests/database/test_aggregate_reconciliation.py` | passing |
| D-02 | `test_invalid_aggregate_count_is_rejected` | `tests/database/test_aggregate_reconciliation.py` | passing |
| D-03 | `test_empty_collections_return_empty_lists` | `tests/database/test_empty_queries.py` | passing |
| D-04 | `test_impossible_filters_return_empty_lists` | `tests/database/test_empty_queries.py` | passing |
| D-05 | `test_dates_stored_as_bson_dates` | `tests/database/test_loader_contract.py` | passing |
| D-06 | `test_duplicate_complaint_id_rejected` | `tests/database/test_loader_contract.py` | passing |
| D-07 | `test_empty_collections` | `tests/database/test_ml_queries.py` | passing |
| D-08 | `test_emerging_issues_filters` | `tests/database/test_ml_queries.py` | passing |
| D-09 | `test_state_clusters` | `tests/database/test_ml_queries.py` | passing |
| D-10 | `test_unsupported_filter` | `tests/database/test_ml_queries.py` | passing |
| D-11 | `test_stopped_quality_gate_aborts_before_mongodb` | `tests/database/test_quality_gate.py` | passing |
| D-12 | `test_allowed_quality_gates_reach_mongodb` | `tests/database/test_quality_gate.py` | passing |
| D-13 | `test_loading_twice_does_not_create_duplicates` (real-data proof in [idempotency.md](evidence/idempotency.md)) | `tests/database/test_upsert_idempotency.py` | passing |
| D-14 | `test_upsert_updates_existing_complaint` | `tests/database/test_upsert_idempotency.py` | passing |

### Dashboard (Perla Boustany)

Empty selection, invalid date range and basic layout are covered by the manual checklist (section 4), which is not yet recorded.

| ID | Test | File | Status |
|---|---|---|---|
| B-01 | `test_cache_hit` | `tests/dashboard/test_db.py` | skipped in the pipeline image (no streamlit) |
| B-02 | `test_cache_miss` | `tests/dashboard/test_db.py` | skipped in the pipeline image (no streamlit) |
| B-03 | `test_cache_uses_600_second_ttl` | `tests/dashboard/test_db.py` | skipped in the pipeline image (no streamlit) |
| B-04 | `test_redis_unavailable_falls_back_to_mongo` | `tests/dashboard/test_db.py` | skipped in the pipeline image (no streamlit) |
| B-05 | `test_monthly_totals` | `tests/dashboard/test_trends.py` | passing |
| B-06 | `test_month_order` | `tests/dashboard/test_trends.py` | passing |
| B-07 | `test_wallet_percentage` | `tests/dashboard/test_trends.py` | passing |
| B-08 | `test_invalid_months_are_excluded` | `tests/dashboard/test_trends.py` | passing |
| B-09 | `test_empty_monthly_data` | `tests/dashboard/test_trends.py` | passing |

### Analytics and machine learning (Perla Boustany)

The models only describe or diagnose past data; they never predict.

| ID | Test | File | Status |
|---|---|---|---|
| M-01 | `test_percentage` | `tests/analytics/test_calculations.py` | passing |
| M-02 | `test_percentage_zero_denominator` | `tests/analytics/test_calculations.py` | passing |
| M-03 | `test_percentage_change` | `tests/analytics/test_calculations.py` | passing |
| M-04 | `test_percentage_change_zero_previous` | `tests/analytics/test_calculations.py` | passing |
| M-05 | `test_rolling_share` | `tests/analytics/test_calculations.py` | passing |
| M-06 | `test_rolling_share_rejects_invalid_input` | `tests/analytics/test_calculations.py` | passing |
| M-07 | `test_complete_month_excludes_current_month` | `tests/analytics/test_calculations.py` | passing |
| M-08 | `test_complete_year` | `tests/analytics/test_calculations.py` | passing |
| M-09 | `test_q3_channel_summary_uses_counts` | `tests/analytics/test_calculations.py` | passing |
| M-10 | `test_q3_empty_data` | `tests/analytics/test_calculations.py` | passing |
| M-11 | `test_q4_timely_counts_not_double_counted` | `tests/analytics/test_calculations.py` | passing |
| M-12 | `test_q4_empty_data` | `tests/analytics/test_calculations.py` | passing |
| M-13 | `test_q5_state_totals_not_double_counted` | `tests/analytics/test_calculations.py` | passing |
| M-14 | `test_q5_preserves_unknown_state` | `tests/analytics/test_calculations.py` | passing |
| M-15 | `test_ml_24_complete_month_window` | `tests/analytics/test_calculations.py` | passing |
| M-16 | `test_ml_month_index` | `tests/analytics/test_calculations.py` | passing |
| M-17 | `test_linear_regression_detects_increasing_share` | `tests/analytics/test_ml_models.py` | passing |
| M-18 | `test_linear_regression_rejects_flat_share` | `tests/analytics/test_ml_models.py` | passing |
| M-19 | `test_kmeans_selects_valid_state_clusters` | `tests/analytics/test_ml_models.py` | passing |
| M-20 | `test_kmeans_uses_required_seed` | `tests/analytics/test_ml_models.py` | passing |

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
| Tue 24 Nov 2026 | `make test` | 159 passed, 1 skipped | [test_results_2026-11-24.txt](evidence/test_results_2026-11-24.txt) |
