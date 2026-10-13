{#
    Helpers for ABS SDMX-CSV columns loaded with labels=both,
    e.g. region = '2: Melbourne', obs_status = 'r: revised'.
#}

{# '2: Melbourne' -> '2' #}
{% macro abs_code(column) -%}
    nullif(regexp_extract({{ column }}, '^([^:]*):', 1), '')
{%- endmacro %}

{# '2: Melbourne' -> 'Melbourne' #}
{% macro abs_label(column) -%}
    nullif(regexp_extract({{ column }}, '^[^:]*: (.*)$', 1), '')
{%- endmacro %}

{#
    SDMX TIME_PERIOD -> first day of the period.
    '2026-Q2' -> 2026-04-01 (quarterly), '2026-08' -> 2026-08-01 (monthly).
    Anything else returns null (and fails the not_null tests).
#}
{% macro abs_period_start(column) -%}
    case
        when regexp_full_match({{ column }}, '\d{4}-Q[1-4]')
            then make_date(cast(left({{ column }}, 4) as integer),
                           (cast(right({{ column }}, 1) as integer) - 1) * 3 + 1, 1)
        when regexp_full_match({{ column }}, '\d{4}-\d{2}')
            then make_date(cast(left({{ column }}, 4) as integer),
                           cast(right({{ column }}, 2) as integer), 1)
    end
{%- endmacro %}

{#
    Keep only the most recent snapshot of a raw table. Raw files are named
    <dataset>_YYYYMMDD[THHMMSS].<ext>, so the newest file sorts last.
#}
{% macro latest_snapshot_filter(relation) -%}
    _source_file = (select max(_source_file) from {{ relation }})
{%- endmacro %}
