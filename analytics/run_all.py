
"""
Run all five CFPB descriptive analytics questions.

Usage:
    python -m analytics.run_all

The Makefile's 'make analytics' target runs this module.

Each analysis queries genuine MongoDB aggregates and
writes its output files to analytics/output/.
"""

from datetime import datetime, timezone

from analytics import (
    q1_growth,
    q2_fraud,
    q3_channels,
    q4_responses,
    q5_geography,
)


def run():
    """Execute Q1 through Q5 in sequence."""

    start_time = datetime.now(timezone.utc)

    print("=" * 55)
    print("CFPB MONEY TRANSFERS - ANALYTICS")
    print("=" * 55)
    print(f"Started at: {start_time.isoformat()}")

    analyses = [
        ("Q1 - Growth", q1_growth.run),
        ("Q2 - Fraud or Scam", q2_fraud.run),
        ("Q3 - Submission Channels", q3_channels.run),
        ("Q4 - Company Responses", q4_responses.run),
        ("Q5 - Geography", q5_geography.run),
    ]

    completed = []
    failures = []

    for name, analysis_function in analyses:

        print()
        print("-" * 55)
        print(f"Running {name}")
        print("-" * 55)

        try:
            analysis_function()
            completed.append(name)

        except Exception as error:
            print(f"ERROR in {name}: {error}")
            failures.append((name, str(error)))

    finish_time = datetime.now(timezone.utc)

    print()
    print("=" * 55)
    print("ANALYTICS EXECUTION SUMMARY")
    print("=" * 55)

    for name in completed:
        print(f"SUCCESS: {name}")

    for name, error in failures:
        print(f"FAILED: {name} - {error}")

    print()
    print(f"Completed: {len(completed)} / {len(analyses)}")
    print(f"Finished at: {finish_time.isoformat()}")

    duration = (finish_time - start_time).total_seconds()
    print(f"Duration: {duration:.2f} seconds")

    print()
    print("Output directory: analytics/output/")

    if failures:
        raise RuntimeError(
            f"{len(failures)} analytics task(s) failed."
        )

    print("All five analytics scripts executed successfully.")
    print(
        "Note: successful execution does not guarantee "
        "that the database contains complaint records."
    )


if __name__ == "__main__":
    run()
