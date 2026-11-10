"""Create the MinIO bucket used by the platform (run once by the minio-init service).

Safe to run many times: if the bucket already exists, nothing changes.
Settings come from environment variables (.env), never from code.
"""
import os
import sys
import time
from urllib.parse import urlparse

from minio import Minio

MAX_ATTEMPTS = 5
WAIT_SECONDS = 3


def main() -> int:
    endpoint = urlparse(os.environ["MINIO_ENDPOINT"])  # e.g. http://minio:9000
    bucket = os.environ["MINIO_BUCKET"]
    client = Minio(
        endpoint.netloc,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=endpoint.scheme == "https",
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if client.bucket_exists(bucket):
                print(f"Bucket '{bucket}' already exists.")
            else:
                client.make_bucket(bucket)
                print(f"Bucket '{bucket}' created.")
            return 0
        except Exception as exc:  # MinIO not ready yet, or wrong credentials in .env
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {exc}")
            time.sleep(WAIT_SECONDS)
    print(f"Could not create bucket '{bucket}' after {MAX_ATTEMPTS} attempts.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
