"""Profitability: Profit = (Price - Variable cost per unit) x Units - Fixed costs.

The three tools here map to the three questions a profitability case asks:

* ``profit_statement``     What is profit, and what are the margins?
* ``profit_bridge``        Profit changed. How much came from price, volume,
                           unit cost and fixed cost?
* ``segment_profitability`` Which product / region / channel drives it?
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_non_empty, require_non_negative


@dataclass(frozen=True)
class ProfitStatement(Result):
    price: float
    units: float
    variable_cost_per_unit: float
    fixed_costs: float
    revenue: float
    variable_costs: float
    contribution: float
    contribution_per_unit: float
    contribution_margin: float
    total_costs: float
    profit: float
    profit_margin: float


def profit_statement(
    price: float,
    units: float,
    variable_cost_per_unit: float,
    fixed_costs: float,
) -> ProfitStatement:
    """Build a one-period P&L from unit economics.

    Margins are fractions of revenue and are 0 when revenue is 0.
    """
    price = require_non_negative("price", price)
    units = require_non_negative("units", units)
    variable_cost_per_unit = require_non_negative("variable_cost_per_unit", variable_cost_per_unit)
    fixed_costs = require_non_negative("fixed_costs", fixed_costs)

    revenue = price * units
    variable_costs = variable_cost_per_unit * units
    contribution = revenue - variable_costs
    profit = contribution - fixed_costs
    return ProfitStatement(
        price=price,
        units=units,
        variable_cost_per_unit=variable_cost_per_unit,
        fixed_costs=fixed_costs,
        revenue=revenue,
        variable_costs=variable_costs,
        contribution=contribution,
        contribution_per_unit=price - variable_cost_per_unit,
        contribution_margin=contribution / revenue if revenue else 0.0,
        total_costs=variable_costs + fixed_costs,
        profit=profit,
        profit_margin=profit / revenue if revenue else 0.0,
    )


@dataclass(frozen=True)
class ProfitBridge(Result):
    """How profit moved from ``before`` to ``after``.

    ``price_effect + volume_effect + variable_cost_effect + fixed_cost_effect``
    equals ``profit_change`` exactly (up to float rounding).
    """

    profit_before: float
    profit_after: float
    profit_change: float
    price_effect: float
    volume_effect: float
    variable_cost_effect: float
    fixed_cost_effect: float

    @property
    def effects(self) -> dict[str, float]:
        return {
            "price": self.price_effect,
            "volume": self.volume_effect,
            "variable_cost": self.variable_cost_effect,
            "fixed_cost": self.fixed_cost_effect,
        }

    @property
    def biggest_driver(self) -> str:
        """The effect with the largest absolute size."""
        return max(self.effects, key=lambda key: abs(self.effects[key]))


def profit_bridge(before: ProfitStatement, after: ProfitStatement) -> ProfitBridge:
    """Split the profit change into four effects that add up exactly.

    With profit = (p - v) * q - F:

    * volume effect        = (p0 - v0) * (q1 - q0)   old unit margin on the extra units
    * price effect         = (p1 - p0) * q1          price change on today's units
    * variable cost effect = -(v1 - v0) * q1         unit cost change on today's units
    * fixed cost effect    = -(F1 - F0)
    """
    volume = before.contribution_per_unit * (after.units - before.units)
    price = (after.price - before.price) * after.units
    variable_cost = -(after.variable_cost_per_unit - before.variable_cost_per_unit) * after.units
    fixed = -(after.fixed_costs - before.fixed_costs)
    return ProfitBridge(
        profit_before=before.profit,
        profit_after=after.profit,
        profit_change=after.profit - before.profit,
        price_effect=price,
        volume_effect=volume,
        variable_cost_effect=variable_cost,
        fixed_cost_effect=fixed,
    )


@dataclass(frozen=True)
class Segment:
    """Unit economics for one product line, region or channel."""

    name: str
    price: float
    units: float
    variable_cost_per_unit: float
    fixed_costs: float = 0.0


@dataclass(frozen=True)
class SegmentLine(Result):
    name: str
    statement: ProfitStatement
    share_of_revenue: float
    share_of_profit: float


@dataclass(frozen=True)
class SegmentReport(Result):
    lines: tuple[SegmentLine, ...]
    total_revenue: float
    total_profit: float
    shared_fixed_costs: float

    def line(self, name: str) -> SegmentLine:
        for line in self.lines:
            if line.name == name:
                return line
        raise ValidationError(f"no segment named {name!r}")


def segment_profitability(
    segments: Sequence[Segment], shared_fixed_costs: float = 0.0
) -> SegmentReport:
    """Profit by segment, plus totals after any fixed costs not allocated to a segment.

    Lines are sorted by profit, highest first. Shares are 0 when the total is 0.
    """
    require_non_empty("segments", segments)
    shared_fixed_costs = require_non_negative("shared_fixed_costs", shared_fixed_costs)
    names = [segment.name for segment in segments]
    if len(set(names)) != len(names):
        raise ValidationError("segment names must be unique")

    statements = [
        (s.name, profit_statement(s.price, s.units, s.variable_cost_per_unit, s.fixed_costs))
        for s in segments
    ]
    total_revenue = sum(st.revenue for _, st in statements)
    segment_profit = sum(st.profit for _, st in statements)
    lines = tuple(
        sorted(
            (
                SegmentLine(
                    name=name,
                    statement=st,
                    share_of_revenue=st.revenue / total_revenue if total_revenue else 0.0,
                    share_of_profit=st.profit / segment_profit if segment_profit else 0.0,
                )
                for name, st in statements
            ),
            key=lambda line: line.statement.profit,
            reverse=True,
        )
    )
    return SegmentReport(
        lines=lines,
        total_revenue=total_revenue,
        total_profit=segment_profit - shared_fixed_costs,
        shared_fixed_costs=shared_fixed_costs,
    )
