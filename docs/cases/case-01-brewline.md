# Case 1: Brewline Beverages, revenue up but profit down

**Type:** Profitability · **Run it:** `casemath case solve 1` · **Code:** [`case_01_profit_decline.py`](../../src/casemath/cases/case_01_profit_decline.py)

## Prompt

Brewline Beverages sells bottled tea, energy drinks and juice. Revenue grew 2.7% last year, yet operating profit fell from $10.0M to $6.2M. The CEO wants to know why, and what to do about it.

## Exhibits

| Segment | Year | Price | Units | Unit cost | Fixed costs |
|---|---|---|---|---|---|
| Bottled Tea | 1 | $2.00 | 10.0M | $1.20 | $3.0M |
| | 2 | $2.00 | 10.5M | $1.22 | $3.0M |
| Energy Drinks | 1 | $3.00 | 5.0M | $1.50 | $2.0M |
| | 2 | $2.60 | 5.8M | $1.50 | $2.0M |
| Juice | 1 | $2.50 | 6.0M | $1.50 | $1.5M |
| | 2 | $2.50 | 6.1M | $1.95 | $1.5M |

Head-office overhead: $5.0M in year 1, $5.2M in year 2.

## Structure

Start with the profitability tree (Profit = Revenue − Costs; Revenue = Price × Volume; Costs = Fixed + Variable). Since revenue *grew*, the hypothesis is that the problem is on the cost side or in pricing, and that one segment is hiding behind the total.

## Solution

**1. Confirm the headline.**

| | Year 1 | Year 2 | Change |
|---|---|---|---|
| Revenue | $50.00M | $51.33M | +2.7% |
| Operating profit | $10.00M | $6.225M | −$3.775M (−37.8%) |

**2. Segment P&L.**

| Segment | Profit Y1 | Profit Y2 | Change |
|---|---|---|---|
| Bottled Tea | $5.00M | $5.19M | +$0.19M |
| Energy Drinks | $5.50M | $4.38M | −$1.12M |
| Juice | $4.50M | $1.855M | −$2.645M |
| HQ overhead | −$5.00M | −$5.20M | −$0.20M |
| **Total** | **$10.00M** | **$6.225M** | **−$3.775M** |

**3. Bridge each segment** (price, volume, unit cost, fixed cost).

| Segment | Price | Volume | Unit cost | Fixed | Net |
|---|---|---|---|---|---|
| Bottled Tea | 0 | +$0.40M | −$0.21M | 0 | +$0.19M |
| Energy Drinks | **−$2.32M** | +$1.20M | 0 | 0 | −$1.12M |
| Juice | 0 | +$0.10M | **−$2.745M** | 0 | −$2.645M |

MECE check: the six non-zero effects plus HQ overhead add up to exactly −$3.775M. Nothing is missing and nothing is counted twice.

**4. Ask why.**

- *Juice:* unit cost rose 30% ($1.50 → $1.95) while price stayed flat. Unit margin fell from $1.00 to $0.55. This one effect is **73% of the decline**.
- *Energy Drinks:* price was cut 13% ($3.00 → $2.60) to win volume. Volume grew 16%, but to keep last year's $7.5M contribution at the new $1.10 unit margin, it needed **6.82M units**; it sold 5.80M. The cut does not pay for itself. Net effect: **30% of the decline**.
- *Bottled Tea:* grew slightly. Not the problem.

**5. What price fixes Juice?** To restore the $1.00 unit margin at the new $1.95 cost: **$2.95**. (The price that just covers all juice costs at current volume is $2.20, so juice is still profitable today, just much less so.)

## Recommendation

> **Fix Juice first, then reverse the Energy Drinks price cut.**
> 1. Juice input costs rose 30% and explain 73% of the decline. Pass the cost through (price toward $2.95), renegotiate or hedge fruit contracts, or reformulate.
> 2. The Energy Drinks price cut cost $2.3M and won back $1.2M. Roll it back, or keep it only in channels where volume can reach 6.8M units.
> 3. Leave Bottled Tea alone; it is growing profitably.
>
> **Risks:** a Juice price rise may lose volume; test it in one region first. Check whether competitors face the same fruit costs (if so, they will likely raise prices too).

## What this case practises

- Reading a profit decline through the profitability tree
- Segmenting before concluding
- A MECE profit bridge that reconciles to the penny
- Break-even logic for a price cut
