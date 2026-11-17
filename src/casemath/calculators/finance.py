"""Time value of money: NPV, IRR, payback on a discounted basis, perpetuities.

Cash-flow lists are indexed by period: ``flows[0]`` happens today (usually the
negative investment), ``flows[1]`` one period from now, and so on.
"""

from __future__ import annotations

from dataclasses import dataclass

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_count,
    require_non_negative,
    require_number,
    require_numbers,
    require_rate,
)

Flows = list[float] | tuple[float, ...]
"""A period-indexed cash-flow series; ``flows[0]`` is today."""


def discount_factor(rate: float, period: float) -> float:
    """Value today of $1 received ``period`` periods from now: 1 / (1 + r) ** t."""
    rate = require_rate("rate", rate)
    period = require_non_negative("period", period)
    return float(1 / (1 + rate) ** period)


def present_value(amount: float, rate: float, period: float) -> float:
    """``amount`` received at ``period``, discounted to today."""
    return require_number("amount", amount) * discount_factor(rate, period)


def npv(rate: float, flows: Flows) -> float:
    """Net present value of a cash-flow series. ``flows[0]`` is not discounted."""
    rate = require_rate("rate", rate)
    values = require_numbers("flows", flows)
    return sum(v / (1 + rate) ** t for t, v in enumerate(values))


def annuity_pv(payment: float, rate: float, periods: int) -> float:
    """Present value of ``payment`` received at the end of each of ``periods`` periods."""
    payment = require_number("payment", payment)
    rate = require_rate("rate", rate)
    periods = require_count("periods", periods, minimum=0)
    if rate == 0:
        return payment * periods
    return float(payment * (1 - (1 + rate) ** -periods) / rate)


def perpetuity(payment: float, rate: float, growth: float = 0.0) -> float:
    """Value one period before the first ``payment`` of a stream growing at ``growth``.

    Gordon growth: payment / (rate - growth). Requires rate > growth.
    """
    payment = require_number("payment", payment)
    rate = require_rate("rate", rate)
    growth = require_rate("growth", growth)
    if rate <= growth:
        raise ValidationError(
            f"rate ({rate:g}) must be above growth ({growth:g}); "
            "otherwise the stream is worth infinitely much"
        )
    return payment / (rate - growth)


_IRR_GRID = (-0.99, -0.9, -0.75, -0.5, -0.25, 0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1, 2, 5, 10, 100)


def irr(flows: Flows, tolerance: float = 1e-10) -> float:
    """Internal rate of return: the rate at which NPV is zero.

    Scans a grid of rates for the first sign change in NPV, then bisects, so it
    never diverges the way Newton's method can. When the flows change sign more
    than once there may be several IRRs; this returns the lowest one in
    (-99%, 10000%).
    """
    values = require_numbers("flows", flows)
    if not (any(v > 0 for v in values) and any(v < 0 for v in values)):
        raise ValidationError(
            "flows need at least one negative and one positive value to have an IRR"
        )
    grid = (*_IRR_GRID, 10.0, 100.0)
    previous_rate, previous_npv = grid[0], npv(grid[0], values)
    for rate in grid[1:]:
        current = npv(rate, values)
        if previous_npv == 0:
            return previous_rate
        if (previous_npv < 0) != (current < 0):
            low, high, f_low = previous_rate, rate, previous_npv
            while high - low > tolerance:
                mid = (low + high) / 2
                f_mid = npv(mid, values)
                if (f_mid < 0) == (f_low < 0):
                    low, f_low = mid, f_mid
                else:
                    high = mid
            return (low + high) / 2
        previous_rate, previous_npv = rate, current
    raise ValidationError("no IRR found between -99% and 10,000%")


def _payback(values: tuple[float, ...]) -> float | None:
    """Fractional period where the cumulative sum first turns non-negative, or None."""
    cumulative = values[0]
    if cumulative >= 0:
        return 0.0
    for period, flow in enumerate(values[1:], start=1):
        if cumulative + flow >= 0:
            # Assume the flow arrives evenly through the period.
            return period - 1 + (-cumulative / flow)
        cumulative += flow
    return None


def simple_payback(flows: Flows) -> float | None:
    """Periods until undiscounted cumulative cash turns non-negative; None if never."""
    return _payback(require_numbers("flows", flows))


def discounted_payback(rate: float, flows: Flows) -> float | None:
    """Like ``simple_payback`` but on discounted flows; None if never paid back."""
    rate = require_rate("rate", rate)
    values = require_numbers("flows", flows)
    return _payback(tuple(v / (1 + rate) ** t for t, v in enumerate(values)))


@dataclass(frozen=True)
class InvestmentAppraisal(Result):
    rate: float
    flows: tuple[float, ...]
    npv: float
    irr: float | None
    profitability_index: float | None
    simple_payback: float | None
    discounted_payback: float | None

    @property
    def accept(self) -> bool:
        """The NPV rule: invest when NPV is positive."""
        return self.npv > 0


def investment_appraisal(rate: float, flows: Flows) -> InvestmentAppraisal:
    """NPV, IRR, profitability index and both payback measures in one call.

    The profitability index is PV of future flows / initial outlay, defined only
    when ``flows[0]`` is an outlay (negative).
    """
    rate = require_rate("rate", rate)
    values = require_numbers("flows", flows)
    value = npv(rate, values)
    try:
        rate_of_return: float | None = irr(values)
    except ValidationError:
        rate_of_return = None
    index = None if values[0] >= 0 else (value - values[0]) / -values[0]
    return InvestmentAppraisal(
        rate=rate,
        flows=values,
        npv=value,
        irr=rate_of_return,
        profitability_index=index,
        simple_payback=simple_payback(values),
        discounted_payback=discounted_payback(rate, values),
    )
