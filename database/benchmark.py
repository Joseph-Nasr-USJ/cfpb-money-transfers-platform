"""Measure MongoDB query performance before and after the project's indexes.

Runs against the REAL `complaints` collection, never fabricated records.
Requires real curated complaints to have been loaded first.

Run from the repository root in the pipeline container:
    docker compose run --rm pipeline python -m database.benchmark --help
    make benchmark                 # only after real data is loaded

WARNING: During measurement the script temporarily removes the five planned
secondary indexes on `complaints`. Run only when no ingestion or dashboard
activity is in progress. A finally block attempts to restore all five indexes
if any measurement fails or is interrupted. Verify indexes afterward.
"""

from __future__ import annotations

import argparse
import calendar
import os
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from pymongo import MongoClient

from database.indexes import INDEX_SPECS
from database.queries import build_match


DEFAULT_OUTPUT = "docs/evidence/benchmark.md"


def find_nodes(obj: Any, name: str):
    """Yield named subdocuments from either classic or SBE explain layouts."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == name and isinstance(value, dict):
                yield value
            yield from find_nodes(value, name)
    elif isinstance(obj, list):
        for item in obj:
            yield from find_nodes(item, name)


def explain_metrics(explain: dict) -> dict:
    """Extract cursor-level execution statistics, not overall pipeline totals."""
    candidates = list(find_nodes(explain, "executionStats"))
    stats = next(
        (value for value in candidates if "totalDocsExamined" in value),
        None,
    )
    if stats is None:
        raise ValueError("MongoDB explain output lacks executionStats")

    stages = [
        node["stage"]
        for node in find_stage_dicts(explain)
        if isinstance(node.get("stage"), str)
    ]
    stage_set = set(stages)
    if "IXSCAN" in stage_set:
        access = "IXSCAN"
    elif "COLLSCAN" in stage_set:
        access = "COLLSCAN"
    else:
        # MongoDB's slot-based engine can include plan stages as text.
        all_text = str(explain)
        access = "IXSCAN" if "IXSCAN" in all_text else ("COLLSCAN" if "COLLSCAN" in all_text else "Other")

    return {
        "time_ms": float(stats.get("executionTimeMillis", 0)),
        "docs": int(stats.get("totalDocsExamined", 0)),
        "keys": int(stats.get("totalKeysExamined", 0)),
        "plan": access,
    }


def find_stage_dicts(obj: Any):
    """Walk a query plan to find stages such as COLLSCAN and IXSCAN."""
    if isinstance(obj, dict):
        if "stage" in obj:
            yield obj
        for value in obj.values():
            yield from find_stage_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from find_stage_dicts(item)


def representative_values(collection) -> tuple[str, str, str, date, date]:
    """Choose actual nonempty values from the loaded collection."""
    newest = collection.find_one(
        {"date_received": {"$type": "date"}, "sub_product_std": {"$type": "string", "$ne": ""}},
        {"date_received": 1, "sub_product_std": 1},
        sort=[("date_received", -1)],
    )
    if not newest:
        raise ValueError("No dated complaints with a sub-product were found")

    def pick(field: str) -> str:
        row = collection.find_one({field: {"$type": "string", "$ne": ""}}, {field: 1})
        if not row:
            raise ValueError(f"No complaints have a usable {field!r} value")
        return row[field]

    end_date = newest["date_received"].date()
    # Twelve complete named calendar months ending with the latest data month.
    month_number = end_date.year * 12 + end_date.month - 11
    start_year, month_zero = divmod(month_number - 1, 12)
    first_day = date(start_year, month_zero + 1, 1)
    last_day = date(end_date.year, end_date.month, calendar.monthrange(end_date.year, end_date.month)[1])
    return newest["sub_product_std"], pick("state"), pick("company"), first_day, last_day


def query_cases(collection) -> list[tuple[str, list[dict], str]]:
    product, state, company, first_day, last_day = representative_values(collection)
    dates = {"date_from": first_day.isoformat(), "date_to": last_day.isoformat()}

    return [
        (
            "A1 monthly volume: one sub-product, 12 months",
            [
                {"$match": build_match({**dates, "sub_product_std": [product]})},
                {"$group": {"_id": {"$dateTrunc": {"date": "$date_received", "unit": "month"}}, "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ],
            f"sub-product: {product}; window: {first_day} to {last_day}",
        ),
        (
            "A8 state issue profile: one state",
            [
                {"$match": build_match({"state": [state]})},
                {"$group": {"_id": "$issue", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ],
            f"state: {state}",
        ),
        (
            "Company and date-range filter",
            [
                {"$match": build_match({**dates, "company": [company]})},
                {"$group": {"_id": "$year", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ],
            f"company: {company}; window: {first_day} to {last_day}",
        ),
    ]


def evaluate(db, cases: list[tuple[str, list[dict], str]], iterations: int) -> dict:
    result = {}
    for title, pipeline, _ in cases:
        trials = []
        for _ in range(iterations):
            explain = db.command(
                "explain",
                {"aggregate": "complaints", "pipeline": pipeline, "cursor": {}},
                verbosity="executionStats",
            )
            trials.append(explain_metrics(explain))
        result[title] = {
            "time_ms": median(x["time_ms"] for x in trials),
            "docs": median(x["docs"] for x in trials),
            "keys": median(x["keys"] for x in trials),
            "plan": max((x["plan"] for x in trials), key=lambda x: sum(t["plan"] == x for t in trials)),
        }
        print(f"  {title}: {result[title]['time_ms']:.1f} ms; {result[title]['docs']:.0f} docs examined; {result[title]['plan']}")
    return result


def planned_indexes(db):
    return INDEX_SPECS["complaints"]


def remove_planned_indexes(db) -> None:
    names = set(db.complaints.index_information())
    for name, _ in planned_indexes(db):
        if name in names:
            db.complaints.drop_index(name)


def restore_planned_indexes(db) -> None:
    for name, keys in planned_indexes(db):
        db.complaints.create_index(keys, name=name)


def report_text(db_name: str, total: int, cases, before, after, iterations: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# MongoDB index benchmark",
        "",
        f"- Generated: {now}",
        f"- Database: `{db_name}`; collection: `complaints`; documents: {total:,}",
        f"- Repetitions: {iterations} per query per condition using `explain` at `executionStats` verbosity",
        "- Comparison: with planned secondary indexes removed versus restored",
        "- Times are server-reported `executionTimeMillis` (integer-millisecond resolution).",
        "",
        "| Query | Condition | Median time (ms) | Median docs examined | Median keys examined | Access plan |",
        "|---|---|---:|---:|---:|---|",
    ]
    for title, _, _ in cases:
        for label, dataset in (("Before indexes", before), ("After indexes", after)):
            v = dataset[title]
            lines.append(f"| {title} | {label} | {v['time_ms']:.1f} | {v['docs']:.0f} | {v['keys']:.0f} | {v['plan']} |")
    lines.extend(["", "## Query selections", ""])
    for title, _, desc in cases:
        lines.append(f"- **{title}:** {desc}")
    lines.extend([
        "",
        "## Interpretation and limitations",
        "",
        "- Compare documents and index keys examined alongside reported execution time.",
        "- An index does not guarantee `IXSCAN`: MongoDB may select `COLLSCAN` based on selectivity and dataset size.",
        "- This measures representative query shapes, not end-to-end Streamlit render latency.",
        "- Avoid concurrent pipeline/dashboard workloads during the benchmark.",
        "- Results reflect this local data snapshot and computer, not all possible workloads.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare MongoDB aggregation performance before and after indexing")
    parser.add_argument("--iterations", type=int, default=10, help="Explain repetitions per query and condition (default: 10)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Markdown evidence file path")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")

    uri = os.environ.get("MONGO_URI")
    db_name = os.environ.get("MONGO_DB")
    if not uri or not db_name:
        parser.error("MONGO_URI and MONGO_DB must be supplied by the project's environment")

    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        client.admin.command("ping")
        db = client[db_name]
        total = db.complaints.count_documents({})
        if total == 0:
            raise SystemExit("No curated complaints loaded yet. Run the real Spark + MongoDB pipeline before benchmarking.")

        cases = query_cases(db.complaints)  # Check all samples before modifying any indexes.
        expected = {name for name, _ in planned_indexes(db)}
        present = set(db.complaints.index_information())
        unplanned = present - expected - {"_id_"}
        if unplanned:
            raise SystemExit(
                "Unexpected secondary indexes exist; benchmark baseline would be misleading: "
                + ", ".join(sorted(unplanned))
            )

        print(f"Benchmarking {total:,} real complaint documents with {args.iterations} explain runs per query.")
        print("WARNING: Temporarily removing the five planned indexes from complaints. Avoid concurrent traffic.")
        try:
            remove_planned_indexes(db)
            print("BEFORE indexing:")
            before = evaluate(db, cases, args.iterations)
        finally:
            # Restore even if a query fails or Ctrl+C is pressed.
            print("Restoring the five planned complaint indexes ...")
            restore_planned_indexes(db)

        print("AFTER indexing:")
        after = evaluate(db, cases, args.iterations)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report_text(db_name, total, cases, before, after, args.iterations), encoding="utf-8")
        print(f"Evidence saved to {output}")
        print("Check MongoDB Compass > complaints > Indexes to confirm restoration.")


if __name__ == "__main__":
    main()
