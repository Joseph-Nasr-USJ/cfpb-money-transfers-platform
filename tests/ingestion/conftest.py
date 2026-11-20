"""Shared test helpers for the ingestion tests: an in-memory MinIO and fixed settings.

No MinIO server and no internet are needed: MinIO is faked with a dictionary and HTTP calls
are mocked with the `responses` package in each test.
"""
import io
from types import SimpleNamespace

import pytest
from minio.error import S3Error

from ingestion import minio_utils


class FakeMinio:
    """The MinIO client methods our helpers use, backed by a dict {object_key: bytes}."""

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
def fake_minio(monkeypatch):
    client = FakeMinio()
    monkeypatch.setenv("MINIO_BUCKET", "cfpb-lake")
    monkeypatch.setattr(minio_utils, "get_client", lambda: client)
    return client
