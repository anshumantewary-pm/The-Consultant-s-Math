"""Case 4: Northwind Logistics, automate the main warehouse?

Skills: building a cash-flow model, NPV / IRR / discounted payback, weighted
scenarios, Monte Carlo risk, goal seek on a point estimate and on a
probability, and turning "positive NPV but risky" into a negotiating target.
"""

from __future__ import annotations

from typing import Any

from casemath.analysis.distributions import Triangular, Uniform
from casemath.analysis.goal_seek import goal_seek
from casemath.analysis.model import Inputs
from casemath.analysis.montecarlo import simulate
from casemath.analysis.scenarios import compare_scenarios
from casemath.calculators.finance import investment_appraisal, npv
from casemath.cases.base import Case, Solution
from casemath.core.formatting import fmt_money, fmt_pct
from casemath.core.result import Step
from casemath.frameworks.issue_tree import Node, branch, leaf

CAPEX = 12_000_000.0  # vendor quote, paid up front
YEARS = 7  # useful life
SALVAGE = 1_000_000.0  # resale value of the kit at the end of year 7
WACC = 0.09
SAVINGS = 3_200_000.0  # year-1 labour and error savings, base case
SAVINGS_GROWTH = 0.04  # savings grow with throughput
MAINTENANCE = 600_000.0  # per year

SCENARIOS = {
    "Downside: savings $2.4M, flat volume": {"savings": 2_400_000.0, "growth": 0.0},
    "Base": {},
    "Upside: savings $3.8M, +6% volume": {"savings": 3_800_000.0, "growth": 0.06},
}
PROBABILITIES = dict(zip(SCENARIOS, (0.25, 0.50, 0.25), strict=True))

# Operations' ranges for the Monte Carlo.
SAVINGS_RANGE = Triangular(2_200_000.0, 3_200_000.0, 3_600_000.0)
GROWTH_RANGE = Uniform(0.0, 0.06)
MAINTENANCE_RANGE = Triangular(500_000.0, 600_000.0, 900_000.0)
RUNS = 5_000
SEED = 7

MAX_LOSS_PROBABILITY = 0.10  # board rule: at most a 10% chance of destroying value

BASE: dict[str, float] = {
    "capex": CAPEX,
    "savings": SAVINGS,
    "growth": SAVINGS_GROWTH,
    "maintenance": MAINTENANCE,
    "salvage": SALVAGE,
    "rate": WACC,
}


def cash_flows(x: Inputs) -> list[float]:
    """Year 0 capex, then savings (growing) less maintenance, plus salvage in the last year."""
    flows = [-x["capex"]]
    for year in range(1, YEARS + 1):
        flow = x["savings"] * (1 + x["growth"]) ** (year - 1) - x["maintenance"]
        flows.append(flow + (x["salvage"] if year == YEARS else 0.0))
    return flows


def project_npv(x: Inputs) -> float:
    return npv(x["rate"], cash_flows(x))


def _uncertain(capex: float) -> dict[str, Any]:
    return {
        **BASE,
        "capex": capex,
        "savings": SAVINGS_RANGE,
        "growth": GROWTH_RANGE,
        "maintenance": MAINTENANCE_RANGE,
    }


def loss_probability(x: Inputs) -> float:
    """P(NPV < 0) at a given capex. With a fixed seed this falls steadily as capex falls."""
    return simulate(project_npv, _uncertain(x["capex"]), runs=RUNS, seed=SEED).prob_below_threshold


class AutomationInvestmentCase(Case):
    id = "4"
    title = "Northwind Logistics: automate the main warehouse?"
    case_type = "Investment"
    skills = ("NPV", "IRR", "scenarios", "Monte Carlo", "goal seek", "negotiation target")
    prompt = """
Northwind Logistics has a $12M quote to automate its main warehouse with
robotic picking. Operations expects $3.2M a year of labour and error savings,
growing with volume, less $0.6M a year of maintenance. The kit lasts 7 years
and can be resold for $1M. Northwind's cost of capital is 9%. The board's
rule for large projects: positive expected NPV *and* no more than a 10% chance
of destroying value. Should Northwind sign? Exhibits: the base case,
operations' downside / base / upside scenarios and their ranges for savings,
volume growth and maintenance.
"""

    def data(self) -> dict[str, Any]:
        return {
            "capex": CAPEX,
            "years": YEARS,
            "salvage": SALVAGE,
            "wacc": WACC,
            "savings_year_1": SAVINGS,
            "savings_growth": SAVINGS_GROWTH,
            "maintenance_per_year": MAINTENANCE,
            "scenarios": SCENARIOS,
            "scenario_probabilities": PROBABILITIES,
            "ranges": {
                "savings": SAVINGS_RANGE.to_dict(),
                "growth": GROWTH_RANGE.to_dict(),
                "maintenance": MAINTENANCE_RANGE.to_dict(),
            },
            "max_loss_probability": MAX_LOSS_PROBABILITY,
        }

    def structure(self) -> Node:
        return branch(
            "Should Northwind automate?",
            "sum",
            branch(
                "Value in the base case",
                "sum",
                leaf("Cash flows", hint="Capex, savings, maintenance, salvage by year"),
                leaf("NPV and IRR", hint="Above 9%? How long to pay back?"),
            ),
            branch(
                "Risk",
                "sum",
                leaf("Scenarios", hint="Downside / base / upside and expected value"),
                leaf("Simulation", hint="Chance of NPV < 0 across the ranges"),
            ),
            branch(
                "How to make it work",
                "sum",
                leaf("Break-even savings", hint="How far can savings fall?"),
                leaf("Price to pay", hint="What capex meets the 10% risk rule?"),
            ),
        )

    def solve(self) -> Solution:
        flows = cash_flows(BASE)
        appraisal = investment_appraisal(WACC, flows)
        table = compare_scenarios(project_npv, BASE, SCENARIOS, PROBABILITIES)
        sim = simulate(project_npv, _uncertain(CAPEX), runs=RUNS, seed=SEED)
        p5, p95 = sim.band_90
        break_even_savings = goal_seek(project_npv, BASE, "savings", 0.0, 0.0, SAVINGS).value
        max_capex = goal_seek(
            loss_probability,
            {"capex": CAPEX},
            "capex",
            MAX_LOSS_PROBABILITY,
            low=CAPEX * 0.5,
            high=CAPEX,
            tolerance=1_000.0,
        ).value
        discount_needed = 1 - max_capex / CAPEX
        passes = (table.expected_value or 0) > 0 and sim.prob_below_threshold <= (
            MAX_LOSS_PROBABILITY
        )

        steps = (
            *(Step(f"Cash flow, year {t}", f, "$") for t, f in enumerate(flows)),
            Step("NPV at 9%", appraisal.npv, "$"),
            Step("IRR", appraisal.irr or 0.0, "%"),
            Step("Payback", appraisal.simple_payback or 0.0, "years"),
            Step("Discounted payback", appraisal.discounted_payback or 0.0, "years"),
            *(Step(f"NPV, {row.name}", row.output, "$") for row in table.rows),
            Step("Probability-weighted NPV", table.expected_value or 0.0, "$"),
            Step("Simulated mean NPV", sim.mean, "$"),
            Step("Simulated NPV, 5th percentile", p5, "$"),
            Step("Simulated NPV, 95th percentile", p95, "$"),
            Step("Probability NPV < 0", sim.prob_below_threshold, "%"),
            Step("Break-even year-1 savings", break_even_savings, "$"),
            Step("Highest capex meeting the 10% risk rule", max_capex, "$"),
        )

        def money(value: float) -> str:
            return fmt_money(value, compact=True)

        downside = table.rows[0]
        findings = (
            f"On the base case the project clears the bar: NPV {money(appraisal.npv)}, IRR "
            f"{fmt_pct(appraisal.irr or 0.0)} against a {fmt_pct(WACC, 0)} cost of capital, "
            f"payback in {appraisal.simple_payback:.1f} years.",
            f"The downside scenario loses {money(-downside.output)}; weighting the three "
            f"scenarios 25/50/25 still gives {money(table.expected_value or 0.0)}.",
            f"Savings only need to reach {money(break_even_savings)} in year 1 for NPV to be "
            f"zero, {fmt_pct(1 - break_even_savings / SAVINGS)} below plan.",
            f"Across operations' ranges the mean NPV is {money(sim.mean)}, below the base case "
            "because the savings range is skewed to the downside, and there is a "
            f"{fmt_pct(sim.prob_below_threshold)} chance of NPV below zero. The 90% range is "
            f"{money(p5)} to {money(p95)}.",
            f"That fails the board's {fmt_pct(MAX_LOSS_PROBABILITY, 0)} risk rule. At a capex "
            f"of {money(max_capex)} ({fmt_pct(discount_needed)} off the quote) it would pass.",
        )
        recommendation = (
            "Do not sign at $12M. The project creates value on average but carries a "
            f"{fmt_pct(sim.prob_below_threshold, 0)} chance of losing money. Go back to the "
            f"vendor for at least {fmt_pct(discount_needed)} off (capex of "
            f"{money(max_capex)} or less), or an equivalent mix of price cut and savings "
            "guarantee, and sign if they meet it."
        )
        return Solution(
            case_id=self.id,
            title=self.title,
            steps=steps,
            findings=findings,
            recommendation=recommendation,
            answer={
                "npv": appraisal.npv,
                "irr": appraisal.irr,
                "payback_years": appraisal.simple_payback,
                "discounted_payback_years": appraisal.discounted_payback,
                "downside_npv": downside.output,
                "expected_npv": table.expected_value,
                "simulated_mean_npv": sim.mean,
                "prob_loss": sim.prob_below_threshold,
                "npv_p5": p5,
                "npv_p95": p95,
                "break_even_savings": break_even_savings,
                "max_capex": max_capex,
                "discount_needed": discount_needed,
                "passes_board_rule": float(passes),
            },
        )
