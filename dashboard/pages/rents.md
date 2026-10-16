---
title: Rents
sidebar_position: 4
---

CPI rents measure what **all renting households** pay, not advertised rents for new leases, and they are measured **net of Commonwealth Rent Assistance** (CRA). That is why the index moves more slowly than headline asking rents, and why CRA increases push it down (Hobart rents fell {hobart_dec_2023[0]?.fall_pct?.toFixed(1)}% in the December quarter 2023, which the ABS attributes to the 15% CRA increase from 20 September 2023).

```sql hobart_dec_2023
select 100 * (1 - cur.rents_index / prev.rents_index) as fall_pct
from marts.cost_of_living_quarterly cur
join marts.cost_of_living_quarterly prev
  on prev.region_key = cur.region_key and prev.quarter_label = '2023-Q3'
where cur.region_key = 'TAS' and cur.quarter_label = '2023-Q4'
```

```sql splice_range
select min(max_abs_deviation_pct) as smallest, max(max_abs_deviation_pct) as largest,
       max(overlap_quarters) as overlap_quarters
from marts.rents_splice_check
```

```sql regions
select region_key, region_label, region_sort_order
from marts.regions
order by region_sort_order
```

<Dropdown data={regions} name=region value=region_key label=region_label defaultValue="AUS" title="Region" />

```sql rents
select quarter_end_date, quarter_label, rents_annual_pct, rents_source_series,
       rents_is_splice_point, rents_annual_pct_crosses_splice
from marts.cost_of_living_quarterly
where region_key = '${inputs.region.value}'
order by quarter_end_date
```

```sql splice
select min(quarter_end_date) filter (where rents_is_splice_point) as splice_quarter_end,
       min(quarter_label) filter (where rents_is_splice_point) as splice_quarter,
       min(quarter_end_date) filter (where rents_annual_pct_crosses_splice) as crosses_from,
       max(quarter_end_date) filter (where rents_annual_pct_crosses_splice) as crosses_to,
       min(quarter_label) filter (where rents_annual_pct_crosses_splice) as crosses_from_label,
       max(quarter_label) filter (where rents_annual_pct_crosses_splice) as crosses_to_label
from marts.cost_of_living_quarterly
where region_key = '${inputs.region.value}'
```

```sql selected_check
select region_name, capital_city, max_abs_deviation_pct, max_deviation_quarter
from marts.rents_splice_check where region_key = '${inputs.region.value}'
```

<LineChart
  data={rents}
  x=quarter_end_date
  y=rents_annual_pct
  lineColor=rents
  title="Rents: annual % change"
  subtitle="CPI Rents, % change on the same quarter a year earlier. Shaded: changes that compare the new and archived series."
  xAxisTitle="Quarter ending"
  yAxisTitle="% change on a year earlier"
  xFmt="mmm yyyy"
  yFmt='0"%"'
  handleMissing=gap
  chartAreaHeight=320
  echartsOptions={{series: [{lineStyle: {type: 'dashed', width: 2}}]}}
>
  <ReferenceLine y=0 lineColor=reference lineType=solid hideValue=true />
  <ReferenceArea xMin={splice[0].crosses_from} xMax={splice[0].crosses_to} areaColor=reference opacity=0.2 />
  <ReferenceLine x={splice[0].splice_quarter_end} label="Splice point" lineColor=reference color=reference lineType=dashed hideValue=true />
</LineChart>

*Rents (dashed line, as on every page). Source: ABS 6401.0. Up to 2025-Q3: final quarterly CPI release (Table 9). From 2025-Q4: quarterly average of the monthly CPI. Based on ABS data, CC BY 4.0.*

### The splice, in plain English

The ABS stopped publishing quarterly CPI by capital city after the September quarter 2025, when the CPI became fully monthly. To keep one quarterly rents series per city:

1. up to **2025-Q3** we use the official archived quarterly series;
2. from **{splice[0]?.splice_quarter}** (the **splice point**, dashed line) we use the average of each quarter's three monthly values;
3. the archive is rescaled to the new index base using the ratio of the two series in 2025-Q3.

The two series don't agree exactly. Over the {splice_range[0]?.overlap_quarters} quarters where both exist, their ratio drifts by up to {selected_check[0]?.max_abs_deviation_pct?.toFixed(2)}% for {selected_check[0]?.region_name} (largest in {selected_check[0]?.max_deviation_quarter}), and between {splice_range[0]?.smallest?.toFixed(2)}% and {splice_range[0]?.largest?.toFixed(2)}% across all regions. So annual changes from {splice[0]?.crosses_from_label} to {splice[0]?.crosses_to_label} (shaded), which compare a new-series quarter with an archived one, carry up to about ±0.4 percentage points of method noise. Full table: [Methodology](/methodology).

## Latest annual rent change, by region

```sql latest_by_region
select region_label, region_sort_order,
       rents_annual_pct, quarter_label
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
order by region_sort_order
```

<BarChart
  data={latest_by_region}
  x=region_label
  y=rents_annual_pct
  swapXY=true
  sort=false
  fillColor=rents
  rightPadding=48
  title="Rents: annual % change in the latest quarter, by region"
  subtitle="Compares the new monthly-based series with the archived series: treat as ±0.4 points"
  yAxisTitle="% change on a year earlier"
  xAxisTitle="Region (capital city)"
  yFmt='0"%"'
  labels=true
  labelFmt='0.0"%"'
  chartAreaHeight=320
/>

*Latest quarter: {latest_by_region[0]?.quarter_label}. Source: ABS 6401.0. Based on ABS data, CC BY 4.0.*

<Details title="Data table: rents annual % change for the selected region">

<DataTable data={rents} rows=12>
  <Column id=quarter_label title="Quarter" />
  <Column id=rents_annual_pct title="Annual % change" fmt='0.00' />
  <Column id=rents_source_series title="Source series" />
  <Column id=rents_annual_pct_crosses_splice title="Crosses splice" />
</DataTable>

</Details>
