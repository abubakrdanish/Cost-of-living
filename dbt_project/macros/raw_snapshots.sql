{#
    Row count of every snapshot (_source_file) in a raw table, numbered from
    newest (snapshot_rank = 1) to oldest. File names carry a sortable date
    stamp, so name order = download order.
#}
{% macro raw_snapshot_counts(table_name) -%}
    select
        '{{ table_name }}'                                     as raw_table,
        _source_file,
        count(*)                                               as row_count,
        row_number() over (order by _source_file desc)         as snapshot_rank
    from {{ source('raw', table_name) }}
    group by _source_file
{%- endmacro %}

{#
    Observation-level comparison of the two newest snapshots of a raw SDMX
    table. `key_columns` identify one observation. Emits one row per
    observation that is new, removed or whose value changed.
#}
{% macro raw_snapshot_diff(table_name, key_columns) -%}
    {%- set key = key_columns | join(" || '|' || ") -%}
    with ranked as (
        {{ raw_snapshot_counts(table_name) }}
    ),
    latest as (
        select {{ key }} as observation_key, obs_value, obs_status
        from {{ source('raw', table_name) }}
        where _source_file = (select _source_file from ranked where snapshot_rank = 1)
    ),
    previous as (
        select {{ key }} as observation_key, obs_value
        from {{ source('raw', table_name) }}
        where _source_file = (select _source_file from ranked where snapshot_rank = 2)
    )
    select
        '{{ table_name }}'                                          as raw_table,
        (select _source_file from ranked where snapshot_rank = 1)   as latest_file,
        (select _source_file from ranked where snapshot_rank = 2)   as previous_file,
        coalesce(latest.observation_key, previous.observation_key)  as observation_key,
        previous.obs_value                                          as previous_value,
        latest.obs_value                                            as latest_value,
        latest.obs_status                                           as latest_obs_status,
        case
            when previous.observation_key is null then 'added'
            when latest.observation_key is null then 'removed'
            else 'changed'
        end                                                         as change_type
    from latest
    full outer join previous using (observation_key)
    -- Only compare when a previous snapshot exists; otherwise nothing is "added".
    where exists (select 1 from ranked where snapshot_rank = 2)
      and (previous.observation_key is null
           or latest.observation_key is null
           or previous.obs_value is distinct from latest.obs_value)
{%- endmacro %}
