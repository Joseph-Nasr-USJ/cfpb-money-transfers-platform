
"""
Spark MLlib KMeans: US State Complaint-Profile Clustering.

Source:
    MinIO curated complaint Parquet files

Method:
    - Keep the 50 US states and Washington DC.
    - Keep states with at least 100 complaints.
    - Calculate each state's distribution of issues.
    - Fit Spark MLlib KMeans with seed=42.
    - Test K=2 through K=6 when feasible.
    - Select the highest silhouette score.

Outputs:
    analytics/output/ml_state_clusters.csv
    MongoDB collection: ml_state_clusters

No synthetic data is generated.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.sql import functions as F


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from processing.spark_job import build_spark, path_exists


OUTPUT_DIR = ROOT / "analytics" / "output"

CURATED_DIR = (
    "curated/complaints/"
    "domain=money_transfers_payments"
)

COLLECTION_NAME = "ml_state_clusters"

MIN_STATE_COMPLAINTS = 100
RANDOM_SEED = 42
MIN_K = 2
MAX_K = 6

VALID_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT",
    "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY", "DC"
}

OUTPUT_COLUMNS = [
    "state",
    "cluster",
    "complaint_count",
    "k",
    "silhouette_score",
    "seed",
]


def prepare_features(spark, curated_path):
    """
    Calculate a complaint issue distribution per state.

    All individual complaint records remain in Spark.
    Only aggregated state issue profiles are used
    as machine-learning features.
    """

    complaints = (
        spark.read
        .parquet(curated_path)
        .select("state", "issue")
    )

    complaints = complaints.withColumn(
        "state",
        F.upper(F.trim(F.col("state")))
    )

    complaints = complaints.filter(
        F.col("state").isin(sorted(VALID_STATES))
    )

    complaints = complaints.withColumn(
        "issue",
        F.when(
            F.col("issue").isNull()
            | (F.trim(F.col("issue")) == ""),
            F.lit("Unknown")
        ).otherwise(F.trim(F.col("issue")))
    )

    state_totals = (
        complaints
        .groupBy("state")
        .agg(F.count("*").alias("complaint_count"))
        .filter(
            F.col("complaint_count")
            >= MIN_STATE_COMPLAINTS
        )
    )

    eligible_complaints = complaints.join(
        state_totals.select("state"),
        on="state",
        how="inner"
    )

    issue_counts = (
        eligible_complaints
        .groupBy("state", "issue")
        .agg(F.count("*").alias("issue_count"))
    )

    # Find the real issue categories present in the
    # eligible states; no fixed feature values are invented.
    issues = [
        row["issue"]
        for row in (
            issue_counts
            .select("issue")
            .distinct()
            .orderBy("issue")
            .collect()
        )
    ]

    if not issues:
        return None

    issue_matrix = (
        issue_counts
        .groupBy("state")
        .pivot("issue", issues)
        .agg(F.sum("issue_count"))
        .fillna(0)
    )

    issue_matrix = issue_matrix.join(
        state_totals,
        on="state",
        how="inner"
    )

    # Create safe feature names because issue labels
    # may contain spaces or punctuation.
    feature_columns = []

    for index, issue in enumerate(issues):
        feature_name = f"feature_{index}"
        feature_columns.append(feature_name)

        escaped_issue = issue.replace("`", "``")

        issue_matrix = issue_matrix.withColumn(
            feature_name,
            F.col(f"`{escaped_issue}`").cast("double")
            / F.col("complaint_count").cast("double")
        )

    feature_data = issue_matrix.select(
        "state",
        "complaint_count",
        *feature_columns
    )

    assembler = VectorAssembler(
        inputCols=feature_columns,
        outputCol="features"
    )

    return assembler.transform(feature_data).select(
        "state",
        "complaint_count",
        "features"
    )


def select_best_model(feature_data):
    """
    Train candidate KMeans models and select
    the one with the highest silhouette score.
    """

    state_count = feature_data.count()

    # Silhouette evaluation needs enough observations
    # for a meaningful comparison.
    if state_count < 3:
        print(
            "Not enough eligible states for clustering."
        )
        return None, None, None

    # Count distinct complaint profiles, since identical
    # observations can cause empty KMeans clusters.
    distinct_profiles = (
        feature_data.select("features")
        .distinct()
        .count()
    )

    if distinct_profiles < 2:
        print(
            "Eligible states have fewer than two "
            "distinct complaint profiles."
        )
        return None, None, None

    maximum_k = min(
        MAX_K,
        state_count - 1,
        distinct_profiles
    )

    evaluator = ClusteringEvaluator(
        featuresCol="features",
        predictionCol="prediction",
        metricName="silhouette",
        distanceMeasure="squaredEuclidean"
    )

    best_model = None
    best_k = None
    best_score = None

    for k in range(MIN_K, maximum_k + 1):

        print(f"Training KMeans with k={k}")

        algorithm = KMeans(
            k=k,
            seed=RANDOM_SEED,
            featuresCol="features",
            predictionCol="prediction",
            maxIter=100
        )

        try:
            model = algorithm.fit(feature_data)

            predictions = model.transform(
                feature_data
            )

            # Do not accept a model that produced
            # fewer clusters than requested.
            actual_clusters = (
                predictions
                .select("prediction")
                .distinct()
                .count()
            )

            if actual_clusters != k:
                print(
                    f"Skipping k={k}: only "
                    f"{actual_clusters} clusters produced."
                )
                continue

            score = float(
                evaluator.evaluate(predictions)
            )

            print(
                f"k={k}, silhouette={score:.4f}"
            )

            if (
                best_score is None
                or score > best_score
            ):
                best_model = model
                best_k = k
                best_score = score

        except Exception as error:
            print(
                f"Unable to evaluate k={k}: {error}"
            )

    return best_model, best_k, best_score


def publish_to_mongodb(records):
    """Store completed clustering results in MongoDB."""

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

        collection.delete_many({})

        if records:
            collection.insert_many(records)

        collection.create_index(
            "state",
            unique=True
        )

    finally:
        client.close()


def run():
    """Execute the KMeans state-clustering analysis."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 55)
    print("SPARK MLLIB: STATE CLUSTERING")
    print("=" * 55)

    print("Algorithm: KMeans")
    print("Minimum state complaints:", MIN_STATE_COMPLAINTS)
    print("Candidate k values: 2 through 6")
    print("Seed:", RANDOM_SEED)

    bucket = os.getenv(
        "MINIO_BUCKET",
        "cfpb-lake"
    )

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
            print("Skipping KMeans training.")
            print("No fabricated model results generated.")
            return

        feature_data = prepare_features(
            spark,
            curated_path
        )

        if feature_data is None:
            print(
                "No eligible state issue profiles found."
            )
            return

        feature_data = feature_data.cache()

        eligible_count = feature_data.count()

        print(
            "Eligible states:", eligible_count
        )

        if eligible_count < 3:
            print(
                "Insufficient eligible states "
                "for silhouette-based clustering."
            )
            return

        model, best_k, best_score = select_best_model(
            feature_data
        )

        if model is None:
            print(
                "No valid KMeans model could be selected."
            )
            return

        predictions = model.transform(
            feature_data
        )

        rows = predictions.select(
            "state",
            "complaint_count",
            "prediction"
        ).collect()

        results = []

        for row in rows:
            results.append({
                "state": row["state"],
                "cluster": int(row["prediction"]),
                "complaint_count": int(
                    row["complaint_count"]
                ),
                "k": int(best_k),
                "silhouette_score": round(
                    best_score, 6
                ),
                "seed": RANDOM_SEED,
            })

        results.sort(
            key=lambda item: item["state"]
        )

        results_df = pd.DataFrame(
            results,
            columns=OUTPUT_COLUMNS
        )

        results_df.to_csv(
            OUTPUT_DIR / "ml_state_clusters.csv",
            index=False
        )

        publish_to_mongodb(results)

        print()
        print("State clustering completed.")
        print("Selected k:", best_k)
        print(
            "Best silhouette score:",
            round(best_score, 6)
        )
        print("States clustered:", len(results))
        print(
            "CSV: analytics/output/ml_state_clusters.csv"
        )
        print(
            "MongoDB collection:",
            COLLECTION_NAME
        )

        print(
            "Interpretation: clusters describe "
            "similarities in complaint issue profiles, "
            "not geographic risk."
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    run()
