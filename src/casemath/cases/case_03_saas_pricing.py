"""Case 3: Lumen Analytics, should a SaaS company cut its price to grow?

Skills: price elasticity, break-even volume for a price move, customer unit
economics (LTV, CAC payback, LTV/CAC), the profit-maximising price, tornado
sensitivity and goal seek, and spotting that the real problem is not price.
"""

from __future__ import annotations

from typing import Any

from casemath.analysis.goal_seek import goal_seek
from casemath.analysis.model import Inputs
from casemath.analysis.sensitivity import tornado
from casemath.calculators.pricing import (
    arc_elasticity,
    breakeven_volume_change,
    optimal_price_linear,
)
from casemath.calculators.unit_economics import HEALTHY_LTV_TO_CAC, unit_economics
from casemath.cases.base import Case, Solution
from casemath.core.formatting import fmt_money, fmt_pct
from casemath.core.result import Step
from casemath.frameworks.issue_tree import Node, branch, leaf

CURRENT_PRICE = 120.0  # per customer per month
PROPOSED_PRICE = 99.0
COST_TO_SERVE = 24.0  # hosting, support, payment fees per customer-month
CUSTOMERS = 5_000
MONTHLY_CHURN = 0.03
CAC = 1_800.0
# Six-week regional test: monthly sign-ups at each price.
TEST_SIGNUPS = {CURRENT_PRICE: 400.0, PROPOSED_PRICE: 470.0}
SENSITIVITY_SWING = 0.20


def ltv_to_cac(x: Inputs) -> float:
    """LTV/CAC as a model, for tornado and goal seek."""
    margin = (x["price"] - x["cost_to_serve"]) / x["price"]
    return unit_economics(x["price"], margin, x["churn"], x["cac"]).ltv_to_cac


class SaasPricingCase(Case):
    id = "3"
    title = "Lumen Analytics: cut the price to grow?"
    case_type = "Pricing"
    skills = (
        "elasticity",
        "break-even volume",
        "LTV/CAC",
        "optimal price",
        "sensitivity",
        "goal seek",
    )
    prompt = """
Lumen Analytics sells a dashboard product at $120 per customer per month and
has 5,000 customers. Growth has slowed. The CMO wants to cut the price to $99
to win more sign-ups, and points to a six-week regional test where sign-ups
rose from 400 to 470 a month at the lower price. The CFO is worried about
margins. Should Lumen cut the price? If not, what should it do instead?
Exhibits: price, cost to serve, churn, customer acquisition cost and the test.
"""

    def data(self) -> dict[str, Any]:
        return {
            "current_price": CURRENT_PRICE,
            "proposed_price": PROPOSED_PRICE,
            "cost_to_serve_per_month": COST_TO_SERVE,
            "customers": CUSTOMERS,
            "monthly_churn": MONTHLY_CHURN,
            "cac": CAC,
            "test_signups_per_month": {f"{p:g}": q for p, q in TEST_SIGNUPS.items()},
        }

    def structure(self) -> Node:
        return branch(
            "Should Lumen cut its price?",
            "sum",
            branch(
                "Does the cut pay for itself?",
                "sum",
                leaf("Volume needed", hint="How much more volume keeps contribution flat?"),
                leaf("Volume expected", hint="What does the test say about elasticity?"),
            ),
            branch(
                "Is each customer worth acquiring?",
                "sum",
                leaf("Lifetime value", hint="Margin x lifetime, at each price"),
                leaf("Acquisition cost", hint="LTV/CAC and payback vs 3x and churn"),
            ),
            branch(
                "What is the right price?",
                "sum",
                leaf("Demand curve", hint="Fit from the two test points"),
                leaf("Profit-maximising price", hint="Halfway from cost to choke price"),
            ),
            branch(
                "What really drives value?",
                "sum",
                leaf("Sensitivity", hint="Which input moves LTV/CAC most?"),
                leaf("Target", hint="What level of that input gets us to 3x?"),
            ),
        )

    def solve(self) -> Solution:
        price_change = PROPOSED_PRICE / CURRENT_PRICE - 1
        margin_now = (CURRENT_PRICE - COST_TO_SERVE) / CURRENT_PRICE
        margin_cut = (PROPOSED_PRICE - COST_TO_SERVE) / PROPOSED_PRICE

        needed = breakeven_volume_change(price_change, margin_now)
        observed = TEST_SIGNUPS[PROPOSED_PRICE] / TEST_SIGNUPS[CURRENT_PRICE] - 1
        elasticity = arc_elasticity(
            CURRENT_PRICE, TEST_SIGNUPS[CURRENT_PRICE], PROPOSED_PRICE, TEST_SIGNUPS[PROPOSED_PRICE]
        )

        now = unit_economics(CURRENT_PRICE, margin_now, MONTHLY_CHURN, CAC)
        cut = unit_economics(PROPOSED_PRICE, margin_cut, MONTHLY_CHURN, CAC)

        optimum = optimal_price_linear(
            CURRENT_PRICE,
            TEST_SIGNUPS[CURRENT_PRICE],
            PROPOSED_PRICE,
            TEST_SIGNUPS[PROPOSED_PRICE],
            unit_cost=COST_TO_SERVE,
        )

        base = {
            "price": CURRENT_PRICE,
            "cost_to_serve": COST_TO_SERVE,
            "churn": MONTHLY_CHURN,
            "cac": CAC,
        }
        swing = {
            k: (v * (1 - SENSITIVITY_SWING), v * (1 + SENSITIVITY_SWING)) for k, v in base.items()
        }
        sensitivity = tornado(ltv_to_cac, base, swing)
        at_optimum = ltv_to_cac({**base, "price": optimum.price})
        target_churn = goal_seek(
            ltv_to_cac, base, "churn", target=HEALTHY_LTV_TO_CAC, low=0.001, high=MONTHLY_CHURN
        ).value
        target_cac = goal_seek(
            ltv_to_cac, base, "cac", target=HEALTHY_LTV_TO_CAC, low=1.0, high=CAC
        ).value

        # Monthly contribution from one month's sign-ups, now vs after the cut.
        cohort_now = TEST_SIGNUPS[CURRENT_PRICE] * (CURRENT_PRICE - COST_TO_SERVE)
        cohort_cut = TEST_SIGNUPS[PROPOSED_PRICE] * (PROPOSED_PRICE - COST_TO_SERVE)
        # The cut also reprices the existing base.
        base_revenue_lost = CUSTOMERS * (CURRENT_PRICE - PROPOSED_PRICE)

        steps = (
            Step("Price change", price_change, "%"),
            Step("Contribution margin today", margin_now, "%"),
            Step("Volume increase needed to break even", needed, "%"),
            Step("Sign-up increase seen in the test", observed, "%"),
            Step("Arc elasticity of sign-ups", elasticity),
            Step("Monthly contribution per sign-up cohort, $120", cohort_now, "$"),
            Step("Monthly contribution per sign-up cohort, $99", cohort_cut, "$"),
            Step("Monthly margin lost repricing existing customers", base_revenue_lost, "$"),
            Step("LTV at $120", now.ltv, "$"),
            Step("LTV/CAC at $120", now.ltv_to_cac, "x"),
            Step("LTV at $99", cut.ltv, "$"),
            Step("LTV/CAC at $99", cut.ltv_to_cac, "x"),
            Step("CAC payback at $120", now.cac_payback_periods, "months"),
            Step("Choke price (fitted demand)", optimum.choke_price, "$"),
            Step("Profit-maximising price", optimum.price, "$"),
            Step("LTV/CAC at the profit-maximising price", at_optimum, "x"),
            *(
                Step(f"LTV/CAC swing from {bar.input} +/-20%", bar.swing, "x")
                for bar in sensitivity.bars
            ),
            Step("Monthly churn needed for 3x LTV/CAC at $120", target_churn, "%"),
            Step("CAC needed for 3x LTV/CAC at $120", target_cac, "$"),
        )

        findings = (
            f"A {fmt_pct(-price_change)} cut at an {fmt_pct(margin_now, 0)} margin needs "
            f"{fmt_pct(needed)} more volume just to stand still. The test delivered "
            f"{fmt_pct(observed)}: demand is inelastic (elasticity {elasticity:.2f}).",
            f"Each month's sign-ups would earn {fmt_money(cohort_cut, compact=True)} a month "
            f"instead of {fmt_money(cohort_now, compact=True)}, and repricing the existing "
            f"{CUSTOMERS:,} customers gives away {fmt_money(base_revenue_lost, compact=True)} "
            "a month on top.",
            f"Unit economics are already weak: LTV/CAC is {now.ltv_to_cac:.2f}x at $120 "
            f"(CAC payback {now.cac_payback_periods:.1f} months) and would fall to "
            f"{cut.ltv_to_cac:.2f}x at $99. The benchmark is {HEALTHY_LTV_TO_CAC:g}x.",
            f"The fitted demand curve puts the profit-maximising price near "
            f"{fmt_money(optimum.price)}, above today's price, not below it.",
            f"{sensitivity.most_sensitive.capitalize()} is the biggest single lever on LTV/CAC "
            "(it moves both revenue and margin), which argues for raising it. But even at "
            f"{fmt_money(optimum.price, compact=True)} LTV/CAC is only {at_optimum:.2f}x. "
            f"Reaching 3x needs monthly churn down from {fmt_pct(MONTHLY_CHURN)} to "
            f"{fmt_pct(target_churn, 2)}, or CAC down to {fmt_money(target_cac, compact=True)}.",
        )
        recommendation = (
            "Do not cut the price: demand is inelastic, so the cut destroys margin on new and "
            f"existing customers. Test a rise toward {fmt_money(optimum.price, compact=True)} "
            "in one region instead, and put the growth budget into retention: monthly churn "
            f"of about {fmt_pct(target_churn, 1)} is what gets LTV/CAC to 3x; price alone "
            "cannot."
        )
        return Solution(
            case_id=self.id,
            title=self.title,
            steps=steps,
            findings=findings,
            recommendation=recommendation,
            answer={
                "price_change": price_change,
                "volume_needed": needed,
                "volume_observed": observed,
                "elasticity": elasticity,
                "ltv_now": now.ltv,
                "ltv_to_cac_now": now.ltv_to_cac,
                "ltv_to_cac_cut": cut.ltv_to_cac,
                "cac_payback_months": now.cac_payback_periods,
                "optimal_price": optimum.price,
                "ltv_to_cac_at_optimum": at_optimum,
                "target_churn": target_churn,
                "target_cac": target_cac,
                "monthly_margin_lost_on_base": base_revenue_lost,
            },
        )
