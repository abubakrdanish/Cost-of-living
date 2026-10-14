-- What changed between the two newest downloads of each ABS API table:
-- observations added (new periods), removed, or whose value changed
-- (revisions). Empty when a table has only one snapshot.
-- Used by the quality report and the revision tests. The frozen archive
-- table is not compared.

select * from (
    {{ raw_snapshot_diff('abs_cpi_all_groups',
        ['measure', '"index"', 'tsest', 'region', 'freq', 'time_period']) }}
)

union all

select * from (
    {{ raw_snapshot_diff('abs_cpi_rents',
        ['measure', '"index"', 'tsest', 'region', 'freq', 'time_period']) }}
)

union all

select * from (
    {{ raw_snapshot_diff('abs_wpi',
        ['measure', '"index"', 'sector', 'industry', 'tsest', 'region', 'freq', 'time_period']) }}
)
