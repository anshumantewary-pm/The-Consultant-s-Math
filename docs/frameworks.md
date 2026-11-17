# The profitability framework and MECE thinking

This is the reasoning that the code in `casemath.frameworks` implements. Read it before the cases.

## 1. MECE

**M**utually **E**xclusive, **C**ollectively **E**xhaustive. When you split a problem into branches:

- **Mutually exclusive**: no item belongs to two branches. Nothing is counted twice.
- **Collectively exhaustive**: every item belongs to some branch. Nothing is left out.

| Split of "Revenue" | ME? | CE? | Why |
|---|---|---|---|
| Retail + Online + B2B (all channels) | ✅ | ✅ | Each sale goes through exactly one channel |
| Retail + Online | ✅ | ❌ | B2B sales are missing |
| Retail + Online + Discounted sales | ❌ | ✅ | A discounted online sale is in two branches |
| Price × Volume | ✅ | ✅ | An identity: true by definition |

### The numeric test

For a tree with numbers there is a mechanical check: **the branches must add back to the total.**

- Branches add to **less** than the total → a bucket is missing (not CE).
- Branches add to **more** than the total → something is counted twice (not ME).

```
Revenue = 100              Revenue = 100
├── Retail  = 60           ├── Retail  = 60
└── Online  = 30           ├── Online  = 30
    → 10 unexplained       └── Discount = 20
      (missing B2B)            → 10 double-counted
```

`check_mece()` runs this test on every branch that has a stated total, and also flags two structural faults: a "split" into one branch (a rename, not a split) and two siblings with the same label.

What no code can check: whether the split is *useful*. "Customers whose names start with A–M vs N–Z" is MECE and useless. Pick splits that match how the business actually makes decisions (product, customer segment, channel, region) and that separate things that behave differently.

### Three ways to build a MECE split

1. **Use an identity.** Profit = Revenue − Costs; Revenue = Price × Volume. Always MECE.
2. **Use a complete list.** Every channel, every region. Ask "is there anything else?"
3. **Use opposites.** Internal vs external; new vs existing customers; fixed vs variable costs.

## 2. The profitability framework

```
Profit [-]
├── Revenue [x]
│   ├── Price                      Have we or competitors changed prices? Mix shift?
│   └── Volume [x]                 Are we selling more or fewer units? Why?
│       ├── Market size            Is the whole market growing or shrinking?
│       └── Market share           Are we winning or losing against competitors?
└── Costs [+]
    ├── Fixed costs                Rent, salaries, overhead: any step changes?
    └── Variable costs [x]
        ├── Variable cost per unit Inputs, labour, freight per unit: what moved?
        └── Volume
```

(Print it any time with `casemath tree --hints`.)

### How to run a profitability case

1. **Clarify the goal.** "Profit fell 38%; the CEO wants to know why and what to do." Confirm the time frame and whether the decline is in absolute profit or margin.
2. **Lay out the tree** above, out loud, before asking for data.
3. **Revenue or costs?** Ask for both years. Find which side moved. In most cases one side explains most of the change.
4. **Segment.** Split by product line, region or channel. A total that looks flat often hides one segment collapsing while another grows.
5. **Bridge it.** Split the profit change into price, volume, unit cost and fixed cost effects (`profit_bridge`). The four effects add exactly to the total change, so this is MECE by construction:

   | Effect | Formula | Reads as |
   |---|---|---|
   | Volume | (p₀ − v₀) × (q₁ − q₀) | Last year's unit margin on the extra units |
   | Price | (p₁ − p₀) × q₁ | Price change on this year's units |
   | Unit cost | −(v₁ − v₀) × q₁ | Unit-cost change on this year's units |
   | Fixed cost | −(F₁ − F₀) | Change in fixed costs |

6. **Ask why** for the biggest effect. A unit-cost jump is a symptom; the cause is a supplier, a commodity price, a recipe change.
7. **Recommend.** Lead with the answer, give two or three reasons with numbers, then next steps and risks.

### Break-even: the second tool

Break-even turns "is this worth it?" into one number you can sanity-check.

```
Break-even units   = Fixed costs / (Price − Variable cost per unit)
Break-even revenue = Fixed costs / Contribution margin %
Units for target   = (Fixed costs + Target profit) / Unit contribution
Margin of safety   = (Expected units − Break-even units) / Expected units
Payback (years)    = Up-front investment / Annual cash flow
```

Two uses that come up constantly:

- **Was a price cut worth it?** The new volume must reach *old contribution ÷ new unit margin*. Case 1 uses this.
- **Can we get enough share?** Divide break-even volume by market size. If the share needed is larger than the number-two player's, the plan is probably not credible. Case 2 uses this.

## 3. Market share: what the numbers tell you

| Measure | Formula | Use |
|---|---|---|
| Market share | Company sales / Market sales | Position today |
| Relative share | Company sales / Largest rival's sales | Above 1 means you lead (BCG matrix) |
| Required share | Target sales / Market sales | Credibility test for a plan |
| HHI | Σ (share in %)² | Concentration: below 1,000 fragmented, 1,000–1,800 moderate, above 1,800 high |
| Projected share | Share × ((1 + g_company) / (1 + g_market))ⁿ | You gain share only by outgrowing the market |

## 4. Pricing: will a price change pay for itself?

A price rise gains margin on every unit you keep and loses the margin on every unit that leaves. The break-even question is how many you can lose.

```
Arc elasticity          = (ΔQ / avg Q) / (ΔP / avg P)          midpoints, so direction does not matter
Break-even volume change = −ΔP% / (CM% + ΔP%)                    e.g. −15% / (75% + 15%) = −16.7%
Expected volume change   = elasticity × ΔP%                      linear; fine for moderate moves
Profit-maximising price  = VC × e / (1 + e)                      constant elasticity, needs e < −1
```

- **High-margin businesses can afford to lose a lot of volume** on a rise, and must gain a lot on a cut. At a 30% margin a 10% cut needs 50% more volume.
- **Always split elasticity by segment.** An average of an elastic and an inelastic group can make a rise look neutral when the right answer is to raise the price for one group only. Case 3 uses this.
- **Do not extrapolate far beyond the tested price.** Roll out in stages and watch churn.

## 5. M&A synergies: is the premium justified?

```
Premium              = Offer value − Standalone value
Synergy value        = Run-rate profit synergies × multiple − one-off integration costs
Walk-away price      = Standalone value + (risked) synergy value
```

- **Count revenue synergies at their profit margin**, and haircut them: cost synergies are in management's control, cross-selling is not.
- **Phase synergies in** (30% / 70% / 100% is typical) and check when cumulative synergies cover integration costs.
- **If cost synergies alone cover the premium, the deal is robust.** If not, close the gap with price or an earn-out. Case 4 uses this.

## 6. Presenting the answer

Use the pyramid: answer first, then support.

> **Fix Juice first.** Juice unit costs rose 30% and explain 73% of the profit decline. The Energy Drinks price cut explains most of the rest: it cost $2.3M and the extra volume won back only $1.2M. Bottled Tea is healthy. Next step: price Juice to about $2.95 or renegotiate fruit contracts.

Every number in that paragraph comes out of `casemath case solve 1`.
