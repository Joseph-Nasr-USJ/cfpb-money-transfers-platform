"""Assemble the technical report from docs/report/sections/ and check its length.

    python docs/report/build_report.py            writes docs/report/technical_report.md and prints the word counts
    python docs/report/build_report.py --check    prints the word counts only (writes nothing)

Every section lives in its own file in docs/report/sections/, so several people never edit the same
file. technical_report.md is generated: edit the section files, never technical_report.md.

Word counting rules: HTML comments (the section instructions) and headings are not counted; the
appendices (section 8) are not counted either, as the brief says "excluding appendices". A section
whose body is only the pending marker counts as 0 words. Visible "[TO COMPLETE" markers are listed so
none is forgotten in the final version.

Only the Python standard library is used, so the script runs on any machine (python 3.8+).
"""
import re
import sys
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent
SECTIONS_DIR = REPORT_DIR / "sections"
OUTPUT = REPORT_DIR / "technical_report.md"

TITLE = "Banking Complaints Data Platform: Money Transfers and Digital Payments"
SUBTITLE = (
    "Technical report. Group 5, course 020IABDM2 Big Data Frameworks (Dr. Rafiqul Haque), ESIB, USJ. "
    "Marwa Zeineddine, Perla Boustany, Joseph Nasr, Christopher Al Hassrouty, Charbel Mazraani, Loutchiana Marie."
)

# (file, section number, title, owner, target words, draft due). Order = order in the report.
SECTIONS = [
    ("01_executive_summary.md", "1", "Executive summary", "Loutchiana", 300, "Fri 27 Nov"),
    ("02_problem_and_scope.md", "2", "Problem and scope", "Loutchiana (questions with Perla)", 350, "Sat 14 Nov"),
    ("03_data_source_and_limitations.md", "3", "Data source and limitations", "Loutchiana (category changes with Joseph)", 450, "Sun 22 Nov"),
    ("04_1_architecture.md", "4.1", "Architecture and technology choices", "Loutchiana", 300, "Wed 25 Nov"),
    ("04_2_collection.md", "4.2", "Collection, scheduling and raw storage", "Marwa", 450, "Wed 25 Nov"),
    ("04_3_spark_processing.md", "4.3", "Spark processing", "Joseph", 450, "Wed 25 Nov"),
    ("04_4_mongodb.md", "4.4", "MongoDB serving layer", "Christopher", 400, "Wed 25 Nov"),
    ("04_5_dashboard.md", "4.5", "Dashboard", "Perla", 300, "Wed 25 Nov"),
    ("05_1_quality_and_reruns.md", "5.1", "Quality thresholds, reconciliation and rerun evidence", "Joseph", 350, "Wed 25 Nov"),
    ("05_2_index_measurements.md", "5.2", "Index measurements", "Christopher", 200, "Wed 25 Nov"),
    ("05_3_tests_and_operations.md", "5.3", "Tests, deployment and recovery", "Charbel", 350, "Wed 25 Nov"),
    ("06_findings.md", "6", "Findings", "Perla", 500, "Wed 25 Nov"),
    ("07_reflection_and_next_steps.md", "7", "Reflection and next steps", "Loutchiana (with Charbel)", 250, "Wed 25 Nov"),
    ("08_references_and_appendices.md", "8", "References and appendices", "Loutchiana (from every owner)", 0, "Fri 27 Nov"),
]

# Parent headings, written once before the first sub-section of the group.
PARENTS = {
    "4.1": "## 4. Architecture and implementation",
    "5.1": "## 5. Testing and operations",
}

PENDING = re.compile(r"^_Draft pending[^\n]*_\s*$", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING = re.compile(r"^#{1,6} .*$", re.MULTILINE)
MARKER = re.compile(r"\[TO COMPLETE[^\]]*\]")


def read_body(path: Path) -> str:
    """Section text without its instruction comment, or '' if the file is missing or still pending."""
    if not path.exists():
        return ""
    text = COMMENT.sub("", path.read_text(encoding="utf-8"))
    if PENDING.search(text) and len(HEADING.sub("", PENDING.sub("", text)).split()) == 0:
        return ""
    return text.strip()


def count_words(text: str) -> int:
    text = HEADING.sub("", PENDING.sub("", MARKER.sub("", text)))
    return len(re.findall(r"[\w'’-]+", text))


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    parts = [f"# {TITLE}", "", SUBTITLE, ""]
    rows, total, markers = [], 0, []

    for filename, number, title, owner, target, due in SECTIONS:
        body = read_body(SECTIONS_DIR / filename)
        words = count_words(body) if body else 0
        counted = number != "8"
        if counted:
            total += words
        for found in MARKER.findall(body):
            markers.append(f"{number}: {found}")
        status = "missing" if not (SECTIONS_DIR / filename).exists() else ("pending" if not body else "drafted")
        rows.append((number, title, owner, target, words, due, status))

        if number in PARENTS:
            parts += [PARENTS[number], ""]
        if body:
            parts += [body, ""]
        else:
            level = "###" if "." in number else "##"
            parts += [f"{level} {number}. {title}", "", f"_Draft pending ({owner}, due {due})._", ""]

    print(f"{'Sec':<5}{'Section':<56}{'Owner':<42}{'Target':>7}{'Words':>7}  Due / status")
    for number, title, owner, target, words, due, status in rows:
        goal = "appx" if number == "8" else str(target)
        print(f"{number:<5}{title[:54]:<56}{owner[:40]:<42}{goal:>7}{words:>7}  {due} / {status}")
    print(f"\nTotal counted (sections 1 to 7): {total} words. Brief: 4,000 to 5,000 words excluding appendices.")
    if markers:
        print(f"{len(markers)} marker(s) still to complete:")
        for item in markers:
            print("  -", item)

    if not check_only:
        OUTPUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\n")
        print(f"\nWritten: {OUTPUT.relative_to(REPORT_DIR.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
