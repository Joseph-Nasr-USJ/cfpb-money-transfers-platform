"""Development sample: about 5,000 in-domain complaints from the raw CSV, spread across years.

Usage (inside the pipeline container):  python -m ingestion.sample     (also: make sample)
Optional:  python -m ingestion.sample --source path/to/complaints.csv --size 5000 --seed 42

Why: the full CSV is several GB and cannot go in Git (brief 8.7). This small file lets every
teammate develop and test Spark, MongoDB and the dashboard without the full download.

How:
1. Find the latest historical manifest in MinIO and download its raw CSV to data/tmp/
   (or use --source). The raw object itself is only read, never changed.
2. Stream the CSV once and keep only our domain, using config/product_mapping.csv
   (the same file the Spark job uses, so the sample and the curated data agree).
3. Stratified sampling by year: each year's share of the sample equals its share of the domain,
   with a floor of MIN_PER_YEAR rows so small early years still appear. Inside each year rows are
   drawn with reservoir sampling (uniform, memory-bounded) and a fixed seed, so the same raw file
   always gives the same sample.
4. Write data/sample/complaints_sample.csv with the original CSV header, and
   data/sample/sample_info.json describing how it was built.
"""
import argparse
import csv
import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ingestion import minio_utils
from ingestion.historical import _to_iso_date

MAPPING_FILE = Path("config/product_mapping.csv")
OUTPUT_CSV = Path("data/sample/complaints_sample.csv")
OUTPUT_INFO = Path("data/sample/sample_info.json")
WORK_DIR = Path(os.environ.get("INGEST_WORK_DIR", "data/tmp"))
FULL_LOAD_PREFIX = "raw/cfpb/full_load/"
DEFAULT_SIZE = 5000
DEFAULT_SEED = 42
MIN_PER_YEAR = 50
WILDCARD = "*"


def load_domain_rules(path: Path = MAPPING_FILE) -> list:
    """(product, sub_product or '*') pairs that belong to our domain."""
    with open(path, newline="", encoding="utf-8") as handle:
        return [(row["source_product"], row["source_sub_product"]) for row in csv.DictReader(handle)]


def in_domain(product: str, sub_product: str, rules: list) -> bool:
    product, sub_product = (product or "").strip(), (sub_product or "").strip()
    return any(product == p and (s == WILDCARD or sub_product == s) for p, s in rules)


def latest_manifest() -> dict:
    """The manifest of the most recent historical load (ingest_date folders sort by date)."""
    manifests = [k for k in minio_utils.list_keys(FULL_LOAD_PREFIX) if k.endswith("/manifest.json")]
    if not manifests:
        raise FileNotFoundError("No historical load found in MinIO: run 'make ingest-full' first.")
    return minio_utils.read_json(manifests[-1])


def allocate(counts: dict, size: int, minimum: int) -> dict:
    """How many rows to take from each year: proportional to its size, at least `minimum`,
    never more than the year has, and in total at most `size`."""
    total = sum(counts.values())
    if total <= size:
        return dict(counts)                                   # small domain: keep everything
    quota = {year: min(n, max(minimum, round(size * n / total))) for year, n in counts.items()}
    # Fix rounding so the total is exactly `size`: trim the largest years, or top up those with room.
    while sum(quota.values()) > size:
        year = max(quota, key=lambda y: (quota[y], y))
        quota[year] -= 1
    while sum(quota.values()) < size:
        year = max((y for y in quota if quota[y] < counts[y]), key=lambda y: (counts[y] - quota[y], y))
        quota[year] += 1
    return quota


def build_sample(source_csv: Path, size: int = DEFAULT_SIZE, seed: int = DEFAULT_SEED,
                 rules: list = None) -> dict:
    """Stream source_csv once; return header, chosen rows and statistics."""
    rules = rules if rules is not None else load_domain_rules()
    rng = random.Random(seed)
    reservoirs = defaultdict(list)                            # year -> up to `size` rows
    counts = Counter()
    total_rows = 0
    with open(source_csv, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        col = {name: header.index(name) for name in ("Date received", "Product", "Sub-product")}
        for row in reader:
            if not row:
                continue
            total_rows += 1
            if len(row) != len(header) or not in_domain(row[col["Product"]], row[col["Sub-product"]], rules):
                continue
            day = _to_iso_date(row[col["Date received"]])
            year = day[:4] if day else "unknown"
            counts[year] += 1
            bucket = reservoirs[year]
            if len(bucket) < size:                            # reservoir sampling (algorithm R)
                bucket.append(row)
            else:
                slot = rng.randrange(counts[year])
                if slot < size:
                    bucket[slot] = row
    quota = allocate(dict(counts), size, MIN_PER_YEAR)
    chosen = []
    for year in sorted(quota):
        chosen.extend(rng.sample(reservoirs[year], quota[year]))
    id_col = header.index("Complaint ID") if "Complaint ID" in header else None
    if id_col is not None:
        chosen.sort(key=lambda r: int(r[id_col]) if r[id_col].strip().isdigit() else -1)
    return {"header": header, "rows": chosen, "rows_read": total_rows,
            "domain_rows_by_year": dict(sorted(counts.items())),
            "sample_rows_by_year": dict(sorted(quota.items()))}


def write_sample(result: dict, info: dict, csv_path: Path = None, info_path: Path = None) -> None:
    csv_path, info_path = csv_path or OUTPUT_CSV, info_path or OUTPUT_INFO
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(result["header"])
        writer.writerows(result["rows"])
    info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the development sample of in-domain complaints.")
    parser.add_argument("--source", help="local raw CSV (default: latest historical load in MinIO)")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    downloaded = None
    if args.source:
        source, origin = Path(args.source), {"source_file": args.source}
    else:
        manifest = latest_manifest()
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        downloaded = source = WORK_DIR / "sample_source.csv"
        print(f"Downloading {manifest['csv_object']} from MinIO...", flush=True)
        minio_utils.download_file(manifest["csv_object"], str(source))
        origin = {"source_object": manifest["csv_object"], "source_run_id": manifest["run_id"],
                  "source_csv_sha256": manifest.get("csv_sha256")}
    try:
        result = build_sample(source, args.size, args.seed)
    finally:
        if downloaded:
            downloaded.unlink(missing_ok=True)

    info = {
        **origin,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domain_rule_file": str(MAPPING_FILE),
        "method": f"stratified by year of date_received, proportional with a floor of {MIN_PER_YEAR} "
                  f"rows per year, reservoir sampling within each year, seed {args.seed}",
        "rows_read": result["rows_read"],
        "domain_rows": sum(result["domain_rows_by_year"].values()),
        "sample_rows": len(result["rows"]),
        "domain_rows_by_year": result["domain_rows_by_year"],
        "sample_rows_by_year": result["sample_rows_by_year"],
    }
    write_sample(result, info)
    print(f"Wrote {OUTPUT_CSV} with {info['sample_rows']:,} rows "
          f"({info['domain_rows']:,} in-domain of {info['rows_read']:,} read).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
