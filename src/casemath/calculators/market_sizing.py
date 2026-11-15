"""Market sizing, top-down and bottom-up, with every step recorded.

Top-down: start from a population and narrow it with filters
          (e.g. 1.4B people x 35% urban x 20% target income ...).
Bottom-up: add up segments, each count x units per year x price.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from casemath.core.result import Result, Step
from casemath.core.validate import (
    require_fraction,
    require_non_empty,
    require_non_negative,
)


@dataclass(frozen=True)
class MarketSize(Result):
    steps: tuple[Step, ...]
    customers: float
    units_per_year: float
    value_per_year: float


def top_down(
    population: float,
    filters: Sequence[tuple[str, float]],
    units_per_customer: float,
    price_per_unit: float,
    customer_label: str = "people",
    unit_label: str = "units",
) -> MarketSize:
    """Narrow a starting population by each ``(label, fraction)`` filter in turn.

    ``customer_label`` and ``unit_label`` only change how the steps read
    (e.g. "EVs" and "sessions").
    """
    population = require_non_negative("population", population)
    units_per_customer = require_non_negative("units_per_customer", units_per_customer)
    price_per_unit = require_non_negative("price_per_unit", price_per_unit)

    steps = [Step("Starting population", population, customer_label)]
    customers = population
    for label, fraction in filters:
        customers *= require_fraction(f"filter {label!r}", fraction)
        steps.append(Step(f"x {fraction:.0%} {label}", customers, customer_label))

    units = customers * units_per_customer
    value = units * price_per_unit
    steps.append(
        Step(f"x {units_per_customer:g} {unit_label} per customer per year", units, unit_label)
    )
    steps.append(Step(f"x {price_per_unit:g} per {unit_label.rstrip('s')}", value, "$"))
    return MarketSize(
        steps=tuple(steps), customers=customers, units_per_year=units, value_per_year=value
    )


@dataclass(frozen=True)
class SizingSegment:
    name: str
    count: float
    units_per_year: float
    price_per_unit: float


def bottom_up(segments: Sequence[SizingSegment]) -> MarketSize:
    """Sum of count x units x price over segments (e.g. small / mid / large hospitals)."""
    require_non_empty("segments", segments)
    steps = []
    customers = units = value = 0.0
    for s in segments:
        count = require_non_negative(f"{s.name}.count", s.count)
        per = require_non_negative(f"{s.name}.units_per_year", s.units_per_year)
        price = require_non_negative(f"{s.name}.price_per_unit", s.price_per_unit)
        segment_value = count * per * price
        steps.append(Step(f"{s.name}: {count:g} x {per:g} x {price:g}", segment_value, "$"))
        customers += count
        units += count * per
        value += segment_value
    steps.append(Step("Total", value, "$"))
    return MarketSize(
        steps=tuple(steps), customers=customers, units_per_year=units, value_per_year=value
    )
