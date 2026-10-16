# Data Sources

All three datasets come from the Australian Bureau of Statistics (ABS). Everything below was checked against the live API and ABS website on **2026-10-12**, which is also the date the raw files were last downloaded. Each raw file's exact download time, URL and SHA-256 are in its `.meta.json` sidecar in `data/raw/<source>/`.

| # | Dataset | Publisher | URL / API | Format | Update frequency | Licence / attribution | Status |
|---|---|---|---|---|---|---|---|
| 1 | Consumer Price Index (CPI), 6401.0: All groups | ABS | Data API dataflow `ABS,CPI,2.0.0`, key `1.10001...` | SDMX-CSV | Monthly (complete monthly CPI since Oct 2025); quarterly series also updated in Mar/Jun/Sep/Dec releases | CC BY 4.0 | Ingested |
| 2 | Wage Price Index (WPI), 6345.0 | ABS | Data API dataflow `ABS,WPI,1.2.0`, key `1......Q` | SDMX-CSV | Quarterly | CC BY 4.0 | Ingested |
| 3a | Rents: CPI component, current | ABS | Data API dataflow `ABS,CPI,2.0.0`, key `1.30014+115522...` | SDMX-CSV | Monthly | CC BY 4.0 | Ingested |
| 3b | Rents: CPI component, quarterly history by capital city | ABS | 6401.0 Sep quarter 2025, Table 9: `https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/sep-quarter-2025/640107.xlsx` | XLSX (ABS time series workbook) | Frozen (final quarterly CPI release) | CC BY 4.0 | Ingested |
| 4 | Homes Victoria Rental Report (optional, later) | Homes Victoria via data.gov.au | Not yet looked up | | Quarterly | Stated in the brief as CC BY 3.0 AU, **not yet verified** | Not started |

## ABS Data API

- **Base URL:** `https://data.api.abs.gov.au/rest/`. The host `api.data.abs.gov.au` in the original brief **does not resolve**. ABS says the current base URL replaced an older endpoint on 29 Nov 2024.
- **No API key** is needed (ABS user guide: "freely accessible without the need for an API key").
- **Status:** Beta. "Availability … is not guaranteed" and it "may be subject to change". Nothing is published about rate limits, so the client waits at least 2 s between requests and backs off on 429/5xx.
- **List dataflows:** `GET /rest/dataflow/ABS` with `Accept: application/vnd.sdmx.structure+json` (1,227 dataflows on 2026-10-12).
- **Inspect a structure:** `GET /rest/dataflow/ABS/{id}?references=all` returns the dimensions and codelists.
- **Query data:** `GET /rest/data/{agency},{dataflow},{version}/{key}?startPeriod=&endPeriod=`. Dimension values are separated by `.`, a blank position means "all", and `+` joins several values.
- **Format used:** `Accept: application/vnd.sdmx.data+csv;labels=both`, which returns CSV with code and label together (for example `2: Melbourne`).
- Full-history pulls for these keys are small (0.2–3.2 MB, about 2 s each), so the date-range parameters aren't needed.
- Guide: <https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide>

## 1. CPI: `ABS,CPI,2.0.0`

Dimensions: `MEASURE.INDEX.TSEST.REGION.FREQ`

| Dimension | Values used | Notes |
|---|---|---|
| MEASURE | `1` Index numbers | Percentage changes are left to dbt |
| INDEX | `10001` All groups CPI | |
| TSEST | all | `10` Original. Seasonally adjusted (`20`) exists only for some Australia series |
| REGION | all | `50` Australia (weighted average of eight capitals), `1` Sydney, `2` Melbourne, `3` Brisbane, `4` Adelaide, `5` Perth, `6` Hobart, `7` Darwin, `8` Canberra |
| FREQ | all | `M` Monthly, `Q` Quarterly |

**Coverage (2026-10-12):**
- Quarterly runs from 1948-Q3 to 2026-Q2 (Darwin from 1980-Q3).
- Monthly runs from **2024-04** to 2026-08 for every region.
- Index base: **Sep 2025 = 100.0**.

**Release info:** Latest release is Aug 2026, published 30 Sep 2026. The next is Sep 2026, due 28 Oct 2026. Release page: <https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/latest-release>

Other CPI dataflows that exist but are **not** used:
- `CPI_M` 1.2.0 (Monthly CPI Indicator) is marked **CEASED**.
- `CPI_Q` 1.0.0 returned only one series (Rents, Australia, seasonally adjusted) for the keys tested.

## 2. WPI: `ABS,WPI,1.2.0`

Dimensions: `MEASURE.INDEX.SECTOR.INDUSTRY.TSEST.REGION.FREQ`. We request `MEASURE=1` (quarterly index), with every other dimension open and `FREQ=Q`.

What actually has data (checked 2026-10-12, 15,312 observations, 1997-Q3 to 2026-Q2):

| Breakdown | Available? |
|---|---|
| States/territories (`1`–`8` NSW…ACT, plus `AUS`) | Yes: **Original only**, all industries, by sector (`7` Private and Public, `1` Private, `2` Public) |
| Industry (19 ANZSIC divisions) | **Australia only**. There is no state × industry breakdown |
| Seasonally adjusted / trend | **Australia only** |
| Index type (`INDEX`) | `THRPEB` total hourly rates of pay excluding bonuses (the headline WPI) is the most complete. `OHRPEB`, `THRPIB` and `OHRPIB` have fewer series |

- **Index base:** 2008-09 = 100, per the ABS release page. The API's `BASE_PERIOD` column is **blank** for WPI.
- **Release info:** Latest release is Jun 2026, published 19 Aug 2026. The next is Sep 2026, due **18 Nov 2026**. Release page: <https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/wage-price-index-australia/latest-release>

## 3. Rents (CPI component)

The CPI has two codes named "Rents": `30014` (expenditure class) and `115522` (sub-group). They hold the same series and differ by 0.01 on 3 observations, which looks like rounding. Both are kept in raw, and staging should use **`30014`**.

| Raw dataset | Frequency | Regions | Period | Base |
|---|---|---|---|---|
| `abs_cpi_rents` (API) | Monthly | Australia + 8 capitals | 2022-07 → 2026-08 | Sep 2025 = 100 |
| `abs_cpi_rents` (API) | Quarterly | **Australia only** | 1972-Q3 → 2026-Q2 | Sep 2025 = 100 |
| `abs_cpi_capital_cities_quarterly_2025q3` (XLSX) | Quarterly | Australia + 8 capitals | 1972-Q3 → 2025-Q3 (Darwin 1980-Q3) | 2011-12 = 100 (checked: FY2011-12 average ≈ 100.0) |

The XLSX is the whole Table 9 (all CPI groups by capital city, 1,368 series, 231,122 observations), loaded unfiltered. Its rents series IDs are:
- Sydney `A2331836L`
- Melbourne `A2331841F`
- Brisbane `A2331846T`
- Adelaide `A2331851K`
- Perth `A2331856W`
- Hobart `A2331861R`
- Darwin `A2331866A`
- Canberra `A2331871V`
- Australia `A2331876F`

## Licence and attribution

The ABS website licenses its material under **Creative Commons Attribution 4.0 International (CC BY 4.0)**: <https://creativecommons.org/licenses/by/4.0/>. Source: <https://www.abs.gov.au/website-privacy-copyright-and-disclaimer>.

- Use "Source: Australian Bureau of Statistics" for unchanged data, and **"Based on Australian Bureau of Statistics data"** for anything this pipeline derives (all marts and dashboards).
- Material excluded from the licence includes the Commonwealth Coat of Arms, the ABS logo, trade marks and third-party content. Don't use the ABS logo in the dashboard.
- The copyright page says nothing about automated or API access. The pipeline only uses the documented Data API and direct file downloads linked from release pages, and it doesn't crawl.

Attribution text to use in the README and dashboard:

> Based on Australian Bureau of Statistics data: Consumer Price Index, Australia (6401.0) and Wage Price Index, Australia (6345.0), licensed under CC BY 4.0.

## Gaps, doubts and things to watch

1. **Capital-city rents have no single quarterly series.** The ABS stopped publishing quarterly capital-city CPI after Sep quarter 2025. Monthly capital-city rents only start in 2022-07. A long quarterly series has to splice the archive (to 2025-Q3) onto quarterly averages of the monthly series (from 2025-Q4).
2. **The splice is not exact.** Across all 9 regions, the ratio of the monthly average to archive quarterly differs from the 2025-Q3 link factor by up to **0.14% (Sydney) to 0.41% (Hobart)** over 2022-Q3 to 2025-Q3. So a quarter is not exactly the average of its months in the new methodology. *(Corrected 2026-10-13: the Week 1 figure of "±0.2%" was measured on Melbourne only and understated the gap. See `int_rents_splice_overlap` and data_dictionary.md.)* By contrast, the API's quarterly **all-groups** capital-city CPI is an exact rebase of the archive (constant ratio 1.434). All-groups therefore needs no splice: use the API quarterly series directly.
3. **Revisions:** 19 monthly Australia rents observations (2022-07 to 2026-07) are flagged `OBS_STATUS = r: revised`. *(Clarified 2026-10-16: all 19 are on the **seasonally adjusted** series, which staging drops, so the Original series used in the mart has no revision flags at present.)* The raw tables keep every downloaded snapshot, so later revisions can be compared.
4. **Geography mismatch:** CPI is by **capital city** and WPI is by **state/territory**. Joining them by mapping each capital to its state is an approximation, and it should be labelled that way in the marts and dashboard.
5. **Grain mismatch:** CPI is monthly and quarterly. WPI and the archive rents are quarterly. The marts should be quarterly.
6. **WPI base period** isn't in the API data (blank `BASE_PERIOD`). It's taken from the release page instead.
7. **The API is in beta**, so dataflow versions could change (for example `CPI` 2.0.0 → 2.x). The ingestion pins versions, so a change will show up as an error, not as silently different data.
8. **CPI coverage is metropolitan households only**, not regional areas.
9. **CPI rents are net of Commonwealth Rent Assistance.** CRA increases lower the index. The ABS attributes Hobart's −2.5% in the Dec qtr 2023 to the 15% CRA increase from 20 Sep 2023 ([ABS, CPI Dec quarter 2023](https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/dec-quarter-2023)). The index is therefore not a measure of market asking rents.
10. **The archive has duplicate Rents columns.** Table 9 has two identical "Rents" series per city (sub-group and expenditure class), and their values match in all 213 quarters. `A2326xxx` is used. Which column is the expenditure class was inferred from column order, so it's an inference, but it has no effect on values.
