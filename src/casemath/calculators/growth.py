"""Compound growth helpers used by market share and sizing."""

from __future__ import annotations

from casemath.core.validate import require_non_negative, require_positive, require_rate


def cagr(start_value: float, end_value: float, years: float) -> float:
    """Compound annual growth rate: (end / start) ** (1 / years) - 1."""
    start_value = require_positive("start_value", start_value)
    end_value = require_non_negative("end_value", end_value)
    years = require_positive("years", years)
    return float((end_value / start_value) ** (1 / years) - 1)


def grow(value: float, rate: float, years: float) -> float:
    """``value`` compounded at ``rate`` for ``years``."""
    value = require_non_negative("value", value)
    rate = require_rate("rate", rate)
    years = require_non_negative("years", years)
    return float(value * (1 + rate) ** years)


def rule_of_72(rate: float) -> float:
    """Quick mental estimate of years to double. ``rate`` is a fraction (0.08 = 8%)."""
    rate = require_positive("rate", rate)
    return 72 / (rate * 100)
