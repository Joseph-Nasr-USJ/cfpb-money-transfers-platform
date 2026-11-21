# Dashboard metric definitions

All complaint measures use curated MongoDB records, counted once per complaint ID.
Date filters use the date the CFPB received the complaint (`date_received`).
Unless noted, percentages use the same filters for the numerator and denominator.
Show `N/A` when the denominator is zero. Display missing categories as `Unknown`.

| Metric | Definition and fields | Interpretation |
| --- | --- | --- |
| Total complaints | Count of curated complaints matching the selected dates and categories. | Counts records published in the CFPB database. |
| Monthly and yearly volume | Count complaints by calendar month or year of `date_received`. | Label partial periods. Product labels changed in 2017, so use standardized sub-products. |
| Month-on-month and year-on-year change | `100 × (current count − comparison count) / comparison count`. Compare with the previous calendar month or the same month last year. The headline annual YoY compares the latest two complete calendar years covered by the selection. | Exclude incomplete months from growth comparisons. Show `N/A` if the comparison count is missing or zero. Growth in complaints does not establish growth in usage. |
| Sub-product share | `100 × complaints in the standardized sub-product / all domain complaints in the same scope`. For wallet share, use `sub_product_std = Mobile or digital wallet`. | Label the selected period and preserve the domain denominator when showing wallet share. |
| Issue and sub-issue share | `100 × issue count / sub-product count`. For sub-issues, use `100 × sub-issue count / parent issue count` within the same sub-product. Use `issue`, `sub_issue`, and `sub_product_std`. | Missing sub-issues remain visible as `Unknown`. |
| Fraud-or-scam share | For each core sub-product, divide complaints with `issue = Fraud or scam` by all complaints for that sub-product. Multiply by 100. For the rolling share, divide the summed fraud-or-scam counts by the summed total counts across the 12-month window. | The consumer selected the issue label. It does not establish confirmed fraud. The issue filter does not change this measure’s denominator. |
| Submission channel share | `100 × complaints for a given submitted_via value / all complaints in that year and scope`. | A change in channel mix may reflect how complaints were routed or collected. |
| Company response share | For overall share, divide each `company_response` count by all complaints in the same group. For closed outcome share, exclude `In progress` and `Unknown` from both numerator and denominator. Multiply by 100. | Label which denominator is used. Response categories do not measure customer satisfaction. |
| Timely response percentage | `100 × timely_yes / timely_known`, using `timely_response`. Known values are `true` and `false`. | Missing values are excluded. The flag does not measure how long the issue took to resolve. |
| Processing lag | Calendar days from `date_received` to `date_sent_to_company`. Report the median of valid non-negative lags and counts in buckets of 0, 1, 2–3, 4–7, 8–14, and 15+ days. | This measures how long it took to send the complaint to the company. The MongoDB headline median is approximate. |
| Company share | `100 × complaints for the company / all complaints in the stated scope`. | Label it as share of complaints. The source provides no market-share or transaction denominator for ranking companies. |
| State issue profile | Show counts by `state` and `issue`. Divide each issue count by all complaints in that state and scope for the within-state share. | Show unknown states separately. Raw counts describe complaint volume. |
| Field completeness | `100 × records with a populated field / records checked`, reported per field from the quality report. | Show which run and dataset the quality report covers. Missing optional fields may reflect how the source collects data. |
| Freshness | Show the latest `date_received` available in MongoDB and the timestamp of the last successful MongoDB load as separate values. | The dates answer different questions. A successful load can contain older complaints. |