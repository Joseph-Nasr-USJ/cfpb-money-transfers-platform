## How the measures are defined

All measures use curated complaint records, each counted once by complaint ID. Dates use the day the CFPB received the complaint. Unless noted, a percentage uses the same filters in its numerator and its denominator. A percentage with a denominator of zero is shown as *N/A*, and a missing category is shown as *Unknown*. Partial periods (the current month and year) are labelled.

**Total complaints.** The number of complaints that match the selected dates and filters. It counts records published in the CFPB database.

**Monthly and yearly volume.** Complaints counted by calendar month or year of receipt. Product labels changed in 2017, so the platform uses standardised sub-products.

**Month-on-month and year-on-year change.** `100 × (current count − comparison count) / comparison count`, compared with the previous calendar month or the same month last year. The headline yearly change compares the latest two complete calendar years in the selection. Incomplete months are excluded, and *N/A* is shown if the comparison count is zero. Growth in complaints is not growth in usage.

**Sub-product share.** `100 × complaints in a sub-product / all complaints of the domain` in the same scope. The mobile or digital wallet share uses the whole domain as its denominator, so it stays comparable when other filters change.

**Issue share.** `100 × issue count / complaints of the sub-product`. The CFPB defines sub-issues for some issues only, and none of the complaints in this domain has one (0 of 205,383 checked records in the full load of 24 November 2026), so no sub-issue share is shown and every breakdown is by issue.

**Fraud-or-scam share.** For each core sub-product, the complaints whose issue is *Fraud or scam* divided by all complaints of that sub-product, times 100. The rolling share divides the sum of the fraud-or-scam counts by the sum of all counts over a 12-month window. The consumer chooses the issue; it is not confirmed fraud. The issue filter does not change this denominator.

**Submission channel share.** `100 × complaints submitted through a channel / all complaints` in the same year and scope.

**Company response share.** Each response category divided by all complaints in the group. The *closed outcome* share leaves out *In progress* and *Unknown* from both numerator and denominator. The chart states which denominator it uses. Response categories do not measure satisfaction.

**Timely response percentage.** `100 × complaints marked timely (Yes) / complaints with a known Yes or No`. Missing and invalid values are excluded and reported separately. The flag does not measure how long a problem took to resolve.

**Processing lag.** The number of calendar days from the CFPB receiving the complaint to the CFPB sending it to the company. The dashboard shows the median of valid, non-negative values and a distribution in buckets of 0, 1, 2 to 3, 4 to 7, 8 to 14 and 15 or more days. **It is not the company's resolution time.** The headline median is approximate.

**Company share.** `100 × complaints about a company / all complaints` in the stated scope. It is a share of complaints. There is no market-share or transaction denominator, so it is never a ranking of company quality.

**State issue profile.** Complaint counts by state and issue, with the within-state share `100 × issue count / all complaints of that state`. States with an unknown value are shown separately. Raw counts describe complaint volume, not risk.

**Emerging issues (Spark MLlib).** For each sub-product and issue, a straight line is fitted to the issue's monthly share of its sub-product over the last 24 complete months. The slope is in percentage points per month. An issue is called *emerging* when the slope is at least +0.2 points per month, R² is at least 0.5 and there are at least 50 complaints in the window. These rules were fixed before the results were seen. It describes past complaint shares and is not a forecast.

**State groups (Spark MLlib).** States with at least 100 complaints are grouped by the mix of issues and submission channels in their complaints (K-means, 2 to 6 groups, the number chosen by the silhouette score). Smaller states are listed separately. A group describes a complaint profile, not consumers, companies or service quality.

**Field completeness.** `100 × records with a populated field / records checked`, per field, from the quality report of the last run. A missing optional field may reflect how the source collects data.

**Freshness.** Two separate values: the latest complaint date available (`date_received`) and the time of the last successful load into the database. They answer different questions: a successful load can contain only older complaints.
