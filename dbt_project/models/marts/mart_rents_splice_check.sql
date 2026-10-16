-- One row per region: how well the archived quarterly rents and the quarterly
-- average of monthly rents agree in their overlap (2022-Q3 to 2025-Q3).
-- Exposes the splice check to the dashboard, which reads marts only.
-- Detail per quarter: intermediate.int_rents_splice_overlap.

with overlap as (

    select * from {{ ref('int_rents_splice_overlap') }}

),

per_region as (

    select
        cpi_region_code,
        count(*)                                    as overlap_quarters,
        min(quarter_start_date)                     as first_overlap_quarter,
        max(quarter_start_date)                     as last_overlap_quarter,
        any_value(link_quarter)                     as link_quarter,
        any_value(link_factor)                      as link_factor,
        max(abs(deviation_pct))                     as max_abs_deviation_pct,
        arg_max(quarter_start_date, abs(deviation_pct)) as max_deviation_quarter
    from overlap
    group by cpi_region_code

)

select
    regions.region_key,
    regions.region_name,
    regions.capital_city,
    regions.region_sort_order,
    per_region.overlap_quarters,
    year(per_region.first_overlap_quarter) || '-Q' || quarter(per_region.first_overlap_quarter) as first_overlap_quarter,
    year(per_region.last_overlap_quarter) || '-Q' || quarter(per_region.last_overlap_quarter)   as last_overlap_quarter,
    year(per_region.link_quarter) || '-Q' || quarter(per_region.link_quarter)                   as link_quarter,
    round(per_region.link_factor, 4)                as link_factor,
    round(per_region.max_abs_deviation_pct, 2)      as max_abs_deviation_pct,
    year(per_region.max_deviation_quarter) || '-Q' || quarter(per_region.max_deviation_quarter) as max_deviation_quarter,
    {{ var('rents_splice_tolerance_pct') }}         as tolerance_pct
from per_region
inner join {{ ref('dim_region') }} as regions using (cpi_region_code)
order by regions.region_sort_order
