"""Customer unit economics: lifetime value, acquisition cost payback, LTV/CAC.

All rates are per period (usually per month). Churn is the fraction of
customers lost each period, so expected lifetime is 1 / churn periods.
"""

from __future__ import annotations

from dataclasses import dataclass

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_fraction,
    require_non_negative,
    require_positive,
)

HEALTHY_LTV_TO_CAC = 3.0
"""Rule of thumb: a customer should be worth at least 3x what it cost to win."""


def _churn(churn: float) -> float:
    churn = require_fraction("churn", churn)
    if churn == 0:
        raise ValidationError("churn must be > 0; with no churn a customer lasts forever")
    return churn


def customer_lifetime(churn: float) -> float:
    """Expected periods a customer stays: 1 / churn."""
    return 1 / _churn(churn)


def lifetime_value(
    revenue_per_period: float,
    gross_margin: float,
    churn: float,
    discount_rate: float = 0.0,
) -> float:
    """Gross-margin lifetime value of one customer.

    LTV = margin per period x retention-adjusted lifetime. With a per-period
    ``discount_rate`` d, the lifetime multiple becomes (1 + d) / (d + churn),
    the standard discounted-retention formula; d = 0 gives 1 / churn.
    """
    revenue = require_non_negative("revenue_per_period", revenue_per_period)
    margin = require_fraction("gross_margin", gross_margin)
    churn = _churn(churn)
    discount = require_non_negative("discount_rate", discount_rate)
    multiple = 1 / churn if discount == 0 else (1 + discount) / (discount + churn)
    return revenue * margin * multiple


def cac_payback(cac: float, revenue_per_period: float, gross_margin: float) -> float:
    """Periods of gross margin needed to earn back the cost of acquiring a customer."""
    cac = require_non_negative("cac", cac)
    revenue = require_non_negative("revenue_per_period", revenue_per_period)
    margin = require_fraction("gross_margin", gross_margin)
    if revenue * margin == 0:
        raise ValidationError("revenue_per_period x gross_margin must be > 0 to pay back CAC")
    return cac / (revenue * margin)


@dataclass(frozen=True)
class UnitEconomics(Result):
    revenue_per_period: float
    gross_margin: float
    churn: float
    cac: float
    lifetime_periods: float
    ltv: float
    ltv_to_cac: float
    cac_payback_periods: float
    payback_within_lifetime: bool

    @property
    def healthy(self) -> bool:
        """LTV/CAC at or above the 3x rule of thumb and CAC repaid before churn."""
        return self.ltv_to_cac >= HEALTHY_LTV_TO_CAC and self.payback_within_lifetime


def unit_economics(
    revenue_per_period: float,
    gross_margin: float,
    churn: float,
    cac: float,
    discount_rate: float = 0.0,
) -> UnitEconomics:
    """LTV, LTV/CAC and CAC payback in one result."""
    cac = require_positive("cac", cac)
    ltv = lifetime_value(revenue_per_period, gross_margin, churn, discount_rate)
    payback = cac_payback(cac, revenue_per_period, gross_margin)
    lifetime = customer_lifetime(churn)
    return UnitEconomics(
        revenue_per_period=float(revenue_per_period),
        gross_margin=float(gross_margin),
        churn=float(churn),
        cac=cac,
        lifetime_periods=lifetime,
        ltv=ltv,
        ltv_to_cac=ltv / cac,
        cac_payback_periods=payback,
        payback_within_lifetime=payback <= lifetime,
    )
