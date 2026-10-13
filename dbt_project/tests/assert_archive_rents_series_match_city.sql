-- The abs_archive_rents_series seed maps ABS series IDs to regions by hand.
-- Check each series' own description names Rents and the expected city, so a
-- typo in the seed cannot silently attach one city's rents to another.

select distinct series_id, capital_city, series_description
from {{ ref('stg_abs__cpi_rents_archive') }}
where series_description not like 'Index Numbers ;  Rents ;  ' || capital_city || ' ;'
