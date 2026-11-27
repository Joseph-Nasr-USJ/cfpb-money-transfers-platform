"""Spark job: raw CFPB records of one ingestion run -> curated complaints, quarantine, aggregates, quality report.

    spark-submit processing/spark_job.py --source full_load|api --run-id <run_id>
                 [--input <path>] [--lake-root <path>] [--ignore-quality-gate]

Exit codes: 0 success (or nothing to process), 1 quality gate FAIL or missing input, 2 wrong arguments.

Inputs (MinIO bucket from MINIO_BUCKET, default layout from the team contract):
    full_load: raw/cfpb/full_load/ingest_date=YYYY-MM-DD/complaints.csv
    api:       raw/cfpb/api/ingest_date=YYYY-MM-DD/run_id=<run_id>/response_*.json
    The ingest date and the ingestion time come from the run_id (YYYYMMDDTHHMMSSZ_<full|api>).
Outputs:
    curated/complaints/option=5/year=YYYY/month=MM/                          Parquet, merged with earlier runs
    curated/aggregates/agg_monthly/ and curated/aggregates/agg_company_year/  Parquet, rebuilt from all curated data
    quarantine/run_id=<run_id>/                                              Parquet, rejected records + reject_reason
    quality/run_id=<run_id>/quality_report.json

Curated data is never written when the quality gate fails (unless --ignore-quality-gate, development only).
Re-running the same run_id gives the same curated data: records are merged by complaint_id with the
deduplication tie-break, and only the year/month partitions touched by the run are rewritten.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # spark-submit only puts processing/ on the path
    sys.path.insert(0, str(REPO_ROOT))

from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

from processing import quality  # noqa: E402
from processing.paths import AGG_COMPANY_YEAR_DIR, AGG_MONTHLY_DIR, CURATED_DIR  # noqa: E402,F401
from processing import schema  # noqa: E402
from processing import transforms as t  # noqa: E402

RUN_ID_PATTERN = re.compile(r"^(\d{8})T(\d{6})Z_(full|api)$")
SOURCE_SUFFIX = {"full_load": "full", "api": "api"}
MAPPING_CSV = REPO_ROOT / "config" / "product_mapping.csv"
STATE_CODES_CSV = REPO_ROOT / "config" / "state_codes.csv"


# ---------- helpers ----------

def parse_run_id(run_id: str, source: str):
    """Return (ingest_date 'YYYY-MM-DD', ingested_at 'YYYY-MM-DD HH:MM:SS') or raise ValueError."""
    match = RUN_ID_PATTERN.match(run_id)
    if not match:
        raise ValueError(f"run_id '{run_id}' does not match YYYYMMDDTHHMMSSZ_full or YYYYMMDDTHHMMSSZ_api")
    day, time_part, suffix = match.groups()
    if suffix != SOURCE_SUFFIX[source]:
        raise ValueError(f"run_id '{run_id}' ends with _{suffix} but --source is {source}")
    stamp = datetime.strptime(day + time_part, "%Y%m%d%H%M%S")
    return stamp.strftime("%Y-%m-%d"), stamp.strftime("%Y-%m-%d %H:%M:%S")


def default_input(lake_root: str, source: str, run_id: str, ingest_date: str) -> str:
    if source == "full_load":
        return f"{lake_root}/raw/cfpb/full_load/ingest_date={ingest_date}/complaints.csv"
    return f"{lake_root}/raw/cfpb/api/ingest_date={ingest_date}/run_id={run_id}/response_*.json"


def _fs_path(spark: SparkSession, path: str):
    jvm = spark.sparkContext._jvm
    hadoop_path = jvm.org.apache.hadoop.fs.Path(path)
    return hadoop_path.getFileSystem(spark.sparkContext._jsc.hadoopConfiguration()), hadoop_path


def path_exists(spark: SparkSession, path: str) -> bool:
    """True if the path (wildcards allowed) matches at least one file or folder."""
    fs, hadoop_path = _fs_path(spark, path)
    matches = fs.globStatus(hadoop_path)
    return matches is not None and len(matches) > 0


def delete_path(spark: SparkSession, path: str) -> None:
    fs, hadoop_path = _fs_path(spark, path)
    if fs.exists(hadoop_path):
        fs.delete(hadoop_path, True)


def write_text(spark: SparkSession, path: str, text: str) -> None:
    """Write one small text object (works for local paths and s3a://)."""
    fs, hadoop_path = _fs_path(spark, path)
    stream = fs.create(hadoop_path, True)
    try:
        stream.write(bytearray(text.encode("utf-8")))
    finally:
        stream.close()


def read_source(spark: SparkSession, source: str, path: str) -> DataFrame:
    if source == "full_load":
        return t.standardise_columns(schema.read_csv(spark, path), schema.CSV_TO_STANDARD)
    return t.standardise_columns(schema.read_api_pages(spark, path), schema.API_TO_STANDARD)


def build_aggregates(curated: DataFrame):
    """Dashboard-ready aggregates, always rebuilt from the full curated data."""
    agg_monthly = curated.groupBy(
        "year_month", "sub_product_std", "issue", "state", "submitted_via", "company_response"
    ).agg(
        F.count(F.lit(1)).alias("complaint_count"),
        F.sum(F.col("timely_response").cast("int")).alias("timely_yes_count"),
        F.count("timely_response").alias("timely_known_count"),
        F.sum("processing_lag_days").alias("lag_sum_days"),
        F.count("processing_lag_days").alias("lag_count"),
    )
    agg_company_year = curated.groupBy("year", "company", "sub_product_std").agg(
        F.count(F.lit(1)).alias("complaint_count")
    )
    return agg_monthly, agg_company_year


def merge_into_curated(spark: SparkSession, lake_root: str, run_id: str, new_curated: DataFrame) -> None:
    """Merge this run's records with the curated data already stored, partition by partition.

    Only the year/month partitions that contain records of this run are rewritten. The merged rows
    go to a staging folder first, because Spark cannot overwrite a folder it is still reading from.
    """
    curated_path = f"{lake_root}/{CURATED_DIR}"
    staging_root = f"{lake_root}/curated/_staging"
    staging_path = f"{staging_root}/run_id={run_id}"
    merged = new_curated
    if path_exists(spark, curated_path):
        touched = new_curated.select("year", "month").distinct()
        existing = (
            spark.read.schema(schema.CURATED_SCHEMA).option("basePath", curated_path).parquet(curated_path)
            .join(F.broadcast(touched), ["year", "month"], "left_semi")
        )
        merged = t.conform_to_curated(t.deduplicate(existing.unionByName(new_curated)))

    delete_path(spark, staging_path)
    with_partition_folders(merged).write.mode("overwrite").partitionBy("year", "month").parquet(staging_path)
    staged = spark.read.schema(schema.CURATED_SCHEMA).option("basePath", staging_path).parquet(staging_path)
    with_partition_folders(staged).write.mode("overwrite").partitionBy("year", "month").parquet(curated_path)
    delete_path(spark, staging_root)


def with_partition_folders(df: DataFrame) -> DataFrame:
    """Turn year and month into the folder text of the contract: year=2024/month=03, not month=3.

    Only the folder names change. Readers that use CURATED_SCHEMA (Spark) or hive partitioning
    (pyarrow in the MongoDB loader) read month=03 back as the integer 3.
    """
    return (
        df.withColumn("year", F.lpad(F.col("year").cast("string"), 4, "0"))
        .withColumn("month", F.lpad(F.col("month").cast("string"), 2, "0"))
    )


# ---------- the job ----------

def run(spark: SparkSession, source: str, run_id: str, input_path: str = None, lake_root: str = None,
        ignore_quality_gate: bool = False, generated_at: datetime = None):
    """Run the job and return (exit_code, quality_report or None)."""
    for key, value in t.REQUIRED_SPARK_CONF.items():
        spark.conf.set(key, value)
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    lake_root = (lake_root or f"s3a://{os.environ.get('MINIO_BUCKET', 'cfpb-lake')}").rstrip("/")
    ingest_date, ingested_at = parse_run_id(run_id, source)
    input_path = input_path or default_input(lake_root, source, run_id, ingest_date)

    if not path_exists(spark, input_path):
        if source == "api":
            print(f"No API pages found at {input_path}: nothing to process for {run_id}.")
            return 0, None
        print(f"Input not found: {input_path}")
        return 1, None

    # 1. Read, standardise and transform
    std = t.add_lineage(read_source(spark, source, input_path), source, run_id, ingested_at).cache()
    raw_input = std.count()
    typed = t.normalise_values(t.parse_dates(std))
    mapping_df = t.read_reference_csv(spark, str(MAPPING_CSV))
    state_codes_df = t.read_reference_csv(spark, str(STATE_CODES_CSV))
    in_domain, out_of_domain = t.apply_domain(typed, mapping_df)
    in_domain = in_domain.cache()
    out_of_domain_count = out_of_domain.count()
    in_domain_count = in_domain.count()
    checked = t.derive_fields(t.deduplicate(in_domain)).cache()
    duplicates_removed = in_domain_count - checked.count()
    clean, quarantine = t.split_quarantine(checked, state_codes_df)
    new_curated = t.conform_to_curated(clean).cache()

    # 2. Quality report and quarantine (always written: they are the evidence of the run)
    report = quality.build_quality_report(
        run_id=run_id, source_type=source, raw_input=raw_input, out_of_domain=out_of_domain_count,
        duplicates_removed=duplicates_removed, checked_df=checked, curated_df=new_curated,
        quarantine_df=quarantine, generated_at=generated_at,
    )
    quarantine.write.mode("overwrite").parquet(f"{lake_root}/quarantine/run_id={run_id}")
    report_path = f"{lake_root}/quality/run_id={run_id}/quality_report.json"
    gate_failed = report["overall_status"] == quality.FAIL
    report["quality_gate"] = (
        "overridden" if gate_failed and ignore_quality_gate else "stopped" if gate_failed else "passed"
    )

    if gate_failed and not ignore_quality_gate:
        write_text(spark, report_path, quality.report_to_json(report))
        print(f"Quality gate FAILED for {run_id}: curated data not written. Report: {report_path}")
        return 1, report

    # 3. Curated data (merged by complaint_id) and aggregates rebuilt from all curated data
    merge_into_curated(spark, lake_root, run_id, new_curated)
    curated_all = spark.read.schema(schema.CURATED_SCHEMA).option("basePath", f"{lake_root}/{CURATED_DIR}") \
        .parquet(f"{lake_root}/{CURATED_DIR}").cache()
    totals = curated_all.agg(
        F.count(F.lit(1)).alias("rows"), F.countDistinct("complaint_id").alias("ids")
    ).collect()[0]
    agg_monthly, agg_company_year = build_aggregates(curated_all)
    agg_monthly.coalesce(1).write.mode("overwrite").parquet(f"{lake_root}/{AGG_MONTHLY_DIR}")
    agg_company_year.coalesce(1).write.mode("overwrite").parquet(f"{lake_root}/{AGG_COMPANY_YEAR_DIR}")

    report["curated_snapshot"] = {"total_records": totals["rows"], "distinct_complaint_ids": totals["ids"]}
    write_text(spark, report_path, quality.report_to_json(report))
    print(json.dumps({
        "run_id": run_id, "source": source, "overall_status": report["overall_status"],
        "quality_gate": report["quality_gate"], "counts": report["counts"],
        "curated_total": totals["rows"], "quality_report": report_path,
    }))
    return 0, report


def build_spark() -> SparkSession:
    """Local Spark session with the S3A settings for MinIO (credentials from the environment only).

    Driver memory comes from SPARK_DRIVER_MEMORY in .env: spark-submit reads that variable itself.
    """
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    builder = (
        SparkSession.builder.appName("cfpb-spark-job")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.endpoint", endpoint)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", str(endpoint.startswith("https")).lower())
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER", ""))
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD", ""))
        .config("spark.sql.shuffle.partitions", "8")
    )
    if "SPARK_MASTER" not in os.environ:
        builder = builder.master("local[*]")
    return builder.getOrCreate()


def parse_args(argv):
    parser = argparse.ArgumentParser(description="CFPB Spark job: raw -> curated, quarantine, aggregates, quality.")
    parser.add_argument("--source", required=True, choices=["full_load", "api"])
    parser.add_argument("--run-id", required=True, help="YYYYMMDDTHHMMSSZ_full or YYYYMMDDTHHMMSSZ_api")
    parser.add_argument("--input", help="override the raw input path (local path or s3a://), e.g. the sample CSV")
    parser.add_argument("--lake-root", help="override the output root (default s3a://<MINIO_BUCKET>)")
    parser.add_argument("--ignore-quality-gate", action="store_true",
                        help="development only: write curated data even when the quality gate fails")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        parse_run_id(args.run_id, args.source)
    except ValueError as error:
        print(f"Wrong arguments: {error}")
        return 2
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")
    try:
        code, _ = run(spark, args.source, args.run_id, args.input, args.lake_root, args.ignore_quality_gate)
        return code
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
