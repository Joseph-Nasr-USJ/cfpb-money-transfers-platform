"""Tests for ingestion/historical.py: download, resume, retries, manifest, run log, same-day rerun.

The CFPB server is mocked with `responses` and serves a tiny ZIP built in the test, so the
tests run in seconds without the real multi-GB file.
"""
import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
import requests
import responses

from ingestion import historical

URL = "https://files.example.test/ccdb/complaints.csv.zip"

# 3 complaints; the second has a quoted field with a comma AND a line break (one record, two text lines).
CSV_TEXT = (
    "Date received,Product,Issue,Company,Complaint ID\n"
    '2024-03-15,"Money transfer, virtual currency, or money service",Fraud or scam,Example Pay Inc.,9000001\n'
    '03/22/24,Money transfers,"Other transaction problem,\nsecond line",Global Remit LLC,9000007\n'
    "2016-05-02,Credit card,Fees or interest,Card Bank,9000020\n"
)


def make_zip(text=CSV_TEXT) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("complaints.csv", text)
    return buffer.getvalue()


@pytest.fixture
def env(monkeypatch, tmp_path, fake_minio):
    """Settings, a temporary work folder, no real waiting, and a clock that moves 1 s per call."""
    monkeypatch.setenv("CFPB_CSV_URL", URL)
    monkeypatch.setenv("API_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("API_MAX_RETRIES", "2")
    monkeypatch.setattr(historical, "WORK_DIR", tmp_path / "work")
    monkeypatch.setattr(historical.time, "sleep", lambda seconds: None)
    clock = {"now": datetime(2026, 11, 20, 14, 0, 0, tzinfo=timezone.utc)}

    def tick():
        clock["now"] += timedelta(seconds=1)
        return clock["now"]

    monkeypatch.setattr(historical, "utc_now", tick)
    return fake_minio


@responses.activate
def test_successful_load_writes_raw_files_manifest_and_log(env, tmp_path):
    payload = make_zip()
    responses.get(URL, body=payload, status=200, headers={"Content-Length": str(len(payload)), "ETag": '"v1"'})

    log = historical.run()

    prefix = "raw/cfpb/full_load/ingest_date=2026-11-20/"
    assert log["outcome"] == "success"
    assert env.objects[prefix + "complaints.csv.zip"] == payload                 # original kept unchanged
    assert env.objects[prefix + "complaints.csv"].decode() == CSV_TEXT
    manifest = json.loads(env.objects[prefix + "manifest.json"])
    assert manifest["sha256"] == hashlib.sha256(payload).hexdigest()
    assert manifest["size_bytes"] == len(payload)
    assert manifest["record_count"] == 3                                        # not 4 text lines
    assert manifest["source_url"] == URL
    assert manifest["max_date_received"] == "2024-03-22"                         # MM/dd/yy understood
    assert manifest["max_complaint_id"] == 9000020
    for field in ("download_started_at", "download_finished_at", "run_id"):
        assert manifest[field]
    stored_log = json.loads(env.objects[f"logs/ingestion/run_id={log['run_id']}.json"])
    assert stored_log["outcome"] == "success" and stored_log["record_count"] == 3
    assert stored_log["http"] == {"last_status": 200, "retries": 0, "errors": []}
    assert log["run_id"].endswith("_full")
    assert not list((tmp_path / "work").iterdir())                              # local cache cleaned


@responses.activate
def test_server_error_then_success_is_retried(env):
    payload = make_zip()
    responses.get(URL, status=503)
    responses.get(URL, body=payload, status=200, headers={"Content-Length": str(len(payload))})

    log = historical.run()

    assert log["outcome"] == "success"
    assert log["http"]["retries"] == 1
    assert len(log["http"]["errors"]) == 1


@responses.activate
def test_persistent_server_error_stops_after_max_retries(env):
    responses.get(URL, status=500)

    log = historical.run()

    assert log["outcome"] == "failed"
    assert log["http"]["retries"] == 2                                          # API_MAX_RETRIES, never forever
    assert len(responses.calls) == 3                                            # first try + 2 retries
    assert f"logs/ingestion/run_id={log['run_id']}.json" in env.objects         # failure is logged too
    assert not any(key.startswith("raw/") for key in env.objects)


@responses.activate
def test_not_found_is_not_retried(env):
    responses.get(URL, status=404)

    log = historical.run()

    assert log["outcome"] == "failed"
    assert log["http"]["retries"] == 0
    assert len(responses.calls) == 1


@responses.activate
def test_timeout_is_retried_then_logged(env):
    responses.get(URL, body=requests.Timeout("read timed out"))

    log = historical.run()

    assert log["outcome"] == "failed"
    assert log["http"]["retries"] == 2
    assert "Timeout" in log["http"]["errors"][0]


@responses.activate
def test_interrupted_download_resumes_with_range(env, tmp_path):
    payload = make_zip()
    half = len(payload) // 2
    work = tmp_path / "work"
    work.mkdir()
    (work / "complaints.csv.zip.part").write_bytes(payload[:half])               # left by a broken run
    (work / "complaints.csv.zip.part.validator.json").write_text(json.dumps({"validator": '"v1"'}))

    def partial(request):
        assert request.headers["Range"] == f"bytes={half}-"
        assert request.headers["If-Range"] == '"v1"'
        headers = {"Content-Range": f"bytes {half}-{len(payload) - 1}/{len(payload)}"}
        return 206, headers, payload[half:]

    responses.add_callback(responses.GET, URL, callback=partial)

    log = historical.run()

    assert log["outcome"] == "success"
    assert log["sha256"] == hashlib.sha256(payload).hexdigest()                  # same as a full download


@responses.activate
def test_same_day_rerun_with_identical_file_uploads_nothing(env):
    payload = make_zip()
    responses.get(URL, body=payload, status=200, headers={"Content-Length": str(len(payload))})
    first = historical.run()
    before = dict(env.objects)

    second = historical.run()

    assert first["outcome"] == "success"
    assert second["outcome"] == "skipped_identical"
    assert second["record_count"] == 3
    raw_before = {k: v for k, v in before.items() if k.startswith("raw/")}
    raw_after = {k: v for k, v in env.objects.items() if k.startswith("raw/")}
    assert raw_after == raw_before                                              # raw zone untouched
    assert f"logs/ingestion/run_id={second['run_id']}.json" in env.objects      # but the run is logged


@responses.activate
def test_same_day_rerun_with_different_file_fails_without_overwriting(env):
    first_payload, second_payload = make_zip(), make_zip(CSV_TEXT + "2024-07-01,Money transfers,X,Y,9000099\n")
    responses.get(URL, body=first_payload, status=200)
    historical.run()
    responses.replace(responses.GET, URL, body=second_payload, status=200)

    log = historical.run()

    assert log["outcome"] == "failed"
    prefix = "raw/cfpb/full_load/ingest_date=2026-11-20/"
    assert env.objects[prefix + "complaints.csv.zip"] == first_payload          # never overwritten


@responses.activate
def test_main_prints_run_id_last_and_returns_exit_code(env, capsys):
    payload = make_zip()
    responses.get(URL, body=payload, status=200)

    assert historical.main() == 0
    last_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert last_line.endswith("_full")


@responses.activate
def test_sends_the_default_requests_user_agent(env):
    """The CFPB firewall (Akamai) blocks custom and fake-browser agents; it accepts the requests default."""
    payload = make_zip()
    responses.get(URL, body=payload, status=200)

    historical.run()

    assert responses.calls[0].request.headers["User-Agent"].startswith("python-requests/")


class BrokenStream:
    """A response whose connection drops after `cut` bytes, like the real 20 Nov failure."""

    def __init__(self, data, status=200, headers=None, cut=None):
        self.data, self.status_code, self.cut = data, status, cut
        self.headers = headers or {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, chunk_size=1):
        sent = self.data if self.cut is None else self.data[:self.cut]
        for i in range(0, len(sent), 7):
            yield sent[i:i + 7]
        if self.cut is not None:
            raise requests.exceptions.ChunkedEncodingError(
                f"Connection broken: IncompleteRead({self.cut} bytes read, {len(self.data) - self.cut} more expected)")


def test_connection_dropped_mid_download_resumes_and_finishes(env, monkeypatch):
    """Regression test for the 20 Nov failure: ChunkedEncodingError was not retried."""
    payload = make_zip()
    third = len(payload) // 3
    calls = []

    def fake_get(url, headers=None, **kwargs):
        calls.append(dict(headers or {}))
        start = int(headers["Range"].split("=")[1].rstrip("-")) if headers and "Range" in headers else 0
        rest = payload[start:]
        if start == 0:
            return BrokenStream(payload, headers={"Content-Length": str(len(payload)), "ETag": '"v1"'}, cut=third)
        if start == third:
            return BrokenStream(rest, 206, {"Content-Range": f"bytes {start}-{len(payload) - 1}/{len(payload)}"},
                                cut=third)                                  # drops again, still progress
        return BrokenStream(rest, 206, {"Content-Range": f"bytes {start}-{len(payload) - 1}/{len(payload)}"})

    monkeypatch.setattr(historical.requests, "get", fake_get)

    log = historical.run()

    assert log["outcome"] == "success"
    assert log["sha256"] == hashlib.sha256(payload).hexdigest()
    assert log["http"]["resumes"] == 2 and log["http"]["retries"] == 0
    assert [c.get("Range") for c in calls] == [None, f"bytes={third}-", f"bytes={2 * third}-"]
    assert all(c.get("If-Range") == '"v1"' for c in calls[1:])


def test_connection_that_drops_without_progress_gives_up(env, monkeypatch):
    payload = make_zip()

    def fake_get(url, headers=None, **kwargs):
        return BrokenStream(payload, cut=0)                                 # breaks before any byte

    monkeypatch.setattr(historical.requests, "get", fake_get)

    log = historical.run()

    assert log["outcome"] == "failed"
    assert log["http"]["retries"] == 2                                      # API_MAX_RETRIES, then stop
    assert "ChunkedEncodingError" in log["http"]["errors"][0]
