-- Revision handling, part 2: ABS revision flags (OBS_STATUS = r) must be
-- carried into the mart exactly, not dropped or invented.
--   * cpi_is_revised = the quarterly CPI observation's flag
--   * rents_includes_revised_month = any revised month in that quarter
--     (only for quarters taken from the monthly series)
--   * wpi_is_revised = the WPI observation's flag

with regions as (

    select region_key, cpi_region_code, wpi_region_code from {{ ref('dim_region') }}

),

expected as (

    select
        mart.region_key,
        mart.quarter_start_date,
        coalesce(cpi.is_revised, false)                as expected_cpi,
        coalesce(rents.includes_revised_month, false)  as expected_rents,
        coalesce(wpi.is_revised, false)                as expected_wpi,
        coalesce(mart.cpi_is_revised, false)           as mart_cpi,
        coalesce(mart.rents_includes_revised_month, false) as mart_rents,
        coalesce(mart.wpi_is_revised, false)           as mart_wpi
    from {{ ref('mart_cost_of_living_quarterly') }} as mart
    inner join regions using (region_key)
    left join {{ ref('stg_abs__cpi_all_groups') }} as cpi
        on cpi.cpi_region_code = regions.cpi_region_code
       and cpi.frequency_code = 'Q'
       and cpi.quarter_start_date = mart.quarter_start_date
    left join {{ ref('int_rents_quarterly_spliced') }} as rents
        on rents.cpi_region_code = regions.cpi_region_code
       and rents.quarter_start_date = mart.quarter_start_date
    left join {{ ref('stg_abs__wpi') }} as wpi
        on wpi.wpi_region_code = regions.wpi_region_code
       and wpi.quarter_start_date = mart.quarter_start_date

)

select *
from expected
where expected_cpi <> mart_cpi
   or expected_rents <> mart_rents
   or expected_wpi <> mart_wpi
