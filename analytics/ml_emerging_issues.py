
"""
Spark MLlib model: Emerging Complaint Issues.

Uses:
- Joseph's existing Spark/MinIO configuration
- Curated Parquet complaint records
- Spark MLlib LinearRegression
- MongoDB for dashboard results

Rules:
- Last 24 complete calendar months
- Slope >= 0.2 percentage points per month
- R-squared >= 0.50
- At least 50 issue complaints in the window

Outputs:
- analytics/output/ml_emerging_issues.csv
- MongoDB collection: ml_emerging_issues

No synthetic data is generated.
"""

import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from pymongo import MongoClient
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.sql import Row
from pyspark.sql import functions as F
from pyspark.sql.types import DateType

# Allow spark-submit to locate the project packages.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from processing.spark_job import CURATED_DIR, build_spark, path_exists

OUTPUT_DIR = ROOT / "analytics" / "output"



COLLECTION_NAME = "ml_emerging_issues"

WINDOW_MONTHS = 24
MIN_COMPLAINTS = 50
MIN_SLOPE = 0.2
MIN_R2 = 0.5

OUTPUT_COLUMNS = [
    "sub_product_std",
    "issue",
    "complaint_count_24m",
    "slope_pp_per_month",
    "r2",
    "is_emerging",
    "window_start",
    "window_end",
    "months_analyzed",
]


def add_months(month_start, number):
    """Move a first-of-month date by a number of months."""
    month_index = (
        month_start.year * 12
        + month_start.month - 1
        + number
    )

    year = month_index // 12
    month = month_index % 12 + 1

    return date(year, month, 1)


def analysis_window(today=None):
    """
    Return the beginning of the 24-month window
    and the first day of the excluded current month.
    """
    today = today or datetime.now(timezone.utc).date()

    current_month = date(today.year, today.month, 1)
    start = add_months(current_month, -WINDOW_MONTHS)

    return start, current_month


def month_index(month_value, window_start):
    """Convert YYYY-MM into a zero-based month number."""
    year, month = map(int, month_value.split("-"))

    return (
        (year - window_start.year) * 12
        + month - window_start.month
    )


def fit_issue_model(spark, monthly_counts, monthly_totals):
    """
    Fit Spark MLlib LinearRegression to one issue.

    X: month index 0 through 23
    Y: issue percentage of all complaints in
       the same sub-product and calendar month.
    """
    training_rows = []

    for index, total in enumerate(monthly_totals):
        issue_count = monthly_counts.get(index, 0)

        percentage = (
            100.0 * issue_count / total
            if total > 0
            else 0.0
        )

        training_rows.append(
            Row(
                month_index=float(index),
                issue_share_pct=float(percentage)
            )
        )

    training_df = spark.createDataFrame(training_rows)

    assembler = VectorAssembler(
        inputCols=["month_index"],
        outputCol="features"
    )

    training_df = assembler.transform(training_df)

    regression = LinearRegression(
        featuresCol="features",
        labelCol="issue_share_pct",
        fitIntercept=True,
        regParam=0.0,
        elasticNetParam=0.0,
        maxIter=100
    )

    model = regression.fit(training_df)

    slope = float(model.coefficients[0])
    r2 = float(model.summary.r2)

    if not math.isfinite(slope):
        raise ValueError("Regression produced an invalid slope.")

    if not math.isfinite(r2):
        # Constant issue shares have no meaningful
        # positive-trend evidence.
        r2 = 0.0

    return slope, r2


def save_results(records):
    """Export aggregated model results as CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        records,
        columns=OUTPUT_COLUMNS
    )

    df.to_csv(
        OUTPUT_DIR / "ml_emerging_issues.csv",
        index=False
    )

    return df


def publish_results(records):
    """
    Replace MongoDB model results after a successful
    calculation. Do not modify the complaints collection.
    """
    mongo_uri = os.getenv(
        "MONGO_URI",
        "mongodb://mongo:27017"
    )

    database_name = os.getenv(
        "MONGO_DB",
        "cfpb_money_transfers"
    )

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")

        collection = client[
            database_name
        ][COLLECTION_NAME]

        # Results are derived and reproducible.
        # Clear the previous model run only after
        # new calculations have completed.
        collection.delete_many({})

        if records:
            collection.insert_many(records)

        collection.create_index(
            [("sub_product_std", 1), ("issue", 1)],
            unique=True
        )

    finally:
        client.close()


def run():
    """Train emerging-issue regressions on curated data."""

    print("=" * 55)
    print("SPARK MLLIB: EMERGING ISSUES")
    print("=" * 55)

    window_start, window_end = analysis_window()

    print("Analysis start:", window_start)
    print("Analysis end (exclusive):", window_end)
    print("Model: Spark MLlib LinearRegression")

    bucket = os.getenv("MINIO_BUCKET", "cfpb-lake")

    lake_root = os.getenv(
        "LAKE_ROOT",
        f"s3a://{bucket}"
    ).rstrip("/")

    curated_path = f"{lake_root}/{CURATED_DIR}"

    print("Curated source:", curated_path)

    spark = build_spark()

    try:
        if not path_exists(spark, curated_path):
            print("No curated Parquet dataset exists yet.")
            print("Skipping ML training.")
            print("No fabricated model results generated.")
            return

        complaints = (
            spark.read
            .parquet(curated_path)
            .select(
                "date_received",
                "sub_product_std",
                "issue"
            )
        )

        # date_received is a DateType in the
        # team's curated schema.
        if not isinstance(
            complaints.schema["date_received"].dataType,
            DateType
        ):
            complaints = complaints.withColumn(
                "date_received",
                F.to_date("date_received")
            )

        complaints = complaints.filter(
            (F.col("date_received") >= F.lit(window_start))
            & (F.col("date_received") < F.lit(window_end))
            & F.col("sub_product_std").isNotNull()
        )

        # Denominator: all complaints in each
        # sub-product and calendar month.
        complaints = complaints.withColumn(
            "year_month",
            F.date_format("date_received", "yyyy-MM")
        )

        monthly_totals_df = (
            complaints
            .groupBy("sub_product_std", "year_month")
            .agg(F.count("*").alias("total_count"))
        )

        # Numerator: complaints about each issue
        # within that same sub-product and month.
        monthly_issues_df = (
            complaints
            .filter(
                F.col("issue").isNotNull()
                & (F.trim(F.col("issue")) != "")
            )
            .groupBy(
                "sub_product_std",
                "issue",
                "year_month"
            )
            .agg(F.count("*").alias("issue_count"))
        )

        # Collect monthly aggregates only,
        # never the individual complaint records.
        total_rows = monthly_totals_df.collect()
        issue_rows = monthly_issues_df.collect()

        if not total_rows:
            print("No complaints in the analysis window.")
            print("Skipping ML training.")
            print("No fabricated results generated.")
            return

        # Check time coverage before claiming trends.
        observed_months = {
            row["year_month"]
            for row in total_rows
        }

        required_months = {
            add_months(window_start, index).strftime("%Y-%m")
            for index in range(WINDOW_MONTHS)
        }

        missing_months = sorted(
            required_months - observed_months
        )

        if missing_months:
            print(
                "Insufficient data coverage for a "
                "24-complete-month analysis."
            )
            print(
                "Months without complaint records:",
                ", ".join(missing_months)
            )
            print(
                "Skipping model training to avoid "
                "misleading trend results."
            )
            return

        # Prepare denominator counts by sub-product.
        totals_by_product = {}

        for row in total_rows:
            product = row["sub_product_std"]
            index = month_index(
                row["year_month"],
                window_start
            )

            if product not in totals_by_product:
                totals_by_product[product] = [
                    0
                ] * WINDOW_MONTHS

            totals_by_product[product][index] = int(
                row["total_count"]
            )

        # Prepare issue counts.
        counts_by_issue = {}

        for row in issue_rows:
            key = (
                row["sub_product_std"],
                row["issue"]
            )

            index = month_index(
                row["year_month"],
                window_start
            )

            if key not in counts_by_issue:
                counts_by_issue[key] = {}

            counts_by_issue[key][index] = int(
                row["issue_count"]
            )

        results = []

        for (product, issue), monthly_counts in sorted(
            counts_by_issue.items()
        ):
            complaint_count = sum(
                monthly_counts.values()
            )

            # Not enough observations for eligibility.
            if complaint_count < MIN_COMPLAINTS:
                continue

            monthly_totals = totals_by_product[product]

            # A product must have data in every month
            # for its 24-month regression to be valid.
            if any(total <= 0 for total in monthly_totals):
                print(
                    "Skipping sub-product with incomplete "
                    "monthly coverage:",
                    product
                )
                continue

            slope, r2 = fit_issue_model(
                spark,
                monthly_counts,
                monthly_totals
            )

            is_emerging = (
                slope >= MIN_SLOPE
                and r2 >= MIN_R2
                and complaint_count >= MIN_COMPLAINTS
            )

            results.append({
                "sub_product_std": product,
                "issue": issue,
                "complaint_count_24m": complaint_count,
                "slope_pp_per_month": round(slope, 4),
                "r2": round(r2, 4),
                "is_emerging": bool(is_emerging),
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "months_analyzed": WINDOW_MONTHS,
            })

        results.sort(
            key=lambda record: (
                not record["is_emerging"],
                -record["slope_pp_per_month"]
            )
        )

        result_df = save_results(results)

        publish_results(results)

        emerging_count = int(
            result_df["is_emerging"].sum()
        ) if not result_df.empty else 0

        print()
        print("ML training completed.")
        print("Issue models evaluated:", len(results))
        print("Emerging issues identified:", emerging_count)
        print(
            "CSV: analytics/output/ml_emerging_issues.csv"
        )
        print(
            "MongoDB collection:",
            COLLECTION_NAME
        )

        print(
            "Important: emerging means an increasing "
            "share of published complaints, not "
            "proof of increased consumer risk."
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    run()
