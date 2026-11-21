<!--
Section 3. Data source and limitations
Owner: Loutchiana (category changes with Joseph) | Target: 450 words | Written: Sat 21 Nov
Sources checked on 21 Nov 2026: CFPB database page (last modified 29 Oct 2026), field reference, release notes 20 to 24,
and Marwa's API test (docs/api_notes.md, 20 Nov: licence CC0).
Facts to confirm before submission: (1) the earliest date_received of our domain, from the profiling of the full file;
(2) the legacy product labels and their mapping, with Joseph and the lecturer; (3) whether the course requires the AI
disclosure sentence and its wording.
-->

## 3. Data source and limitations

**Source and usage basis.** The platform uses the CFPB Consumer Complaint Database: the full CSV ZIP for the history and the official API for daily updates (references in section 8). The CFPB states that the complaint data it publishes is "freely available for anyone to use, analyze, and build on", and the API metadata declares the licence CC0, public domain (tested on 20 November 2026).

**Fields and coverage.** The CFPB publishes 15 fields: Complaint ID, Date received, Date sent to company, Product, Sub-product, Issue, Sub-issue, Company, Company public response, Company response to consumer, Timely response?, State, ZIP code, Tags and Submitted via. Not every product has sub-products and not every issue has sub-issues, so sub-issue is mostly empty in our domain. The database generally updates daily. Only complaints sent to companies for response are eligible, and they are published after the company responds or after 15 days, whichever comes first, so recent weeks are provisional. Complaints referred to other regulators are not published.

**Current restrictions.** Complaint narratives were removed in September 2026 (release 24), which is why the project does no text analysis; the consumer-consent and consumer-disputed fields are also gone. Since July 2026 filtered exports are limited to 100,000 complaints, so we use the full ZIP for the history and narrow API windows for updates. ZIP codes are masked or suppressed for small areas. The data contains no transactions, balances, confirmed fraud labels or resolution durations.

**Representativeness.** The CFPB states that the database "is not a statistical sample of consumers' experiences". Following Session 1, inference needs a random sample and correlation does not imply causation, so we describe the published complaints and neither generalise nor claim causes. The CFPB advises considering company size and market share when comparing companies; the data cannot provide them, so company figures are shares of complaints, never a quality ranking.

**Category changes.** The CFPB updated its product and issue forms in August 2023 and 2026 but keeps the labels the consumer selected, so history is not re-coded. In our domain three legacy labels used before April 2017 (Money transfers, Virtual currency, and Prepaid card with the sub-product Mobile wallet) are mapped to the current domain by `config/product_mapping.csv`, and the original labels are kept next to the standard ones. The mapping is to be confirmed with the lecturer.

**Responsible use and ethics.** The data is public, but the platform still limits its use. It never displays individual records or free text, makes no attempt to re-identify anyone and does not use ZIP codes. Company results carry a caution and are never rankings. No statement claims causality or confirmed fraud, and small groups are grouped or flagged. A quality failure stops a run, so bad data never reaches the dashboard. AI assistants were used for drafting and code support; every contribution was reviewed and tested by the team, who can explain it.
