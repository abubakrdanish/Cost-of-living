---
title: Prices, rents and wages over time
sidebar_position: 2
---

```sql regions
select region_key, region_label, region_sort_order
from marts.regions
order by region_sort_order
```

<Dropdown data={regions} name=region value=region_key label=region_label defaultValue="AUS" title="Region" />

```sql indexes
-- Long format: one row per quarter and measure, for the selected region.
select quarter_end_date, quarter_label, 'Prices (CPI)' as measure, cpi_index as index_value
from marts.cost_of_living_quarterly where region_key = '${inputs.region.value}'
union all
select quarter_end_date, quarter_label, 'Rents', rents_index
from marts.cost_of_living_quarterly where region_key = '${inputs.region.value}'
union all
select quarter_end_date, quarter_label, 'Wages (WPI)', wpi_index
from marts.cost_of_living_quarterly where region_key = '${inputs.region.value}'
order by quarter_end_date
```

```sql selected
select region_name, capital_city, state_name, comparison_note
from marts.regions where region_key = '${inputs.region.value}'
```

<LineChart
  data={indexes}
  x=quarter_end_date
  y=index_value
  series=measure
  seriesOrder={['Prices (CPI)', 'Rents', 'Wages (WPI)']}
  seriesColors={{'Prices (CPI)': 'cpi', 'Rents': 'rents', 'Wages (WPI)': 'wages'}}
  title="Prices, rents and wages: index, 1997-Q3 = 100"
  subtitle="All three series rebased so that 1997-Q3 = 100. 200 means the measure has doubled since 1997-Q3."
  xAxisTitle="Quarter ending"
  yAxisTitle="Index (1997-Q3 = 100)"
  xFmt="mmm yyyy"
  yFmt="0"
  handleMissing=gap
  chartAreaHeight=320
  echartsOptions={{series: [
    {lineStyle: {type: 'solid', width: 2}},
    {lineStyle: {type: 'dashed', width: 2}},
    {lineStyle: {type: 'dotted', width: 2.5}}
  ]}}
>
  <ReferenceLine y=100 label="1997-Q3 = 100" lineColor=reference color=reference lineType=solid hideValue=true />
</LineChart>

*Line styles: prices solid, rents dashed, wages dotted. {selected[0]?.comparison_note} Source: ABS 6401.0 (CPI, capital city) and 6345.0 (WPI, state). Rents are spliced at 2025-Q4 (see [Rents](/rents)). Based on ABS data, CC BY 4.0.*

## Cumulative change since 1997-Q3, by region

```sql cumulative
select region_label, region_sort_order,
       'Prices (CPI)' as measure, cpi_index - 100 as change_pct
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
union all
select region_label, region_sort_order, 'Rents', rents_index - 100
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
union all
select region_label, region_sort_order, 'Wages (WPI)', wpi_index - 100
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
order by region_sort_order
```

```sql latest
select max(quarter_label) as latest_quarter from marts.cost_of_living_quarterly
```

<BarChart
  data={cumulative}
  x=region_label
  y=change_pct
  series=measure
  type=grouped
  swapXY=true
  sort=false
  seriesOrder={['Prices (CPI)', 'Rents', 'Wages (WPI)']}
  seriesColors={{'Prices (CPI)': 'cpi', 'Rents': 'rents', 'Wages (WPI)': 'wages'}}
  title="Cumulative % change, 1997-Q3 to latest quarter"
  subtitle="Index change since 1997-Q3 (1997-Q3 = 100), by region"
  yAxisTitle="% change since 1997-Q3"
  xAxisTitle="Region (capital city)"
  yFmt='0"%"'
  chartAreaHeight=420
/>

*Latest quarter: {latest[0]?.latest_quarter}. Bars start at 0%, so lengths are comparable. CPI and rents: capital city; WPI: whole state. Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*

<Details title="Data table: cumulative % change by region">

```sql cumulative_table
select region_label, cpi_index - 100 as cpi_pct, rents_index - 100 as rents_pct, wpi_index - 100 as wpi_pct
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
order by region_sort_order
```

<DataTable data={cumulative_table} rows=all>
  <Column id=region_label title="Region (capital city)" />
  <Column id=cpi_pct title="Prices (CPI) %" fmt='0.0' />
  <Column id=rents_pct title="Rents %" fmt='0.0' />
  <Column id=wpi_pct title="Wages (WPI) %" fmt='0.0' />
</DataTable>

</Details>

<Details title="Data table: index values for the selected region">

<DataTable data={indexes} rows=12>
  <Column id=quarter_label title="Quarter" />
  <Column id=measure title="Measure" />
  <Column id=index_value title="Index (1997-Q3 = 100)" fmt='0.0' />
</DataTable>

</Details>
