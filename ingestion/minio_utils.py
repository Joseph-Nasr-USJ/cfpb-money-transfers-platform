"""MinIO helpers for the ingestion layer (raw zone, run logs and pipeline state).

All settings come from environment variables (.env), never from code:
MINIO_ENDPOINT (for example http://minio:9000), MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET.

Safety rule: objects under raw/ are immutable. The brief says source files are preserved
"without destructive modification", so these helpers refuse to overwrite any raw object,
even when overwrite=True is passed. Run logs and state files may be overwritten on purpose.
"""
import io
import json
import os
from functools import lru_cache
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

RAW_PREFIX = "raw/"
NOT_FOUND_CODES = {"NoSuchKey", "NoSuchObject", "NotFound", "ResourceNotFound"}


@lru_cache(maxsize=1)
def get_client() -> Minio:
    """Build one MinIO client from the environment (same logic as docker/minio_init.py)."""
    endpoint = urlparse(os.environ["MINIO_ENDPOINT"])  # e.g. http://minio:9000
    return Minio(
        endpoint.netloc,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=endpoint.scheme == "https",
    )


def bucket() -> str:
    """Name of the platform bucket (cfpb-lake)."""
    return os.environ["MINIO_BUCKET"]


def object_exists(object_key: str) -> bool:
    """True if the object exists in the bucket, False if it does not."""
    try:
        get_client().stat_object(bucket(), object_key)
        return True
    except S3Error as exc:
        if exc.code in NOT_FOUND_CODES:
            return False
        raise  # wrong credentials, missing bucket...: a real error, never hidden


def _check_can_write(object_key: str, overwrite: bool) -> None:
    """Refuse to replace an existing object, and never replace anything under raw/."""
    if not object_exists(object_key):
        return
    if object_key.startswith(RAW_PREFIX):
        raise FileExistsError(f"Raw objects are immutable and already exist: {object_key}")
    if not overwrite:
        raise FileExistsError(f"Object already exists (pass overwrite=True to replace it): {object_key}")


def upload_file(local_path: str, object_key: str, content_type: str = "application/octet-stream",
                overwrite: bool = False) -> str:
    """Upload a local file. Large files are sent in parts by the MinIO client (never fully in memory)."""
    _check_can_write(object_key, overwrite)
    get_client().fput_object(bucket(), object_key, local_path, content_type=content_type)
    return object_key


def upload_bytes(data: bytes, object_key: str, content_type: str = "application/octet-stream",
                 overwrite: bool = False) -> str:
    """Upload a small in-memory payload, for example one API response page."""
    _check_can_write(object_key, overwrite)
    get_client().put_object(bucket(), object_key, io.BytesIO(data), length=len(data), content_type=content_type)
    return object_key


def download_file(object_key: str, local_path: str) -> str:
    """Download an object to a local path (used by the sampling script)."""
    get_client().fget_object(bucket(), object_key, local_path)
    return local_path


def read_json(object_key: str) -> dict:
    """Read a JSON object (manifest, run log, high-water mark)."""
    response = get_client().get_object(bucket(), object_key)
    try:
        return json.loads(response.read().decode("utf-8"))
    finally:
        response.close()
        response.release_conn()


def write_json(obj: dict, object_key: str, overwrite: bool = False) -> str:
    """Write a JSON object, pretty-printed so it is readable in the MinIO console."""
    data = json.dumps(obj, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    return upload_bytes(data, object_key, content_type="application/json", overwrite=overwrite)


def list_keys(prefix: str) -> list:
    """Every object key under a prefix, sorted (for example all manifests of the full load)."""
    objects = get_client().list_objects(bucket(), prefix=prefix, recursive=True)
    return sorted(obj.object_name for obj in objects)
