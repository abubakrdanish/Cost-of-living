-- One continuous quarterly CPI Rents series per region (approved 2026-10-13):
--   * up to and including 2025-Q3: archived quarterly series (base 2011-12 = 100),
--     multiplied by the link factor so it is on the current base (Sep 2025 = 100);
--   * from 2025-Q4: quarterly average of the monthly series (already Sep 2025 = 100).
-- The link factor is the ratio monthly_avg / archive in the link quarter
-- (2025-Q3). See int_rents_splice_overlap for how stable that ratio is.

with archive as (

    select cpi_region_code, quarter_start_date, index_value
    from {{ ref('stg_abs__cpi_rents_archive') }}

),

monthly as (

    select * from {{ ref('int_rents_monthly_to_quarterly') }}

),

link as (

    select distinct cpi_region_code, link_quarter, link_factor
    from {{ ref('int_rents_splice_overlap') }}

),

archive_rebased as (

    select
        archive.cpi_region_code,
        archive.quarter_start_date,
        archive.index_value * link.link_factor  as index_value,
        'archive_quarterly_table9'              as source_series,
        false                                   as includes_revised_month,
        link.link_factor,
        link.link_quarter
    from archive
    inner join link using (cpi_region_code)

),

monthly_after_link as (

    select
        monthly.cpi_region_code,
        monthly.quarter_start_date,
        monthly.index_value,
        'api_monthly_average'                   as source_series,
        monthly.includes_revised_month,
        link.link_factor,
        link.link_quarter
    from monthly
    inner join link using (cpi_region_code)
    where monthly.quarter_start_date > link.link_quarter

)

select
    *,
    -- First quarter taken from the new series: the join point of the splice.
    quarter_start_date = cast(link_quarter + interval 3 month as date) as is_splice_point
from (
    select * from archive_rebased
    union all
    select * from monthly_after_link
)
