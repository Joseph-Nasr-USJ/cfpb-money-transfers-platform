<!--
Section 2. Problem and scope
Owner: Loutchiana (the questions with Perla)
Target: 350 words | Written: Sat 21 Nov
Facts to confirm before submission: the record count (205,271 curated in the full load of 24 Nov 2026, of which 199,561 current label; the API test of 20 Nov gave 199,152;
Marwa's docs/api_notes.md) against the final quality report; the legacy product labels with the lecturer; the final wording of Q1
to Q5 with Perla.
-->

## 2. Problem and scope

**Problem.** A public-interest organisation that monitors consumer financial complaints needs a dependable way to collect the records the CFPB publishes, check their quality and show what they say to people who do not write code. Our platform turns the CFPB Consumer Complaint Database into evidence for one financial domain and states what the records cannot tell us. The analysis is descriptive and diagnostic (Session 1); it does not predict.

**Intended users.** Policy analysts in payments oversight (which issues and sub-products are growing), service and operations managers (channels, response categories, timely-response rates) and the platform maintainer (run logs, quality reports, freshness).

**Chosen option.** Option 5, money transfers and digital payments: emerging issues, shifts in submission channels and growth rates.

**Filters.** The domain is defined by `config/product_mapping.csv`; original source labels are kept next to our standard categories.

| Source product | Sub-products kept | Standard category |
|---|---|---|
| Money transfer, virtual currency, or money service | all | same label |
| Money transfers (label used before 2017) | all | Money transfer, virtual currency, or money service |
| Virtual currency (legacy label) | all | Virtual currency |
| Prepaid card | Mobile wallet only | Mobile or digital wallet |

Four core sub-products are compared throughout: domestic (US) money transfer, international money transfer, mobile or digital wallet and virtual currency; the rest are grouped as "Other money services". The CFPB API returned 199,152 records for the current label on 20 November 2026. The full load of 24 November keeps 205,271 curated complaints: 199,561 under the current label and 5,710 under the legacy labels of the mapping.

**Reporting period.** The full history in the CFPB file, kept current by a 24-hour incremental collection. Each question's window is fixed in advance, and the current year is labelled partial.

**Analytical questions.**

| # | Question | Window |
|---|---|---|
| Q1 (demo) | Which sub-products and issues grew fastest, and how did the mobile or digital wallet share change? | 2021 to 2025 |
| Q2 (demo) | How did the "Fraud or scam" share change across the four core sub-products? | since 2018 |
| Q3 | Has the mix of submission channels changed over time? | full history |
| Q4 | How do response categories and timely-response rates differ by sub-product and among the largest companies by share? | full history |
| Q5 | Which states show different issue profiles (optionally per 100,000 residents)? | full history |

Q1 and Q5 use Spark MLlib descriptively (issue-share trends, K-means groups of states). Every answer shows raw counts and percentages within each group, with its caution next to it.
