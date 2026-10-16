-- Regions and the city-vs-state comparison caveat (marts schema only).
-- region_label is a short display name for chart axes and the region picker.
select *,
       case when is_national then 'Australia (8 capitals)'
            when region_key = 'ACT' then 'ACT (Canberra)'
            else region_name || ' (' || capital_city || ')' end as region_label
from marts.dim_region
