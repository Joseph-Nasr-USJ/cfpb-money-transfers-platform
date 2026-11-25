"""Unit tests for ingestion/minio_utils.py with an in-memory fake of the MinIO client.

No MinIO server is needed: the fake stores objects in a dictionary.
"""
import io
import json
from types import SimpleNamespace

import pytest
from minio.error import S3Error

from ingestion import minio_utils


class FakeMinio:
    """The few MinIO client methods our helpers use, backed by a dict {key: bytes}."""

    def __init__(self):
        self.objects = {}

    def stat_object(self, bucket, key):
        if key not in self.objects:
            raise S3Error(None, "NoSuchKey", "not found", key, "req", "host")
        return SimpleNamespace(size=len(self.objects[key]))

    def fput_object(self, bucket, key, path, content_type=None):
        with open(path, "rb") as handle:
            self.objects[key] = handle.read()

    def put_object(self, bucket, key, stream, length, content_type=None):
        self.objects[key] = stream.read(length)

    def fget_object(self, bucket, key, path):
        with open(path, "wb") as handle:
            handle.write(self.objects[key])

    def get_object(self, bucket, key):
        return SimpleNamespace(read=io.BytesIO(self.objects[key]).read, close=lambda: None, release_conn=lambda: None)

    def list_objects(self, bucket, prefix="", recursive=True):
        return [SimpleNamespace(object_name=k) for k in self.objects if k.startswith(prefix)]


@pytest.fixture
def fake(monkeypatch):
    client = FakeMinio()
    monkeypatch.setenv("MINIO_BUCKET", "cfpb-lake")
    monkeypatch.setattr(minio_utils, "get_client", lambda: client)
    return client


def test_object_exists(fake):
    assert minio_utils.object_exists("logs/a.json") is False
    fake.objects["logs/a.json"] = b"{}"
    assert minio_utils.object_exists("logs/a.json") is True


def test_object_exists_raises_on_other_errors(monkeypatch, fake):
    def denied(bucket, key):
        raise S3Error(None, "AccessDenied", "denied", key, "req", "host")
    monkeypatch.setattr(fake, "stat_object", denied)
    with pytest.raises(S3Error):
        minio_utils.object_exists("logs/a.json")


def test_write_and_read_json_round_trip(fake):
    minio_utils.write_json({"run_id": "x", "record_count": 3}, "logs/ingestion/run_id=x.json")
    assert minio_utils.read_json("logs/ingestion/run_id=x.json") == {"run_id": "x", "record_count": 3}


def test_refuses_to_overwrite_without_flag(fake):
    minio_utils.write_json({"v": 1}, "state/high_water_mark.json")
    with pytest.raises(FileExistsError):
        minio_utils.write_json({"v": 2}, "state/high_water_mark.json")
    minio_utils.write_json({"v": 2}, "state/high_water_mark.json", overwrite=True)
    assert minio_utils.read_json("state/high_water_mark.json") == {"v": 2}


def test_raw_objects_are_never_overwritten(fake):
    key = "raw/cfpb/api/ingest_date=2026-11-17/run_id=x/response_1.json"
    minio_utils.upload_bytes(b"first", key)
    with pytest.raises(FileExistsError):
        minio_utils.upload_bytes(b"second", key, overwrite=True)
    assert fake.objects[key] == b"first"


def test_upload_and_download_file(fake, tmp_path):
    source = tmp_path / "in.csv"
    source.write_bytes(b"a,b\n1,2\n")
    minio_utils.upload_file(str(source), "raw/cfpb/full_load/ingest_date=2026-11-17/complaints.csv")
    target = tmp_path / "out.csv"
    minio_utils.download_file("raw/cfpb/full_load/ingest_date=2026-11-17/complaints.csv", str(target))
    assert target.read_bytes() == b"a,b\n1,2\n"


def test_list_keys_sorted_by_prefix(fake):
    fake.objects.update({"raw/b.json": b"", "raw/a.json": b"", "logs/c.json": b""})
    assert minio_utils.list_keys("raw/") == ["raw/a.json", "raw/b.json"]


def test_sha256_of_object_matches_the_content(fake):
    import hashlib
    fake.objects["raw/x.zip"] = b"abc" * 1000
    assert minio_utils.sha256_of_object("raw/x.zip", chunk_size=7) == hashlib.sha256(b"abc" * 1000).hexdigest()
