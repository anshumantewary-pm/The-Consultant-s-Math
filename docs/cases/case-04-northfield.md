# Case 4: Northfield Foods, is a 30% premium for Crestline Snacks justified?

**Type:** M&A · **Run it:** `casemath case solve 4` · **Code:** [`case_04_ma_synergy.py`](../../src/casemath/cases/case_04_ma_synergy.py)

## Prompt

Northfield Foods has agreed terms to buy Crestline Snacks for **$520M**. Crestline's unaffected market value is **$400M**. Comparable deals trade at **8x EBITDA**. Is the price justified, and what is the most Northfield should pay?

## Exhibits

| Synergy | Type | Run-rate a year |
|---|---|---|
| Procurement (joint buying) | Cost | $8M |
| Plant consolidation | Cost | $6M |
| Overlapping SG&A | Cost | $4M |
| Cross-sell Crestline into Northfield's grocery accounts | Revenue | $30M revenue at a 25% margin |

| | Year 1 | Year 2 | Year 3 | Year 4 |
|---|---|---|---|---|
| Phase-in (share of run-rate) | 30% | 70% | 100% | 100% |
| One-off integration costs | $20M | $10M | | |

## Structure

```
Is the deal worth it?
├── Value of synergies = run-rate synergies × multiple − integration costs
│                        ├── Cost synergies:    how certain?
│                        └── Revenue synergies: profit, not revenue; how likely?
└── Premium over standalone value = $520M − $400M
```

## Solution

**1. Premium.** $520M − $400M = **$120M (30%)**. Synergies must be worth more than this, or Northfield's shareholders lose value.

**2. Run-rate synergies.** Cost: 8 + 6 + 4 = **$18M**. Revenue: $30M × 25% = **$7.5M of profit** (count profit, never revenue). Total **$25.5M**.

**3. Value at 8x, net of $30M integration costs.**

| Scenario | Run-rate | Value | vs $120M premium |
|---|---|---|---|
| Management case | $25.5M | 25.5 × 8 − 30 = **$174M** | +$54M |
| Revenue synergies at 50% | $21.75M | **$144M** | +$24M |
| Cost synergies only | $18M | **$114M** | **−$6M** |

Revenue synergies are 29% of the total and the least certain. Without them the premium is not covered.

**4. Integration payback (risked case).** Cumulative net synergies: −$13.5M (year 1), −$8.3M (year 2), +$13.5M (year 3). **Paid back in year 3.**

**5. Prices.** Walk-away price = $400M + $144M = **$544M**. Price fully backed by cost synergies = $400M + $114M = **$514M**.

## Recommendation

> **Proceed, but the price is near the edge.**
> 1. Walk away above $544M.
> 2. Push the fixed price toward $514M, the value cost synergies alone support, and pay the rest as an earn-out tied to cross-selling revenue. That moves the riskiest synergy's risk to the seller.
> 3. Name an owner for each synergy line and track delivery against the 30/70/100% phase-in.
