-- The main mart: one row per quarter x region (marts schema only).
-- region_label is a short display name for chart axes.
select *,
       case when is_national then 'Australia (8 capitals)'
            when region_key = 'ACT' then 'ACT (Canberra)'
            else region_name || ' (' || capital_city || ')' end as region_label
from marts.mart_cost_of_living_quarterly
