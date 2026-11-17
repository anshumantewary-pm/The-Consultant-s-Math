"""M&A synergies: are they worth the premium we are about to pay?

* ``SynergyItem``       One synergy at full run-rate. Cost synergies count in full;
                        revenue synergies count at their profit margin and can be
                        haircut for delivery risk.
* ``synergy_schedule``  Phase synergies in, subtract one-off integration costs,
                        and find the year the integration pays back.
* ``synergy_value``     Capitalise run-rate synergies at a multiple, net of one-off costs.
                        This is the most a buyer can pay above standalone value.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_fraction,
    require_non_empty,
    require_non_negative,
)

SynergyKind = Literal["cost", "revenue"]


@dataclass(frozen=True)
class SynergyItem:
    """A synergy at full run-rate, per year.

    For ``kind="revenue"``, ``run_rate`` is extra *revenue*; ``margin`` turns it
    into profit. ``probability`` haircuts any synergy for delivery risk.
    """

    name: str
    run_rate: float
    kind: SynergyKind = "cost"
    margin: float = 1.0
    probability: float = 1.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("synergy name must not be blank")
        if self.kind not in ("cost", "revenue"):
            raise ValidationError(f"synergy kind must be 'cost' or 'revenue', got {self.kind!r}")
        require_non_negative(f"{self.name}: run_rate", self.run_rate)
        require_fraction(f"{self.name}: margin", self.margin)
        require_fraction(f"{self.name}: probability", self.probability)
        if self.kind == "cost" and self.margin != 1.0:
            raise ValidationError(f"{self.name}: margin applies to revenue synergies only")

    @property
    def profit_run_rate(self) -> float:
        """Run-rate profit impact after margin and risk haircut."""
        return self.run_rate * self.margin * self.probability


@dataclass(frozen=True)
class SynergyYear(Result):
    year: int
    phase_in: float
    synergies: float
    integration_costs: float
    net: float
    cumulative: float


@dataclass(frozen=True)
class SynergySchedule(Result):
    run_rate_cost: float
    run_rate_revenue: float
    run_rate_total: float
    integration_costs: float
    years: tuple[SynergyYear, ...]
    payback_year: int | None  # first year cumulative net >= 0; None = not within the plan


def synergy_schedule(
    items: Sequence[SynergyItem],
    phase_in: Sequence[float],
    integration_costs: Sequence[float] = (),
) -> SynergySchedule:
    """Year-by-year synergies and one-off costs.

    ``phase_in[i]`` is the fraction of run-rate achieved in year ``i + 1``.
    ``integration_costs[i]`` is the one-off spend in that year; it may be shorter
    than ``phase_in`` (missing years cost nothing) but not longer.
    """
    require_non_empty("items", items)
    require_non_empty("phase_in", phase_in)
    phases = [require_fraction(f"phase_in[{i}]", p) for i, p in enumerate(phase_in)]
    costs = [require_non_negative(f"integration_costs[{i}]", c)
             for i, c in enumerate(integration_costs)]  # fmt: skip
    if len(costs) > len(phases):
        raise ValidationError(
            f"integration_costs has {len(costs)} years but phase_in only {len(phases)}"
        )
    names = [item.name for item in items]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ValidationError(f"duplicate synergy names: {', '.join(duplicates)}")

    cost_rr = math.fsum(i.profit_run_rate for i in items if i.kind == "cost")
    revenue_rr = math.fsum(i.profit_run_rate for i in items if i.kind == "revenue")
    total_rr = cost_rr + revenue_rr
    costs += [0.0] * (len(phases) - len(costs))

    years: list[SynergyYear] = []
    cumulative = 0.0
    for year, (phase, cost) in enumerate(zip(phases, costs, strict=True), start=1):
        realised = total_rr * phase
        net = realised - cost
        cumulative += net
        years.append(SynergyYear(year, phase, realised, cost, net, cumulative))
    payback = next((y.year for y in years if y.cumulative >= 0 and y.synergies > 0), None)
    return SynergySchedule(
        run_rate_cost=cost_rr,
        run_rate_revenue=revenue_rr,
        run_rate_total=total_rr,
        integration_costs=math.fsum(costs),
        years=tuple(years),
        payback_year=payback,
    )


def synergy_value(run_rate: float, multiple: float, one_off_costs: float = 0.0) -> float:
    """Value of synergies: run-rate profit x valuation multiple - one-off costs.

    Compare this with the premium over standalone value: a premium above it
    hands the synergies (and more) to the seller.
    """
    run_rate = require_non_negative("run_rate", run_rate)
    multiple = require_non_negative("multiple", multiple)
    one_off_costs = require_non_negative("one_off_costs", one_off_costs)
    return run_rate * multiple - one_off_costs


def acquisition_premium(offer_value: float, standalone_value: float) -> float:
    """Premium as a fraction of standalone (unaffected) value."""
    offer_value = require_non_negative("offer_value", offer_value)
    standalone_value = require_non_negative("standalone_value", standalone_value)
    if standalone_value == 0:
        raise ValidationError("standalone_value must be > 0")
    return offer_value / standalone_value - 1
