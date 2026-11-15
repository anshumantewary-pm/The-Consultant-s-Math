# Case 2: VoltWay, should it enter a city's EV fast-charging market?

**Type:** Market entry · **Run it:** `casemath case solve 2` · **Code:** [`case_02_market_entry.py`](../../src/casemath/cases/case_02_market_entry.py)

## Prompt

VoltWay runs EV fast-charging stations in two cities and is considering a third. Entry means 20 stations: **$2.0M up front** and **$800K a year** to run. The board's rule: **operating break-even by year 3** and **payback within 5 years**. Should VoltWay enter? If not, what would make it work?

## Exhibits

| Item | Value |
|---|---|
| EVs in the city | 50,000 |
| Share of EV owners using public fast charging | 30% |
| Fast-charge sessions per user | 6 a month (72 a year) |
| Price per session | $8.00 |
| Variable cost per session (power, fees, wear) | $5.00 |
| VoltWay's expected year-1 share | 8% |
| VoltWay session growth | 60% a year |
| Market growth | 25% a year |
| Incumbents (sessions a year) | ChargeCo 486,000 · GridGo 324,000 · 10 independents at 27,000 each |
| Offer from a ride-hailing fleet | 150,000 sessions a year at $7.00, fixed contract |

## Structure

```
Should VoltWay enter?
├── Market attractiveness:  size today, growth
├── Competition:            concentration, likely response
├── Economics:              break-even, payback
└── Capabilities and risk:  sites and grid access, ways to de-risk
```

## Solution

**1. Size the market (top-down).**

50,000 EVs × 30% × 72 sessions = **1,080,000 sessions a year**, × $8 = **$8.64M**, growing 25% a year.

**2. Competition.** ChargeCo 45%, GridGo 30%, independents 2.5% each.
HHI = 45² + 30² + 10 × 2.5² = **2,988: highly concentrated**. Two players hold three quarters of the market.

**3. Break-even.**
Contribution per session = $8 − $5 = $3.
Break-even = $800K ÷ $3 = **266,667 sessions a year = 24.7% of today's market**. VoltWay would need nearly GridGo's size just to cover its running costs. That is a red flag.

**4. Project VoltWay's own volume.** 8% share = 86,400 sessions in year 1, growing 60% a year while the market grows 25%:

| Year | Sessions | Share | Operating profit (retail only) |
|---|---|---|---|
| 1 | 86,400 | 8.0% | −$540,800 |
| 2 | 138,240 | 10.2% | −$385,280 |
| 3 | 221,184 | 13.1% | −$136,448 |
| 4 | 353,894 | 16.8% | +$261,683 |

Retail only: break-even in **year 4**, payback = $2.0M ÷ $261,683 = **7.6 years**. **Fails both tests.**

**5. Add the fleet contract.** 150,000 sessions × ($7 − $5) = +$300,000 a year:

| Year | Operating profit (with fleet) |
|---|---|
| 1 | −$240,800 |
| 2 | −$85,280 |
| 3 | +$163,552 |
| 4 | +$561,683 |

Break-even in **year 3**, payback = $2.0M ÷ $561,683 = **3.6 years**. **Passes both tests.**

**6. How big must the contract be?**
- To break even in year 3: $136,448 ÷ $2 = 68,224 sessions.
- To pay back in 5 years, year-4 profit must reach $400,000: ($400,000 − $261,683) ÷ $2 = 69,159 sessions.

**Minimum anchor contract: 69,159 sessions a year.** The 150,000 offered clears it with a wide margin.

## Recommendation

> **Do not enter on retail demand alone. Enter only with the fleet contract signed.**
> 1. Retail-only break-even needs 24.7% of a highly concentrated market; VoltWay reaches 16.8% by year 4. It breaks even a year late and pays back in 7.6 years.
> 2. The fleet contract moves break-even to year 3 and payback to 3.6 years. Anything above about 69,000 sessions a year at $7 passes the board's rule.
> 3. Sign the contract before committing the $2.0M.
>
> **Risks:** incumbents cut price (each $1 off the retail price adds ~133,000 sessions to break-even); the fleet operator churns (ask for a multi-year term with minimum volumes); grid connection delays push out year 1.

## What this case practises

- Top-down market sizing
- Concentration (HHI) as a reality check on share targets
- Break-even volume → required market share
- Turning a "no" into a "yes, if" with the minimum condition quantified
