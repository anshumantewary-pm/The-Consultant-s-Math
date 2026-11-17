"""Pricing math: elasticity, the volume a price move needs, profit-maximising price.

Elasticity is %change in quantity / %change in price, so it is normally
negative: -2 means a 1% price rise loses 2% of volume.
"""

from __future__ import annotations

from casemath.core.errors import ValidationError
from casemath.core.validate import (
    require_fraction,
    require_non_negative,
    require_number,
    require_positive,
)


def arc_elasticity(price_before: float, units_before: float, price_after: float,
                   units_after: float) -> float:  # fmt: skip
    """Midpoint (arc) price elasticity between two observed points.

    Uses average price and quantity as the base so the answer is the same
    whichever point you call "before".
    """
    p0 = require_positive("price_before", price_before)
    q0 = require_non_negative("units_before", units_before)
    p1 = require_positive("price_after", price_after)
    q1 = require_non_negative("units_after", units_after)
    if p0 == p1:
        raise ValidationError("price_before and price_after must differ to measure elasticity")
    if q0 + q1 == 0:
        raise ValidationError("units_before and units_after cannot both be zero")
    pct_q = (q1 - q0) / ((q0 + q1) / 2)
    pct_p = (p1 - p0) / ((p0 + p1) / 2)
    return pct_q / pct_p


def breakeven_volume_change(price_change: float, contribution_margin: float) -> float:
    """Volume change that leaves total contribution unchanged after a price move.

    ``price_change`` is a fraction of the current price (-0.10 = a 10% cut) and
    ``contribution_margin`` is (price - unit cost) / price. The answer is
    -dP / (CM + dP): a 10% cut at a 30% margin needs +50% volume.
    """
    change = require_number("price_change", price_change)
    margin = require_fraction("contribution_margin", contribution_margin)
    if margin + change <= 0:
        raise ValidationError(
            f"a {change:+.0%} price change at a {margin:.0%} contribution margin makes every "
            "unit loss-making; no volume increase can compensate"
        )
    return -change / (margin + change)


def volume_after_price_change(units: float, price_change: float, elasticity: float) -> float:
    """Units after a price move under constant elasticity: Q x (1 + dP) ** e."""
    units = require_non_negative("units", units)
    change = require_number("price_change", price_change)
    elasticity = require_number("elasticity", elasticity)
    if change <= -1:
        raise ValidationError("price_change must be above -100%")
    return float(units * (1 + change) ** elasticity)
