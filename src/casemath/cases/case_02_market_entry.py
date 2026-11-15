"""Case 2: VoltWay, should it enter a city's EV fast-charging market?

Skills: top-down market sizing, market share and concentration, break-even,
share projection, payback, and turning a "no" into a "yes, if".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from casemath.calculators.breakeven import break_even_units, payback_period
from casemath.calculators.market_share import (
    hhi,
    project_share,
    required_share,
    share_table,
)
from casemath.calculators.market_sizing import top_down
from casemath.cases.base import Case, Solution
from casemath.core.formatting import fmt_money, fmt_number, fmt_pct
from casemath.core.result import Step
from casemath.frameworks.issue_tree import Node, branch, leaf

EVS_IN_CITY = 50_000
SHARE_USING_PUBLIC_FAST_CHARGING = 0.30
SESSIONS_PER_USER_PER_YEAR = 6 * 12
PRICE_PER_SESSION = 8.0
VARIABLE_COST_PER_SESSION = 5.0  # electricity, payment fees, wear
FIXED_COSTS_PER_YEAR = 20 * 40_000.0  # 20 stations x site rent, maintenance, staff
CAPEX = 2_000_000.0
YEAR_1_SHARE = 0.08
VOLTWAY_GROWTH = 0.60
MARKET_GROWTH = 0.25
HORIZON_YEARS = 4
COMPETITORS = {"ChargeCo": 486_000.0, "GridGo": 324_000.0} | {
    f"Independent {i}": 27_000.0 for i in range(1, 11)
}
FLEET_ANCHOR_SESSIONS = 150_000.0
FLEET_ANCHOR_PRICE = 7.0
MAX_BREAK_EVEN_YEAR = 3
MAX_PAYBACK_YEARS = 5.0


@dataclass(frozen=True)
class Scenario:
    name: str
    operating_profit: tuple[float, ...]  # year 1 .. HORIZON_YEARS
    break_even_year: int | None
    payback_years: float | None

    @property
    def passes(self) -> bool:
        return (
            self.break_even_year is not None
            and self.break_even_year <= MAX_BREAK_EVEN_YEAR
            and self.payback_years is not None
            and self.payback_years <= MAX_PAYBACK_YEARS
        )


def _scenario(name: str, retail_sessions: tuple[float, ...], anchor_sessions: float) -> Scenario:
    retail_margin = PRICE_PER_SESSION - VARIABLE_COST_PER_SESSION
    anchor_margin = FLEET_ANCHOR_PRICE - VARIABLE_COST_PER_SESSION
    profit = tuple(
        s * retail_margin + anchor_sessions * anchor_margin - FIXED_COSTS_PER_YEAR
        for s in retail_sessions
    )
    break_even_year = next((year for year, p in enumerate(profit, start=1) if p >= 0), None)
    final = profit[-1]
    payback = payback_period(CAPEX, final) if final > 0 else None
    return Scenario(name, profit, break_even_year, payback)


class MarketEntryCase(Case):
    id = "2"
    title = "VoltWay: enter the city's EV fast-charging market?"
    case_type = "Market entry"
    skills = ("market sizing", "market share", "HHI", "break-even", "payback")
    prompt = """
VoltWay runs EV fast-charging stations in two cities and is considering a
third. Entry means 20 stations: $2.0M up front and $800K a year to run. The
board's rule: operating break-even by year 3 and payback within 5 years.
Should VoltWay enter? If not, what would make it work? Exhibits: EV count and
charging habits, price and cost per session, competitor volumes, and a fleet
operator offering a fixed contract.
"""

    def data(self) -> dict[str, Any]:
        return {
            "evs_in_city": EVS_IN_CITY,
            "share_using_public_fast_charging": SHARE_USING_PUBLIC_FAST_CHARGING,
            "sessions_per_user_per_year": SESSIONS_PER_USER_PER_YEAR,
            "price_per_session": PRICE_PER_SESSION,
            "variable_cost_per_session": VARIABLE_COST_PER_SESSION,
            "fixed_costs_per_year": FIXED_COSTS_PER_YEAR,
            "capex": CAPEX,
            "year_1_share": YEAR_1_SHARE,
            "voltway_growth": VOLTWAY_GROWTH,
            "market_growth": MARKET_GROWTH,
            "competitor_sessions": COMPETITORS,
            "fleet_anchor": {"sessions": FLEET_ANCHOR_SESSIONS, "price": FLEET_ANCHOR_PRICE},
        }

    def structure(self) -> Node:
        return branch(
            "Should VoltWay enter?",
            "sum",
            branch(
                "Market attractiveness",
                "sum",
                leaf("Size today", hint="How many charging sessions a year?"),
                leaf("Growth", hint="How fast is EV adoption growing?"),
            ),
            branch(
                "Competition",
                "sum",
                leaf("Concentration", hint="Who holds share? HHI?"),
                leaf("Likely response", hint="Will incumbents cut price?"),
            ),
            branch(
                "Economics",
                "sum",
                leaf("Break-even", hint="Sessions and share needed?"),
                leaf("Payback", hint="When is the $2M earned back?"),
            ),
            branch(
                "Capabilities and risk",
                "sum",
                leaf("Sites and grid access"),
                leaf("Ways to de-risk", hint="Partners, phasing, contracts?"),
            ),
        )

    def solve(self) -> Solution:
        market = top_down(
            EVS_IN_CITY,
            [("use public fast charging", SHARE_USING_PUBLIC_FAST_CHARGING)],
            SESSIONS_PER_USER_PER_YEAR,
            PRICE_PER_SESSION,
            customer_label="EVs",
            unit_label="sessions",
        )
        sessions = market.units_per_year
        table = share_table(COMPETITORS)
        concentration = hhi(table.shares())

        be_sessions = break_even_units(
            FIXED_COSTS_PER_YEAR, PRICE_PER_SESSION, VARIABLE_COST_PER_SESSION
        )
        be_share = required_share(be_sessions, sessions)

        projection = project_share(
            YEAR_1_SHARE * sessions, sessions, VOLTWAY_GROWTH, MARKET_GROWTH, HORIZON_YEARS - 1
        )
        retail = projection.company_revenue  # sessions per year, years 1..4
        base = _scenario("Retail only", retail, 0.0)
        fleet = _scenario("Retail + fleet anchor", retail, FLEET_ANCHOR_SESSIONS)

        anchor_margin = FLEET_ANCHOR_PRICE - VARIABLE_COST_PER_SESSION
        base_profit_at_deadline = base.operating_profit[MAX_BREAK_EVEN_YEAR - 1]
        need_for_break_even = -base_profit_at_deadline / anchor_margin
        need_for_payback = (CAPEX / MAX_PAYBACK_YEARS - base.operating_profit[-1]) / anchor_margin
        min_anchor = math.ceil(max(need_for_break_even, need_for_payback, 0.0))

        steps = (
            *market.steps,
            Step("Market HHI (incumbents)", concentration.hhi),
            Step("Leader share (ChargeCo)", table.rows[0].share, "%"),
            Step("Contribution per session", PRICE_PER_SESSION - VARIABLE_COST_PER_SESSION, "$"),
            Step("Break-even sessions per year", be_sessions, "sessions"),
            Step("Break-even share of today's market", be_share, "%"),
            Step("VoltWay share in year 4 (projected)", projection.final_share, "%"),
            *(
                Step(f"Retail only: year {y} operating profit", p, "$")
                for y, p in enumerate(base.operating_profit, start=1)
            ),
            Step("Retail only: payback", base.payback_years or math.inf, "years"),
            *(
                Step(f"With fleet anchor: year {y} operating profit", p, "$")
                for y, p in enumerate(fleet.operating_profit, start=1)
            ),
            Step("With fleet anchor: payback", fleet.payback_years or math.inf, "years"),
            Step("Minimum anchor contract to pass both tests", min_anchor, "sessions"),
        )

        def money(value: float) -> str:
            return fmt_money(value, compact=True)

        def years(value: float | None) -> str:
            return "never" if value is None else f"in {value:.1f} years"

        findings = (
            f"The market is about {fmt_number(sessions)} sessions ({money(market.value_per_year)})"
            f" a year today, growing {fmt_pct(MARKET_GROWTH, 0)} a year.",
            f"It is {concentration.band} (HHI {fmt_number(concentration.hhi)}): ChargeCo "
            f"{fmt_pct(table.rows[0].share, 0)} and GridGo {fmt_pct(table.rows[1].share, 0)}.",
            f"At {money(PRICE_PER_SESSION - VARIABLE_COST_PER_SESSION)} per session, VoltWay must "
            f"sell {fmt_number(be_sessions)} sessions a year to break even: "
            f"{fmt_pct(be_share)} of today's market, close to GridGo's size.",
            f"Retail only, VoltWay breaks even in year {base.break_even_year} and pays back "
            f"{years(base.payback_years)}. That fails the board's rule.",
            f"A fleet contract of {fmt_number(FLEET_ANCHOR_SESSIONS)} sessions at "
            f"{money(FLEET_ANCHOR_PRICE)} brings break-even to year {fleet.break_even_year} and "
            f"pays back {years(fleet.payback_years)}. That passes.",
        )
        recommendation = (
            "Do not enter on retail demand alone. Enter only with an anchor fleet contract of at "
            f"least {fmt_number(min_anchor)} sessions a year at {money(FLEET_ANCHOR_PRICE)} or "
            f"better; the offered {fmt_number(FLEET_ANCHOR_SESSIONS)} clears that with room "
            "to spare. Sign the contract before committing the capex."
        )
        return Solution(
            case_id=self.id,
            title=self.title,
            steps=steps,
            findings=findings,
            recommendation=recommendation,
            answer={
                "market_sessions": sessions,
                "market_value": market.value_per_year,
                "hhi": concentration.hhi,
                "break_even_sessions": be_sessions,
                "break_even_share": be_share,
                "final_share": projection.final_share,
                "base_break_even_year": base.break_even_year,
                "base_payback_years": base.payback_years,
                "fleet_break_even_year": fleet.break_even_year,
                "fleet_payback_years": fleet.payback_years,
                "min_anchor_sessions": float(min_anchor),
                "base_passes": float(base.passes),
                "fleet_passes": float(fleet.passes),
            },
        )
