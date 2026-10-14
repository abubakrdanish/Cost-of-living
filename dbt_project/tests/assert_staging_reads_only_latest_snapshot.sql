-- Revision handling, part 1: when ABS revises a value, the newer download
-- holds the new value and older downloads keep the old one. Staging must read
-- ONLY the newest snapshot, otherwise old and revised values would both
-- flow downstream (or the wrong one would win).

with staged as (

    select 'stg_abs__cpi_all_groups' as model, 'abs_cpi_all_groups' as raw_table, _source_file
    from {{ ref('stg_abs__cpi_all_groups') }}
    union all
    select 'stg_abs__cpi_rents', 'abs_cpi_rents', _source_file
    from {{ ref('stg_abs__cpi_rents') }}
    union all
    select 'stg_abs__cpi_rents_archive', 'abs_cpi_capital_cities_quarterly_2025q3', _source_file
    from {{ ref('stg_abs__cpi_rents_archive') }}
    union all
    select 'stg_abs__wpi', 'abs_wpi', _source_file
    from {{ ref('stg_abs__wpi') }}

),

newest as (

    select 'abs_cpi_all_groups' as raw_table, max(_source_file) as newest_file
    from {{ source('raw', 'abs_cpi_all_groups') }}
    union all
    select 'abs_cpi_rents', max(_source_file) from {{ source('raw', 'abs_cpi_rents') }}
    union all
    select 'abs_cpi_capital_cities_quarterly_2025q3', max(_source_file)
    from {{ source('raw', 'abs_cpi_capital_cities_quarterly_2025q3') }}
    union all
    select 'abs_wpi', max(_source_file) from {{ source('raw', 'abs_wpi') }}

)

select distinct staged.model, staged._source_file, newest.newest_file
from staged
inner join newest using (raw_table)
where staged._source_file <> newest.newest_file
