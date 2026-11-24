# CFPB Complaint API: notes and tested behaviour

**Owner:** Marwa Zeineddine (data acquisition lead). Tested from Beirut on **20 Nov 2026** with PowerShell and a browser.

These notes record how the official API really behaves, because several points differ from its published specification. Every design decision in `ingestion/incremental.py` points back to a finding here.

## Endpoint and sources

| Item | Value |
|---|---|
| Search endpoint | `https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/` (`CFPB_API_URL`) |
| Full CSV ZIP | `https://files.consumerfinance.gov/ccdb/complaints.csv.zip` (`CFPB_CSV_URL`) |
| Official documentation | https://cfpb.github.io/api/ccdb/api.html , fields https://cfpb.github.io/api/ccdb/fields.html , release notes https://cfpb.github.io/api/ccdb/release-notes.html |
| Licence | `_meta.license` = CC0 (public domain) |

## Parameters we use

| Parameter | Value | Why |
|---|---|---|
| `product` | repeated once per label in `config/product_mapping.csv`; `Product•Sub-product` for the legacy wallet row | one request series for the whole domain |
| `date_received_min` | window start (`YYYY-MM-DD`) | |
| `date_received_max` | window end **+ 1 day** | see finding 4 |
| `size` | `API_PAGE_SIZE` = 100 | small, safe pages |
| `sort` | `created_date_desc` | gives stable sort values for `search_after` |
| `search_after` | `<epoch_ms>_<complaint_id>` of the last hit of the previous page | see findings 2 and 3 |
| `no_aggs`, `no_highlight` | `true` | smaller responses; aggregations are not needed |
| `frm`, `format` | **never sent** | see findings 2 and 5 |

## Response structure

```
{ "took": .., "timed_out": false,
  "hits": { "total": {"value": 2704, "relation": "eq"},
            "hits": [ { "_id": "...", "_source": { ...one complaint... }, "sort": [1792669710000, "30690627"] } ] },
  "_meta": { "license": "CC0", "last_updated": "2026-11-19T12:00:00-05:00", "last_indexed": "2026-11-20T12:00:00-05:00",
             "total_record_count": 19316897, "is_data_stale": false, "has_data_issue": false,
             "break_points": { "2": [1792669710000, "30690627"] } } }
```

Record keys (15): `complaint_id, date_received, date_sent_to_company, product, sub_product, issue, sub_issue, company, company_public_response, company_response, timely, state, zip_code, tags, submitted_via`. The narrative, consumer consent and consumer disputed fields are no longer returned. These keys match `API_TO_STANDARD` in `processing/schema.py`.

## Tested findings (20 Nov 2026)

Test query: our current product label, window 1 to 22 Oct 2026, `sort=created_date_desc`, `size=100`.

| # | Test | Result | Consequence |
|---|---|---|---|
| 1 | User-Agent | custom `cfpb-course-project/1.0`: **403**; browser imitation: **403**; `python-requests/2.34.2`: **200**. Same for the API and the ZIP host. The 403 page comes from Akamai (`errors.edgesuite.net`). | Collectors send the requests library's default User-Agent (defect logged, regression test added). |
| 2 | Offset paging `frm=100` | 100 hits, **overlap with page 1: 100 of 100** (same page again, no error). | `frm` is never used. A guard stops a run when a page brings no new complaint. |
| 3 | `search_after=1792669710000_30690627` (sort values of the last hit, joined with `_`), with or without `frm` | 100 hits, **overlap with page 1: 0** | Pagination by `search_after`. `_meta.break_points["2"]` equals the last hit's sort values. |
| 4 | `date_received_max=2026-10-22` | First hit received **2026-10-22T23:57:30Z** | The spec says "<" (exclusive) but the end day was returned. We send end + 1 day so the end day is always included; the overlap and de-duplication make extra days harmless. |
| 5 | `size=1000` | 1,000 hits, although the published spec says a maximum of 100 | We keep 100. The spec also says a `format` parameter switches to export mode and ignores `size`, so we never send it. |
| 6 | Volume | 2,704 complaints in the 22-day test window (about 125 per day); 199,152 for the current label in total | A 21-day overlap window is about 28 pages of 100, far below the 100,000 export limit. |
| 7 | Full CSV ZIP download (20 Nov) | **369,859,546 bytes (about 370 MB)**. On our connection, about 37 KB/s, the transfer broke after 104 MB (`ChunkedEncodingError`). | Mid-transfer breaks are retried, and an attempt that made progress resumes at once without counting against `API_MAX_RETRIES` (defect fixed 24 Nov, regression tests added). |
| 8 | Dates | API dates are UTC timestamps (`2026-10-22T23:57:30.000Z`); the CSV has plain dates | Spark takes the first 10 characters. **To check once the full CSV is loaded:** compare a few complaint IDs present in both sources to confirm the day is the same. |

## Rules that follow from the publication policy

- The CFPB publishes a complaint only after the company responds or after 15 days, and the database generally updates daily, so recent days fill in late and existing complaints change (for example the company response).
- That is why the incremental window starts at the high-water mark minus `OVERLAP_DAYS` = 21, and why duplicates are removed by complaint_id with the documented tie-break (latest ingestion wins).
- `_meta.last_updated` and `_meta.last_indexed` are saved in every run log (`source_meta`) and can feed the freshness indicator.

## How to reproduce a probe

From a PowerShell window (no Docker needed), with the User-Agent that the firewall accepts:

```powershell
$ua = "python-requests/2.34.2"
Invoke-WebRequest -UserAgent $ua -UseBasicParsing "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/?size=1&no_aggs=true"
```
