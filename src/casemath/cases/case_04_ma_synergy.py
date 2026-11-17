"""Case 4: Northfield Foods, is a 30% premium for Crestline Snacks justified?

Skills: synergy sizing (cost vs revenue), risk haircuts, phase-in and
integration-cost payback, synergy value vs premium, walk-away price.
"""

from __future__ import annotations

from typing import Any

from casemath.calculators.synergy import (
    SynergyItem,
    acquisition_premium,
    synergy_schedule,
    synergy_value,
)
from casemath.cases.base import Case, Solution
from casemath.core.formatting import fmt_money, fmt_pct
from casemath.core.result import Step
from casemath.frameworks.issue_tree import Node, branch, leaf

STANDALONE_VALUE = 400_000_000.0  # Crestline's unaffected equity value
OFFER_VALUE = 520_000_000.0
EBITDA_MULTIPLE = 8.0
PHASE_IN = (0.30, 0.70, 1.00, 1.00)
INTEGRATION_COSTS = (20_000_000.0, 10_000_000.0)
REVENUE_SYNERGY_PROBABILITY = 0.5  # management cases deliver about half of cross-selling

COST_SYNERGIES = (
    SynergyItem("Procurement (joint buying)", 8_000_000),
    SynergyItem("Plant consolidation", 6_000_000),
    SynergyItem("Overlapping SG&A", 4_000_000),
)
REVENUE_SYNERGY = SynergyItem(
    "Cross-sell Crestline into Northfield's grocery accounts",
    30_000_000,
    kind="revenue",
    margin=0.25,
)


def money(value: float) -> str:
    return fmt_money(value, compact=True)


class SynergyCase(Case):
    id = "4"
    title = "Northfield Foods: is a 30% premium for Crestline justified?"
    case_type = "M&A"
    skills = ("synergy sizing", "risk haircut", "payback", "valuation multiple", "deal price")
    prompt = """
Northfield Foods, a packaged-food maker, has agreed terms to buy Crestline
Snacks for $520M. Crestline's unaffected market value is $400M. Northfield's
team has identified cost and revenue synergies and estimated integration
costs. Comparable deals trade at 8x EBITDA. Is the price justified, and what
is the most Northfield should pay?
"""

    def data(self) -> dict[str, Any]:
        return {
            "standalone_value": STANDALONE_VALUE,
            "offer_value": OFFER_VALUE,
            "ebitda_multiple": EBITDA_MULTIPLE,
            "phase_in": list(PHASE_IN),
            "integration_costs": list(INTEGRATION_COSTS),
            "synergies": [
                {"name": s.name, "kind": s.kind, "run_rate": s.run_rate, "margin": s.margin}
                for s in (*COST_SYNERGIES, REVENUE_SYNERGY)
            ],
        }

    def structure(self) -> Node:
        return branch(
            "Is the deal worth it?",
            "difference",
            branch(
                "Value of synergies",
                "difference",
                branch(
                    "Run-rate synergies x multiple",
                    "sum",
                    leaf("Cost synergies", hint="Procurement, plants, SG&A: how certain?"),
                    leaf("Revenue synergies", hint="Profit, not revenue; how likely to land?"),
                ),
                leaf("One-off integration costs", hint="Severance, IT, plant closures"),
            ),
            leaf("Premium over standalone value", hint="Offer price - unaffected value"),
            hint="Paying a premium above synergy value transfers value to the seller.",
        )

    def solve(self) -> Solution:
        premium = OFFER_VALUE - STANDALONE_VALUE
        premium_pct = acquisition_premium(OFFER_VALUE, STANDALONE_VALUE)
        one_off = sum(INTEGRATION_COSTS)

        plan = synergy_schedule((*COST_SYNERGIES, REVENUE_SYNERGY), PHASE_IN, INTEGRATION_COSTS)
        haircut_revenue = SynergyItem(
            REVENUE_SYNERGY.name,
            REVENUE_SYNERGY.run_rate,
            kind="revenue",
            margin=REVENUE_SYNERGY.margin,
            probability=REVENUE_SYNERGY_PROBABILITY,
        )
        risked = synergy_schedule((*COST_SYNERGIES, haircut_revenue), PHASE_IN, INTEGRATION_COSTS)

        value_plan = synergy_value(plan.run_rate_total, EBITDA_MULTIPLE, one_off)
        value_risked = synergy_value(risked.run_rate_total, EBITDA_MULTIPLE, one_off)
        value_cost_only = synergy_value(plan.run_rate_cost, EBITDA_MULTIPLE, one_off)
        walk_away = STANDALONE_VALUE + value_risked
        cost_only_price = STANDALONE_VALUE + value_cost_only

        steps = (
            Step("Premium offered", premium, "$"),
            Step("Premium vs standalone value", premium_pct, "%"),
            Step("Run-rate cost synergies", plan.run_rate_cost, "$"),
            Step("Run-rate revenue synergies (profit)", plan.run_rate_revenue, "$"),
            Step("Run-rate synergies, management case", plan.run_rate_total, "$"),
            Step("One-off integration costs", one_off, "$"),
            Step("Synergy value, management case", value_plan, "$"),
            Step("Synergy value, revenue synergies at 50%", value_risked, "$"),
            Step("Synergy value, cost synergies only", value_cost_only, "$"),
            Step("Integration paid back in year (risked)", float(risked.payback_year or 0)),
            Step("Walk-away price (risked case)", walk_away, "$"),
            Step("Price fully backed by cost synergies", cost_only_price, "$"),
        )
        share_kept = 1 - premium / value_risked
        findings = (
            f"The {fmt_pct(premium_pct, 0)} premium is {money(premium)}. Synergies must be worth "
            "more than that, or the deal destroys value for Northfield's shareholders.",
            f"Management's case: {money(plan.run_rate_total)} a year at run-rate, worth "
            f"{money(value_plan)} at {EBITDA_MULTIPLE:g}x after {money(one_off)} of integration "
            "costs. On paper, comfortably above the premium.",
            f"Revenue synergies are {fmt_pct(plan.run_rate_revenue / plan.run_rate_total, 0)} of "
            f"the total and the least certain. At a 50% haircut the value is "
            f"{money(value_risked)}; Northfield keeps {fmt_pct(share_kept, 0)} of it.",
            f"Cost synergies alone are worth {money(value_cost_only)}: "
            f"{money(premium - value_cost_only)} short of the premium. The deal depends on "
            "cross-selling.",
            f"Integration costs are paid back in year {risked.payback_year} as synergies reach "
            "full run-rate.",
        )
        recommendation = (
            f"Proceed, but the price is near the edge. Walk away above {money(walk_away)}. "
            f"Try to bring the fixed price down to about {money(cost_only_price)}, the value "
            "cost synergies alone support, and pay the rest as an earn-out tied to cross-selling "
            "revenue. Appoint a synergy owner for each line and track delivery against the "
            "phase-in plan."
        )
        return Solution(
            case_id=self.id,
            title=self.title,
            steps=steps,
            findings=findings,
            recommendation=recommendation,
            answer={
                "premium": premium,
                "premium_pct": premium_pct,
                "run_rate_cost": plan.run_rate_cost,
                "run_rate_revenue": plan.run_rate_revenue,
                "synergy_value_plan": value_plan,
                "synergy_value_risked": value_risked,
                "synergy_value_cost_only": value_cost_only,
                "payback_year": None if risked.payback_year is None else float(risked.payback_year),
                "walk_away_price": walk_away,
                "cost_only_price": cost_only_price,
            },
        )
