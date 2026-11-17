"""Time value of money: NPV, IRR, payback on a discounted basis, perpetuities.

Cash-flow lists are indexed by period: ``flows[0]`` happens today (usually the
negative investment), ``flows[1]`` one period from now, and so on.
"""

from __future__ import annotations

from casemath.core.errors import ValidationError
from casemath.core.validate import (
    require_count,
    require_non_negative,
    require_number,
    require_numbers,
    require_rate,
)


def discount_factor(rate: float, period: float) -> float:
    """Value today of $1 received ``period`` periods from now: 1 / (1 + r) ** t."""
    rate = require_rate("rate", rate)
    period = require_non_negative("period", period)
    return float(1 / (1 + rate) ** period)


def present_value(amount: float, rate: float, period: float) -> float:
    """``amount`` received at ``period``, discounted to today."""
    return require_number("amount", amount) * discount_factor(rate, period)


def npv(rate: float, flows: list[float] | tuple[float, ...]) -> float:
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
