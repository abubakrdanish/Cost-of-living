-- Historical quarterly CPI Rents by capital city, 1972-Q3 to 2025-Q3, from the
-- final quarterly CPI release (6401.0 Sep quarter 2025, Table 9).
-- Only the 9 Rents series listed in the abs_archive_rents_series seed are kept.
-- Index base: 2011-12 = 100 (checked: FY2011-12 quarterly average = 100.0).

with source as (

    select * from {{ source('raw', 'abs_cpi_capital_cities_quarterly_2025q3') }}
    where {{ latest_snapshot_filter(source('raw', 'abs_cpi_capital_cities_quarterly_2025q3')) }}

),

series as (

    select * from {{ ref('abs_archive_rents_series') }}

)

select
    source.series_id,
    series.cpi_region_code,
    series.capital_city,
    trim(source.series_description)                  as series_description,
    source.series_type,
    source.frequency,
    source.period                                    as period_date,  -- ABS stamps quarters by their last month
    cast(date_trunc('quarter', source.period) as date) as quarter_start_date,
    source.value                                     as index_value,
    '2011-12 = 100.0'                                as base_period_label,
    source._source_file,
    source._loaded_at
from source
inner join series using (series_id)
where source.series_type = 'Original'
  and source.frequency = 'Quarter'
