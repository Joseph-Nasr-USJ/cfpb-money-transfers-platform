"""Draw docs/images/architecture.png (the architecture diagram of docs/architecture.md).

    python docs/images/make_architecture_diagram.py

Needs matplotlib only. The same diagram is written as Mermaid in docs/architecture.md (GitHub renders it);
if you change one, change the other. Layers follow the Conceptual Big Data Framework of Session 2.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "architecture.png"

# Okabe-Ito colour-blind-safe palette (fills are light tints of it).
FILL = {
    "src": "#F2F2F2", "collect": "#DCEBF7", "raw": "#FBE9C6", "proc": "#D3EBE2",
    "cur": "#FBE9C6", "serve": "#F6DDE9", "analytics": "#E9E3F3", "present": "#F9E3D2",
}
EDGE = "#333333"

fig, ax = plt.subplots(figsize=(17.4, 9.4))
ax.set_xlim(0, 17.4)
ax.set_ylim(0, 9.4)
ax.axis("off")


def box(cx, cy, w, h, title, lines, fill, badge=None):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fill, ec=EDGE, lw=1.4))
    ax.text(cx, cy + h / 2 - 0.30, title, ha="center", va="center", fontsize=11.5, fontweight="bold")
    ax.text(cx, cy - 0.22, "\n".join(lines), ha="center", va="center", fontsize=9.3, linespacing=1.45)
    if badge:
        ax.add_patch(plt.Circle((cx - w / 2 + 0.05, cy + h / 2 - 0.05), 0.24, fc="#222222", ec="white", lw=1.5, zorder=5))
        ax.text(cx - w / 2 + 0.05, cy + h / 2 - 0.05, badge, ha="center", va="center", color="white",
                fontsize=10.5, fontweight="bold", zorder=6)


def arrow(p, q, label=None, dashed=False, rad=0.0, lx=0.0, ly=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=17, lw=1.7, color="#222222",
                                 linestyle=(0, (5, 3)) if dashed else "-", connectionstyle=f"arc3,rad={rad}", zorder=4))
    if label:
        ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, ha="center", va="center", fontsize=8.6,
                style="italic", bbox=dict(fc="white", ec="none", pad=1.2), zorder=7)


ax.text(0.25, 9.05, "Banking Complaints Data Platform: architecture (option 5, Money Transfers and Digital Payments)",
        fontsize=14, fontweight="bold", va="center")
ax.text(0.25, 8.65, "Batch platform, scheduled every 24 hours. Descriptive and diagnostic analysis only. "
        "Every service runs with Docker Compose (make up).", fontsize=10, va="center", color="#444444")

W, H = 2.4, 2.15
TOP, MID, LOW = 6.75, 4.1, 1.55
X = [1.45, 4.85, 8.25, 11.65, 15.05]

# Row 1: sources -> collection -> raw -> processing -> curated
box(X[0], TOP, 2.0, H, "CFPB sources", ["Full CSV ZIP (once)", "Complaint API", "(every 24 hours)"], FILL["src"])
box(X[1], TOP, W, H, "Collection", ["Apache NiFi flow", "schedule + provenance", "Python collectors", "(tested fallback)"], FILL["collect"], "1")
box(X[2], TOP, W, H, "Raw storage", ["MinIO, bucket cfpb-lake", "raw/ files never edited", "manifests + run logs"], FILL["raw"], "2")
box(X[3], TOP, W, H, "Processing", ["Apache Spark, local mode", "explicit schema, clean,", "deduplicate, quality gate"], FILL["proc"], "3")
box(X[4], TOP, W, H, "Curated storage", ["MinIO: curated/ Parquet", "+ aggregates", "quarantine/ + quality/"], FILL["cur"], "4")

# Row 2: analytics and serving
box(X[3], MID, W, H, "Analytics", ["Q1 to Q5 scripts", "Spark MLlib (descriptive):", "LinearRegression, KMeans"], FILL["analytics"], "6")
box(X[4], MID, W, H, "Serving", ["database/load.py (upserts)", "MongoDB 7.0", "cfpb_money_transfers"], FILL["serve"], "5")

# Row 3: presentation
box(X[2], LOW, W, 1.7, "Cache", ["Redis", "cache-aside, TTL 600 s"], FILL["present"])
box(X[3] + 0.0, LOW, W, 1.7, "Presentation", ["Streamlit dashboard", "port 8501, aggregates only"], FILL["present"], "7")

# Arrows
arrow((X[0] + 1.0, TOP), (X[1] - W / 2, TOP))
arrow((X[1] + W / 2, TOP), (X[2] - W / 2, TOP), "raw files", ly=0.3)
arrow((X[2] + W / 2, TOP), (X[3] - W / 2, TOP), "reads", ly=0.3)
arrow((X[3] + W / 2, TOP), (X[4] - W / 2, TOP), "Parquet", ly=0.3)
arrow((X[4], TOP - H / 2), (X[4], MID + H / 2), "bulk load")
arrow((X[4] - W / 2 + 0.25, TOP - H / 2), (X[3] + W / 2 - 0.25, MID + H / 2), "MLlib reads", lx=-0.75, ly=0.0)
arrow((X[3] + W / 2, MID - 0.35), (X[4] - W / 2, MID - 0.35), "results", ly=-0.3)
arrow((X[4] - W / 2, MID + 0.35), (X[3] + W / 2, MID + 0.35), "queries", ly=0.3)
arrow((X[3] + W / 2, LOW + 0.25), (X[4] - 0.25, MID - H / 2), "cache miss", lx=0.75, ly=-0.1)
arrow((X[3] - W / 2, LOW), (X[2] + W / 2, LOW), "lookup", ly=0.3)

ax.text(0.25, 3.55, "Reads MongoDB only:\nthe dashboard never touches\nthe raw layer and never shows\nindividual complaint records.",
        fontsize=9.5, va="center", color="#222222", bbox=dict(fc="#FFFFFF", ec="#999999", boxstyle="round,pad=0.5"))
ax.text(0.25, 1.55, "Docker Compose services:\nminio, minio-init, mongo, nifi,\npipeline (Python, Java 17, PySpark),\nredis, dashboard",
        fontsize=9.5, va="center", color="#222222", bbox=dict(fc="#FFFFFF", ec="#999999", boxstyle="round,pad=0.5"))

fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
print(f"Written: {OUT}")
