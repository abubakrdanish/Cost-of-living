# Findings

Every figure here comes from a named query in [`findings_queries.sql`](findings_queries.sql), run read-only against the marts:

```bash
python -m orchestration.findings          # all queries
python -m orchestration.findings F2 F4    # just some
```

The results below were run on **2026-10-16** against data up to **2026-Q2** (the quarter ending June 2026). They will change as the ABS publishes and revises data; the dashboard's Overview page recalculates the same figures live.

"Australia" means CPI and rents for the weighted average of the eight capital cities, and the WPI for all of Australia. "Real wage growth" means WPI annual % minus CPI annual %, in percentage points.

## What the data shows

| # | Finding | Figures | Query |
|---|---|---|---|
| 1 | Over the whole period, wages rose a little faster than prices. | 1997-Q3 to 2026-Q2, Australia: prices **+121.1%**, rents **+139.4%**, wages **+141.7%**. WPI ÷ CPI is **9.3%** higher than in 1997-Q3. | `F1_cumulative_australia` |
| 2 | Most of that gain was lost after 2021. | WPI ÷ CPI peaked in **2020-Q2** (117.1, 1997-Q3 = 100) and fell **7.4%** to a low in **2023-Q2** (108.5). It was 109.3 in 2026-Q2. The 2020 peak is partly a temporary dip in prices during the COVID-19 period. | `F2_real_wage_peak_and_trough` |
| 3 | The longest recent stretch of falling real wages was 10 quarters. | Negative real wage growth for **10** quarters in a row, **2021-Q2 to 2023-Q3**. The lowest point was **−4.47** points in **2022-Q4**. Over the full series it was positive in **83 of 112** quarters (**74%**). | `F4_negative_runs_australia`, `F3_real_wage_growth_australia` |
| 4 | Prices are again rising faster than wages, everywhere. | Negative real wage growth since **2025-Q4** (3 quarters). In 2026-Q2 it was negative in **all 9** regions, from **−0.47** (Victoria) to **−1.77** points (Tasmania). | `F4_negative_runs_australia`, `F5_latest_real_wage_growth_by_region` |
| 5 | Rents grew very unevenly across capitals. | Since 1997-Q3: Brisbane **+155.5%** (most), Darwin **+90.5%** (least). Rents outpaced the state's wages only in **Brisbane** (rents 4.5% ahead of wages) and **Sydney** (3.5% ahead). Darwin rents are **18.7%** behind NT wages. | `F6_rents_vs_wages_by_region` |
| 6 | Latest annual rent growth is fastest in Perth and Darwin and slowest in Canberra. | 2026-Q2: Perth **5.38%**, Darwin **5.28%** … Canberra **1.22%**. Every one of these compares across the splice, so treat them as ±0.4 points. | `F7_latest_rent_growth_by_region` |
| 7 | The rents splice is small but not zero. | The ratio of the two rents series drifts by **0.14%** (Sydney) to **0.41%** (Hobart, 2023-Q3) in the overlap. | `F8_splice_gap` |

## What the data does not show

- **Why.** Nothing here identifies causes, such as interest rates, migration, the mining cycle or policy. Statements are about how the indexes moved, not why.
- **Affordability or levels.** These are indexes (change over time), not dollar rents or dollar wages. A city with slow rent growth can still be expensive.
- **Market rents.** CPI rents cover all renting households, including long-standing leases, and are net of Commonwealth Rent Assistance. This data says nothing about advertised rents for new leases.
- **Regional Australia.** CPI and rents are capital cities only, while wages are whole states, so each region compares city prices with state wages.
- **Individual pay.** The WPI prices the same jobs over time. It excludes promotions, job changes, hours and bonuses, so it is not what any one person earned.
