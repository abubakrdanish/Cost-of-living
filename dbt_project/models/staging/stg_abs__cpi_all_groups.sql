-- All groups CPI, Original series, monthly and quarterly, Australia + 8 capitals.
-- Latest raw snapshot only. Index base: Sep 2025 = 100.

with source as (

    select * from {{ source('raw', 'abs_cpi_all_groups') }}
    where {{ latest_snapshot_filter(source('raw', 'abs_cpi_all_groups')) }}

),

renamed as (

    select
        {{ abs_code('measure') }}            as measure_code,
        {{ abs_code('"index"') }}            as index_code,
        {{ abs_label('"index"') }}           as index_label,
        {{ abs_code('tsest') }}              as adjustment_type_code,
        {{ abs_label('tsest') }}             as adjustment_type_label,
        {{ abs_code('region') }}             as cpi_region_code,
        {{ abs_label('region') }}            as region_label,
        {{ abs_code('freq') }}               as frequency_code,
        time_period,
        {{ abs_period_start('time_period') }} as period_start_date,
        cast(obs_value as double)            as index_value,
        {{ abs_label('unit_measure') }}      as unit_label,
        {{ abs_code('obs_status') }}         as obs_status_code,
        {{ abs_label('base_period') }}       as base_period_label,
        _source_file,
        _loaded_at
    from source

)

select
    *,
    cast(date_trunc('quarter', period_start_date) as date) as quarter_start_date,
    coalesce(obs_status_code = 'r', false)                 as is_revised
from renamed
where measure_code = '1'            -- index numbers
  and index_code = '10001'          -- All groups CPI
  and adjustment_type_code = '10'   -- Original
