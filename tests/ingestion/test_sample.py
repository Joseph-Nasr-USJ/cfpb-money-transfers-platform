"""Tests for ingestion/sample.py: domain filter, stratified allocation, determinism, output files."""
import csv
import json
from pathlib import Path

from ingestion import sample

HEADER = ["Date received", "Product", "Sub-product", "Issue", "Company", "Complaint ID"]
MT = "Money transfer, virtual currency, or money service"
RULES = sample.load_domain_rules()          # the real config/product_mapping.csv


def write_csv(path: Path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)


def test_domain_rules_follow_product_mapping():
    assert sample.in_domain(MT, "Domestic (US) money transfer", RULES)
    assert sample.in_domain("Money transfers", "International money transfer", RULES)   # legacy label
    assert sample.in_domain("Prepaid card", "Mobile wallet", RULES)                     # legacy wallet only
    assert not sample.in_domain("Prepaid card", "General-purpose prepaid card", RULES)
    assert not sample.in_domain("Credit card", "Store credit card", RULES)


def test_allocation_is_proportional_with_a_floor_and_exact_total():
    quota = sample.allocate({"2016": 10, "2020": 2000, "2024": 8000}, size=1000, minimum=50)
    assert sum(quota.values()) == 1000
    assert quota["2016"] == 10                     # cannot take more rows than the year has
    assert quota["2024"] > quota["2020"] > 50


def test_small_domain_is_kept_whole():
    assert sample.allocate({"2020": 3, "2021": 4}, size=100, minimum=50) == {"2020": 3, "2021": 4}


def test_build_sample_filters_domain_and_spreads_years(tmp_path):
    rows = []
    for i in range(3000):
        year = 2018 + i % 6
        rows.append([f"{year}-05-0{1 + i % 9}", MT, "Mobile or digital wallet", "Fraud or scam", "Co", str(10_000 + i)])
    rows.append(["2024-01-01", "Credit card", "Store credit card", "Fees", "Bank", "1"])     # out of domain
    rows.append(["05/02/16", "Money transfers", "Domestic (US) money transfer", "X", "Co", "2"])  # legacy, MM/dd/yy
    source = tmp_path / "raw.csv"
    write_csv(source, rows)

    result = sample.build_sample(source, size=600, seed=7, rules=RULES)

    assert len(result["rows"]) == 600
    assert result["rows_read"] == 3002
    assert sum(result["domain_rows_by_year"].values()) == 3001
    assert result["sample_rows_by_year"]["2016"] == 1                   # the one legacy row is kept
    assert set(result["sample_rows_by_year"]) == {"2016", "2018", "2019", "2020", "2021", "2022", "2023"}
    assert all(row[1] != "Credit card" for row in result["rows"])
    ids = [int(row[5]) for row in result["rows"]]
    assert ids == sorted(ids) and len(set(ids)) == 600                    # sorted, no duplicates


def test_same_seed_gives_the_same_sample(tmp_path):
    rows = [[f"{2019 + i % 3}-02-01", MT, "Virtual currency", "Fraud or scam", "Co", str(i)] for i in range(1, 2001)]
    source = tmp_path / "raw.csv"
    write_csv(source, rows)
    first = sample.build_sample(source, size=300, seed=42, rules=RULES)
    second = sample.build_sample(source, size=300, seed=42, rules=RULES)
    assert first["rows"] == second["rows"]


def test_main_reads_latest_manifest_from_minio_and_writes_files(fake_minio, tmp_path, monkeypatch):
    rows = [[f"20{18 + i % 5}-03-01", MT, "Domestic (US) money transfer", "I", "Co", str(i)] for i in range(1, 401)]
    local = tmp_path / "raw.csv"
    write_csv(local, rows)
    old = "raw/cfpb/full_load/ingest_date=2026-11-01/"
    new = "raw/cfpb/full_load/ingest_date=2026-11-20/"
    fake_minio.objects[old + "manifest.json"] = json.dumps({"run_id": "old", "csv_object": old + "complaints.csv"}).encode()
    fake_minio.objects[new + "manifest.json"] = json.dumps(
        {"run_id": "20261120T140000Z_full", "csv_object": new + "complaints.csv", "csv_sha256": "abc"}).encode()
    fake_minio.objects[new + "complaints.csv"] = local.read_bytes()
    monkeypatch.setattr(sample, "WORK_DIR", tmp_path / "work")
    monkeypatch.setattr(sample, "OUTPUT_CSV", tmp_path / "out" / "complaints_sample.csv")
    monkeypatch.setattr(sample, "OUTPUT_INFO", tmp_path / "out" / "sample_info.json")

    assert sample.main(["--size", "100"]) == 0

    out_csv = tmp_path / "out" / "complaints_sample.csv"
    with open(out_csv, newline="", encoding="utf-8") as handle:
        written = list(csv.reader(handle))
    assert written[0] == HEADER and len(written) == 101
    info = json.loads((tmp_path / "out" / "sample_info.json").read_text())
    assert info["source_run_id"] == "20261120T140000Z_full"        # latest manifest, not the older one
    assert info["sample_rows"] == 100 and info["domain_rows"] == 400
    assert not (tmp_path / "work" / "sample_source.csv").exists()   # temporary copy removed

