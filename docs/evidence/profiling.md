# Profiling of the money transfer domain

Source: the full historical load `20261124T134839Z_full` (24 Nov 2026). The CSV holds 19,397,176
complaints for all CFPB products. Our domain (four product labels, see
`config/product_mapping.csv`) is 205,383 checked records (1.06% of the file), of which 205,271
are curated. Figures come from the run's quality report and from queries on the curated data in
MongoDB.

## Complaints by product label (curated)

| Product label | Complaints | Share |
|---|---|---|
| Money transfer, virtual currency, or money service | 199,561 | 97.22% |
| Money transfers (legacy label) | 5,274 | 2.57% |
| Prepaid card (legacy label) | 418 | 0.20% |
| Virtual currency (legacy label) | 18 | 0.01% |
| **Total** | **205,271** | 100% |

## Complaints by year received (curated)

| Year | Complaints | | Year | Complaints |
|---|---|---|---|---|
| 2013 | 509 | | 2020 | 8,304 |
| 2014 | 1,180 | | 2021 | 13,889 |
| 2015 | 1,783 | | 2022 | 13,528 |
| 2016 | 1,738 | | 2023 | 13,746 |
| 2017 | 3,765 | | 2024 | 16,746 |
| 2018 | 5,430 | | 2025 | 84,612 |
| 2019 | 5,081 | | 2026 (to 23 Nov) | 34,960 |

The years add up to 205,271. Volume in 2025 is about five times that of 2024 (84,612 against
16,746). The findings section examines this change; profiling only records it.

## Field completeness (205,383 checked records, before quarantine)

| Field | Filled | Field | Filled |
|---|---|---|---|
| complaint_id | 100% | company_response | 100% |
| date_received | 100% | timely_response | 100% |
| product | 100% | submitted_via | 100% |
| issue | 100% | date_sent_to_company | 100% |
| company | 100% | zip_code | 99.694% |
| sub_product | 100% | state | 95.013% |
| company_public_response | 14.175% | sub_issue | not applicable (see below) |

- **sub_issue:** no record of the four product labels has a sub-issue (0 of 205,383). The quality
  report therefore classes every empty `sub_issue` as not applicable rather than missing, and any
  analysis by sub-issue (for example a sub-issue share) cannot be computed for this domain.
- **state:** about 5% of records have no state. Geography results describe the 95% that do.
- **company_public_response:** filled for about 14% of records; companies choose whether to publish
  a response, so this field is expected to be sparse.

## Quarantined records

| Reason | Records | Share of checked records |
|---|---|---|
| Date sent to company before date received (`negative_lag`) | 80 | 0.039% |
| State not in `config/state_codes.csv` (`invalid_state`) | 32 | 0.016% |
| **Total** | **112** | 0.055% |

## Consistency

Every product and sub-product combination in the domain maps to a standard sub-product in
`config/product_mapping.csv` (0 unmapped combinations).
