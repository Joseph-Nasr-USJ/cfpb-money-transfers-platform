"""Sanity checks on the hand-made fixtures used by the Spark transformation tests."""
import csv
import json
from collections import Counter
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

CSV_HEADERS = [
    "Date received", "Product", "Sub-product", "Issue", "Sub-issue",
    "Consumer complaint narrative", "Company public response", "Company", "State",
    "ZIP code", "Tags", "Consumer consent provided?", "Submitted via",
    "Date sent to company", "Company response to consumer", "Timely response?",
    "Consumer disputed?", "Complaint ID",
]
API_KEYS = {
    "complaint_id", "date_received", "date_sent_to_company", "product", "sub_product",
    "issue", "sub_issue", "company", "company_public_response", "state", "zip_code",
    "tags", "submitted_via", "company_response", "timely",
}


def read_csv_rows():
    with (FIXTURES / "mini_complaints.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, list(reader)


def read_api_hits():
    page = json.loads((FIXTURES / "mini_api_page.json").read_text(encoding="utf-8"))
    return page, [hit["_source"] for hit in page["hits"]["hits"]]


def test_csv_has_real_headers_and_22_rows():
    header, rows = read_csv_rows()
    assert header == CSV_HEADERS
    assert len(rows) == 22
    assert all(len(row) == len(CSV_HEADERS) for row in rows)


def test_csv_contains_the_deliberate_cases():
    _, rows = read_csv_rows()
    ids = Counter(row[-1] for row in rows)
    products = {row[1] for row in rows}
    assert ids["9000012"] == 2                    # duplicate Complaint ID
    assert ids[""] == 1                           # missing Complaint ID
    assert {"Money transfers", "Virtual currency", "Prepaid card"} <= products   # legacy labels
    assert "Credit card" in products              # out of domain
    assert any(row[0] == "2024-02-30" for row in rows)          # invalid date
    assert any(row[0] == "03/22/24" for row in rows)            # MM/dd/yy format


def test_api_page_structure_and_cases():
    page, sources = read_api_hits()
    assert page["hits"]["total"]["value"] == len(sources) == 8
    assert all(API_KEYS <= set(src) for src in sources)
    ids = Counter(src["complaint_id"] for src in sources)
    assert ids["9000102"] == 2                    # duplicate inside the page
    assert any(src["date_received"] == "not-a-date" for src in sources)
