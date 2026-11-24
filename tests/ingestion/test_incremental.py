"""Tests for ingestion/incremental.py with a mocked CFPB API (no internet needed).

FakeApi imitates what we measured on the live API on 20 Nov 2026: results sorted by
created date (newest first), each hit carrying "sort": [epoch_ms, "complaint_id"], and
search_after = "<epoch_ms>_<complaint_id>" returning the next page. A "broken" mode
imitates the frm offset, which returns the same first page again.
"""
import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from ingestion import incremental

API = "https://api.example.test/search/api/v1/"
MT = "Money transfer, virtual currency, or money service"


def complaint(i: int) -> dict:
    received = datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(hours=i)
    return {
        "_source": {"complaint_id": str(30_000_000 + i), "product": MT,
                    "sub_product": "Mobile or digital wallet", "issue": "Fraud or scam",
                    "date_received": received.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "date_sent_to_company": received.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "timely": "Yes", "company": "Example Pay Inc.", "state": "CA"},
        "sort": [int(received.timestamp() * 1000), str(30_000_000 + i)],
    }


class FakeApi:
    def __init__(self, count: int, broken: bool = False, fail_first: int = 0, fail_status: int = 500):
        self.hits = sorted((complaint(i) for i in range(count)), key=lambda h: h["sort"], reverse=True)
        self.broken, self.fail_first, self.fail_status = broken, fail_first, fail_status
        self.requests = []

    def __call__(self, request):
        query = parse_qs(urlparse(request.url).query)
        self.requests.append(query)
        if self.fail_first > 0:
            self.fail_first -= 1
            return self.fail_status, {"Retry-After": "1"} if self.fail_status == 429 else {}, "busy"
        size = int(query["size"][0])
        start = 0
        if "search_after" in query and not self.broken:
            marker = query["search_after"][0]
            start = next(i for i, h in enumerate(self.hits) if "_".join(map(str, h["sort"])) == marker) + 1
        body = {"hits": {"total": {"value": len(self.hits), "relation": "eq"},
                         "hits": self.hits[start:start + size]},
                "_meta": {"last_updated": "2026-11-19T12:00:00-05:00", "last_indexed": "2026-11-20T12:00:00-05:00",
                          "total_record_count": 19316897, "is_data_stale": False}}
        return 200, {}, json.dumps(body)


@pytest.fixture
def env(monkeypatch, fake_minio):
    monkeypatch.setenv("CFPB_API_URL", API)
    monkeypatch.setenv("API_PAGE_SIZE", "100")
    monkeypatch.setenv("API_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("API_MAX_RETRIES", "3")
    monkeypatch.setenv("OVERLAP_DAYS", "21")
    monkeypatch.setattr(incremental.time, "sleep", lambda seconds: None)
    return fake_minio


def stored_log(fake_minio, run_id):
    return json.loads(fake_minio.objects[f"logs/ingestion/run_id={run_id}.json"])


def test_product_filters_come_from_the_mapping_file():
    assert incremental.product_filters() == [MT, "Money transfers", "Virtual currency", "Prepaid card•Mobile wallet"]


def test_window_is_high_water_mark_minus_overlap_until_today():
    start, end = incremental.compute_window({"date_received_max": "2026-11-10"}, date(2026, 11, 20), 21)
    assert (start, end) == (date(2026, 10, 20), date(2026, 11, 20))


@responses.activate
def test_known_window_builds_the_right_request(env):
    api = FakeApi(5)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 10))

    query = api.requests[0]
    assert query["product"] == incremental.product_filters()
    assert query["date_received_min"] == ["2026-11-01"]
    assert query["date_received_max"] == ["2026-11-11"]          # end + 1 day: end day always included
    assert query["size"] == ["100"] and query["sort"] == ["created_date_desc"]
    assert "frm" not in query and "format" not in query            # never offset paging or export mode
    assert log["window"] == {"start": "2026-11-01", "end": "2026-11-10"}
    assert log["outcome"] == "success" and log["record_count"] == 5


@responses.activate
def test_pagination_uses_search_after_and_stops_on_the_last_page(env):
    api = FakeApi(250)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["record_count"] == 250
    assert log["pagination"]["pages_fetched"] == 3                 # 100 + 100 + 50
    assert len(api.requests) == 3
    assert "search_after" not in api.requests[0]
    assert api.requests[1]["search_after"][0] == "_".join(map(str, api.hits[99]["sort"]))
    prefix = f"raw/cfpb/api/ingest_date={log['run_id'][:4]}-{log['run_id'][4:6]}-{log['run_id'][6:8]}/run_id={log['run_id']}/"
    assert log["raw_paths"] == [f"{prefix}response_{n}.json" for n in (1, 2, 3)]
    assert all(path in env.objects for path in log["raw_paths"])  # every page saved raw
    assert log["pagination"]["expected_total"] == 250
    assert log["source_meta"]["last_indexed"] == "2026-11-20T12:00:00-05:00"
    assert log["high_water_mark_next"]["date_received_max"] == "2026-11-11"
    assert stored_log(env, log["run_id"])["outcome"] == "success"


@responses.activate
def test_exact_multiple_of_page_size_ends_with_an_empty_page(env):
    api = FakeApi(200)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["record_count"] == 200 and log["pagination"]["pages_fetched"] == 2
    assert len(api.requests) == 3                                  # third request returns no hits


@responses.activate
def test_raw_page_is_stored_byte_for_byte(env):
    api = FakeApi(3)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    stored = json.loads(env.objects[log["raw_paths"][0]])
    assert [h["_source"]["complaint_id"] for h in stored["hits"]["hits"]] == [h["_source"]["complaint_id"] for h in api.hits]


@responses.activate
def test_pagination_that_repeats_the_same_page_is_detected(env):
    """The behaviour we measured for frm: the same page again. The run must stop, never loop."""
    api = FakeApi(250, broken=True)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "failed"
    assert "not advancing" in log["http"]["errors"][-1]
    assert len(api.requests) == 2


@responses.activate
def test_empty_window_gives_outcome_empty(env):
    responses.add_callback(responses.GET, API, callback=FakeApi(0))

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 2))

    assert log["outcome"] == "empty" and log["record_count"] == 0
    assert incremental.main(["--start", "2026-11-01", "--end", "2026-11-02"]) == 0


@responses.activate
def test_server_error_then_success_is_retried(env):
    api = FakeApi(5, fail_first=2)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "success" and log["http"]["retries"] == 2


@responses.activate
def test_server_error_forever_stops_after_max_retries(env):
    api = FakeApi(5, fail_first=99)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "failed"
    assert log["http"]["retries"] == 3 and len(api.requests) == 4  # 1 try + 3 retries, never forever
    assert incremental.main(["--start", "2026-11-01", "--end", "2026-11-20"]) == 1


@responses.activate
def test_rate_limit_429_respects_retry_after(env, monkeypatch):
    waits = []
    monkeypatch.setattr(incremental.time, "sleep", waits.append)
    api = FakeApi(5, fail_first=1, fail_status=429)
    responses.add_callback(responses.GET, API, callback=api)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "success" and waits == [1]            # Retry-After: 1 instead of 2 s


@responses.activate
def test_timeout_is_retried(env):
    calls = {"n": 0}
    api = FakeApi(5)

    def flaky(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.Timeout("read timed out")
        return api(request)

    responses.add_callback(responses.GET, API, callback=flaky)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "success" and log["http"]["retries"] == 1
    assert "Timeout" in log["http"]["errors"][0]


@responses.activate
def test_client_error_is_not_retried(env):
    responses.get(API, status=400, body="bad request")

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "failed" and log["http"]["retries"] == 0
    assert len(responses.calls) == 1


@responses.activate
def test_failed_run_resumes_from_its_last_saved_page(env):
    """A run stopped after 2 of 3 pages: --resume fetches only page 3 with the saved search_after."""
    api = FakeApi(250)
    responses.add_callback(responses.GET, API, callback=api)
    stopped = incremental.new_log("20261120T020000Z_api", incremental.settings(),
                                  {"product": [MT], "date_received_min": "2026-11-01", "date_received_max": "2026-11-21"},
                                  date(2026, 11, 1), date(2026, 11, 20), {"source": "test"})
    stopped["outcome"] = "failed"
    stopped["pagination"].update(pages_fetched=2, last_offset=200, expected_total=250,
                                 search_after="_".join(map(str, api.hits[199]["sort"])))
    stopped["seen_ids"] = [h["_source"]["complaint_id"] for h in api.hits[:200]]
    stopped["record_count"] = 200
    incremental.save_log(stopped)

    resumed = incremental.run(resume_run_id="20261120T020000Z_api")

    assert resumed["outcome"] == "success" and resumed["record_count"] == 250
    assert resumed["pagination"]["pages_fetched"] == 3
    assert len(api.requests) == 1                                   # only the missing page was fetched
    assert "raw/cfpb/api/ingest_date=2026-11-20/run_id=20261120T020000Z_api/response_3.json" in env.objects


def test_a_successful_run_cannot_be_resumed(env):
    done = incremental.new_log("20261120T030000Z_api", incremental.settings(), {"product": [MT]},
                               date(2026, 11, 1), date(2026, 11, 20), {})
    done["outcome"] = "success"
    incremental.save_log(done)
    refused = incremental.run(resume_run_id="20261120T030000Z_api")
    assert refused["outcome"] == "failed" and refused["run_id"] != "20261120T030000Z_api"
    assert stored_log(env, "20261120T030000Z_api")["outcome"] == "success"   # finished log untouched


def test_bootstrap_uses_the_latest_historical_manifest(env):
    env.objects["raw/cfpb/full_load/ingest_date=2026-11-20/manifest.json"] = json.dumps(
        {"run_id": "20261120T140000Z_full", "max_date_received": "2026-11-18", "max_complaint_id": 30690627}).encode()
    hwm = incremental.bootstrap_high_water_mark()
    assert hwm["date_received_max"] == "2026-11-18" and hwm["run_id"] == "20261120T140000Z_full"


def test_without_high_water_mark_or_historical_load_the_run_fails_clearly(env):
    log = incremental.run()
    assert log["outcome"] == "failed"
    assert "make ingest-full" in log["http"]["errors"][-1]


@responses.activate
def test_page_cut_off_mid_transfer_is_retried(env, monkeypatch):
    api = FakeApi(5)
    calls = {"n": 0}

    def cut_once(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.exceptions.ChunkedEncodingError("Connection broken: IncompleteRead")
        return api(request)

    responses.add_callback(responses.GET, API, callback=cut_once)

    log = incremental.run(date(2026, 11, 1), date(2026, 11, 20))

    assert log["outcome"] == "success" and log["http"]["retries"] == 1
