-- One row per region. CPI and rents describe a capital city; WPI describes the
-- whole state or territory. Joining them via this mapping is an approximation.

select
    region_key,
    region_sort_order,
    is_national,
    state_name                                        as region_name,
    capital_city,
    state_name,
    cpi_region_code,
    wpi_region_code,
    case
        when is_national then
            'CPI and rents: weighted average of the eight capital cities. '
            || 'WPI: all of Australia. Comparing them is an approximation.'
        else
            'CPI and rents: ' || capital_city || ' only. WPI: all of '
            || state_name || '. Comparing them is an approximation.'
    end                                               as comparison_note
from {{ ref('region_mapping') }}
