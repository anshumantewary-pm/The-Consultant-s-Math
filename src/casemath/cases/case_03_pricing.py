"""Case 3: LedgerLite, should it raise its subscription price 15%?

Skills: price elasticity, break-even volume change, segment-level pricing,
and spotting that an average hides two very different customers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from casemath.calculators.pricing import PriceChange, price_change_impact, price_elasticity
from casemath.cases.base import Case, Solution
from casemath.core.formatting import fmt_money, fmt_pct
from casemath.core.result import Step
from casemath.frameworks.issue_tree import Node, branch, leaf

PRICE = 40.0  # per subscriber per month
VARIABLE_COST = 10.0  # hosting, support, payment fees per subscriber per month
FIXED_COSTS = 250_000.0  # per month
PROPOSED_PRICE = 46.0  # +15%
PREMIUM_TIER_PRICE = 50.0  # +25%
DISCOUNT_PRICE = 36.0  # -10%
TEST_PRICE = 44.0


@dataclass(frozen=True)
class CustomerSegment:
    name: str
    subscribers: float
    test_before: float  # subscribers in the test region before the change
    test_after: float  # ... and after a $40 -> $44 test


SEGMENTS = (
    CustomerSegment("Small businesses", 12_000, test_before=3_000, test_after=2_550),
    CustomerSegment("Accounting firms", 8_000, test_before=2_000, test_after=1_960),
)


def money(value: float) -> str:
    return fmt_money(value, compact=True)


class PricingCase(Case):
    id = "3"
    title = "LedgerLite: raise the subscription price 15%?"
    case_type = "Pricing"
    skills = ("price elasticity", "break-even volume", "segmentation", "profitability")
    prompt = """
LedgerLite sells bookkeeping software for $40 per subscriber per month to
20,000 subscribers. The CFO proposes a 15% price rise to $46 to lift profit.
Last quarter a regional test raised the price to $44; the exhibits show how
many subscribers each customer group kept. Should LedgerLite raise the price?
"""

    def data(self) -> dict[str, Any]:
        return {
            "price": PRICE,
            "variable_cost_per_subscriber": VARIABLE_COST,
            "fixed_costs_per_month": FIXED_COSTS,
            "proposed_price": PROPOSED_PRICE,
            "test_price": TEST_PRICE,
            "segments": [
                {
                    "segment": s.name,
                    "subscribers": s.subscribers,
                    "test_region_before": s.test_before,
                    "test_region_after": s.test_after,
                }
                for s in SEGMENTS
            ],
        }

    def structure(self) -> Node:
        return branch(
            "Does the price rise increase profit?",
            "difference",
            branch(
                "Contribution after the rise",
                "product",
                leaf("New unit margin", hint="Price - variable cost: how much does each sub gain?"),
                leaf(
                    "Subscribers kept", hint="Elasticity: how many leave? Does it differ by group?"
                ),
            ),
            leaf("Contribution today", hint="Margin x subscribers at $40"),
            hint="Fixed costs do not move with price, so compare contribution only.",
        )

    def solve(self) -> Solution:
        elasticity = {
            s.name: price_elasticity(PRICE, s.test_before, TEST_PRICE, s.test_after)
            for s in SEGMENTS
        }

        def impact(segment: CustomerSegment, new_price: float) -> PriceChange:
            return price_change_impact(
                PRICE, segment.subscribers, VARIABLE_COST, new_price, elasticity[segment.name]
            )

        smb, firms = SEGMENTS
        uniform = {s.name: impact(s, PROPOSED_PRICE) for s in SEGMENTS}
        uniform_change = sum(c.contribution_change for c in uniform.values())
        firms_premium = impact(firms, PREMIUM_TIER_PRICE)
        smb_cut = impact(smb, DISCOUNT_PRICE)
        break_even_rise = uniform[smb.name].break_even_volume_change
        break_even_premium = firms_premium.break_even_volume_change

        base_contribution = sum(s.subscribers for s in SEGMENTS) * (PRICE - VARIABLE_COST)
        base_profit = base_contribution - FIXED_COSTS
        recommended_profit = base_profit + firms_premium.contribution_change

        steps = (
            Step("Profit today (per month)", base_profit, "$"),
            Step("Contribution margin today", (PRICE - VARIABLE_COST) / PRICE, "%"),
            Step("Elasticity: small businesses", elasticity[smb.name]),
            Step("Elasticity: accounting firms", elasticity[firms.name]),
            Step("Max volume loss for +15% to pay", break_even_rise, "%"),
            Step("Expected loss at +15%: small businesses",
                 uniform[smb.name].expected_volume_change, "%"),
            Step("Expected loss at +15%: accounting firms",
                 uniform[firms.name].expected_volume_change, "%"),
            Step("+15% for all: contribution change", uniform_change, "$"),
            Step("Accounting firms at $50: contribution change",
                 firms_premium.contribution_change, "$"),
            Step("Max volume loss for +25% to pay", break_even_premium, "%"),
            Step("Small businesses at $36: contribution change", smb_cut.contribution_change, "$"),
            Step("Profit with recommended pricing (per month)", recommended_profit, "$"),
        )  # fmt: skip
        findings = (
            f"At a {fmt_pct((PRICE - VARIABLE_COST) / PRICE, 0)} contribution margin, a 15% rise "
            f"pays off as long as no more than {fmt_pct(-break_even_rise)} of subscribers leave.",
            f"The test shows two different customers: small businesses are elastic "
            f"(e = {elasticity[smb.name]:.2f}), accounting firms barely react "
            f"(e = {elasticity[firms.name]:.2f}).",
            f"A uniform $46 price loses {fmt_pct(-uniform[smb.name].expected_volume_change)} of "
            f"small businesses (more than the {fmt_pct(-break_even_rise)} limit) and only "
            f"{fmt_pct(-uniform[firms.name].expected_volume_change)} of firms. Net: "
            f"{fmt_money(uniform_change)} a month, a wash.",
            f"Charging firms $50 (a Pro tier) adds {money(firms_premium.contribution_change)} a "
            f"month: expected loss {fmt_pct(-firms_premium.expected_volume_change)} vs a "
            f"{fmt_pct(-break_even_premium)} limit.",
            f"Cutting the small-business price to $36 adds only "
            f"{money(smb_cut.contribution_change)} a month: not worth the revenue risk.",
        )
        recommendation = (
            f"Do not raise the price for everyone. Launch a Pro tier for accounting firms at "
            f"{fmt_money(PREMIUM_TIER_PRICE)} (profit up {money(firms_premium.contribution_change)}"
            f" a month, {fmt_pct(firms_premium.contribution_change / base_profit, 0)}) and hold "
            "small businesses at $40. Roll Pro out region by region: $50 is beyond the tested "
            "$44, so confirm churn stays under the break-even limit before going national."
        )
        return Solution(
            case_id=self.id,
            title=self.title,
            steps=steps,
            findings=findings,
            recommendation=recommendation,
            answer={
                "profit_today": base_profit,
                "elasticity_small_business": elasticity[smb.name],
                "elasticity_accounting_firms": elasticity[firms.name],
                "break_even_volume_change_15pct": break_even_rise,
                "uniform_rise_contribution_change": uniform_change,
                "pro_tier_contribution_change": firms_premium.contribution_change,
                "small_business_cut_contribution_change": smb_cut.contribution_change,
                "recommended_profit": recommended_profit,
            },
        )
