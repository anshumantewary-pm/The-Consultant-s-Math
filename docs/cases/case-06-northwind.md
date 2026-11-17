# Case 6: Northwind Logistics, automate the main warehouse?

**Type:** Investment under uncertainty · **Run it:** `casemath case solve 6` · **Code:** [`case_06_automation_investment.py`](../../src/casemath/cases/case_06_automation_investment.py)

## Prompt

Northwind Logistics has a **$12M quote** to automate its main warehouse with robotic picking. Operations expects **$3.2M a year** of labour and error savings, growing with volume, less **$0.6M a year** of maintenance. The kit lasts **7 years** and can be resold for **$1M**. Northwind's cost of capital is **9%**. The board's rule for large projects: **positive expected NPV and no more than a 10% chance of destroying value**. Should Northwind sign?

## Exhibits

| Item | Value |
|---|---|
| Capex (year 0) | $12.0M |
| Year-1 savings | $3.2M, growing 4% a year with volume |
| Maintenance | $0.6M a year |
| Life / salvage | 7 years / $1.0M |
| Cost of capital | 9% |

| Scenario (operations) | Savings | Volume growth | Weight |
|---|---|---|---|
| Downside | $2.4M | 0% | 25% |
| Base | $3.2M | 4% | 50% |
| Upside | $3.8M | 6% | 25% |

| Range for simulation | Distribution |
|---|---|
| Year-1 savings | Triangular: low $2.2M, most likely $3.2M, high $3.6M |
| Volume growth | Uniform 0% to 6% |
| Maintenance | Triangular: $0.5M, $0.6M, $0.9M |

## Structure

```
Should Northwind automate?
├── Value in the base case:  cash flows, NPV and IRR
├── Risk:                    scenarios, simulation
└── How to make it work:     break-even savings, price to pay
```

## Solution

**1. Base case.** Year *t* cash flow = $3.2M × 1.04^(t−1) − $0.6M, plus $1M salvage in year 7.

| Year | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Cash flow ($M) | −12.00 | 2.60 | 2.73 | 2.86 | 3.00 | 3.14 | 3.29 | 4.45 |

NPV at 9% = **$3.46M**, IRR = **16.5%**, payback **4.3 years**, discounted payback **5.5 years**. On a point estimate this is an easy yes.

**2. Scenarios.** Downside **−$2.39M**, base **+$3.46M**, upside **+$8.01M**. Probability-weighted NPV = **$3.13M**. Still positive, but the downside is a real loss.

**3. How far can savings fall?** Goal seek: NPV hits zero at year-1 savings of **$2.58M**, 19% below plan. Operations' own range goes down to $2.2M.

**4. Monte Carlo** (5,000 runs, seed 7): mean NPV **$1.56M**, 90% range **−$1.5M to +$4.4M**, and a **21% chance that NPV is below zero**. The mean is less than half the base case because the savings and maintenance ranges are skewed toward the bad side. That is the number the deterministic answer hides.

**5. Make it pass.** 21% fails the board's 10% rule. Goal seek on the *simulated loss probability* (seeded, so it is a steady function of capex): the rule is met at a capex of **$11.12M**, **7.3% off the quote**.

## Recommendation

> **Do not sign at $12M.** The project creates value on average but carries a 21% chance of losing money, which breaks the board's rule. Go back to the vendor for **at least 7.3% off** (capex of $11.1M or less), or an equivalent mix of price cut and savings guarantee, and sign if they meet it.

## What interviewers look for

- Not stopping at "NPV is positive". The board set a risk test; answer it.
- Explaining *why* the simulated mean is below the base case (skewed ranges), not just reporting it.
- Ending with a number the client can negotiate with, not "the project is risky".
