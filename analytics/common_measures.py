
"""
Shared calculation functions for the CFPB analytics scripts.

These functions work on aggregated values returned by
MongoDB or Spark. They do not read individual complaints.
"""

from datetime import date


def percentage(part, total):
    """Calculate a percentage, or return None if undefined."""
    if total is None or total == 0 or part is None:
        return None

    return round(100 * part / total, 2)


def percentage_change(current, previous):
    """Calculate percentage change between two counts."""
    if current is None or previous is None or previous == 0:
        return None

    return round(100 * (current - previous) / previous, 2)


def rolling_share(numerators, denominators, window=12):
    """
    Calculate rolling percentages from aggregated counts.

    Returns one percentage per period, using up to
    the previous 'window' periods.
    """
    if len(numerators) != len(denominators):
        raise ValueError("Counts must have the same length.")

    if window < 1:
        raise ValueError("Window must be at least 1.")

    results = []

    for index in range(len(numerators)):
        start = max(0, index - window + 1)

        numerator_total = sum(numerators[start:index + 1])
        denominator_total = sum(denominators[start:index + 1])

        results.append(
            percentage(numerator_total, denominator_total)
        )

    return results


def is_complete_month(year, month, today=None):
    """Return True when a calendar month has finished."""
    if today is None:
        today = date.today()

    return (year, month) < (today.year, today.month)


def is_complete_year(year, today=None):
    """Return True when a calendar year has finished."""
    if today is None:
        today = date.today()

    return year < today.year
