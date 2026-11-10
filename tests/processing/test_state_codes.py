"""Checks on the state reference list used to validate the `state` field."""
import csv
from collections import Counter
from pathlib import Path

STATE_CODES = Path(__file__).resolve().parents[2] / "config" / "state_codes.csv"


def load_rows():
    with STATE_CODES.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_columns():
    with STATE_CODES.open(newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["code", "name", "category"]


def test_expected_counts():
    rows = load_rows()
    counts = Counter(r["category"] for r in rows)
    assert len(rows) == 62
    assert counts == {"state": 50, "federal_district": 1, "territory": 5,
                      "freely_associated_state": 3, "military": 3}


def test_codes_are_unique_two_uppercase_letters():
    codes = [r["code"] for r in load_rows()]
    assert len(codes) == len(set(codes))
    assert all(len(c) == 2 and c.isalpha() and c.isupper() for c in codes)


def test_key_codes_present():
    codes = {r["code"] for r in load_rows()}
    assert {"DC", "PR", "GU", "VI", "AA", "AE", "AP", "FM", "MH", "PW"} <= codes
