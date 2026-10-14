-- Row-count sanity check against the previous load. ABS time series only
-- grow (new periods are appended; revisions change values, not row counts),
-- so a newer snapshot with FEWER rows than the one before means a series was
-- dropped, the query key changed, or the download was truncated.
-- Passes trivially when a table has only one snapshot.

with counts as (

    {{ raw_snapshot_counts('abs_cpi_all_groups') }}
    union all
    {{ raw_snapshot_counts('abs_cpi_rents') }}
    union all
    {{ raw_snapshot_counts('abs_wpi') }}
    union all
    {{ raw_snapshot_counts('abs_cpi_capital_cities_quarterly_2025q3') }}

)

select
    latest.raw_table,
    latest._source_file   as latest_file,
    latest.row_count      as latest_rows,
    previous._source_file as previous_file,
    previous.row_count    as previous_rows
from counts as latest
inner join counts as previous
    on previous.raw_table = latest.raw_table
   and previous.snapshot_rank = 2
where latest.snapshot_rank = 1
  and latest.row_count < previous.row_count
