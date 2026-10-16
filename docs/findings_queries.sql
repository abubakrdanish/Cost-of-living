-- Queries behind every figure in the Findings (README and dashboard Overview).
-- They read marts only. Run them all, read-only, with:
--     python -m orchestration.findings
-- Each block starts with "-- name: <id>" and a one-line description.
-- "Latest quarter" means the mart's last quarter (2026-Q2 on 2026-10-16).

-- name: F0_range
-- The period covered by the mart.
select min(quarter_label) as first_quarter,
       max(quarter_label) as latest_quarter,
       count(distinct quarter_start_date) as quarters,
       count(distinct region_key) as regions
from marts.mart_cost_of_living_quarterly;

-- name: F1_cumulative_australia
-- Australia: cumulative % change since 1997-Q3 (index - 100), latest quarter,
-- and wages relative to prices (WPI index / CPI index - 1).
select quarter_label,
       round(cpi_index - 100, 1)                      as cpi_change_pct,
       round(rents_index - 100, 1)                    as rents_change_pct,
       round(wpi_index - 100, 1)                      as wpi_change_pct,
       round(100 * (wpi_index / cpi_index - 1), 1)    as wages_vs_prices_pct
from marts.mart_cost_of_living_quarterly
where region_key = 'AUS'
  and quarter_start_date = (select max(quarter_start_date) from marts.mart_cost_of_living_quarterly);

-- name: F2_real_wage_peak_and_trough
-- Australia: highest WPI/CPI ratio (x100) up to 2021, and the lowest after it.
with r as (
    select quarter_start_date, quarter_label, 100 * wpi_index / cpi_index as real_wage_index
    from marts.mart_cost_of_living_quarterly
    where region_key = 'AUS'
),
peak as (
    select arg_max(quarter_label, real_wage_index) as peak_quarter,
           round(max(real_wage_index), 1)           as peak_value,
           arg_max(quarter_start_date, real_wage_index) as peak_date
    from r where quarter_start_date < '2022-01-01'
)
select peak.peak_quarter, peak.peak_value,
       arg_min(r.quarter_label, r.real_wage_index)   as trough_quarter,
       round(min(r.real_wage_index), 1)              as trough_value,
       round(100 * (min(r.real_wage_index) / peak.peak_value - 1), 1) as fall_pct,
       (select round(real_wage_index, 1) from r
         where quarter_start_date = (select max(quarter_start_date) from r)) as latest_value
from r, peak
where r.quarter_start_date > peak.peak_date
group by peak.peak_quarter, peak.peak_value;

-- name: F3_real_wage_growth_australia
-- Australia: how often real wage growth (WPI annual % - CPI annual %) was
-- positive, and its lowest value.
select count(*)                                               as quarters_with_value,
       count(*) filter (where real_wage_growth_pct_pts > 0)   as quarters_positive,
       round(100.0 * count(*) filter (where real_wage_growth_pct_pts > 0) / count(*), 0) as pct_positive,
       min(real_wage_growth_pct_pts)                          as lowest_pct_pts,
       arg_min(quarter_label, real_wage_growth_pct_pts)       as lowest_quarter
from marts.mart_cost_of_living_quarterly
where region_key = 'AUS' and real_wage_growth_pct_pts is not null;

-- name: F4_negative_runs_australia
-- Australia: runs of consecutive quarters with negative real wage growth
-- since 2020 (start, end, length).
with s as (
    select quarter_start_date, quarter_label, real_wage_growth_pct_pts < 0 as negative,
           row_number() over (order by quarter_start_date)
         - row_number() over (partition by real_wage_growth_pct_pts < 0 order by quarter_start_date) as grp
    from marts.mart_cost_of_living_quarterly
    where region_key = 'AUS' and quarter_start_date >= '2020-01-01'
)
select min(quarter_label) as first_quarter, max(quarter_label) as last_quarter, count(*) as quarters
from s where negative
group by grp
order by first_quarter;

-- name: F5_latest_real_wage_growth_by_region
-- Latest quarter: real wage growth by region, and how many regions are negative.
select region_key, real_wage_growth_pct_pts,
       count(*) filter (where real_wage_growth_pct_pts < 0) over () as regions_negative
from marts.mart_cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.mart_cost_of_living_quarterly)
order by region_sort_order;

-- name: F6_rents_vs_wages_by_region
-- Since 1997-Q3: rents and wages cumulative % change by region, and whether
-- rents grew faster than wages (rents index / WPI index - 1).
select region_key, capital_city,
       round(rents_index - 100, 1)                    as rents_change_pct,
       round(wpi_index - 100, 1)                      as wpi_change_pct,
       round(100 * (rents_index / wpi_index - 1), 1)  as rents_vs_wages_pct
from marts.mart_cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.mart_cost_of_living_quarterly)
order by rents_change_pct desc;

-- name: F7_latest_rent_growth_by_region
-- Latest quarter: annual rent change by region (these cross the splice, so
-- treat as +/- ~0.4 points).
select region_key, capital_city, rents_annual_pct, rents_annual_pct_crosses_splice
from marts.mart_cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.mart_cost_of_living_quarterly)
order by rents_annual_pct desc;

-- name: F8_splice_gap
-- Rents splice: largest deviation in the overlap, smallest and largest region.
select min(max_abs_deviation_pct) as smallest_max_deviation_pct,
       arg_min(capital_city, max_abs_deviation_pct) as smallest_city,
       max(max_abs_deviation_pct) as largest_max_deviation_pct,
       arg_max(capital_city, max_abs_deviation_pct) as largest_city,
       arg_max(max_deviation_quarter, max_abs_deviation_pct) as largest_quarter
from marts.mart_rents_splice_check;
