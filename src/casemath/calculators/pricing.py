"""Pricing: will a price change pay for itself?

The question every pricing case asks is whether the extra margin per unit
beats the units lost (or gained). Three tools:

* ``price_elasticity``          How sensitive is volume to price? (midpoint / arc method)
* ``break_even_volume_change``  How much volume can a price change lose before
                                contribution falls? ``-dP / (CM + dP)``
* ``price_change_impact``       Apply an elasticity and compare contribution and profit.

Plus ``profit_maximising_price``: the markup rule ``P = VC x e / (1 + e)`` for
constant-elasticity demand, which only exists when demand is elastic (e < -1);
``optimal_price_linear``: the best price on a straight-line demand curve fitted
through two observations; and ``volume_after_price_change`` under constant elasticity.
"""

from __future__ import annotations

from dataclasses import dataclass

from casemath.calculators.profitability import ProfitStatement, profit_statement
from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_non_negative,
    require_number,
    require_positive,
    require_rate,
)


def price_elasticity(
    price_before: float, units_before: float, price_after: float, units_after: float
) -> float:
    """Arc elasticity: % change in units / % change in price, both on midpoints.

    Midpoints make the answer the same whichever period you call "before".
    Usually negative: a price rise loses volume.
    """
    price_before = require_positive("price_before", price_before)
    price_after = require_positive("price_after", price_after)
    units_before = require_non_negative("units_before", units_before)
    units_after = require_non_negative("units_after", units_after)
    if price_before == price_after:
        raise ValidationError("price_before and price_after must differ to measure elasticity")
    if units_before + units_after == 0:
        raise ValidationError("units_before and units_after must not both be 0")
    pct_units = (units_after - units_before) / ((units_after + units_before) / 2)
    pct_price = (price_after - price_before) / ((price_after + price_before) / 2)
    return pct_units / pct_price


def break_even_volume_change(
    price: float, variable_cost_per_unit: float, price_change: float
) -> float:
    """Volume change (fraction) at which a price change leaves contribution flat.

    ``price_change`` is a fraction: 0.10 = +10%. For a price rise the result is
    negative: the most volume you can lose. For a cut it is positive: the
    volume you must gain. Formula: -dP / (CM% + dP).
    """
    price = require_positive("price", price)
    variable_cost_per_unit = require_non_negative("variable_cost_per_unit", variable_cost_per_unit)
    price_change = require_rate("price_change", price_change)
    new_price = price * (1 + price_change)
    if new_price <= variable_cost_per_unit:
        raise ValidationError(
            f"new price ({new_price:g}) must be above variable_cost_per_unit "
            f"({variable_cost_per_unit:g}); no volume makes up for a negative margin"
        )
    margin = (price - variable_cost_per_unit) / price
    return -price_change / (margin + price_change)


@dataclass(frozen=True)
class PriceChange(Result):
    price_change: float
    elasticity: float
    expected_volume_change: float
    break_even_volume_change: float
    before: ProfitStatement
    after: ProfitStatement
    contribution_change: float
    profit_change: float

    @property
    def pays_off(self) -> bool:
        """True if profit goes up (or stays flat)."""
        return self.profit_change >= 0


def price_change_impact(
    price: float,
    units: float,
    variable_cost_per_unit: float,
    new_price: float,
    elasticity: float,
    fixed_costs: float = 0.0,
) -> PriceChange:
    """Apply a linear elasticity (%dQ = e x %dP) to a price change.

    Linear is the case-interview convention and is fine for moderate moves;
    the further ``new_price`` is from the tested range, the less it holds.
    """
    price = require_positive("price", price)
    new_price = require_positive("new_price", new_price)
    elasticity = require_number("elasticity", elasticity)
    before = profit_statement(price, units, variable_cost_per_unit, fixed_costs)
    change = new_price / price - 1
    volume_change = elasticity * change
    if volume_change < -1:
        raise ValidationError(
            f"elasticity {elasticity:g} with a {change:+.1%} price change implies volume "
            f"falls {-volume_change:.0%}; below zero units, so the linear model no longer applies"
        )
    after = profit_statement(new_price, units * (1 + volume_change), variable_cost_per_unit,
                             fixed_costs)  # fmt: skip
    return PriceChange(
        price_change=change,
        elasticity=elasticity,
        expected_volume_change=volume_change,
        break_even_volume_change=break_even_volume_change(price, variable_cost_per_unit, change),
        before=before,
        after=after,
        contribution_change=after.contribution - before.contribution,
        profit_change=after.profit - before.profit,
    )


def profit_maximising_price(variable_cost_per_unit: float, elasticity: float) -> float:
    """Markup rule for constant-elasticity demand: P = VC x e / (1 + e).

    Only defined for elastic demand (e < -1). With inelastic demand, raising the
    price always adds profit in this model, so there is no interior optimum.
    """
    variable_cost_per_unit = require_positive("variable_cost_per_unit", variable_cost_per_unit)
    elasticity = require_number("elasticity", elasticity)
    if elasticity >= -1:
        raise ValidationError(
            f"elasticity must be < -1 (elastic demand), got {elasticity:g}; with inelastic "
            "demand a higher price always earns more, so there is no profit-maximising price"
        )
    return variable_cost_per_unit * elasticity / (1 + elasticity)


def volume_after_price_change(units: float, price_change: float, elasticity: float) -> float:
    """Units after a price move under constant elasticity: Q x (1 + dP) ** e."""
    units = require_non_negative("units", units)
    change = require_number("price_change", price_change)
    elasticity = require_number("elasticity", elasticity)
    if change <= -1:
        raise ValidationError("price_change must be above -100%")
    return float(units * (1 + change) ** elasticity)


@dataclass(frozen=True)
class PriceOptimum(Result):
    intercept: float  # units demanded at a price of zero
    slope: float  # units lost per $1 of price
    unit_cost: float
    price: float
    units: float
    contribution: float
    choke_price: float  # price at which demand reaches zero


def optimal_price_linear(
    price_a: float, units_a: float, price_b: float, units_b: float, unit_cost: float
) -> PriceOptimum:
    """Fit straight-line demand Q = a - bP through two points and maximise (P - c) x Q.

    Setting the derivative to zero gives P* = (a / b + c) / 2: halfway between
    unit cost and the choke price.
    """
    pa = require_non_negative("price_a", price_a)
    qa = require_non_negative("units_a", units_a)
    pb = require_non_negative("price_b", price_b)
    qb = require_non_negative("units_b", units_b)
    cost = require_non_negative("unit_cost", unit_cost)
    if pa == pb:
        raise ValidationError("price_a and price_b must differ to fit a demand curve")
    slope = -(qb - qa) / (pb - pa)
    if slope <= 0:
        raise ValidationError(
            "demand must fall as price rises (units_b vs units_a looks flat or upward)"
        )
    intercept = qa + slope * pa
    choke = intercept / slope
    if cost >= choke:
        raise ValidationError(
            f"unit_cost ({cost:g}) is at or above the choke price ({choke:.2f}); "
            "no price earns a positive margin"
        )
    price = (choke + cost) / 2
    units = intercept - slope * price
    return PriceOptimum(
        intercept=intercept,
        slope=slope,
        unit_cost=cost,
        price=price,
        units=units,
        contribution=(price - cost) * units,
        choke_price=choke,
    )
