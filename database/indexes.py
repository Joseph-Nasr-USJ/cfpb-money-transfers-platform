"""Create the MongoDB indexes specified in the shared Big Data project contract.

Run from the pipeline container:
    docker compose run --rm pipeline python -m database.indexes

Safe to rerun: indexes with the same keys and names are not duplicated.
Reapply after replacing an aggregate collection through a rename.
"""

import os

from pymongo import ASCENDING, MongoClient


# Equality / common filter field first, followed by the date range field.
INDEX_SPECS = {
    "complaints": [
        ("sub_product_date_idx", [("sub_product_std", ASCENDING), ("date_received", ASCENDING)]),
        ("issue_date_idx", [("issue", ASCENDING), ("date_received", ASCENDING)]),
        ("state_date_idx", [("state", ASCENDING), ("date_received", ASCENDING)]),
        ("company_date_idx", [("company", ASCENDING), ("date_received", ASCENDING)]),
        ("channel_date_idx", [("submitted_via", ASCENDING), ("date_received", ASCENDING)]),
    ],
    "agg_monthly": [
        ("month_sub_product_idx", [("year_month", ASCENDING), ("sub_product_std", ASCENDING)]),
    ],
}


def create_indexes(db) -> None:
    """Create the planned indexes and print their names for verification."""
    for collection_name, specs in INDEX_SPECS.items():
        collection = db[collection_name]
        for index_name, fields in specs:
            created_name = collection.create_index(fields, name=index_name)
            print(f"{collection_name}: {created_name}")


def main() -> None:
    uri = os.environ["MONGO_URI"]
    db_name = os.environ["MONGO_DB"]

    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        client.admin.command("ping")
        print(f"Connected to MongoDB database: {db_name}")
        create_indexes(client[db_name])
        print("All required indexes are ready.")


if __name__ == "__main__":
    main()
