---
title: Australian cost of living, 1997 to 2026
sidebar_position: 1
---

```sql range
select min(quarter_label) as first_quarter,
       max(quarter_label) as latest_quarter,
       strftime(max(quarter_end_date), '%B %Y') as latest_quarter_end
from marts.cost_of_living_quarterly
```

```sql latest_aus
select *,
       cpi_index - 100 as cpi_change,
       rents_index - 100 as rents_change,
       wpi_index - 100 as wpi_change,
       100 * (wpi_index / cpi_index - 1) as wages_vs_prices
from marts.cost_of_living_quarterly
where region_key = 'AUS'
  and quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
```

```sql latest_by_region
select region_label, cpi_annual_pct, rents_annual_pct, wpi_annual_pct, real_wage_growth_pct_pts
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
order by region_sort_order
```

```sql real_wage_peak
-- Same logic as docs/findings_queries.sql F2_real_wage_peak_and_trough
with r as (
    select quarter_start_date, quarter_label, 100 * wpi_index / cpi_index as real_wage_index
    from marts.cost_of_living_quarterly where region_key = 'AUS'
),
peak as (
    select arg_max(quarter_label, real_wage_index) as peak_quarter,
           max(real_wage_index) as peak_value,
           arg_max(quarter_start_date, real_wage_index) as peak_date
    from r where quarter_start_date < '2022-01-01'
)
select peak.peak_quarter, peak.peak_value,
       arg_min(r.quarter_label, r.real_wage_index) as trough_quarter,
       min(r.real_wage_index) as trough_value,
       100 * (1 - min(r.real_wage_index) / peak.peak_value) as fall_pct
from r, peak
where r.quarter_start_date > peak.peak_date
group by peak.peak_quarter, peak.peak_value
```

```sql negative_run
-- Same logic as docs/findings_queries.sql F4_negative_runs_australia (longest run)
with s as (
    select quarter_label, real_wage_growth_pct_pts < 0 as negative,
           row_number() over (order by quarter_start_date)
         - row_number() over (partition by real_wage_growth_pct_pts < 0 order by quarter_start_date) as grp
    from marts.cost_of_living_quarterly
    where region_key = 'AUS' and quarter_start_date >= '2020-01-01'
)
select min(quarter_label) as first_quarter, max(quarter_label) as last_quarter, count(*) as quarters
from s where negative group by grp order by quarters desc limit 1
```

```sql rents_extremes
select arg_max(capital_city, rents_index) as fastest_city, max(rents_index) - 100 as fastest_pct,
       arg_min(capital_city, rents_index) as slowest_city, min(rents_index) - 100 as slowest_pct,
       count(*) filter (where rents_index > wpi_index and not is_national) as cities_rents_beat_wages
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
```

How have prices, rents and wages changed in Australia since 1997, by state and capital city? This dashboard compares three official Australian Bureau of Statistics (ABS) measures, quarter by quarter, from {range[0]?.first_quarter} to {range[0]?.latest_quarter} (the quarter ending {range[0]?.latest_quarter_end}):

- the Consumer Price Index (CPI, all groups), which measures prices paid by households in each capital city;
- the CPI Rents component, which measures rents paid by renting households;
- the Wage Price Index (WPI), which measures the price of labour (hourly pay rates for the same jobs over time) in each state.

Every number on these pages is calculated from the pipeline's `marts` tables. The figures are index changes, not dollar amounts. CPI and rents describe capital cities, while wages describe whole states; see [Methodology](/methodology).

## Latest quarter: Australia, change over 12 months

<BigValue data={latest_aus} value=cpi_annual_pct title="Prices (CPI)" fmt='0.0"%"' />
<BigValue data={latest_aus} value=rents_annual_pct title="Rents" fmt='0.0"%"' />
<BigValue data={latest_aus} value=wpi_annual_pct title="Wages (WPI)" fmt='0.0"%"' />
<BigValue data={latest_aus} value=real_wage_growth_pct_pts title="Real wage growth (pts)" fmt='+0.00;-0.00' />

*Annual % change to {range[0]?.latest_quarter}. Real wage growth = WPI annual % minus CPI annual %, in percentage points. "Australia" = CPI for the weighted average of the eight capital cities and WPI for all of Australia. Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*

## Key findings

1. **Since 1997-Q3, wages have risen a little faster than prices overall.** In Australia, prices rose +{latest_aus[0]?.cpi_change?.toFixed(1)}%, rents +{latest_aus[0]?.rents_change?.toFixed(1)}% and wages +{latest_aus[0]?.wpi_change?.toFixed(1)}%. Wages relative to prices (WPI ÷ CPI) were {latest_aus[0]?.wages_vs_prices?.toFixed(1)}% higher than in 1997-Q3.
2. **Most of that gain was lost after 2021.** Wages relative to prices (WPI ÷ CPI) peaked in {real_wage_peak[0]?.peak_quarter} and fell {real_wage_peak[0]?.fall_pct?.toFixed(1)}% to a low in {real_wage_peak[0]?.trough_quarter}. The 2020 peak is partly a temporary dip in prices during the COVID-19 period. Real wage growth was negative for {negative_run[0]?.quarters} quarters in a row, from {negative_run[0]?.first_quarter} to {negative_run[0]?.last_quarter}.
3. **Prices are again rising faster than wages.** In {range[0]?.latest_quarter}, real wage growth was negative in every one of the nine regions (see the table below).
4. **Rents grew very unevenly across capitals.** Since 1997-Q3, rents rose most in {rents_extremes[0]?.fastest_city} (+{rents_extremes[0]?.fastest_pct?.toFixed(1)}%) and least in {rents_extremes[0]?.slowest_city} (+{rents_extremes[0]?.slowest_pct?.toFixed(1)}%). Rents outpaced the state's wages in only {rents_extremes[0]?.cities_rents_beat_wages} of the eight capitals.

What this does not show: why any of this happened; levels or affordability in dollars; market asking rents for new leases (CPI rents cover all renting households and are net of Commonwealth Rent Assistance); or anything about regional areas outside the capital cities.

<DataTable data={latest_by_region} rows=all>
  <Column id=region_label title="Region (capital city)" />
  <Column id=cpi_annual_pct title="Prices (CPI) %" fmt='0.0' />
  <Column id=rents_annual_pct title="Rents %" fmt='0.0' />
  <Column id=wpi_annual_pct title="Wages (WPI) %" fmt='0.0' />
  <Column id=real_wage_growth_pct_pts title="Real wage growth, pts" fmt='+0.00;-0.00' />
</DataTable>

*Annual % change to the latest quarter, by region. Rents changes in this quarter compare the new monthly series with the archived quarterly series (see [Rents](/rents)). Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*

Pages: [Prices, rents and wages over time](/over-time) · [Real wage growth](/real-wages) · [Rents](/rents) · [Methodology and limitations](/methodology)
