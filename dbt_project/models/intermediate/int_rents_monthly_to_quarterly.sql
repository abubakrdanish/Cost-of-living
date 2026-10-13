-- Quarterly averages of the monthly CPI Rents series (Australia + 8 capitals,
-- from 2022-Q3). Only complete quarters (all 3 months published) are kept;
-- a partial quarter such as 2026-Q3 with only Jul and Aug is excluded.
-- Base: Sep 2025 = 100.

select
    cpi_region_code,
    quarter_start_date,
    avg(index_value)   as index_value,
    count(*)           as months_in_quarter,
    bool_or(is_revised) as includes_revised_month
from {{ ref('stg_abs__cpi_rents') }}
where frequency_code = 'M'
group by cpi_region_code, quarter_start_date
having count(*) = 3
