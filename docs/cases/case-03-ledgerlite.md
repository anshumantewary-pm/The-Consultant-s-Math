# Case 3: LedgerLite, should it raise its subscription price 15%?

**Type:** Pricing · **Run it:** `casemath case solve 3` · **Code:** [`case_03_pricing.py`](../../src/casemath/cases/case_03_pricing.py)

## Prompt

LedgerLite sells bookkeeping software for **$40 per subscriber per month** to **20,000 subscribers**. The CFO proposes a 15% rise to **$46** to lift profit. Last quarter a regional test raised the price to $44. Should LedgerLite raise the price?

## Exhibits

| Item | Value |
|---|---|
| Price | $40 a month |
| Variable cost (hosting, support, payment fees) | $10 a subscriber a month |
| Fixed costs | $250,000 a month |

| Segment | Subscribers | Test region before ($40) | Test region after ($44) |
|---|---|---|---|
| Small businesses | 12,000 | 3,000 | 2,550 |
| Accounting firms | 8,000 | 2,000 | 1,960 |

## Structure

```
Does the price rise increase profit?   (fixed costs do not move, so compare contribution)
├── Contribution after the rise = new unit margin × subscribers kept
│                                                   └── elasticity: does it differ by group?
└── Contribution today          = $30 × 20,000
```

## Solution

**1. Today.** Contribution $30 a sub (75% margin) × 20,000 = $600K; profit = $600K − $250K = **$350K a month**.

**2. How much volume can a +15% rise lose?** Break-even volume change = −ΔP ÷ (CM% + ΔP) = −15% ÷ (75% + 15%) = **−16.7%**. If fewer than 1 in 6 subscribers leave, the rise pays.

**3. Elasticity from the test (midpoint method).** Price change = $4 ÷ $42 = 9.5%.

| Segment | Volume change (midpoint) | Elasticity |
|---|---|---|
| Small businesses | −450 ÷ 2,775 = −16.2% | **−1.70** (elastic) |
| Accounting firms | −40 ÷ 1,980 = −2.0% | **−0.21** (inelastic) |

The blended number hides two very different customers.

**4. Uniform $46.**

| Segment | Expected volume | vs −16.7% limit | Contribution change |
|---|---|---|---|
| Small businesses | −25.5% | fails | −$38.3K |
| Accounting firms | −3.2% | passes | +$38.8K |
| **Total** | | | **+$0.5K: a wash** |

**5. Price by segment.**
- Accounting firms at **$50** (+25%): expected loss 5.3% vs a 25.0% limit; contribution **+$63.0K a month**.
- Small businesses at $36 (−10%): +$5.1K. Too small to justify the revenue risk; hold at $40.

## Recommendation

> **Do not raise the price for everyone. Launch a $50 Pro tier for accounting firms and hold small businesses at $40.**
> 1. A uniform $46 drives out a quarter of small-business customers and leaves profit flat.
> 2. Accounting firms barely react to price. At $50 profit rises $63K a month (+18%) to about $413K.
> 3. $50 is beyond the tested $44, so roll out Pro region by region and check churn stays well under the 25% limit.
