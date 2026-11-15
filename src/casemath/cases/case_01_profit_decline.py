"""Case 1: Brewline Beverages, revenue up but profit down 38%. Why?

Skills: profitability framework, profit bridge, segment analysis, MECE
reconciliation, break-even on a price cut.
"""

from __future__ import annotations

from typing import Any

from casemath.calculators.breakeven import break_even_price
from casemath.calculators.profitability import (
    ProfitBridge,
    Segment,
    profit_bridge,
    segment_profitability,
)
from casemath.cases.base import Case, Solution
from casemath.core.errors import CaseMathError
from casemath.core.formatting import fmt_money, fmt_pct
from casemath.core.result import Step
from casemath.frameworks.issue_tree import Node, branch, leaf
from casemath.frameworks.mece import check_mece
from casemath.frameworks.profitability import profitability_tree


def money(value: float) -> str:
    return fmt_money(value, compact=True)


YEAR_1 = (
    Segment("Bottled Tea", price=2.00, units=10_000_000, variable_cost_per_unit=1.20,
            fixed_costs=3_000_000),
    Segment("Energy Drinks", price=3.00, units=5_000_000, variable_cost_per_unit=1.50,
            fixed_costs=2_000_000),
    Segment("Juice", price=2.50, units=6_000_000, variable_cost_per_unit=1.50,
            fixed_costs=1_500_000),
)  # fmt: skip
YEAR_2 = (
    Segment("Bottled Tea", price=2.00, units=10_500_000, variable_cost_per_unit=1.22,
            fixed_costs=3_000_000),
    Segment("Energy Drinks", price=2.60, units=5_800_000, variable_cost_per_unit=1.50,
            fixed_costs=2_000_000),
    Segment("Juice", price=2.50, units=6_100_000, variable_cost_per_unit=1.95,
            fixed_costs=1_500_000),
)  # fmt: skip
HQ_FIXED = {"year_1": 5_000_000.0, "year_2": 5_200_000.0}


class ProfitDeclineCase(Case):
    id = "1"
    title = "Brewline Beverages: revenue up, profit down"
    case_type = "Profitability"
    skills = ("profitability framework", "profit bridge", "MECE", "break-even")
    prompt = """
Brewline Beverages sells bottled tea, energy drinks and juice. Revenue grew
2.7% last year, yet operating profit fell from $10.0M to $6.2M. The CEO wants
to know why, and what to do about it. Exhibits: price, volume, unit cost and
fixed cost by product line for both years, plus head-office overhead.
"""

    def data(self) -> dict[str, Any]:
        def rows(segments: tuple[Segment, ...]) -> list[dict[str, Any]]:
            return [
                {
                    "segment": s.name,
                    "price": s.price,
                    "units": s.units,
                    "variable_cost_per_unit": s.variable_cost_per_unit,
                    "fixed_costs": s.fixed_costs,
                }
                for s in segments
            ]

        return {"year_1": rows(YEAR_1), "year_2": rows(YEAR_2), "hq_fixed_costs": HQ_FIXED}

    def structure(self) -> Node:
        return profitability_tree()

    def solve(self) -> Solution:
        y1 = segment_profitability(YEAR_1, HQ_FIXED["year_1"])
        y2 = segment_profitability(YEAR_2, HQ_FIXED["year_2"])
        change = y2.total_profit - y1.total_profit
        bridges: dict[str, ProfitBridge] = {
            s.name: profit_bridge(y1.line(s.name).statement, y2.line(s.name).statement)
            for s in YEAR_1
        }
        hq_effect = -(HQ_FIXED["year_2"] - HQ_FIXED["year_1"])

        # MECE: every dollar of the profit change must land in exactly one bucket.
        buckets = [
            leaf(f"{name}: {effect}", value)
            for name, bridge in bridges.items()
            for effect, value in bridge.effects.items()
            if value
        ]
        reconciliation = branch(
            "Profit change", "sum", *buckets, leaf("HQ overhead", hq_effect), value=change
        )
        mece = check_mece(reconciliation)
        if not mece.ok:  # pragma: no cover - guards the exhibit data itself
            raise CaseMathError(mece.summary())

        juice = bridges["Juice"]
        energy = bridges["Energy Drinks"]
        e1 = y1.line("Energy Drinks").statement
        e2 = y2.line("Energy Drinks").statement
        # Units Energy Drinks needed at the new price to keep last year's contribution.
        energy_units_needed = e1.contribution / e2.contribution_per_unit
        # Juice price that restores last year's unit margin at this year's unit cost.
        j1 = y1.line("Juice").statement
        j2 = y2.line("Juice").statement
        juice_price_needed = j2.variable_cost_per_unit + j1.contribution_per_unit
        # Sanity check with the break-even price helper: price to cover juice costs at all.
        juice_break_even_price = break_even_price(
            j2.fixed_costs, j2.units, j2.variable_cost_per_unit
        )

        share_juice = juice.variable_cost_effect / change
        juice_cost_rise = j2.variable_cost_per_unit / j1.variable_cost_per_unit - 1
        share_energy = (energy.price_effect + energy.volume_effect) / change

        steps = (
            Step("Year 1 revenue", y1.total_revenue, "$"),
            Step("Year 2 revenue", y2.total_revenue, "$"),
            Step("Year 1 operating profit", y1.total_profit, "$"),
            Step("Year 2 operating profit", y2.total_profit, "$"),
            Step("Profit change", change, "$"),
            Step("Profit change vs Year 1", change / y1.total_profit, "%"),
            Step("Juice: unit cost effect", juice.variable_cost_effect, "$"),
            Step("Energy Drinks: price effect", energy.price_effect, "$"),
            Step("Energy Drinks: extra volume effect", energy.volume_effect, "$"),
            Step("Bottled Tea: net change", bridges["Bottled Tea"].profit_change, "$"),
            Step("HQ overhead change", hq_effect, "$"),
            Step("Energy units needed to justify price cut", energy_units_needed, "units"),
            Step("Energy units actually sold", e2.units, "units"),
            Step("Juice price to restore unit margin", juice_price_needed, "$"),
            Step("Juice break-even price (covers costs only)", juice_break_even_price, "$"),
        )
        findings = (
            "Revenue is not the problem: it grew in every line. The decline is in margins.",
            f"Juice unit cost rose {fmt_pct(juice_cost_rise)}"
            f" ({fmt_money(j1.variable_cost_per_unit)} to {fmt_money(j2.variable_cost_per_unit)}),"
            f" costing {money(-juice.variable_cost_effect)}: {fmt_pct(share_juice, 0)} of the"
            " decline.",
            f"The Energy Drinks price cut ({fmt_money(e1.price)} to {fmt_money(e2.price)}) cost "
            f"{money(-energy.price_effect)}; the extra volume won back only "
            f"{money(energy.volume_effect)}. Net: {fmt_pct(share_energy, 0)} of the decline.",
            f"To pay for the cut, Energy Drinks needed {energy_units_needed / 1e6:.2f}M units; "
            f"it sold {e2.units / 1e6:.2f}M.",
            "Bottled Tea is healthy and HQ overhead is a minor factor.",
            f"MECE check: the {len(buckets) + 1} buckets reconcile exactly to the profit change.",
        )
        recommendation = (
            f"Fix Juice first: pass the input cost through (price to about "
            f"{fmt_money(juice_price_needed)}) or renegotiate fruit contracts and reformulate. "
            "Then roll back the Energy Drinks price cut, or keep it only where volume growth "
            f"can reach {energy_units_needed / 1e6:.1f}M units. Leave Bottled Tea as is."
        )
        return Solution(
            case_id=self.id,
            title=self.title,
            steps=steps,
            findings=findings,
            recommendation=recommendation,
            answer={
                "profit_year_1": y1.total_profit,
                "profit_year_2": y2.total_profit,
                "profit_change": change,
                "juice_cost_effect": juice.variable_cost_effect,
                "energy_price_effect": energy.price_effect,
                "energy_volume_effect": energy.volume_effect,
                "energy_units_needed": energy_units_needed,
                "juice_price_needed": juice_price_needed,
            },
        )
