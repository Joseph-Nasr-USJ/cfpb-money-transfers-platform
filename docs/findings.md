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



## Q2 — Fraud or Scam — Demo Question

**Question:** How did the "Fraud or scam" share differ across the four core sub-products?

Virtual currency had the highest overall Fraud-or-scam complaint share among the four core sub-products, at 34.08%. Mobile or digital wallet followed at 28.35%, international money transfer at 24.32%, and domestic money transfer at 18.94%. In absolute terms, mobile or digital wallet generated the largest number of Fraud-or-scam complaints among these four groups, with 18,426, followed by domestic money transfer with 16,985.

These results show that the ranking changes depending on whether the comparison is based on the number of complaints or the proportion within each sub-product. Virtual currency has the highest proportional concentration, while mobile wallets have the largest absolute Fraud-or-scam count.

**Key numbers**
- Virtual currency: 7,817 of 22,938 complaints — 34.08%.
- Mobile/digital wallet: 18,426 of 65,002 — 28.35%.
- International money transfer: 4,364 of 17,945 — 24.32%.
- Domestic money transfer: 16,985 of 89,686 — 18.94%.

**Charts and outputs**
- `analytics/output/q2_fraud_monthly.png`
- `analytics/output/q2_fraud_rolling_12m.png`
- `analytics/output/q2_fraud_summary.csv`
- `analytics/output/q2_fraud_monthly.csv`

**Caution:** "Fraud or scam" is a category selected in the complaint process. It does not mean that fraud was independently investigated or verified.

---






## Q3 — Submission Channels

**Question:** Has the mix of submission channels changed over time?

Web submission became increasingly dominant in the complaint dataset. Web represented 91.58% of complaints in 2021, fell temporarily to 87.77% in 2022, then increased to 90.53% in 2023, 91.04% in 2024 and 98.36% in 2025. Over the same period, Phone fell from 5.66% in 2021 to only 1.20% in 2025, while Referral fell from 2.44% to 0.30%.

Across the complete dataset, Web accounts for 191,726 complaints, or 93.30% of all records. Phone accounts for 4.53%, Referral 1.62%, Postal mail 0.48%, Fax 0.07%, and Email is effectively negligible.

**Key numbers**
- Web: 91.58% in 2021 → 98.36% in 2025.
- Phone: 5.66% → 1.20%.
- Referral: 2.44% → 0.30%.
- Overall Web share: 93.30%.

**Charts and outputs**
- `analytics/output/q3_channel_counts.png`
- `analytics/output/q3_channel_shares.png`
- `analytics/output/q3_channels_yearly.csv`
- `analytics/output/q3_channels_summary.csv`

**Caution:** Changes in CFPB submission channels may reflect operational or intake-process changes rather than changes in consumer preferences.

---


