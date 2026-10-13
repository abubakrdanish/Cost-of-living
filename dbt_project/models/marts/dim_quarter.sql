-- One row per calendar quarter, from the earliest to the latest quarter seen in
-- any staging model (1948-Q3 to the current partial quarter).

with bounds as (

    select min(quarter_start_date) as first_quarter, max(quarter_start_date) as last_quarter
    from (
        select quarter_start_date from {{ ref('stg_abs__cpi_all_groups') }}
        union all
        select quarter_start_date from {{ ref('stg_abs__cpi_rents') }}
        union all
        select quarter_start_date from {{ ref('stg_abs__cpi_rents_archive') }}
        union all
        select quarter_start_date from {{ ref('stg_abs__wpi') }}
    )

),

quarters as (

    select cast(q as date) as quarter_start_date
    from bounds, range(first_quarter, last_quarter + interval 1 day, interval 3 month) as t(q)

)

select
    quarter_start_date,
    cast(quarter_start_date + interval 3 month - interval 1 day as date) as quarter_end_date,
    year(quarter_start_date)                                   as year,
    quarter(quarter_start_date)                                as quarter_number,
    year(quarter_start_date) || '-Q' || quarter(quarter_start_date) as quarter_label,
    -- Australian financial year runs July to June: 1997-Q3 is in FY 1997-98.
    case
        when quarter(quarter_start_date) >= 3
            then year(quarter_start_date) || '-' || right(cast(year(quarter_start_date) + 1 as varchar), 2)
        else (year(quarter_start_date) - 1) || '-' || right(cast(year(quarter_start_date) as varchar), 2)
    end                                                        as financial_year
from quarters
