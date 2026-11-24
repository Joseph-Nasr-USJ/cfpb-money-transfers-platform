"""Data lake paths shared by the Spark job, the MongoDB loader and the Spark MLlib scripts.

Every reader and writer of curated data imports these constants, so a path change is made in one
place and the writer and the readers can never point at different folders.

Curated complaints follow the course contract for option 5:
    curated/complaints/option=5/year=YYYY/month=MM/   (four-digit year, two-digit month)
"""

CURATED_DIR = "curated/complaints/option=5"
AGG_MONTHLY_DIR = "curated/aggregates/agg_monthly"
AGG_COMPANY_YEAR_DIR = "curated/aggregates/agg_company_year"


def curated_partition(year: int, month: int) -> str:
    """Folder of one curated partition, e.g. (2024, 3) -> curated/complaints/option=5/year=2024/month=03."""
    if not 1 <= int(month) <= 12:
        raise ValueError(f"month must be between 1 and 12, got {month}")
    return f"{CURATED_DIR}/year={int(year):04d}/month={int(month):02d}"
