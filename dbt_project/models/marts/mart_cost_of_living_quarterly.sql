-- Grain: one row per quarter x region (9 regions: Australia + 8 states/capitals).
-- Range: var('mart_start_quarter') (1997-Q3) to the latest quarter that CPI,
-- rents and WPI all cover (2026-Q2 on 2026-10-13).
--
-- Every region x quarter in the range gets a row (a full spine), so a value
-- that does not exist shows up as a null explained in missing_reason rather
-- than as a missing row.
--
-- Indexes are rebased to 100 at var('index_base_quarter') (1997-Q3).
-- Annual % changes are computed on the ABS-base values over the full history
-- before the range filter, so CPI and rents changes exist from the first row.

{% set start_quarter = var('mart_start_quarter') %}
{% set base_quarter = var('index_base_quarter') %}

with regions as (

    select * from {{ ref('dim_region') }}

),

-- One CTE per series, keyed by region_key and quarter.

cpi as (

    select
        regions.region_key,
        cpi.quarter_start_date,
        cpi.index_value,
        cpi.is_revised
    from {{ ref('stg_abs__cpi_all_groups') }} as cpi
    inner join regions using (cpi_region_code)
    where cpi.frequency_code = 'Q'

),

rents as (

    select
        regions.region_key,
        rents.quarter_start_date,
        rents.index_value,
        rents.source_series,
        rents.is_splice_point,
        rents.includes_revised_month as is_revised
    from {{ ref('int_rents_quarterly_spliced') }} as rents
    inner join regions using (cpi_region_code)

),

wpi as (

    select
        regions.region_key,
        wpi.quarter_start_date,
        wpi.index_value,
        wpi.is_revised
    from {{ ref('stg_abs__wpi') }} as wpi
    inner join regions using (wpi_region_code)

),

-- Annual % change against the same quarter a year earlier. A join rather than
-- lag(), so a gap in a series can never pair the wrong quarters.

cpi_changes as (

    select
        cur.*,
        100 * (cur.index_value / prev.index_value - 1) as annual_pct
    from cpi as cur
    left join cpi as prev
        on prev.region_key = cur.region_key
       and prev.quarter_start_date = cast(cur.quarter_start_date - interval 1 year as date)

),

rents_changes as (

    select
        cur.*,
        100 * (cur.index_value / prev.index_value - 1) as annual_pct,
        -- True when the two quarters compared come from different source series.
        prev.source_series is not null
            and prev.source_series <> cur.source_series as annual_pct_crosses_splice
    from rents as cur
    left join rents as prev
        on prev.region_key = cur.region_key
       and prev.quarter_start_date = cast(cur.quarter_start_date - interval 1 year as date)

),

wpi_changes as (

    select
        cur.*,
        100 * (cur.index_value / prev.index_value - 1) as annual_pct
    from wpi as cur
    left join wpi as prev
        on prev.region_key = cur.region_key
       and prev.quarter_start_date = cast(cur.quarter_start_date - interval 1 year as date)

),

-- Range and spine.

series_bounds as (

    select
        least(
            (select max(quarter_start_date) from cpi),
            (select max(quarter_start_date) from rents),
            (select max(quarter_start_date) from wpi)
        ) as end_quarter,
        (select min(quarter_start_date) from cpi)   as cpi_first_quarter,
        (select min(quarter_start_date) from rents) as rents_first_quarter,
        (select min(quarter_start_date) from wpi)   as wpi_first_quarter

),

spine as (

    select regions.*, quarters.*
    from regions
    cross join {{ ref('dim_quarter') }} as quarters
    cross join series_bounds
    where quarters.quarter_start_date between cast('{{ start_quarter }}' as date)
                                          and series_bounds.end_quarter

),

-- Base-quarter value per region, for rebasing.

base as (

    select
        regions.region_key,
        (select index_value from cpi
          where cpi.region_key = regions.region_key
            and cpi.quarter_start_date = cast('{{ base_quarter }}' as date))   as cpi_base,
        (select index_value from rents
          where rents.region_key = regions.region_key
            and rents.quarter_start_date = cast('{{ base_quarter }}' as date)) as rents_base,
        (select index_value from wpi
          where wpi.region_key = regions.region_key
            and wpi.quarter_start_date = cast('{{ base_quarter }}' as date))   as wpi_base
    from regions

),

joined as (

    select
        spine.quarter_start_date,
        spine.quarter_end_date,
        spine.quarter_label,
        spine.year,
        spine.quarter_number,
        spine.financial_year,
        spine.region_key,
        spine.region_name,
        spine.capital_city,
        spine.state_name,
        spine.is_national,
        spine.region_sort_order,

        cpi_changes.index_value                       as cpi_index_abs_base,
        rents_changes.index_value                     as rents_index_abs_base,
        wpi_changes.index_value                       as wpi_index_abs_base,

        100 * cpi_changes.index_value / base.cpi_base     as cpi_index,
        100 * rents_changes.index_value / base.rents_base as rents_index,
        100 * wpi_changes.index_value / base.wpi_base     as wpi_index,

        cpi_changes.annual_pct                        as cpi_annual_pct,
        rents_changes.annual_pct                      as rents_annual_pct,
        wpi_changes.annual_pct                        as wpi_annual_pct,
        wpi_changes.annual_pct - cpi_changes.annual_pct as real_wage_growth_pct_pts,

        rents_changes.source_series                   as rents_source_series,
        rents_changes.is_splice_point                 as rents_is_splice_point,
        rents_changes.annual_pct_crosses_splice       as rents_annual_pct_crosses_splice,

        cpi_changes.is_revised                        as cpi_is_revised,
        rents_changes.is_revised                      as rents_includes_revised_month,
        wpi_changes.is_revised                        as wpi_is_revised,

        series_bounds.cpi_first_quarter,
        series_bounds.rents_first_quarter,
        series_bounds.wpi_first_quarter
    from spine
    cross join series_bounds
    left join base          using (region_key)
    left join cpi_changes   using (region_key, quarter_start_date)
    left join rents_changes using (region_key, quarter_start_date)
    left join wpi_changes   using (region_key, quarter_start_date)

)

select
    quarter_start_date,
    quarter_end_date,
    quarter_label,
    year,
    quarter_number,
    financial_year,
    region_key,
    region_name,
    capital_city,
    state_name,
    is_national,
    region_sort_order,

    round(cpi_index, 2)                 as cpi_index,
    round(rents_index, 2)               as rents_index,
    round(wpi_index, 2)                 as wpi_index,

    round(cpi_index_abs_base, 2)        as cpi_index_abs_base,
    round(rents_index_abs_base, 2)      as rents_index_abs_base,
    round(wpi_index_abs_base, 2)        as wpi_index_abs_base,

    round(cpi_annual_pct, 2)            as cpi_annual_pct,
    round(rents_annual_pct, 2)          as rents_annual_pct,
    round(wpi_annual_pct, 2)            as wpi_annual_pct,
    round(real_wage_growth_pct_pts, 2)  as real_wage_growth_pct_pts,

    rents_source_series,
    rents_is_splice_point,
    rents_annual_pct_crosses_splice,
    cpi_is_revised,
    rents_includes_revised_month,
    wpi_is_revised,

    -- Null when every value is present; otherwise lists what is missing and why.
    nullif(concat_ws('; ',
        case when cpi_index_abs_base is null
             then 'CPI not published for this region and quarter' end,
        case when rents_index_abs_base is null
             then 'Rents not published for this region and quarter' end,
        case when wpi_index_abs_base is null
             then 'WPI not published for this region and quarter' end,
        case when cpi_index_abs_base is not null and cpi_annual_pct is null
             then 'CPI annual change needs the same quarter a year earlier (CPI starts '
                  || strftime(cpi_first_quarter, '%Y-%m') || ')' end,
        case when rents_index_abs_base is not null and rents_annual_pct is null
             then 'Rents annual change needs the same quarter a year earlier (rents start '
                  || strftime(rents_first_quarter, '%Y-%m') || ')' end,
        case when wpi_index_abs_base is not null and wpi_annual_pct is null
             then 'WPI annual change needs the same quarter a year earlier (WPI starts '
                  || year(wpi_first_quarter) || '-Q' || quarter(wpi_first_quarter) || ')' end,
        case when real_wage_growth_pct_pts is null
             then 'Real wage growth needs both WPI and CPI annual change' end
    ), '')                              as missing_reason
from joined
order by quarter_start_date, region_sort_order
