---
title: Real wage growth
sidebar_position: 3
---

**Real wage growth** here means the Wage Price Index's annual % change *minus* the CPI's annual % change, in percentage points. Above zero, wages grew faster than prices over the year; below zero, slower. It is a simple approximation: the exact form, (1 + WPI%) ÷ (1 + CPI%) − 1, differs from it by at most {approx_error[0]?.max_gap?.toFixed(2)} points in any region and quarter (largest in {approx_error[0]?.at_quarter}, when inflation was highest).

```sql approx_error
select max(abs(100 * ((1 + wpi_annual_pct / 100) / (1 + cpi_annual_pct / 100) - 1)
               - real_wage_growth_pct_pts)) as max_gap,
       arg_max(quarter_label, abs(100 * ((1 + wpi_annual_pct / 100) / (1 + cpi_annual_pct / 100) - 1)
               - real_wage_growth_pct_pts)) as at_quarter
from marts.cost_of_living_quarterly
where real_wage_growth_pct_pts is not null
```

```sql first_value
select min(quarter_label) filter (where real_wage_growth_pct_pts is not null) as first_quarter,
       min(quarter_label) as wpi_first_quarter
from marts.cost_of_living_quarterly
```

```sql regions
select region_key, region_label, region_sort_order
from marts.regions
order by region_sort_order
```

<Dropdown data={regions} name=region value=region_key label=region_label defaultValue="AUS" title="Region" />

```sql real
select quarter_end_date, quarter_label, real_wage_growth_pct_pts, missing_reason
from marts.cost_of_living_quarterly
where region_key = '${inputs.region.value}'
order by quarter_end_date
```

```sql components
select quarter_end_date, quarter_label, 'Wages (WPI)' as measure, wpi_annual_pct as annual_pct
from marts.cost_of_living_quarterly where region_key = '${inputs.region.value}'
union all
select quarter_end_date, quarter_label, 'Prices (CPI)', cpi_annual_pct
from marts.cost_of_living_quarterly where region_key = '${inputs.region.value}'
order by quarter_end_date
```

```sql selected
select comparison_note from marts.regions where region_key = '${inputs.region.value}'
```

<LineChart
  data={real}
  x=quarter_end_date
  y=real_wage_growth_pct_pts
  lineColor=wages
  title="Real wage growth: WPI annual % minus CPI annual %"
  subtitle="Percentage points. Above 0 = wages grew faster than prices over the year."
  xAxisTitle="Quarter ending"
  yAxisTitle="Percentage points"
  xFmt="mmm yyyy"
  yFmt='+0.0;-0.0;0'
  handleMissing=gap
  chartAreaHeight=300
>
  <ReferenceLine y=0 label="Wages and prices grew equally" labelPosition=aboveStart lineColor=reference color=reference lineType=solid hideValue=true />
</LineChart>

*The line starts in {first_value[0]?.first_quarter}: the WPI begins in {first_value[0]?.wpi_first_quarter}, so its first annual change needs a year of data (shown as a gap, not zero). {selected[0]?.comparison_note} Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*

<LineChart
  data={components}
  x=quarter_end_date
  y=annual_pct
  series=measure
  seriesOrder={['Prices (CPI)', 'Wages (WPI)']}
  seriesColors={{'Prices (CPI)': 'cpi', 'Wages (WPI)': 'wages'}}
  title="The two parts: annual % change in prices and in wages"
  subtitle="Both series on one % axis; the gap between them is the real wage growth above."
  xAxisTitle="Quarter ending"
  yAxisTitle="% change on a year earlier"
  xFmt="mmm yyyy"
  yFmt='0"%"'
  handleMissing=gap
  chartAreaHeight=300
  echartsOptions={{series: [
    {lineStyle: {type: 'solid', width: 2}},
    {lineStyle: {type: 'dotted', width: 2.5}}
  ]}}
>
  <ReferenceLine y=0 lineColor=reference lineType=solid hideValue=true />
</LineChart>

*Line styles: prices solid, wages dotted. Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*

## Latest quarter, by region

```sql latest_by_region
select region_label, region_sort_order,
       real_wage_growth_pct_pts, quarter_label
from marts.cost_of_living_quarterly
where quarter_start_date = (select max(quarter_start_date) from marts.cost_of_living_quarterly)
order by region_sort_order
```

<BarChart
  data={latest_by_region}
  x=region_label
  y=real_wage_growth_pct_pts
  swapXY=true
  sort=false
  fillColor=wages
  rightPadding=48
  title="Real wage growth in the latest quarter, by region"
  subtitle="WPI annual % minus CPI annual %, percentage points"
  yAxisTitle="Percentage points"
  xAxisTitle="Region (capital city)"
  yFmt='+0.0;-0.0;0'
  labels=true
  labelFmt='+0.00;-0.00'
  chartAreaHeight=320
/>

*Latest quarter: {latest_by_region[0]?.quarter_label}. Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*

## How often have wages kept up?

```sql share_positive
select region_label,
       count(real_wage_growth_pct_pts) as quarters_with_value,
       count(*) filter (where real_wage_growth_pct_pts > 0) as quarters_positive,
       100.0 * count(*) filter (where real_wage_growth_pct_pts > 0) / count(real_wage_growth_pct_pts) as share_positive_pct,
       min(real_wage_growth_pct_pts) as lowest_pts,
       arg_min(quarter_label, real_wage_growth_pct_pts) as lowest_quarter
from marts.cost_of_living_quarterly
group by region_label, region_sort_order
order by region_sort_order
```

<DataTable data={share_positive} rows=all>
  <Column id=region_label title="Region (capital city)" />
  <Column id=quarters_positive title="Quarters wages beat prices" wrapTitle=true />
  <Column id=quarters_with_value title="of quarters" />
  <Column id=share_positive_pct title="Share %" fmt='0' />
  <Column id=lowest_pts title="Lowest, pts" fmt='+0.00;-0.00' />
  <Column id=lowest_quarter title="Lowest in" />
</DataTable>

*{first_value[0]?.first_quarter} to the latest quarter. Source: ABS 6401.0, 6345.0. Based on ABS data, CC BY 4.0.*
