"""Build docs/presentation/slides_draft.pptx (the draft deck of the demonstration).

    python docs/presentation/build_slides.py

Needs python-pptx (pip install python-pptx). One slide per step of the 8-step demonstration plus the framing slides
(see slides_outline.md). The slides of Loutchiana (problem, scope, architecture, tools) are complete; the slides of the
other presenters hold the facts that come from the repository and a marked frame for their evidence screenshot.
Every [TO COMPLETE ...] marker is a gap to fill before the presentation. Rebuild after editing this file.
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

HERE = Path(__file__).resolve().parent
OUT = HERE / "slides_draft.pptx"
DIAGRAM = HERE.parent / "images" / "architecture.png"
IMAGES = HERE.parent / "images"

# Palette: deep petrol and teal (data and finance), one warm accent used sparingly.
NAVY, TEAL, AMBER = "0B2A3A", "1B998B", "F4A259"
INK, MUTED, WHITE, TINT, PALE = "1F2933", "52616B", "FFFFFF", "E4F2F0", "F3F6F7"
HEAD, BODY = "Cambria", "Calibri"
W, H = 13.333, 7.5


def rgb(hex_value):
    return RGBColor.from_string(hex_value)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]


# ---------- helpers ----------

def background(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb(color)


def text(slide, x, y, w, h, content, size=16, bold=False, color=INK, font=BODY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False, name=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.05)
    frame.margin_top = frame.margin_bottom = Inches(0.03)
    frame.vertical_anchor = anchor
    lines = content if isinstance(content, list) else [content]
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        run = paragraph.add_run()
        run.text = line
        run.font.size, run.font.bold, run.font.italic = Pt(size), bold, italic
        run.font.color.rgb, run.font.name = rgb(color), font
    return box


def bullets(slide, x, y, w, h, items, size=16, color=INK, gap=8, name=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.05)
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(gap)
        properties = paragraph._p.get_or_add_pPr()
        properties.set("marL", str(Emu(Inches(0.28))))
        properties.set("indent", str(-Emu(Inches(0.28))))
        for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
            for found in properties.findall(qn(tag)):
                properties.remove(found)
        color_el = etree.SubElement(properties, qn("a:buClr"))
        etree.SubElement(color_el, qn("a:srgbClr")).set("val", TEAL)
        etree.SubElement(properties, qn("a:buChar")).set("char", "•")
        run = paragraph.add_run()
        run.text = item
        run.font.size, run.font.name = Pt(size), BODY
        run.font.color.rgb = rgb(color)
    return box


def shape(slide, kind, x, y, w, h, fill=None, line=None, line_width=1.0, dash=False, name=None):
    item = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        item.name = name
    if fill:
        item.fill.solid()
        item.fill.fore_color.rgb = rgb(fill)
    else:
        item.fill.background()
    if line:
        item.line.color.rgb = rgb(line)
        item.line.width = Pt(line_width)
        if dash:
            item.line.dash_style = MSO_LINE.DASH
    else:
        item.line.fill.background()
    item.shadow.inherit = False
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        item.adjustments[0] = 0.06
    return item


def card(slide, x, y, w, h, title, body=None, fill=PALE, title_size=18, body_size=15, title_color=NAVY):
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill)
    text(slide, x + 0.2, y + 0.15, w - 0.4, 0.5, title, size=title_size, bold=True, color=title_color, font=HEAD)
    if body:
        text(slide, x + 0.2, y + 0.75, w - 0.4, h - 0.9, body, size=body_size, color=INK)


def badge(slide, x, y, label, fill=TEAL, color=WHITE, d=0.62):
    circle = shape(slide, MSO_SHAPE.OVAL, x, y, d, d, fill=fill)
    frame = circle.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.CENTER
    run = paragraph.add_run()
    run.text = label
    run.font.size, run.font.bold, run.font.name = Pt(20), True, HEAD
    run.font.color.rgb = rgb(color)


def placeholder(slide, x, y, w, h, label):
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=TINT, line=TEAL, line_width=1.5, dash=True,
          name="Evidence placeholder")
    text(slide, x + 0.2, y, w - 0.4, h, label, size=15, color=MUTED, italic=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)


def evidence_picture(slide, x, y, w, h, file_name, crop, caption):
    """Place a cropped screenshot from docs/images inside the box x, y, w, h (inches), centred, with a caption."""
    from io import BytesIO
    from PIL import Image
    image = Image.open(IMAGES / file_name).crop(crop)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    ratio = image.width / image.height
    pic_w, pic_h = w, w / ratio
    if pic_h > h - 0.5:
        pic_h = h - 0.5
        pic_w = pic_h * ratio
    left = x + (w - pic_w) / 2
    top = y + (h - 0.5 - pic_h) / 2
    shape(slide, MSO_SHAPE.RECTANGLE, left - 0.04, top - 0.04, pic_w + 0.08, pic_h + 0.08, fill=WHITE, line=TEAL, line_width=1)
    slide.shapes.add_picture(buffer, Inches(left), Inches(top), width=Inches(pic_w), height=Inches(pic_h))
    text(slide, x, y + h - 0.45, w, 0.4, caption, size=12, color=MUTED, italic=True, align=PP_ALIGN.CENTER)


def stat_card(slide, x, y, w, h, title, lines):
    """A navy card with a big word and short lines (used when the evidence is a few numbers)."""
    shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=NAVY)
    text(slide, x + 0.2, y + 0.15, w - 0.4, 0.8, title, size=34, bold=True, color=AMBER, font=HEAD, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    bullets(slide, x + 0.25, y + 1.1, w - 0.5, h - 1.3, lines, size=15, gap=6, color=WHITE)


def content_slide(title, step=None, presenter=None, notes=None, number=None):
    slide = prs.slides.add_slide(BLANK)
    background(slide, WHITE)
    left = 0.6
    if step is not None:
        badge(slide, 0.6, 0.42, str(step))
        left = 1.45
    text(slide, left, 0.35, W - left - 0.6, 0.8, title, size=34, bold=True, color=NAVY, font=HEAD,
         anchor=MSO_ANCHOR.MIDDLE, name="Title")
    footer = "Group 5  |  020IABDM2 Big Data Frameworks"
    if presenter:
        footer = f"Presenter: {presenter}  |  {footer}"
    text(slide, 0.6, 7.0, 9.5, 0.3, footer, size=11, color=MUTED)
    if number:
        text(slide, W - 1.4, 7.0, 0.8, 0.3, str(number), size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        slide.notes_slide.notes_text_frame.text = notes
    return slide


def table(slide, x, y, w, col_widths, rows, header=True, size=14, row_h=0.62):
    graphic = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = graphic.table
    tbl.first_row = header
    for index, width in enumerate(col_widths):
        tbl.columns[index].width = Inches(width)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.05)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            is_head = header and r == 0
            cell.fill.fore_color.rgb = rgb(NAVY if is_head else (PALE if r % 2 == 0 else WHITE))
            frame = cell.text_frame
            frame.word_wrap = True
            paragraph = frame.paragraphs[0]
            run = paragraph.add_run()
            run.text = value
            run.font.size = Pt(size)
            run.font.bold = is_head or c == 0
            run.font.name = BODY
            run.font.color.rgb = rgb(WHITE if is_head else INK)
    return tbl


# ---------- 1. title ----------
s = prs.slides.add_slide(BLANK)
background(s, NAVY)
text(s, 0.9, 1.5, 11.5, 1.6, "Banking Complaints Data Platform", size=48, bold=True, color=WHITE, font=HEAD,
     anchor=MSO_ANCHOR.BOTTOM, name="Title")
text(s, 0.9, 3.25, 11.5, 0.7, "Option 5: Money Transfers and Digital Payments", size=28, color="9ED8CF", font=HEAD)
text(s, 0.9, 4.35, 11.5, 0.5, "Group 5  |  020IABDM2 Big Data Frameworks  |  ESIB, USJ  |  30 November 2026", size=18, color=WHITE)
text(s, 0.9, 5.0, 11.5, 0.9, "Marwa Zeineddine, Joseph Nasr, Christopher Al Hassrouty, Perla Boustany, Loutchiana Marie, "
     "Charbel Mazraani", size=16, color="C9D6DC")
s.notes_slide.notes_text_frame.text = ("Good morning. We are Group 5 and we chose option 5: money transfers and digital payments. "
                                       "Fifteen minutes of live demonstration, then five minutes of questions.")

# ---------- 2. problem and users ----------
s = content_slide("The problem and who it serves", presenter="Loutchiana", number=2, notes=(
    "Our users are policy analysts in payments oversight, service and operations managers, and the person who maintains "
    "the platform. The project question is from the brief: how can a small team turn public complaint records into useful "
    "evidence while making clear what those records can and cannot tell us."))
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 1.55, 4.9, 4.95, fill=NAVY)
text(s, 0.9, 1.8, 4.3, 0.4, "THE PROJECT QUESTION", size=13, bold=True, color="9ED8CF")
text(s, 0.9, 2.35, 4.3, 3.9, "How can a small data engineering team turn public complaint records into useful evidence, "
     "while making clear what those records can and cannot tell us?", size=22, color=WHITE, font=HEAD, italic=True)
card(s, 5.85, 1.55, 6.9, 1.5, "Policy analysts in payments oversight", "Which issues and sub-products are growing?", body_size=15)
card(s, 5.85, 3.25, 6.9, 1.5, "Service and operations managers", "Submission channels, response categories, timely-response rates", body_size=15)
card(s, 5.85, 4.95, 6.9, 1.55, "The platform maintainer", "Run logs, quality reports and a freshness indicator to operate and recover", body_size=15)

# ---------- 3. scope ----------
s = content_slide("Scope: money transfers and digital payments", presenter="Loutchiana", number=3, notes=(
    "We chose option 5. The domain is defined by one file, config/product_mapping.csv. The current CFPB label plus three legacy "
    "labels used before April 2017 are mapped into it, and the original label is kept next to ours. The legacy mapping is "
    "still to be approved by the lecturer. We compare four core sub-products. The CFPB API returned 199,152 records for the "
    "current label on 20 November."))
table(s, 0.6, 1.55, 8.1, [3.4, 2.1, 2.6], [
    ["Source product", "Sub-products", "Standard category"],
    ["Money transfer, virtual currency, or money service", "all", "same label"],
    ["Money transfers (legacy)", "all", "current label"],
    ["Virtual currency (legacy)", "all", "Virtual currency"],
    ["Prepaid card (legacy)", "Mobile wallet only", "Mobile or digital wallet"],
], size=14, row_h=0.78)
text(s, 0.6, 5.65, 8.1, 0.4, "FOUR CORE SUB-PRODUCTS COMPARED", size=13, bold=True, color=TEAL)
for index, label in enumerate(["Domestic transfer", "International transfer", "Mobile or digital wallet", "Virtual currency"]):
    chip = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6 + index * 2.05, 6.05, 1.95, 0.62, fill=TINT)
    chip.adjustments[0] = 0.3
    text(s, 0.6 + index * 2.05, 6.05, 1.95, 0.62, label, size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 9.1, 1.55, 3.65, 3.2, fill=NAVY)
text(s, 9.1, 1.85, 3.65, 1.1, "199,152", size=48, bold=True, color=WHITE, font=HEAD, align=PP_ALIGN.CENTER,
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 9.3, 3.0, 3.25, 1.5, "complaints with the current label (CFPB API, 20 Nov 2026)", size=16, color="C9D6DC",
     align=PP_ALIGN.CENTER)
card(s, 9.1, 4.95, 3.65, 1.7, "Descriptive only", "What was reported, not why. No prediction.", body_size=15)

# ---------- 4. architecture ----------
s = content_slide("Architecture: seven layers, one purpose each", presenter="Loutchiana", number=4, notes=(
    "Seven layers following the course framework. One: Apache NiFi collects every 24 hours and keeps provenance; a tested Python "
    "collector is the fallback. Two: MinIO keeps raw files unchanged. Three: Spark cleans, deduplicates and checks quality; a "
    "failing check stops the run. Four: the trusted data is Parquet, rejected records go to quarantine. Five: MongoDB serves the "
    "dashboard. Six: analysis scripts and two Spark MLlib models describe the data. Seven: Streamlit presents it, with Redis "
    "caching the queries. It is a batch platform refreshed every 24 hours because the CFPB publishes daily and the brief rules "
    "out streaming. Everything starts with one Docker Compose command."))
if DIAGRAM.exists():
    picture_w = 12.1
    picture_h = picture_w * 1264 / 2326
    s.shapes.add_picture(str(DIAGRAM), Inches(0.6), Inches(1.25), width=Inches(picture_w), height=Inches(picture_h))
else:
    placeholder(s, 0.6, 1.3, 12.1, 5.4, "[TO COMPLETE: docs/images/architecture.png is missing]")

# ---------- 5. tools ----------
s = content_slide("Why these tools", presenter="Loutchiana", number=5, notes=(
    "Every tool has one job and an alternative we rejected. NiFi gives scheduling and provenance; Kafka and Flume are for streaming. "
    "MinIO is object storage without a cluster. Spark runs the same code locally as on a cluster; Spark Streaming needs a live "
    "stream. Parquet is columnar and compressed. MongoDB's document model fits filters on many fields. MLlib describes, it does "
    "not predict. Redis caches dashboard queries for ten minutes."))
table(s, 0.6, 1.4, 12.1, [1.75, 3.15, 4.2, 3.0], [
    ["Layer", "Tool", "Why", "Rejected"],
    ["Collection", "Apache NiFi, Python fallback", "Schedule and provenance of every run", "Kafka, Flume, Sqoop"],
    ["Raw storage", "MinIO", "Files kept unchanged, S3-compatible", "HDFS, Ceph"],
    ["Processing", "Spark DataFrames, local", "Lazy and cached; same code on a cluster", "Spark Streaming"],
    ["Curated", "Parquet", "Columnar, compressed, schema inside", "CSV, ORC"],
    ["Serving", "MongoDB", "Filters on many fields, indexes, upserts", "Key-value, graph"],
    ["Analytics", "Spark MLlib", "Describes trends and groups", "Forecasting"],
    ["Presentation", "Streamlit and Redis", "Aggregates only; cache with 10 min TTL", "None"],
], size=14, row_h=0.66)

# ---------- 6. step 2 ----------
s = content_slide("Historical ingestion: the raw manifest", step=2, presenter="Marwa (1:30)", number=6, notes=(
    "The full CSV was downloaded once and stored exactly as received; raw files are never edited or overwritten. The manifest records "
    "the source, the time, the record count and the checksum, so anyone can verify the file."))
bullets(s, 0.6, 1.55, 6.0, 4.8, [
    "Full CSV ZIP downloaded once, stored exactly as received",
    "ZIP and extracted CSV side by side, never overwritten",
    "manifest.json: source URL, start and end time, size, SHA-256, record count",
    "A second identical download is logged as skipped, not stored twice",
], size=18, gap=12)
stat_card(s, 6.95, 1.55, 5.8, 4.8, "19,397,176", ["records in the file of 24 Nov 2026", "complaints.csv.zip: 354.0 MiB",
          "complaints.csv: 5.5 GiB", "manifest.json: 1.1 KiB", "SHA-256 8b6db08e...59dca2",
          "Screenshot: docs/images/minio_raw_full_load.png (run of 22 Nov); manifest of 24 Nov in docs/evidence/"])

# ---------- 7. step 3 ----------
s = content_slide("A bounded incremental run", step=3, presenter="Marwa (2:30)", number=7, notes=(
    "The run uses a bounded date window starting at the high-water mark minus the overlap. Each response is stored in MinIO before it is "
    "processed. The run log records the run id, window, status, retries, outcome, record count and checksum. The high-water mark moves "
    "only after a successful run, and an empty success is different from a failed request."))
bullets(s, 0.6, 1.55, 6.0, 4.8, [
    "Window: high-water mark minus 21 days, bounded by dates",
    "Paged with search_after; timeout and 3 retries (2, 4, 8 s)",
    "Every page saved unchanged before any processing",
    "Run log: id, window, status, retries, outcome, count, checksum",
    "High-water mark moves only after full success",
], size=18, gap=12)
placeholder(s, 6.95, 1.55, 5.8, 4.8, "[TO COMPLETE: screenshot of the raw folder and the run log (Marwa)]")

# ---------- 8. step 4 ----------
s = content_slide("Spark: quality checks and reconciliation", step=4, presenter="Joseph (2:30)", number=8, notes=(
    "Spark uses an explicit schema, standardises names, parses dates, normalises Yes and No, keeps our domain and deduplicates by "
    "Complaint ID. Bad records go to quarantine with a reason. The quality report has six dimensions with thresholds fixed in advance. "
    "Reconciliation: raw equals curated plus quarantined plus out of domain plus duplicates removed. A failure exits with code 1 "
    "and publishes nothing."))
for index, label in enumerate(["Uniqueness", "Completeness", "Validity", "Consistency", "Freshness", "Reconciliation"]):
    col, row = index % 3, index // 3
    chip = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6 + col * 2.75, 1.55 + row * 1.0, 2.6, 0.82, fill=TINT)
    chip.adjustments[0] = 0.25
    text(s, 0.6 + col * 2.75, 1.55 + row * 1.0, 2.6, 0.82, label, size=18, bold=True, color=NAVY,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.6, 3.75, 8.1, 1.2, fill=NAVY)
text(s, 0.8, 3.75, 7.7, 1.2, "raw = curated + quarantined + out of domain + duplicates removed", size=20, bold=True,
     color=WHITE, font=HEAD, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
bullets(s, 0.6, 5.2, 8.1, 1.7, [
    "A FAIL stops the run: Spark exits with code 1, nothing is published",
    "Known bad records are caught (defect D-005)",
], size=16, gap=6)
stat_card(s, 9.0, 1.55, 3.75, 5.2, "PASS", ["Full load of 24 Nov 2026", "19,397,176 raw records", "19,191,793 out of domain",
          "112 quarantined", "205,271 curated", "0 duplicates removed", "(run 20261124T135857Z_full)"])

# ---------- 9. step 5 ----------
s = content_slide("Rerun: the counts are not inflated", step=5, presenter="Joseph (1:30)", number=9, notes=(
    "Deduplication by Complaint ID in Spark and upserts in MongoDB make the run idempotent: running the same window twice leaves the "
    "curated count and the dashboard measures unchanged."))
bullets(s, 0.6, 1.55, 6.0, 4.8, [
    "One record per Complaint ID, with a documented tie-break",
    "Latest ingestion wins; the API beats the full load",
    "MongoDB upserts in batches of 5,000: no second copy",
    "Same window twice: identical curated and MongoDB counts",
], size=18, gap=12)
placeholder(s, 6.95, 1.55, 5.8, 4.8, "[TO COMPLETE: counts before and after the rerun (Joseph)]")

# ---------- 10. step 6 ----------
s = content_slide("MongoDB: collections, indexes, one query", step=6, presenter="Christopher (2:00)", number=10, notes=(
    "One document per complaint with the Complaint ID as _id and native dates. Compound indexes match the dashboard filters, equality "
    "field first and then the date. Every aggregation starts with $match so the indexes are used."))
card(s, 0.6, 1.55, 3.9, 4.9, "Collections", None)
bullets(s, 0.8, 2.3, 3.5, 4.1, ["complaints", "agg_monthly", "agg_company_year", "pipeline_runs", "quality_reports",
                                  "ml_emerging_issues", "ml_state_clusters"], size=16, gap=5)
card(s, 4.7, 1.55, 3.9, 4.9, "Five compound indexes", None)
bullets(s, 4.9, 2.3, 3.5, 4.1, ["sub-product, date", "issue, date", "state, date", "company, date", "channel, date"],
        size=16, gap=5)
text(s, 4.9, 5.05, 3.5, 1.3, "Equality field first, date last. Dates are native BSON Date values.", size=14, color=MUTED)
stat_card(s, 8.9, 1.55, 3.85, 4.9, "205,271", ["complaints in MongoDB", "73,597 monthly summaries", "8,078 company-year summaries",
          "Query on state and date: index scan on state_date_idx (run of 22 Nov)", "(run of 24 Nov)"])

# ---------- 11. step 7 ----------
s = content_slide("Dashboard: answering Q1 and Q2", step=7, presenter="Perla (2:00)", number=11, notes=(
    "Show the dashboard answering the two pre-declared questions, with the denominator, the partial-period label and the caution."))
card(s, 0.6, 1.55, 5.9, 1.75, "Q1", "Which sub-products and issues grew fastest in 2021 to 2025, and how did the wallet share change?", body_size=15)
card(s, 0.6, 3.5, 5.9, 1.75, "Q2", "How did the fraud-or-scam share change across the four core sub-products since 2018?", body_size=15)
text(s, 0.6, 5.5, 5.9, 1.2, "Raw counts and percentages in each group. The issue is chosen by the consumer; a trend is not a forecast.",
     size=14, color=MUTED)
placeholder(s, 6.85, 1.55, 5.9, 5.1, "[TO COMPLETE: dashboard screenshots for Q1 and Q2, with the Spark MLlib emerging-issues result (Perla)]")

# ---------- 12. findings ----------
s = content_slide("What we found", presenter="Perla, Loutchiana", number=12, notes=(
    "Three or four findings, each with its number, denominator, period and caution. Source: docs/findings.md (ready on Tue 24 Nov)."))
for index in range(3):
    card(s, 0.6 + index * 4.1, 1.55, 3.9, 4.6, f"Finding {index + 1}",
         "[TO COMPLETE from docs/findings.md: the number, the denominator, the period and the caution]", body_size=15)
text(s, 0.6, 6.3, 12.1, 0.5, "Every number must be identical in the dashboard, the findings and the report.", size=14, color=MUTED)

# ---------- 13. step 8 ----------
s = content_slide("Two limitations to keep in mind", step=8, presenter="Charbel (1:30)", number=13, notes=(
    "First: the data is not a random sample, so we describe complaints and do not generalise. Second: single-node MongoDB and a local "
    "daily batch. Recovery means rerunning the idempotent pipeline; there is no replication."))
card(s, 0.6, 1.55, 5.95, 3.9, "1. Not a random sample",
     "Complaints come from people who chose to complain. We describe the published complaints and do not generalise. "
     "No transactions, no confirmed fraud, no resolution time. Company figures are shares, never a ranking.", body_size=20)
card(s, 6.8, 1.55, 5.95, 3.9, "2. Single node, daily batch",
     "If the database volume is lost, recovery means rerunning the idempotent pipeline. There is no replication, and the data is "
     "refreshed every 24 hours, not in real time.", body_size=20)

# ---------- 14. improvement ----------
s = content_slide("Next improvement: a MongoDB replica set", presenter="Charbel", number=14, notes=(
    "A replica set with automatic primary election, majority writes and reads from the primary (Session 4.1). Sharding is not needed "
    "at about 200,000 documents."))
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.9, 2.2, 3.2, 1.6, fill=NAVY)
text(s, 0.9, 2.2, 3.2, 1.6, "Primary", size=24, bold=True, color=WHITE, font=HEAD, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
for index, label in enumerate(["Secondary", "Secondary"]):
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.9 + index * 1.75, 4.6, 1.45, 1.2, fill=TINT)
    text(s, 0.9 + index * 1.75, 4.6, 1.45, 1.2, label, size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
for index in range(2):
    connector = s.shapes.add_connector(1, Inches(2.5), Inches(3.8), Inches(1.62 + index * 1.75), Inches(4.6))
    connector.line.color.rgb = rgb(TEAL)
    connector.line.width = Pt(2)
bullets(s, 5.0, 1.9, 7.7, 4.6, [
    "Automatic election of a new primary if one node fails",
    "Majority writes and reads from the primary favour consistency",
    "Today: one node, so no network partition can occur",
    "Sharding is not needed at about 200,000 documents",
], size=20, gap=16)

# ---------- 15. team ----------
s = prs.slides.add_slide(BLANK)
background(s, NAVY)
text(s, 0.6, 0.35, 12.1, 0.8, "The team and the evidence", size=34, bold=True, color=WHITE, font=HEAD, anchor=MSO_ANCHOR.MIDDLE, name="Title")
table(s, 0.6, 1.4, 8.3, [2.3, 6.0], [
    ["Member", "Owns"],
    ["Marwa Zeineddine", "Collection: NiFi flow and Python collectors"],
    ["Joseph Nasr", "Repository, Docker, Spark and quality"],
    ["Christopher Al Hassrouty", "MongoDB model, loading, queries"],
    ["Perla Boustany", "Analysis, Spark MLlib, dashboard"],
    ["Loutchiana Marie", "Report, architecture, data dictionary"],
    ["Charbel Mazraani", "README, runbook, tests, demo"],
], size=14, row_h=0.62)
for index, (number, label) in enumerate([("159", "automated tests passing (24 Nov, 1 skipped)"), ("5", "defects found and fixed, all logged"),
                                          ("6", "members, each presenting one step")]):
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 9.3, 1.4 + index * 1.7, 3.45, 1.5, fill="14455A")
    text(s, 9.3, 1.4 + index * 1.7, 1.35, 1.5, number, size=40, bold=True, color=AMBER, font=HEAD, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 10.6, 1.4 + index * 1.7, 2.05, 1.5, label, size=14, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.6, 7.0, 9.5, 0.3, "Group 5  |  020IABDM2 Big Data Frameworks", size=11, color="9FB3BD")
text(s, W - 1.4, 7.0, 0.8, 0.3, "15", size=11, color="9FB3BD", align=PP_ALIGN.RIGHT)
s.notes_slide.notes_text_frame.text = "Update the test count from the latest dated result in docs/evidence/ before the presentation."

prs.save(str(OUT))
print(f"Written: {OUT}  ({len(prs.slides)} slides)")
