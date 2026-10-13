-- The rents splice assumes the archived quarterly series and the quarterly
-- average of the monthly series move together. Fail if, in any overlap
-- quarter, their ratio drifts from the link factor by more than
-- var('rents_splice_tolerance_pct') percent. Also fail if a region has no
-- overlap at all (the splice could not be checked).

select cpi_region_code, quarter_start_date, deviation_pct, 'deviation above tolerance' as problem
from {{ ref('int_rents_splice_overlap') }}
where abs(deviation_pct) > {{ var('rents_splice_tolerance_pct') }}

union all

select cpi_region_code, null, null, 'fewer than 4 overlap quarters' as problem
from {{ ref('region_mapping') }}
where cpi_region_code not in (
    select cpi_region_code
    from {{ ref('int_rents_splice_overlap') }}
    group by cpi_region_code
    having count(*) >= 4
)
