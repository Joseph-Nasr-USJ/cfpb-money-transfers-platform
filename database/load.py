"""Load Spark-curated Parquet from MinIO into the MongoDB serving layer.

Run only after Spark has successfully written the curated snapshot and aggregates:
    docker compose run --rm pipeline python -m database.load --run-id 20261110T020000Z_api

The loader reads the complete current curated snapshot. It never reads raw CFPB data.
Complaint upserts are idempotent. Aggregate collections are staged before replacement.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime, time, timezone
from pathlib import PurePosixPath
from urllib.parse import urlparse

import pyarrow.dataset as ds
from pyarrow.fs import FileType, S3FileSystem
from bson.int64 import Int64
from pymongo import MongoClient, UpdateOne

from database.indexes import INDEX_SPECS


BATCH_SIZE = 5_000
CURATED_COMPLAINTS = "curated/complaints/domain=money_transfers_payments"
AGGREGATE_PATHS = {
    "agg_monthly": "curated/aggregates/agg_monthly",
    "agg_company_year": "curated/aggregates/agg_company_year",
}
DATE_FIELDS = ("date_received", "date_sent_to_company", "ingested_at")


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Required environment variable {name} is missing")
    return value


def get_filesystem() -> S3FileSystem:
    endpoint = urlparse(required_env("MINIO_ENDPOINT"))
    if endpoint.scheme not in ("http", "https") or not endpoint.netloc:
        raise ValueError("MINIO_ENDPOINT must be a full http(s) URL")
    return S3FileSystem(
        access_key=required_env("MINIO_ROOT_USER"),
        secret_key=required_env("MINIO_ROOT_PASSWORD"),
        endpoint_override=endpoint.netloc,
        scheme=endpoint.scheme,
        region="us-east-1",
    )


def object_path(relative_path: str) -> str:
    return str(PurePosixPath(required_env("MINIO_BUCKET")) / relative_path)


def read_json_object(fs: S3FileSystem, relative_path: str) -> dict:
    path = object_path(relative_path)
    info = fs.get_file_info(path)
    if info.type != FileType.File:
        raise FileNotFoundError(f"Required MinIO object not found: {path}")
    with fs.open_input_file(path) as stream:
        obj = json.loads(stream.read().decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return obj


def parquet_scanner(fs: S3FileSystem, relative_path: str):
    path = object_path(relative_path)
    info = fs.get_file_info(path)
    if info.type == FileType.NotFound:
        raise FileNotFoundError(f"Required curated Parquet directory not found: {path}")
    dataset = ds.dataset(path, filesystem=fs, format="parquet", partitioning="hive")
    if not dataset.files:
        raise ValueError(f"No Parquet files found under {path}")
    return dataset.scanner(batch_size=BATCH_SIZE, use_threads=True)


def to_bson_date(value, field: str):
    """Convert an Arrow date/timestamp to an explicit UTC datetime for BSON Date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid {field} value: {value!r}") from exc
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    raise TypeError(f"Unexpected type for {field}: {type(value).__name__}")


def safe_bson(value):
    """Convert Arrow Python values into ordinary BSON-friendly Python values."""
    if isinstance(value, dict):
        return {str(k): safe_bson(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_bson(v) for v in value]
    if isinstance(value, date):
        return to_bson_date(value, "date")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def make_complaint_document(row: dict) -> tuple[Int64, dict]:
    if row.get("complaint_id") is None:
        raise ValueError("Curated complaint without complaint_id")
    complaint_id = Int64(int(row["complaint_id"]))
    doc = {key: safe_bson(value) for key, value in row.items() if key != "_id"}
    doc["complaint_id"] = complaint_id
    for field in DATE_FIELDS:
        if field in doc:
            doc[field] = to_bson_date(doc[field], field)
    if doc.get("date_received") is None:
        raise ValueError(f"Complaint {complaint_id} is missing date_received")
    # Preserve all three canonical flat fields; nested lineage is additional.
    doc["lineage"] = {
        field: doc.get(field) for field in ("source_type", "ingest_run_id", "ingested_at")
    }
    return complaint_id, doc


def upsert_complaints(db, scanner) -> int:
    total_rows = 0
    for batch in scanner.to_batches():
        rows = batch.to_pylist()
        if not rows:
            continue
        operations = []
        for row in rows:
            complaint_id, doc = make_complaint_document(row)
            operations.append(UpdateOne({"_id": complaint_id}, {"$set": doc}, upsert=True))
        db.complaints.bulk_write(operations, ordered=False)
        total_rows += len(rows)
        print(f"Upserted {total_rows:,} curated rows", flush=True)
    if not total_rows:
        raise ValueError("Curated complaint snapshot is empty; refusing to mark load successful")
    return total_rows


def stage_aggregate(db, fs: S3FileSystem, name: str, relative_path: str, run_id: str) -> tuple[str, int, int]:
    suffix = re.sub(r"[^a-zA-Z0-9_]", "_", run_id)
    temp_name = f"{name}_staging_{suffix}"
    db.drop_collection(temp_name)  # Only this run's temporary staging data.
    collection = db[temp_name]
    inserted = 0
    complaint_total = 0
    try:
        for batch in parquet_scanner(fs, relative_path).to_batches():
            rows = [{k: safe_bson(v) for k, v in row.items()} for row in batch.to_pylist()]
            if not rows:
                continue
            for row in rows:
                count = row.get("complaint_count")
                if not isinstance(count, int) or count < 0:
                    raise ValueError(f"Invalid complaint_count in {name}: {count!r}")
                complaint_total += count
            collection.insert_many(rows, ordered=False)
            inserted += len(rows)
        if inserted == 0:
            raise ValueError(f"{name} was empty; refusing to replace the active collection")
        # Create indexes on staging before rename, so replacement keeps its indexes.
        for index_name, keys in INDEX_SPECS.get(name, []):
            collection.create_index(keys, name=index_name)
        print(f"Staged {name}: {inserted:,} rows, {complaint_total:,} complaints", flush=True)
        return temp_name, inserted, complaint_total
    except Exception:
        db.drop_collection(temp_name)
        raise


def iso_fields_to_dates(document: dict, fields: tuple[str, ...]) -> dict:
    result = dict(document)
    for field in fields:
        if field in result and result[field] is not None:
            result[field] = to_bson_date(result[field], field)
    return result


def load(run_id: str) -> None:
    fs = get_filesystem()
    # Validate run metadata before touching the serving collections.
    run_log = read_json_object(fs, f"logs/ingestion/run_id={run_id}.json")
    quality = read_json_object(fs, f"quality/run_id={run_id}/quality_report.json")
    if run_log.get("run_id") != run_id or quality.get("run_id") != run_id:
        raise ValueError("Run ID in stored metadata does not match --run-id")
    if quality.get("quality_gate") == "stopped":
        raise ValueError("Spark quality gate stopped; MongoDB load aborted")
    if run_log.get("outcome") not in ("success", "skipped_identical"):
        raise ValueError(f"Ingestion run outcome is not successful: {run_log.get('outcome')!r}")

    with MongoClient(required_env("MONGO_URI"), serverSelectionTimeoutMS=10_000) as client:
        client.admin.command("ping")
        db = client[required_env("MONGO_DB")]
        # Read the *complete* latest curated snapshot, not just the newest raw API page.
        curated_count = upsert_complaints(db, parquet_scanner(fs, CURATED_COMPLAINTS))
        mongo_count = db.complaints.count_documents({})
        if curated_count != mongo_count:
            raise ValueError(
                f"Integrity check failed: curated snapshot={curated_count:,}, "
                f"MongoDB complaints={mongo_count:,}; investigate before advancing high-water mark"
            )

        staged = []
        try:
            for name, source in AGGREGATE_PATHS.items():
                temp, _, aggregate_total = stage_aggregate(db, fs, name, source, run_id)
                staged.append(temp)
                if aggregate_total != curated_count:
                    raise ValueError(
                        f"{name} total={aggregate_total:,}, curated snapshot={curated_count:,}"
                    )
            # rename is atomic *per collection*; the two renames are not one transaction.
            for (name, _source), temp in zip(AGGREGATE_PATHS.items(), staged):
                db[temp].rename(name, dropTarget=True)
                print(f"Published {name} from {temp}", flush=True)
        finally:
            for temp in staged:
                if temp in db.list_collection_names():
                    db.drop_collection(temp)

        quality_doc = iso_fields_to_dates(quality, ("generated_at",))
        quality_doc.pop("_id", None)
        db.quality_reports.update_one({"_id": run_id}, {"$set": quality_doc}, upsert=True)

        run_doc = iso_fields_to_dates(run_log, ("started_at", "finished_at"))
        run_doc.pop("_id", None)
        run_doc.update({
            "mongo_count_after": mongo_count,
            "mongo_loaded_at": datetime.now(timezone.utc),
            "mongo_load_status": "success",
        })
        db.pipeline_runs.update_one({"_id": run_id}, {"$set": run_doc}, upsert=True)
        print(f"Load completed: {mongo_count:,} unique complaints; run_id={run_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load curated Parquet into MongoDB")
    parser.add_argument("--run-id", required=True, help="Existing successful Spark/ingestion run ID")
    args = parser.parse_args()
    try:
        load(args.run_id)
    except Exception as exc:
        print(f"ERROR: MongoDB load failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
