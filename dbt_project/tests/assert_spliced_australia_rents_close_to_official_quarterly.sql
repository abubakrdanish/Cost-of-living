-- Cross-check: for Australia, ABS still publishes an official quarterly Rents
-- series in the API. Our spliced series (built the same way as for the
-- capitals) should stay close to it. Warn, not fail, above 0.5%: a
-- difference here shows how much the splice method itself drifts.

{{ config(severity='warn') }}

with official as (

    select quarter_start_date, index_value as official_value
    from {{ ref('stg_abs__cpi_rents') }}
    where frequency_code = 'Q' and cpi_region_code = '50'

),

spliced as (

    select quarter_start_date, index_value as spliced_value, source_series
    from {{ ref('int_rents_quarterly_spliced') }}
    where cpi_region_code = '50'

)

select
    quarter_start_date,
    source_series,
    official_value,
    spliced_value,
    100 * (spliced_value / official_value - 1) as diff_pct
from spliced
inner join official using (quarter_start_date)
where quarter_start_date >= cast('{{ var("mart_start_quarter") }}' as date)
  and abs(100 * (spliced_value / official_value - 1)) > 0.5
