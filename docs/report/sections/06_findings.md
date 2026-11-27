<!--
Section 6. Findings
Owner: Perla Boustany
Target: 500 words | Draft due: Wed 25 Nov
To cover: Reproducible analysis Q1 to Q5, chart definitions, comparison denominators, the two Spark MLlib results with method, rule and caution, implications for the intended user. Source: docs/findings.md.
How to write it: replace the line starting with "_Draft pending_" below by your text and keep the heading.
Use the same terms as the rest of the report ("processing lag", "share of complaints"). Descriptive and
diagnostic language only: no causal claims, no company quality ranking. Never write secrets.
Run "python docs/report/build_report.py --check" to see your word count.
-->

## 6. Findings

The reference full load processed on 24 Nov 2026 contained 205,271 curated complaints. The analysis presented here used a later fixed MongoDB snapshot from 25 Nov 2026 containing 205,500 complaints, after the scheduler had added subsequent API complaints. All counts and percentages reported in this section were calculated from that same 205,500-complaint analytical snapshot.

Q1 examined growth in sub-products and issues from 2021 to 2025. Domestic (US) money transfer increased from 3,069 complaints to 57,853, while mobile or digital wallet increased from 6,405 to 17,149. The average mobile-wallet share of monthly domain complaints fell from 43.48% in 2021 to 35.26% in 2024, then rose to 38.71% in 2025. These are complaint trends, not measures of product usage, market share or consumer harm.

Q2 compared the “Fraud or scam” share within the four core sub-products. Virtual currency had the highest share at 34.08%, followed by mobile or digital wallet at 28.35%, international money transfer at 24.32%, and domestic money transfer at 18.94%. Mobile or digital wallet recorded 18,426 fraud-or-scam complaints and domestic money transfer 16,985. The Q2 charts compare fraud-or-scam share within each core sub-product and its rolling trend. Because the issue is consumer-selected, these figures do not represent independently verified fraud.

Q3 showed a strong shift toward Web submissions. Web represented 91.58% of complaints in 2021 and 98.36% in 2025, while Phone declined from 5.66% to 1.20%. Across the analytical snapshot, Web represented 93.30% of submissions. The Q3 channel chart uses all complaints in each year as the denominator. This change may reflect CFPB collection or routing procedures rather than consumer preference.

Q4 found an overall timely-response rate of 98.29% and a median processing lag of 0 days. Domestic money transfer had a 99.28% timely-response rate, mobile or digital wallet 98.51%, virtual currency 96.67%, and international money transfer 95.59%. Same-day referral accounted for 87.42% of complaints. Timeliness does not measure customer satisfaction, and processing lag is the interval from CFPB receipt to referral, not company resolution time.

Q5 showed the largest raw complaint shares in California at 11.98%, Texas at 9.07%, and Florida at 8.07%. A further 4.99% of records had no state and were labelled “Unknown”. The Q5 state views compare raw complaint shares and issue profiles. These geographic comparisons are not normalised by population, number of customers or product usage.

Two Spark MLlib analyses added descriptive and diagnostic structure. Emerging issues used LinearRegression on monthly issue share within each sub-product over the last 24 complete months. The pre-declared rule required a slope of at least +0.2 percentage points per month, R² of at least 0.5, and at least 50 complaints. Forty-three models were evaluated and none met all three conditions. State segmentation used KMeans on issue-mix and submission-channel shares for states with at least 100 complaints. Testing k=2 through k=6 selected k=2 with a silhouette score of 0.695668.

For a policy or service analyst, these results identify where complaint patterns differ and where further investigation may be useful. They do not forecast future complaints, establish causation, measure geographic risk, or rank company service quality.