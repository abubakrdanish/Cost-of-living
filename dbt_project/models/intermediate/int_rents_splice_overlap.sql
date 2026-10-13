-- Documented check for the rents splice. For every quarter where both the
-- archived quarterly series and the monthly-average series exist (2022-Q3 to
-- 2025-Q3), compare their ratio with the link factor used for the splice
-- (the ratio in the link quarter, 2025-Q3). If quarterly = average of months
-- held exactly, the ratio would be constant and deviation_pct would be 0.

with archive as (

    select cpi_region_code, quarter_start_date, index_value as archive_value
    from {{ ref('stg_abs__cpi_rents_archive') }}

),

monthly as (

    select cpi_region_code, quarter_start_date, index_value as monthly_avg_value
    from {{ ref('int_rents_monthly_to_quarterly') }}

),

overlap as (

    select
        cpi_region_code,
        quarter_start_date,
        archive_value,
        monthly_avg_value,
        monthly_avg_value / archive_value as ratio
    from archive
    inner join monthly using (cpi_region_code, quarter_start_date)

),

link as (

    -- Link quarter = last quarter of the archive (2025-Q3).
    select cpi_region_code, quarter_start_date as link_quarter, ratio as link_factor
    from overlap
    where quarter_start_date = (select max(quarter_start_date) from archive)

)

select
    overlap.cpi_region_code,
    overlap.quarter_start_date,
    overlap.archive_value,
    overlap.monthly_avg_value,
    overlap.ratio,
    link.link_quarter,
    link.link_factor,
    100 * (overlap.ratio / link.link_factor - 1) as deviation_pct
from overlap
inner join link using (cpi_region_code)
