-- Wage Price Index: total hourly rates of pay excluding bonuses (THRPEB, the ABS
-- headline WPI), Private and Public sector, All industries, Original series,
-- quarterly, Australia + 8 states/territories. Latest raw snapshot only.
-- Index base: 2008-09 = 100 (ABS release page; the API's BASE_PERIOD is blank).

with source as (

    select * from {{ source('raw', 'abs_wpi') }}
    where {{ latest_snapshot_filter(source('raw', 'abs_wpi')) }}

),

renamed as (

    select
        {{ abs_code('measure') }}            as measure_code,
        {{ abs_code('"index"') }}            as index_code,
        {{ abs_label('"index"') }}           as index_label,
        {{ abs_code('sector') }}             as sector_code,
        {{ abs_label('sector') }}            as sector_label,
        {{ abs_code('industry') }}           as industry_code,
        {{ abs_label('industry') }}          as industry_label,
        {{ abs_code('tsest') }}              as adjustment_type_code,
        {{ abs_label('tsest') }}             as adjustment_type_label,
        {{ abs_code('region') }}             as wpi_region_code,
        {{ abs_label('region') }}            as region_label,
        {{ abs_code('freq') }}               as frequency_code,
        time_period,
        {{ abs_period_start('time_period') }} as quarter_start_date,
        cast(obs_value as double)            as index_value,
        {{ abs_label('unit_measure') }}      as unit_label,
        {{ abs_code('obs_status') }}         as obs_status_code,
        _source_file,
        _loaded_at
    from source

)

select
    *,
    '2008-09 = 100.0'                      as base_period_label,
    coalesce(obs_status_code = 'r', false) as is_revised
from renamed
where measure_code = '1'             -- quarterly index
  and index_code = 'THRPEB'          -- total hourly rates of pay excluding bonuses
  and sector_code = '7'              -- Private and Public
  and industry_code = 'TOT'          -- All industries
  and adjustment_type_code = '10'    -- Original (the only type published for states)
  and frequency_code = 'Q'
