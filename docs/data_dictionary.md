# Data Dictionary

This covers the dbt models built on the raw tables. Sources, licences and dataflow IDs are in [data_sources.md](data_sources.md). Column-level documentation is also available in the dbt docs site (`dbt docs generate && dbt docs serve`).

## Model layers

| Schema | Model | Type | Rows (2026-10-13) | Purpose |
|---|---|---|---|---|
| reference | `region_mapping` | seed | 9 | Pairs each CPI region code (capital city) with a WPI region code (state) |
| reference | `abs_archive_rents_series` | seed | 9 | ABS series IDs for the archived quarterly Rents series |
| staging | `stg_abs__cpi_all_groups` | view | 2,941 | All groups CPI, Original series, monthly + quarterly |
| staging | `stg_abs__cpi_rents` | view | 666 | CPI Rents (code 30014), Original series, monthly + quarterly |
| staging | `stg_abs__cpi_rents_archive` | view | 1,885 | Archived quarterly Rents by capital city, 1972-Q3 to 2025-Q3 |
| staging | `stg_abs__wpi` | view | 1,044 | WPI headline series (THRPEB, all sectors, all industries, Original) |
| intermediate | `int_rents_monthly_to_quarterly` | view | 144 | Monthly rents averaged into complete quarters |
| intermediate | `int_rents_splice_overlap` | view | 117 | Splice check: archive vs monthly average in the overlap quarters |
| intermediate | `int_rents_quarterly_spliced` | view | 1,912 | One continuous quarterly rents series per region |
| intermediate | `int_raw_snapshot_changes` | view | 0 (one download so far) | What changed between the two newest downloads: added, removed and revised observations |
| marts | `dim_region` | table | 9 | Regions, with a caveat about comparing city CPI and state WPI |
| marts | `dim_quarter` | table | 313 | Calendar quarters 1948-Q3 to 2026-Q3 |
| marts | `mart_cost_of_living_quarterly` | table | 1,044 | **The main output.** Covers 9 regions × 116 quarters |

Every staging model reads only the **latest snapshot** of its raw table. Older snapshots stay in `raw` so later ABS revisions can be compared (`int_raw_snapshot_changes`).

## Materialisation and incremental decisions

This was decided on 2026-10-14: **no dbt model is incremental.** Incremental loading happens where it earns its place, in the raw layer, where each downloaded file is appended once and never reloaded. A full `dbt build` takes about 4 seconds.

| Model | Materialisation | Why not incremental |
|---|---|---|
| raw tables (Python loader) | append-only, one batch per new file | **This is the incremental layer.** Identical downloads aren't saved, and loaded files are skipped. |
| seeds (`region_mapping`, `abs_archive_rents_series`) | table | Nine rows each. They change only when the code changes. |
| `stg_abs__cpi_all_groups`, `stg_abs__cpi_rents`, `stg_abs__wpi` | view | These must reflect the *latest* download in full, because ABS revises past values. An incremental model would need merge keys plus a full refresh after every revision, for about 3,000 rows. |
| `stg_abs__cpi_rents_archive` | view | It reads the largest table (231k rows) but filters to 1,885 rows in well under a second. The release is frozen, so an incremental model would never add anything. |
| `int_rents_*` | view | Small, and the splice link factor depends on the newest data, so recomputing everything is the correct behaviour. |
| `int_raw_snapshot_changes` | view | It compares the two newest downloads, so it has to be recomputed whenever a new one arrives. |
| `dim_region`, `dim_quarter` | table | 9 and 313 rows. |
| `mart_cost_of_living_quarterly` | table | 1,044 rows, rebuilt in under 0.1 s. Rebasing and annual changes depend on the whole history, which revisions can change. |

Revisit this if a raw table grows to millions of rows (for example, adding every CPI expenditure class for every city monthly). The first candidate would then be an incremental staging model keyed on the observation, with `--full-refresh` after an ABS rebase.

## `marts.mart_cost_of_living_quarterly`

**Grain:** one row per `quarter_start_date` × `region_key`.

**Range:** from 1997-Q3 to the latest quarter that CPI, rents and WPI all cover (2026-Q2 on 2026-10-13). WPI starts in 1997-Q3, which is why the range starts there. The end quarter is computed, not fixed, so a release that adds one series before the others doesn't create half-empty rows.

**Completeness:** every region has a row for every quarter in the range. A value that doesn't exist is `null`, and `missing_reason` says why. Today that applies to 36 rows: WPI annual change and real wage growth for 1997-Q3 to 1998-Q2.

**Index base:** all three `*_index` columns are rebased to **1997-Q3 = 100** for each region. A value of 216.6 means "116.6% higher than in 1997-Q3". Annual % changes don't depend on the base.

| Column | Type | Description |
|---|---|---|
| `quarter_start_date` | date | First day of the quarter. FK to `dim_quarter`. |
| `quarter_end_date` | date | Last day of the quarter. |
| `quarter_label` | varchar | e.g. `2026-Q2`. |
| `year`, `quarter_number` | int | Calendar year and quarter (1–4). |
| `financial_year` | varchar | Australian financial year, July–June, e.g. `1997-98`. |
| `region_key` | varchar | `AUS`, `NSW`, `VIC`, `QLD`, `SA`, `WA`, `TAS`, `NT`, `ACT`. FK to `dim_region`. |
| `region_name` | varchar | State or territory name, or `Australia`. |
| `capital_city` | varchar | Capital city whose CPI and rents represent the region. |
| `state_name` | varchar | State or territory whose WPI represents the region. |
| `is_national` | boolean | True for the Australia row. |
| `region_sort_order` | int | Display order (Australia first). |
| `cpi_index` | double | All groups CPI, rebased to 1997-Q3 = 100. |
| `rents_index` | double | CPI Rents (spliced), rebased to 1997-Q3 = 100. |
| `wpi_index` | double | Wage Price Index, rebased to 1997-Q3 = 100. |
| `cpi_index_abs_base` | double | CPI on the ABS base (Sep 2025 = 100), for checking against ABS releases. |
| `rents_index_abs_base` | double | Spliced rents on the current ABS base (Sep 2025 = 100). |
| `wpi_index_abs_base` | double | WPI on the ABS base (2008-09 = 100). |
| `cpi_annual_pct` | double | % change in CPI from the same quarter a year earlier. |
| `rents_annual_pct` | double | % change in rents from the same quarter a year earlier. |
| `wpi_annual_pct` | double | % change in WPI from the same quarter a year earlier. Null for 1997-Q3 to 1998-Q2. |
| `real_wage_growth_pct_pts` | double | `wpi_annual_pct − cpi_annual_pct`, in percentage points. Positive means wages grew faster than prices. |
| `rents_source_series` | varchar | `archive_quarterly_table9` (to 2025-Q3) or `api_monthly_average` (from 2025-Q4). |
| `rents_is_splice_point` | boolean | True for 2025-Q4, the first quarter from the monthly series. |
| `rents_annual_pct_crosses_splice` | boolean | True when the two quarters compared come from different source series (2025-Q4 to 2026-Q3). |
| `cpi_is_revised` | boolean | ABS flags the CPI value as revised. |
| `rents_includes_revised_month` | boolean | At least one month in the rents average is flagged revised. |
| `wpi_is_revised` | boolean | ABS flags the WPI value as revised. |
| `missing_reason` | varchar | Null when every column is filled. Otherwise lists what is missing and why. |

### Which ABS series feed each column

| Measure | ABS source | Series chosen | Why |
|---|---|---|---|
| CPI | `ABS,CPI,2.0.0` | Index numbers, All groups (`10001`), Original, quarterly | Original is the only type published for capital cities |
| Rents | Archive: 6401.0 Sep qtr 2025 Table 9. New: `ABS,CPI,2.0.0` | Rents expenditure class (`30014` / series `A2326xxx`), Original | No quarterly capital-city series after 2025-Q3, so the two are spliced (see below) |
| WPI | `ABS,WPI,1.2.0` | `THRPEB` (total hourly rates of pay excl. bonuses), sector `7` Private and Public, industry `TOT`, Original | ABS headline measure. States only have Original, and industries exist for Australia only |

### How the rents splice works

1. Up to and including **2025-Q3**, use the archived quarterly series (base 2011-12 = 100).
2. From **2025-Q4**, use the quarterly average of the three monthly values (base Sep 2025 = 100). Incomplete quarters are dropped.
3. To put the archive on the new base, multiply it by the **link factor** = monthly average ÷ archive in 2025-Q3.

**How exact is it?** If a quarterly figure were exactly the average of its months, the ratio would be constant in every overlap quarter. In practice it moves a little (`int_rents_splice_overlap`, 2022-Q3 to 2025-Q3):

| Region | Max deviation from the link factor |
|---|---|
| Hobart | 0.41% (2023-Q3) |
| Adelaide | 0.32% |
| Melbourne | 0.32% |
| Canberra | 0.31% |
| Darwin | 0.28% |
| Perth | 0.23% |
| Brisbane | 0.21% |
| Australia | 0.20% |
| Sydney | 0.14% |

So treat rents annual changes for 2025-Q4 to 2026-Q3 (`rents_annual_pct_crosses_splice = true`) as accurate to roughly ±0.4 percentage points. The test `assert_rents_splice_overlap_within_tolerance` fails if any deviation exceeds 0.5%.

**Cross-check:** for Australia, ABS still publishes an official quarterly Rents series. The spliced Australia series stays within **0.105%** of it from 1997-Q3 onward. The largest gap, in 2002-Q1, is the size you'd expect from the archive rounding indexes to 1 decimal place.

## Known limitations

1. **City vs state.** CPI and rents cover capital cities (Australia = weighted average of the eight capitals). WPI covers whole states. Comparing Melbourne prices with Victorian wages is an approximation, especially for large regional populations (QLD, NSW, TAS).
2. **CPI rents aren't market rents.** The ABS measures rents paid by all renting households, **net of Commonwealth Rent Assistance**. That means:
   - The index moves more slowly than new-lease asking rents.
   - CRA increases push it down. Hobart rents fell 2.5% in the Dec qtr 2023, which the ABS attributes to the 15% CRA increase from 20 Sep 2023. They fell again in Dec qtr 2024; I haven't verified the cause of that drop.
3. **The rents series is spliced** at 2025-Q4, with about ±0.4% method noise around the join (see above).
4. **Real wage growth is approximate.** It's a simple difference of annual % changes, not the exact ratio `(1+w)/(1+p)−1`. Across the mart the largest gap is 0.40 points (2022-Q4, when inflation was highest); when CPI inflation is 2–4% it is at most 0.08 points. *(Corrected 2026-10-16: the Week 2 text said "about 0.3 points"; this figure comes from a query, see the real-wages page.)* It also mixes a city price index with a state wage index.
5. **WPI measures the price of labour, not earnings.** It holds job mix fixed, so it excludes promotions, job changes, hours and bonuses. It's not average pay.
6. **Original (not seasonally adjusted) series everywhere.** The Australia WPI row differs slightly from the ABS seasonally adjusted headline. Annual changes compare the same quarter a year apart, which removes most seasonality.
7. **Revisions.** ABS revises recent values. Only the latest snapshot is used. Revision flags are carried through, but past values may change on the next run.
8. **Release timing.** The end quarter is the latest quarter all three series cover. CPI for a quarter is published about 4 weeks after it ends and WPI about 7 weeks after, so for a few weeks each quarter the mart lags the newest CPI.
9. **Coverage before 1997-Q3 isn't in the mart.** CPI (from 1948) and rents (from 1972) have longer histories in staging and intermediate, but the mart starts where WPI starts.
10. **Archive base period was inferred.** The base of 2011-12 = 100 isn't in the Table 9 metadata. It was confirmed by checking that the FY2011-12 average equals 100.0. It doesn't affect the mart, because the archive is re-linked to the new base.
