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




## Q4 — Company Responses and Processing Lag

**Question:** How do response categories and timely-response rates differ across sub-products?

Across all 205,500 curated complaints, 98.29% of complaints with a valid timely-response value were marked as timely. Domestic money transfer had a timely-response rate of 99.28%, mobile or digital wallet 98.51%, virtual currency 96.67%, and international money transfer 95.59%. Debt settlement had the lowest rate among the displayed sub-products at 86.03%.

The median interval between complaint receipt and referral to the company was 0 days. In total, 87.42% of complaints were referred on the same day, 3.35% after one day, 3.19% after two to three days, and 2.72% after 15 or more days. "Closed with explanation" was the dominant company-response category for several major sub-products, including 93.73% of domestic money-transfer complaints.

**Key numbers**
- Total complaints: 205,500.
- Overall timely-response rate: 98.29%.
- Median processing lag: 0 days.
- Same-day referral: 179,647 complaints, or 87.42%.
- Domestic money transfer timely rate: 99.28%.
- Mobile/digital wallet: 98.51%.
- Virtual currency: 96.67%.
- International money transfer: 95.59%.

**Charts and outputs**
- `analytics/output/q4_timely_responses.png`
- `analytics/output/q4_response_categories.png`
- `analytics/output/q4_processing_lag.png`
- `analytics/output/q4_summary.csv`
- `analytics/output/q4_timely_responses.csv`

**Caution:** A timely response does not measure customer satisfaction or whether the consumer's problem was resolved. Processing lag measures the interval between CFPB receipt and referral to the company, not the company's resolution time. Complaint shares also do not provide a market-share denominator.

---




## Q5 — Geographic Patterns

**Question:** Which states show different complaint and issue profiles?

California had the largest number of complaints, with 24,619 complaints or 11.98% of the complete dataset. Texas followed with 18,646 complaints (9.07%), Florida with 16,582 (8.07%), New York with 13,963 (6.79%), and Illinois with 10,636 (5.18%). State information was unavailable for 10,257 complaints, representing 4.99% of all curated complaints, so these records are explicitly labelled as "Unknown" rather than being dropped.

The Spark MLlib KMeans analysis clustered states according to similarities in their issue-mix and submission-channel shares. Fifty-one states or state-level entities met the minimum threshold of 100 complaints. Testing k values from 2 through 6 selected **k = 2** because it produced the highest silhouette score, **0.695668**, indicating the strongest separation among the tested solutions.

**Key numbers**
- California: 24,619 — 11.98%.
- Texas: 18,646 — 9.07%.
- Florida: 16,582 — 8.07%.
- New York: 13,963 — 6.79%.
- Unknown state: 10,257 — 4.99%.
- States included in KMeans: 51.
- Selected clusters: k = 2.
- Silhouette score: 0.695668.
- Random seed: 42.

**Charts and outputs**
- `analytics/output/q5_state_counts.png`
- `analytics/output/q5_issue_share_heatmap.png`
- `analytics/output/q5_state_totals.csv`
- `analytics/output/q5_state_issue_profiles.csv`
- `analytics/output/ml_state_clusters.csv`

**Caution:** Raw state complaint counts are not normalized by population, product usage or the number of customers. Population is not the same as the user base. The KMeans groups describe similarities in published complaint profiles and should not be interpreted as geographic risk, consumer quality or company performance.

---




## Machine-Learning Interpretation

### Emerging Issues — Spark MLlib Linear Regression

The emerging-issues analysis used Spark MLlib `LinearRegression` separately for each sub-product and issue combination over the last 24 complete months. The dependent measure was the issue's monthly percentage share within its sub-product, and the month index was used as the explanatory feature. An issue was classified as emerging only when its slope was at least +0.2 percentage points per month, its R² was at least 0.5, and it had at least 50 complaints in the analysis window.

Forty-three models were evaluated and none satisfied all three thresholds. Some issues had positive slopes, but their R² values were below the required threshold. For example, Fraud or scam within Domestic (US) money transfer had a slope of +0.7946 percentage points per month but an R² of only 0.2048, so it was correctly not classified as emerging.

This result does not mean that no complaint category increased. It means that none showed a sufficiently large, consistent and well-supported increase in complaint share under the rule fixed before the model was run.

### State Segmentation — Spark MLlib KMeans

State segmentation used Spark MLlib `KMeans` on features representing each state's issue mix and submission-channel mix. Only states with at least 100 complaints were included. Candidate values from k = 2 through k = 6 were evaluated using the silhouette score, with seed 42 used for reproducibility.

The best result was k = 2 with a silhouette score of 0.695668, so the final model divided the 51 eligible states into two complaint-profile groups. These clusters can help analysts identify states with similar complaint compositions and submission behaviour, but they do not represent levels of consumer risk or service quality.

---




## Overall Interpretation

The analysis shows that published complaints in the Money Transfers and Digital Payments domain have become increasingly concentrated in digital submission channels, with Web accounting for more than 98% of submissions in 2025. Complaint composition also differs substantially by sub-product: Virtual currency has the highest proportional Fraud-or-scam share, while mobile wallets generate the greatest absolute number of Fraud-or-scam complaints among the four core sub-products.

The machine-learning analyses add diagnostic structure without making predictions. The emerging-issues model found no issue satisfying the predefined statistical rule, while KMeans identified two broad groups of states with similar complaint profiles. These findings can support exploratory work by policy analysts and service managers, but the CFPB complaint database is not a random sample of consumers and therefore should not be used to estimate population-level prevalence, product market share or causal effects.
