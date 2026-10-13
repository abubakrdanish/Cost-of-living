-- All three rebased indexes must equal exactly 100 in the base quarter for
-- every region (catches a wrong or missing base value).

select region_key, quarter_label, cpi_index, rents_index, wpi_index
from {{ ref('mart_cost_of_living_quarterly') }}
where quarter_start_date = cast('{{ var("index_base_quarter") }}' as date)
  and not (cpi_index = 100 and rents_index = 100 and wpi_index = 100)
