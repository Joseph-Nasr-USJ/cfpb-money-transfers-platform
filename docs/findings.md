# Findings

This analysis covers the CFPB Money Transfers and Digital Payments domain using the curated complaint dataset loaded into MongoDB. The full historical run produced 205,500 curated complaints after filtering, validation and quality checks. The analyses are descriptive and diagnostic: they describe patterns in published CFPB complaints and should not be interpreted as measures of market size, product usage, consumer harm or causal effects.

## Q1 — Growth and Emerging Issues — Demo Question

**Question:** Which sub-products and issues grew fastest over 2021 to 2025, and how did the mobile or digital wallet share of the domain change?

Domestic (US) money transfer showed the strongest increase in complaint volume among the comparable major sub-products, rising from 3,069 complaints in 2021 to 57,853 in 2025. Mobile or digital wallet complaints also increased from 6,405 to 17,149, while virtual currency increased from 2,403 to 5,534 and international money transfer increased from 1,258 to 2,386. The average mobile or digital wallet share of monthly domain complaints fell from 43.48% in 2021 to 35.26% in 2024 before increasing again to 38.71% in 2025.

The Spark MLlib emerging-issues analysis examined the last 24 complete months, from November 2024 through October 2026. It evaluated 43 issue/sub-product models using Linear Regression on each issue's monthly share. No issue met all three pre-declared emerging thresholds: slope of at least +0.2 percentage points per month, R² of at least 0.5, and at least 50 complaints in the window. Therefore, the valid ML result is that **no issue was classified as emerging** during this analysis window.

**Key numbers**
- Domestic money transfer: 3,069 complaints in 2021 → 57,853 in 2025.
- Mobile/digital wallet: 6,405 → 17,149.
- Virtual currency: 2,403 → 5,534.
- International money transfer: 1,258 → 2,386.
- Wallet share: 43.48% in 2021, 37.16% in 2022, 37.50% in 2023, 35.26% in 2024 and 38.71% in 2025.
- ML issue models evaluated: 43.
- Issues classified as emerging: 0.

**Charts and outputs**
- `analytics/output/q1_monthly_growth.png`
- `analytics/output/q1_wallet_share.png`
- `analytics/output/q1_monthly_subproducts.csv`
- `analytics/output/q1_wallet_share.csv`
- `analytics/output/ml_emerging_issues.csv`

**Caution:** Growth in complaints does not establish growth in product usage, market share or consumer harm. CFPB categories have changed over time, and trend results should not be interpreted as forecasts. The ML model identifies changes in the share of published complaints only.

---

