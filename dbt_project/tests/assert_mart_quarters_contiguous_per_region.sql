-- Every region must have one row for every quarter in the mart's range, with
-- no gaps: rows per region = number of quarters between first and last.
-- Also checks that every region in dim_region appears.

with per_region as (

    select
        region_key,
        count(*)                as row_count,
        min(quarter_start_date) as first_quarter,
        max(quarter_start_date) as last_quarter
    from {{ ref('mart_cost_of_living_quarterly') }}
    group by region_key

),

expected as (

    select
        region_key,
        row_count,
        date_diff('quarter', first_quarter, last_quarter) + 1 as expected_quarters,
        first_quarter,
        last_quarter
    from per_region

)

select region_key, row_count, expected_quarters, first_quarter, last_quarter,
       'gap or duplicate quarters' as problem
from expected
where row_count <> expected_quarters
   or first_quarter <> (select min(first_quarter) from expected)
   or last_quarter <> (select max(last_quarter) from expected)

union all

select region_key, null, null, null, null, 'region missing from mart' as problem
from {{ ref('dim_region') }}
where region_key not in (select region_key from per_region)
