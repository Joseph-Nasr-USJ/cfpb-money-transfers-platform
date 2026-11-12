"""Spark transformations from raw CFPB records to curated complaints.

Every function takes a DataFrame and returns a new one (no side effects), so each step can
be unit-tested on the fixtures. Order used by spark_job.py:

    standardise_columns -> add_lineage -> parse_dates -> normalise_values -> apply_domain
    -> deduplicate -> derive_fields -> split_quarantine -> conform_to_curated
"""
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from processing.schema import CURATED_SCHEMA, STANDARD_INPUT_COLUMNS, to_standard_columns

# Spark settings every session that runs these transforms must use (job and tests).
# CORRECTED: an impossible date such as 2024-02-30 becomes null instead of raising an error.
REQUIRED_SPARK_CONF = {
    "spark.sql.legacy.timeParserPolicy": "CORRECTED",
    "spark.sql.session.timeZone": "UTC",
}

# Values that mean "no value" in the source; normalised to null.
MISSING_TOKENS = ["", "N/A", "NA", "None", "null"]

# Date formats seen in the sources, tried in this order (API dates are cut to their first 10 characters).
DATE_FORMATS = ["yyyy-MM-dd", "MM/dd/yyyy", "MM/dd/yy"]

CORE_SUB_PRODUCTS = [
    "Domestic (US) money transfer",
    "International money transfer",
    "Mobile or digital wallet",
    "Virtual currency",
]
WILDCARD = "*"


def read_reference_csv(spark: SparkSession, path: str) -> DataFrame:
    """Read a small reference file from config/ (all columns as strings)."""
    return spark.read.option("header", True).option("inferSchema", False).csv(path)


def standardise_columns(df: DataFrame, mapping: dict) -> DataFrame:
    """Rename to the standard names, trim every string, turn empty or placeholder values into null."""
    std = to_standard_columns(df, mapping)
    cleaned = []
    for name in STANDARD_INPUT_COLUMNS:
        value = F.trim(F.col(name))
        cleaned.append(F.when(value.isin(MISSING_TOKENS), F.lit(None)).otherwise(value).alias(name))
    return std.select(cleaned)


def add_lineage(df: DataFrame, source_type: str, run_id: str, ingested_at: str) -> DataFrame:
    """Record where each row came from: source_type ('full_load' or 'api'), run_id and UTC ingestion time."""
    return (
        df.withColumn("source_type", F.lit(source_type))
        .withColumn("ingest_run_id", F.lit(run_id))
        .withColumn("ingested_at", F.to_timestamp(F.lit(ingested_at)))
    )


def _parse_date(column: str):
    text = F.substring(F.col(column), 1, 10)
    return F.coalesce(*[F.to_date(text, fmt) for fmt in DATE_FORMATS])


def parse_dates(df: DataFrame) -> DataFrame:
    """Parse both dates with explicit formats and flag records whose dates cannot be trusted.

    invalid_date_flag is true when date_received is missing or unparseable, or when
    date_sent_to_company is present but unparseable.
    """
    received = _parse_date("date_received")
    sent = _parse_date("date_sent_to_company")
    return (
        df.withColumn("date_received_parsed", received)
        .withColumn("date_sent_parsed", sent)
        .withColumn(
            "invalid_date_flag",
            F.col("date_received_parsed").isNull()
            | (F.col("date_sent_to_company").isNotNull() & F.col("date_sent_parsed").isNull()),
        )
        .withColumn("date_received", F.col("date_received_parsed"))
        .withColumn("date_sent_to_company", F.col("date_sent_parsed"))
        .drop("date_received_parsed", "date_sent_parsed")
    )


def normalise_values(df: DataFrame) -> DataFrame:
    """Typed values: numeric Complaint ID, timely Yes/No to boolean, tags to an array with two flags."""
    tags = F.when(F.col("tags").isNull(), F.array().cast("array<string>")).otherwise(F.split(F.col("tags"), r",\s*"))
    return (
        df.withColumn("complaint_id", F.expr("try_cast(complaint_id AS BIGINT)"))
        .withColumn(
            "timely_response",
            F.when(F.lower("timely_response") == "yes", F.lit(True))
            .when(F.lower("timely_response") == "no", F.lit(False))
            .otherwise(F.lit(None).cast("boolean")),
        )
        .withColumn("tags", tags)
        .withColumn("is_older_american", F.array_contains("tags", "Older American"))
        .withColumn("is_servicemember", F.array_contains("tags", "Servicemember"))
    )


def apply_domain(df: DataFrame, mapping_df: DataFrame):
    """Keep only our domain using config/product_mapping.csv. Returns (in_domain, out_of_domain).

    A mapping row matches on the product and either the exact sub-product or the wildcard "*".
    sub_product_std "*" means: keep the original sub-product.
    """
    m = mapping_df.alias("m")
    d = df.alias("d")
    condition = (F.col("d.product") == F.col("m.source_product")) & (
        (F.col("m.source_sub_product") == WILDCARD)
        | (F.col("d.sub_product") == F.col("m.source_sub_product"))
    )
    joined = d.join(F.broadcast(m), condition, "left")
    sub_std = F.when(F.col("m.sub_product_std") == WILDCARD, F.col("d.sub_product")).otherwise(F.col("m.sub_product_std"))
    enriched = joined.select(
        "d.*",
        F.col("m.product_std").alias("product_std"),
        sub_std.alias("sub_product_std"),
    ).withColumn("is_core_payment", F.coalesce(F.col("sub_product_std").isin(CORE_SUB_PRODUCTS), F.lit(False)))
    in_domain = enriched.filter(F.col("product_std").isNotNull())
    out_of_domain = enriched.filter(F.col("product_std").isNull()).drop("product_std", "sub_product_std", "is_core_payment")
    return in_domain, out_of_domain


def deduplicate(df: DataFrame) -> DataFrame:
    """Keep one record per complaint_id with the documented tie-break rule:

    1. latest ingested_at wins;
    2. if equal, source_type 'api' wins over 'full_load';
    3. if still equal, a record whose company_response is not 'In progress' wins;
    4. if still equal, the latest date_sent_to_company, then a stable hash (deterministic result).
    Rows without a complaint_id are left untouched (they go to quarantine later).
    """
    order = Window.partitionBy("complaint_id").orderBy(
        F.col("ingested_at").desc_nulls_last(),
        F.when(F.col("source_type") == "api", 0).otherwise(1),
        F.when(F.coalesce(F.col("company_response"), F.lit("")) == "In progress", 1).otherwise(0),
        F.col("date_sent_to_company").desc_nulls_last(),
        F.xxhash64(*[F.col(c).cast(StringType()) for c in df.columns]).desc(),
    )
    with_id = df.filter(F.col("complaint_id").isNotNull())
    without_id = df.filter(F.col("complaint_id").isNull())
    kept = (
        with_id.withColumn("_rank", F.row_number().over(order))
        .filter(F.col("_rank") == 1)
        .drop("_rank")
    )
    return kept.unionByName(without_id)


def derive_fields(df: DataFrame) -> DataFrame:
    """year, month, year_month from date_received; processing lag in days (sent minus received).

    The processing lag is NOT the company's resolution time.
    """
    return (
        df.withColumn("year", F.year("date_received"))
        .withColumn("month", F.month("date_received"))
        .withColumn("year_month", F.date_format("date_received", "yyyy-MM"))
        .withColumn("processing_lag_days", F.datediff("date_sent_to_company", "date_received"))
    )


def split_quarantine(df: DataFrame, state_codes_df: DataFrame, quarantine_empty_state: bool = False):
    """Separate bad records. Returns (clean, quarantine) where quarantine has a reject_reason.

    Reasons (several can apply, joined with ';'): null_id, invalid_date, negative_lag,
    invalid_state (a state value not in config/state_codes.csv), and missing_state only
    when quarantine_empty_state is True.
    """
    codes = state_codes_df.select(F.col("code").alias("_state_code")).distinct()
    flagged = df.join(F.broadcast(codes), df["state"] == codes["_state_code"], "left")
    reasons = [
        F.when(F.col("complaint_id").isNull(), F.lit("null_id")),
        F.when(F.col("invalid_date_flag"), F.lit("invalid_date")),
        F.when(F.col("processing_lag_days") < 0, F.lit("negative_lag")),
        F.when(F.col("state").isNotNull() & F.col("_state_code").isNull(), F.lit("invalid_state")),
    ]
    if quarantine_empty_state:
        reasons.append(F.when(F.col("state").isNull(), F.lit("missing_state")))
    flagged = flagged.withColumn("reject_reason", F.concat_ws(";", *reasons)).drop("_state_code")
    clean = flagged.filter(F.col("reject_reason") == "").drop("reject_reason")
    quarantine = flagged.filter(F.col("reject_reason") != "")
    return clean, quarantine


def conform_to_curated(df: DataFrame) -> DataFrame:
    """Select the curated columns in contract order with their final types."""
    return df.select([F.col(f.name).cast(f.dataType).alias(f.name) for f in CURATED_SCHEMA.fields])
