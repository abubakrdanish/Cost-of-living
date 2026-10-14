-- Warn (not fail) when a new snapshot is more than 25% larger than the one
-- before. A normal monthly release adds a few dozen rows to tables of
-- thousands, so a big jump usually means the ABS added series or the query
-- key widened, which is worth a look before trusting downstream numbers.

{{ config(severity='warn') }}

with counts as (

    {{ raw_snapshot_counts('abs_cpi_all_groups') }}
    union all
    {{ raw_snapshot_counts('abs_cpi_rents') }}
    union all
    {{ raw_snapshot_counts('abs_wpi') }}

)

select
    latest.raw_table,
    latest.row_count   as latest_rows,
    previous.row_count as previous_rows
from counts as latest
inner join counts as previous
    on previous.raw_table = latest.raw_table
   and previous.snapshot_rank = 2
where latest.snapshot_rank = 1
  and latest.row_count > previous.row_count * 1.25
