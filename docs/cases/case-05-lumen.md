# Case 5: Lumen Analytics, cut the price to grow?

**Type:** Pricing · **Run it:** `casemath case solve 5` · **Code:** [`case_05_saas_pricing.py`](../../src/casemath/cases/case_05_saas_pricing.py)

## Prompt

Lumen Analytics sells a dashboard product at **$120 per customer per month** and has **5,000 customers**. Growth has slowed. The CMO wants to cut the price to **$99** to win more sign-ups, and points to a six-week regional test where sign-ups rose from **400 to 470 a month** at the lower price. The CFO is worried about margins. Should Lumen cut the price? If not, what should it do instead?

## Exhibits

| Item | Value |
|---|---|
| Current price | $120 per customer-month |
| Proposed price | $99 (−17.5%) |
| Cost to serve (hosting, support, fees) | $24 per customer-month |
| Customers today | 5,000 |
| Monthly churn | 3% |
| Customer acquisition cost (CAC) | $1,800 |
| Regional test: monthly sign-ups | 400 at $120 · 470 at $99 |

## Structure

```
Should Lumen cut its price?
├── Does the cut pay for itself?        volume needed, volume expected
├── Is each customer worth acquiring?   lifetime value, acquisition cost
├── What is the right price?            demand curve, profit-maximising price
└── What really drives value?           sensitivity, target
```

## Solution

**1. Does the cut pay for itself?** Margin today = ($120 − $24) / $120 = 80%.
Volume needed = 0.175 / (0.80 − 0.175) = **+28.0%**. The test delivered **+17.5%**.
Arc elasticity = (70 / 435) / (−21 / 109.5) = **−0.84: inelastic**. The cut cannot pay for itself.

In money: a month of sign-ups earns 400 × $96 = **$38.4K** a month today and 470 × $75 = **$35.25K** after the cut. Repricing the existing 5,000 customers gives away another **$105K a month**.

**2. Unit economics.**

| | $120 | $99 |
|---|---|---|
| Margin per customer-month | $96 | $75 |
| LTV (margin / 3% churn) | $3,200 | $2,500 |
| LTV / CAC | **1.78×** | **1.39×** |
| CAC payback | 18.75 months | 24 months |

Both are below the 3× benchmark. The cut makes a weak position worse.

**3. The right price.** The two test points give straight-line demand Q = 800 − 3.33P, so the choke price is $240. The profit-maximising price is halfway between unit cost and the choke price: ($240 + $24) / 2 = **$132**, above today's price.

**4. What drives value?** A ±20% tornado on LTV/CAC:

| Input | LTV/CAC swing |
|---|---|
| Price | 0.89× |
| CAC | 0.74× |
| Churn | 0.74× |
| Cost to serve | 0.18× |

Price is the biggest single lever because it moves both revenue and margin, which again argues for raising it. But even at $132, LTV/CAC is only **2.00×**. Goal seek: reaching 3× at $120 needs monthly churn of **1.78%** (from 3%) or CAC of **$1,067** (from $1,800).

## Recommendation

> **Do not cut the price.** Demand is inelastic, so the cut destroys margin on new and existing customers. Test a rise toward **$132** in one region instead, and put the growth budget into retention: monthly churn of about **1.8%** is what gets LTV/CAC to 3×; price alone cannot.

## What interviewers look for

- Asking for the margin *before* judging the volume uplift. +17.5% sounds good until you know +28% was needed.
- Remembering the existing base: a list-price cut reprices every current customer, not just new ones.
- Noticing that the real problem (LTV/CAC 1.78×) predates the pricing question.
