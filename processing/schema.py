"""Explicit schemas for the CFPB inputs and the curated output, and the mapping from
source names (CSV headers and API JSON keys) to our standard snake_case column names.

Both sources are read with every column as a string, then mapped to the same standard
input columns. Types are cast later (transforms.py) so a malformed value never makes the
read itself fail, and the curated output is checked against CURATED_SCHEMA.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType, BooleanType, DateType, IntegerType, LongType,
    StringType, StructField, StructType, TimestampType,
)

# Standard input columns, identical for the full CSV load and the API pages.
STANDARD_INPUT_COLUMNS = [
    "complaint_id", "date_received", "date_sent_to_company",
    "product", "sub_product", "issue", "sub_issue",
    "company", "company_public_response", "company_response", "timely_response",
    "state", "zip_code", "tags", "submitted_via",
]

# CSV header (full export complaints.csv) -> standard name.
CSV_TO_STANDARD = {
    "Complaint ID": "complaint_id",
    "Date received": "date_received",
    "Date sent to company": "date_sent_to_company",
    "Product": "product",
    "Sub-product": "sub_product",
    "Issue": "issue",
    "Sub-issue": "sub_issue",
    "Company": "company",
    "Company public response": "company_public_response",
    "Company response to consumer": "company_response",
    "Timely response?": "timely_response",
    "State": "state",
    "ZIP code": "zip_code",
    "Tags": "tags",
    "Submitted via": "submitted_via",
}

# API JSON key (hits.hits[]._source) -> standard name.
API_TO_STANDARD = {
    "complaint_id": "complaint_id",
    "date_received": "date_received",
    "date_sent_to_company": "date_sent_to_company",
    "product": "product",
    "sub_product": "sub_product",
    "issue": "issue",
    "sub_issue": "sub_issue",
    "company": "company",
    "company_public_response": "company_public_response",
    "company_response": "company_response",
    "timely": "timely_response",
    "state": "state",
    "zip_code": "zip_code",
    "tags": "tags",
    "submitted_via": "submitted_via",
}

# Source fields we deliberately ignore: narratives were removed from the database,
# consent and dispute fields are no longer meaningful. They may or may not be present.
IGNORED_SOURCE_FIELDS = {
    "Consumer complaint narrative", "Consumer consent provided?", "Consumer disputed?",
    "complaint_what_happened", "consumer_consent_provided", "consumer_disputed", "has_narrative",
}

# Explicit schema of one API page: only the fields we use are declared, all as strings.
API_SOURCE_SCHEMA = StructType([StructField(key, StringType(), True) for key in API_TO_STANDARD])
API_PAGE_SCHEMA = StructType([
    StructField("hits", StructType([
        StructField("hits", ArrayType(StructType([
            StructField("_source", API_SOURCE_SCHEMA, True),
        ])), True),
    ]), True),
])

# Explicit schema of the curated output (same in Parquet and MongoDB).
CURATED_SCHEMA = StructType([
    StructField("complaint_id", LongType(), False),
    StructField("date_received", DateType(), True),
    StructField("date_sent_to_company", DateType(), True),
    StructField("product", StringType(), True),
    StructField("sub_product", StringType(), True),
    StructField("product_std", StringType(), True),
    StructField("sub_product_std", StringType(), True),
    StructField("is_core_payment", BooleanType(), True),
    StructField("issue", StringType(), True),
    StructField("sub_issue", StringType(), True),
    StructField("company", StringType(), True),
    StructField("company_public_response", StringType(), True),
    StructField("company_response", StringType(), True),
    StructField("timely_response", BooleanType(), True),
    StructField("state", StringType(), True),
    StructField("zip_code", StringType(), True),
    StructField("tags", ArrayType(StringType()), True),
    StructField("is_older_american", BooleanType(), True),
    StructField("is_servicemember", BooleanType(), True),
    StructField("submitted_via", StringType(), True),
    StructField("year", IntegerType(), True),
    StructField("month", IntegerType(), True),
    StructField("year_month", StringType(), True),
    StructField("processing_lag_days", IntegerType(), True),
    StructField("source_type", StringType(), False),
    StructField("ingest_run_id", StringType(), False),
    StructField("ingested_at", TimestampType(), False),
])


def read_csv(spark: SparkSession, path: str) -> DataFrame:
    """Read the full-export CSV with every column as a string (no type inference)."""
    return (
        spark.read
        .option("header", True)
        .option("inferSchema", False)
        .option("multiLine", True)
        .option("escape", '"')
        .option("mode", "PERMISSIVE")
        .csv(path)
    )


def read_api_pages(spark: SparkSession, path: str) -> DataFrame:
    """Read one or more API response pages and return one row per complaint (_source)."""
    pages = spark.read.option("multiLine", True).schema(API_PAGE_SCHEMA).json(path)
    return pages.select(F.explode("hits.hits").alias("hit")).select("hit._source.*")


def to_standard_columns(df: DataFrame, mapping: dict) -> DataFrame:
    """Return exactly STANDARD_INPUT_COLUMNS as strings, whatever the source looked like.

    Known source columns are renamed, ignored or unknown columns are dropped, and a
    standard column missing from the source is added as null (reported by the quality checks).
    """
    present = {standard: source for source, standard in mapping.items() if source in df.columns}
    return df.select([
        (F.col(f"`{present[name]}`") if name in present else F.lit(None)).cast(StringType()).alias(name)
        for name in STANDARD_INPUT_COLUMNS
    ])
