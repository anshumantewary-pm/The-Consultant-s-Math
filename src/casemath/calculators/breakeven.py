"""Break-even: the volume (or price, or time) at which profit is zero.

Core identity: break-even units = Fixed costs / (Price - Variable cost per unit).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_non_negative,
    require_number,
    require_positive,
)


def _unit_margin(price: float, variable_cost_per_unit: float) -> float:
    price = require_non_negative("price", price)
    variable_cost_per_unit = require_non_negative("variable_cost_per_unit", variable_cost_per_unit)
    margin = price - variable_cost_per_unit
    if margin <= 0:
        raise ValidationError(
            f"price ({price:g}) must be above variable_cost_per_unit "
            f"({variable_cost_per_unit:g}); every unit loses money, so there is no break-even"
        )
    return margin


def break_even_units(fixed_costs: float, price: float, variable_cost_per_unit: float) -> float:
    """Units to sell for profit = 0. Fractional; round up for whole units."""
    fixed_costs = require_non_negative("fixed_costs", fixed_costs)
    return fixed_costs / _unit_margin(price, variable_cost_per_unit)


def break_even_revenue(fixed_costs: float, price: float, variable_cost_per_unit: float) -> float:
    """Revenue at break-even = Fixed costs / contribution margin %."""
    return break_even_units(fixed_costs, price, variable_cost_per_unit) * price


def units_for_target_profit(
    target_profit: float, fixed_costs: float, price: float, variable_cost_per_unit: float
) -> float:
    """Units needed to earn ``target_profit`` (may be negative for an acceptable loss)."""
    target_profit = require_number("target_profit", target_profit)
    fixed_costs = require_non_negative("fixed_costs", fixed_costs)
    return max(0.0, (fixed_costs + target_profit) / _unit_margin(price, variable_cost_per_unit))


def break_even_price(fixed_costs: float, units: float, variable_cost_per_unit: float) -> float:
    """Lowest price that covers all costs at a given volume."""
    fixed_costs = require_non_negative("fixed_costs", fixed_costs)
    units = require_positive("units", units)
    variable_cost_per_unit = require_non_negative("variable_cost_per_unit", variable_cost_per_unit)
    return variable_cost_per_unit + fixed_costs / units


def margin_of_safety(expected_units: float, break_even: float) -> float:
    """How far expected sales can fall before a loss, as a fraction of expected sales.

    Negative means the plan is already below break-even.
    """
    expected_units = require_positive("expected_units", expected_units)
    break_even = require_non_negative("break_even", break_even)
    return (expected_units - break_even) / expected_units


def payback_period(investment: float, cash_flow_per_period: float) -> float:
    """Periods to earn back an up-front investment from a steady cash flow."""
    investment = require_non_negative("investment", investment)
    cash_flow_per_period = require_number("cash_flow_per_period", cash_flow_per_period)
    if cash_flow_per_period <= 0:
        raise ValidationError(
            "cash_flow_per_period must be > 0; the investment is never paid back"
        )
    return investment / cash_flow_per_period


@dataclass(frozen=True)
class BreakEvenAnalysis(Result):
    fixed_costs: float
    price: float
    variable_cost_per_unit: float
    contribution_per_unit: float
    contribution_margin: float
    break_even_units: float
    break_even_units_whole: int
    break_even_revenue: float
    expected_units: float | None
    margin_of_safety: float | None


def break_even_analysis(
    fixed_costs: float,
    price: float,
    variable_cost_per_unit: float,
    expected_units: float | None = None,
) -> BreakEvenAnalysis:
    """Everything in one call; adds margin of safety when ``expected_units`` is given."""
    units = break_even_units(fixed_costs, price, variable_cost_per_unit)
    margin = price - variable_cost_per_unit
    safety = None if expected_units is None else margin_of_safety(expected_units, units)
    return BreakEvenAnalysis(
        fixed_costs=float(fixed_costs),
        price=float(price),
        variable_cost_per_unit=float(variable_cost_per_unit),
        contribution_per_unit=margin,
        contribution_margin=margin / price,
        break_even_units=units,
        break_even_units_whole=math.ceil(units - 1e-9),
        break_even_revenue=units * price,
        expected_units=None if expected_units is None else float(expected_units),
        margin_of_safety=safety,
    )
