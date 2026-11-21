"""Export the technical report to DOCX and PDF.

    python docs/report/export_report.py                    draft export (warns about open markers and the word count)
    python docs/report/export_report.py --final            final export: stops if a [TO COMPLETE] marker is left
                                                           or the text is outside 4,000 to 5,000 words
    python docs/report/export_report.py --out-dir DIR      write the files into DIR (default: docs/report/)

Steps: build_report.py assembles technical_report.md from the section files; pandoc converts it to DOCX
and to a self-contained HTML page; Chrome or Edge prints that page to PDF.

Needs pandoc (Windows: winget install JohnMacFarlane.Pandoc) and Chrome or Edge for the PDF.
The standard library only; run it from anywhere.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent
REPO_ROOT = REPORT_DIR.parent.parent
MARKDOWN = REPORT_DIR / "technical_report.md"
MIN_WORDS, MAX_WORDS = 4000, 5000

CSS = """
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt; line-height: 1.45; max-width: 760px; margin: 0 auto; color: #111; }
h1 { font-size: 20pt; } h2 { font-size: 15pt; margin-top: 1.6em; } h3 { font-size: 12.5pt; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 0.8em 0; }
th, td { border: 1px solid #999; padding: 4px 6px; vertical-align: top; } th { background: #eee; }
img { max-width: 100%; } code { font-size: 9.5pt; }
@page { size: A4; margin: 18mm; }
"""

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
BROWSER_NAMES = ["google-chrome", "chromium", "chromium-browser", "chrome", "msedge"]


def find_browser():
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed: {' '.join(str(c) for c in command[:3])} ...")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the technical report to DOCX and PDF.")
    parser.add_argument("--final", action="store_true", help="stop if markers are left or the word count is out of range")
    parser.add_argument("--out-dir", default=str(REPORT_DIR), help="folder for the exported files")
    args = parser.parse_args()

    if not shutil.which("pandoc"):
        raise SystemExit("pandoc not found. Windows: winget install JohnMacFarlane.Pandoc, then open a new terminal.")

    summary = run([sys.executable, str(REPORT_DIR / "build_report.py")])
    print(summary)
    total = int(re.search(r"Total counted \(sections 1 to 7\): (\d+) words", summary).group(1))
    markers = re.search(r"(\d+) marker\(s\) still to complete", summary)
    problems = []
    if markers:
        problems.append(f"{markers.group(1)} [TO COMPLETE] marker(s) are still in the text")
    if not MIN_WORDS <= total <= MAX_WORDS:
        problems.append(f"{total} words; the brief asks for {MIN_WORDS} to {MAX_WORDS} excluding appendices")
    if problems:
        message = "; ".join(problems)
        if args.final:
            raise SystemExit(f"FINAL export stopped: {message}.")
        print(f"WARNING (draft export): {message}.\n")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    docx_path, pdf_path = out_dir / "technical_report.docx", out_dir / "technical_report.pdf"
    resource_path = f"{REPORT_DIR}{';' if sys.platform == 'win32' else ':'}{REPO_ROOT / 'docs'}"

    run(["pandoc", str(MARKDOWN), "-f", "gfm", "-o", str(docx_path), "--toc", f"--resource-path={resource_path}"])
    print(f"Written: {docx_path}")

    browser = find_browser()
    if not browser:
        print("No Chrome or Edge found: the PDF was not written (open the DOCX and use Save as PDF).")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        css_file, html_file = Path(tmp) / "report.css", Path(tmp) / "report.html"
        css_file.write_text(CSS, encoding="utf-8")
        run(["pandoc", str(MARKDOWN), "-f", "gfm", "-s", "--embed-resources", "--metadata", "pagetitle=Technical report",
             "-c", str(css_file), f"--resource-path={resource_path}", "-o", str(html_file)])
        run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
             html_file.as_uri()])
    print(f"Written: {pdf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
