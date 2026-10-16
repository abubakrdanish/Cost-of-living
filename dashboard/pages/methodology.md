---
title: Methodology and limitations
sidebar_position: 5
---

## Data sources

| Measure | ABS publication | How it is obtained | Frequency used |
|---|---|---|---|
| Prices: CPI, all groups | [Consumer Price Index, Australia (6401.0)](https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/latest-release) | [ABS Data API](https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide) dataflow `ABS,CPI,2.0.0`, index `10001`, Original | Quarterly |
| Rents: CPI rents component | 6401.0 | `ABS,CPI,2.0.0`, index `30014`, Original (monthly from 2022-07), plus the [final quarterly release, Table 9](https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/sep-quarter-2025) (1972-Q3 to 2025-Q3) | Quarterly (spliced) |
| Wages: Wage Price Index | [Wage Price Index, Australia (6345.0)](https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/wage-price-index-australia/latest-release) | `ABS,WPI,1.2.0`: total hourly rates of pay excluding bonuses, private and public sector, all industries, Original | Quarterly |

**Attribution.** Based on Australian Bureau of Statistics data: Consumer Price Index, Australia (6401.0) and Wage Price Index, Australia (6345.0), licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The figures shown are derived from ABS data (rebased, averaged, spliced and differenced) and are not ABS publications.

**Index base.** Every index on these pages is rebased so that **1997-Q3 = 100** for each region. 1997-Q3 is the first quarter in which all three series exist (the WPI starts then). Rebasing changes the starting point only; annual % changes are unaffected.

## City prices vs state wages (an approximation)

The CPI and rents are measured for **capital cities**; the WPI is measured for **whole states and territories**. Each region pairs a capital with its state, so comparing, say, Melbourne prices with Victorian wages is an approximation. It is weakest where many people live outside the capital.

```sql regions
select region_name, capital_city, state_name, comparison_note
from marts.regions order by region_sort_order
```

<DataTable data={regions} rows=all>
  <Column id=region_name title="Region" />
  <Column id=capital_city title="CPI and rents measured in" wrap=true />
  <Column id=state_name title="WPI measured in" />
  <Column id=comparison_note title="Note" wrap=true />
</DataTable>

## The rents splice

The ABS published quarterly CPI by capital city until the September quarter 2025, then moved to a fully monthly CPI. Rents up to 2025-Q3 come from the archived quarterly series; from 2025-Q4 they are the average of the three monthly values, joined using the ratio of the two series in 2025-Q3.

```sql splice
select region_name, capital_city, link_factor, max_abs_deviation_pct, max_deviation_quarter,
       tolerance_pct, overlap_quarters, first_overlap_quarter, last_overlap_quarter, link_quarter
from marts.rents_splice_check order by region_sort_order
```

```sql splice_range
select min(max_abs_deviation_pct) as smallest, arg_min(capital_city, max_abs_deviation_pct) as smallest_city,
       max(max_abs_deviation_pct) as largest, arg_max(capital_city, max_abs_deviation_pct) as largest_city
from marts.rents_splice_check
```

If a quarter were exactly the average of its months, the ratio would be constant. In fact it moves by between {splice_range[0]?.smallest?.toFixed(2)}% ({splice_range[0]?.smallest_city}) and {splice_range[0]?.largest?.toFixed(2)}% ({splice_range[0]?.largest_city}). Annual rent changes that compare a quarter after the splice with one before it are flagged on the [Rents](/rents) page; treat them as accurate to roughly ±0.4 percentage points. The pipeline fails its tests if any deviation exceeds the tolerance.

Overlap: {splice[0]?.first_overlap_quarter} to {splice[0]?.last_overlap_quarter} ({splice[0]?.overlap_quarters} quarters) for every region; link quarter {splice[0]?.link_quarter}.

<DataTable data={splice} rows=all>
  <Column id=region_name title="Region" />
  <Column id=capital_city title="Capital city" wrap=true />
  <Column id=link_factor title="Link factor" fmt='0.0000' />
  <Column id=max_abs_deviation_pct title="Max deviation %" fmt='0.00' />
  <Column id=max_deviation_quarter title="Largest in" />
  <Column id=tolerance_pct title="Test limit %" fmt='0.0' />
</DataTable>

## Revisions

```sql revisions
select count(*) filter (where cpi_is_revised) as cpi_revised,
       count(*) filter (where rents_includes_revised_month) as rents_revised,
       count(*) filter (where wpi_is_revised) as wpi_revised,
       count(*) as total_rows
from marts.cost_of_living_quarterly
```

The ABS revises recent values. The pipeline keeps every download and uses the newest one; the data quality report lists what changed between downloads. In the series used here, ABS flags {revisions[0]?.cpi_revised} CPI values, {revisions[0]?.rents_revised} rents quarters (a quarter counts if any of its months is revised) and {revisions[0]?.wpi_revised} WPI values as revised, out of {revisions[0]?.total_rows} region-quarters. (The download does contain revision flags, but on the seasonally adjusted rents series, which these pages do not use.) Numbers on this site can change slightly after each ABS release.

## Known limitations and unknowns

```sql hobart_dec_2024
select 100 * (1 - cur.rents_index / prev.rents_index) as fall_pct
from marts.cost_of_living_quarterly cur
join marts.cost_of_living_quarterly prev
  on prev.region_key = cur.region_key and prev.quarter_label = '2024-Q3'
where cur.region_key = 'TAS' and cur.quarter_label = '2024-Q4'
```

- **CPI rents are not market rents.** They cover all renting households and are net of Commonwealth Rent Assistance, so they rise more slowly than advertised rents and drop when CRA increases.
- **Unexplained: Hobart rents in the December quarter 2024** fell {hobart_dec_2024[0]?.fall_pct?.toFixed(1)}% on the previous quarter. The cause has not been verified (a CRA change is plausible but unconfirmed).
- **The WPI is not average earnings.** It prices the same jobs over time, so it excludes promotions, job changes, hours worked and bonuses.
- **Original series throughout.** States have no seasonally adjusted WPI, so the Original series is used everywhere. The Australia row therefore differs slightly from the ABS's seasonally adjusted headline.
- **Real wage growth is a simple difference** of annual % changes, not the exact ratio (see [Real wage growth](/real-wages) for the size of the gap).
- **Capital cities only.** The CPI covers metropolitan households; regional Australia is not measured.
- **Inferred archive details.** The archive's index base (2011-12 = 100) was confirmed from the data rather than stated in the file, and its two identical Rents columns were matched to the expenditure class by column order. Neither affects the values shown.
- **No causal claims.** These pages show how the measures moved together, not why.

Full documentation: `docs/data_sources.md`, `docs/data_dictionary.md` and `docs/operations.md` in the project repository.
