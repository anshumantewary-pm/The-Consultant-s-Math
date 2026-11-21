"""Borrower in, lending decision out.

``decide(borrower)`` spreads the financials, restates them pro forma for the
new facility, rates the borrower, works out LGD, capital and RAROC, runs every
policy check, and then decides:

* **Decline** if any hard stop fails (KYC, grade outside appetite, DSCR below 1.0x).
* **Refer** to the credit committee if there are three or more policy
  exceptions or the grade is 8.
* **Approve with conditions** if there are one or two exceptions.
* **Approve** otherwise.

It also proposes the structure (covenants with headroom, the margin that would
meet the hurdle, the amount that fits policy), the approver, conditions
precedent, key risks with mitigants, and the early-warning triggers that
``collections.monitor`` later tests the live facility against.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from casemath.core.result import Result
from casemath.credit.analysis import (
    CollateralCover,
    DebtCapacity,
    Returns,
    Spread,
    debt_capacity,
    exposure_at_default,
    loss_given_default,
    pro_forma,
    returns,
    spread,
    spread_history,
)
from casemath.credit.model import BankPolicy, Borrower, Industry, get_industry
from casemath.credit.rating import Rating, rate

APPROVE = "Approve"
APPROVE_WITH_CONDITIONS = "Approve with conditions"
REFER = "Refer to credit committee"
DECLINE = "Decline"


@dataclass(frozen=True)
class Check(Result):
    key: str
    label: str
    actual: str
    limit: str
    passed: bool
    hard: bool  # a failed hard check is a decline; a failed soft check is an exception


@dataclass(frozen=True)
class Covenants(Result):
    max_leverage: float
    min_icr: float
    min_dscr: float
    reporting: str  # "quarterly" or "semi-annually"


@dataclass(frozen=True)
class RiskItem(Result):
    risk: str
    mitigant: str


@dataclass(frozen=True)
class CreditDecision(Result):
    borrower: Borrower
    industry: Industry
    history: tuple[Spread, ...]
    pro_forma: Spread
    rating: Rating
    capacity: DebtCapacity
    cover: CollateralCover
    returns: Returns
    checks: tuple[Check, ...]
    decision: str
    reasons: tuple[str, ...]
    approver: str
    covenants: Covenants
    recommended_amount: float
    recommended_margin: float
    conditions: tuple[str, ...]
    risks: tuple[RiskItem, ...]
    monitoring_triggers: tuple[str, ...]
    total_exposure: float

    @property
    def exceptions(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if not c.passed and not c.hard)

    @property
    def hard_stops(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if not c.passed and c.hard)


def _x(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _m(value: float) -> str:
    return f"{value / 1e6:,.1f}M"


def _floor_to(value: float, step: float) -> float:
    return math.floor(value / step) * step


def _ceil_to(value: float, step: float) -> float:
    return math.ceil(value / step) * step


def _checks(
    b: Borrower,
    industry: Industry,
    pf: Spread,
    rating: Rating,
    cover: CollateralCover,
    ret: Returns,
    exposure: float,
    policy: BankPolicy,
) -> tuple[Check, ...]:
    g = rating.final.grade
    checks = [
        Check(
            "kyc",
            "KYC, sanctions and adverse media",
            ", ".join(b.kyc_flags) or "clear",
            "no open flags",
            not b.kyc_flags,
            True,
        ),
        Check(
            "appetite",
            "Risk grade within appetite",
            f"grade {g} ({rating.final.equivalent})",
            f"grade <= {policy.worst_grade}",
            g <= policy.worst_grade,
            True,
        ),
        Check(
            "dscr_hard",
            "Pro forma DSCR above 1.0x",
            _x(pf.dscr),
            f">= {policy.hard_min_dscr:.2f}x",
            pf.dscr is None or pf.dscr >= policy.hard_min_dscr,
            True,
        ),
        Check(
            "leverage",
            "Leverage within industry ceiling",
            _x(pf.leverage),
            f"<= {industry.max_leverage:.2f}x",
            pf.leverage is not None and pf.leverage <= industry.max_leverage,
            False,
        ),
        Check(
            "dscr",
            "Pro forma DSCR",
            _x(pf.dscr),
            f">= {policy.min_dscr:.2f}x",
            pf.dscr is None or pf.dscr >= policy.min_dscr,
            False,
        ),
        Check(
            "icr",
            "Pro forma interest cover",
            _x(pf.icr),
            f">= {policy.min_icr:.2f}x",
            pf.icr is not None and pf.icr >= policy.min_icr,
            False,
        ),
        Check(
            "payback",
            "Debt payback from free cash flow",
            "n/a" if pf.payback_years is None else f"{pf.payback_years:.1f} yrs",
            f"<= {policy.max_payback_years:g} yrs",
            pf.net_debt <= 0
            or (pf.payback_years is not None and pf.payback_years <= policy.max_payback_years),
            False,
        ),
        Check(
            "tenor",
            "Tenor within limit for grade",
            f"{b.request.tenor_years:g} yrs",
            f"<= {policy.tenor_limit(g):g} yrs",
            b.request.tenor_years <= policy.tenor_limit(g),
            False,
        ),
        Check(
            "hold",
            "Single-name hold limit",
            _m(exposure),
            f"<= {_m(policy.hold_limit(g))}",
            exposure <= policy.hold_limit(g),
            False,
        ),
        Check(
            "raroc",
            "RAROC above hurdle",
            f"{ret.raroc * 100:.1f}%",
            f">= {policy.hurdle_raroc * 100:.1f}%",
            ret.raroc >= policy.hurdle_raroc,
            False,
        ),
    ]
    if g >= policy.secured_coverage_from_grade:
        checks.append(
            Check(
                "security",
                "Collateral cover (sub-investment grade)",
                _x(cover.coverage),
                ">= 1.00x",
                cover.coverage >= 1.0,
                False,
            )
        )
    return tuple(checks)


def _approver(exposure: float, grade: int, exceptions: int, policy: BankPolicy) -> str:
    tiers = policy.authorities
    index = next(
        (i for i, (limit, worst, _) in enumerate(tiers) if exposure <= limit and grade <= worst),
        len(tiers) - 1,
    )
    if exceptions:
        index = min(index + 1, len(tiers) - 1)  # exceptions go one level up
    return tiers[index][2]


def _covenants(pf: Spread, industry: Industry, grade: int, policy: BankPolicy) -> Covenants:
    """Set covenants about 25% looser than pro forma, but never looser than policy."""
    leverage = pf.leverage if pf.leverage is not None else industry.max_leverage
    max_leverage = min(_ceil_to(leverage * 1.25, 0.25), industry.max_leverage + 0.5)
    icr = pf.icr if pf.icr is not None else policy.min_icr
    min_icr = max(_floor_to(icr * 0.75, 0.25), 1.5)
    dscr = pf.dscr if pf.dscr is not None else policy.min_dscr
    min_dscr = max(_floor_to(dscr * 0.8, 0.05), 1.05)
    return Covenants(
        max_leverage=max_leverage,
        min_icr=min_icr,
        min_dscr=min_dscr,
        reporting="quarterly" if grade >= 5 else "semi-annually",
    )


_MITIGANTS = {
    "leverage": "Amortising structure, leverage covenant with step-downs, no further debt",
    "icr": "Interest cover covenant; consider hedging floating-rate exposure",
    "dscr": "Cash sweep of excess cash flow; DSCR covenant tested quarterly",
    "margin": "Margin trend in quarterly MI; benchmark against peers at annual review",
    "size": "Concentration limits; guarantees from operating subsidiaries",
    "liquidity": "Minimum liquidity covenant; committed revolver for working capital",
    "management": "Key-person clause; board-level reporting; sponsor engagement",
    "market": "Customer concentration reporting; change-of-business clause",
    "industry": "Shorter tenor; sector-stress scenario at each review",
    "reporting": "Audited accounts within 120 days; information undertakings",
    "track_record": "Tighter reporting and a shorter first review cycle",
}


def _risks(rating: Rating, b: Borrower, cover: CollateralCover) -> tuple[RiskItem, ...]:
    items = [
        RiskItem(
            f"{f.label} scores low: {f.display}, {f.score:.0f}/100 on the scorecard",
            _MITIGANTS[f.key],
        )
        for f in rating.weakest
        if f.score < 70
    ]
    if b.request.amortisation == 0 and b.request.facility_type == "term_loan":
        items.append(
            RiskItem(
                "Bullet repayment creates refinancing risk at maturity",
                "Refinancing plan tested at annual review; consider 10-20% annual amortisation",
            )
        )
    if cover.coverage < 1.0 and b.request.seniority == "senior_secured":
        items.append(
            RiskItem(
                f"Collateral covers {cover.coverage:.2f}x of exposure after haircuts",
                "Additional security, guarantees, or a lower amount",
            )
        )
    return tuple(items)


def _conditions(
    b: Borrower, rating: Rating, cov: Covenants, exceptions: tuple[Check, ...]
) -> tuple[str, ...]:
    items = [
        "Satisfactory KYC refresh and sanctions screening of borrower, owners and guarantors",
        "Executed facility agreement and legal opinion on capacity and enforceability",
        f"Financial covenants: Debt/EBITDA <= {cov.max_leverage:.2f}x, "
        f"interest cover >= {cov.min_icr:.2f}x, DSCR >= {cov.min_dscr:.2f}x, "
        f"tested {cov.reporting}",
        f"Management accounts {cov.reporting}; audited accounts within 120 days of year end",
    ]
    if b.request.seniority == "senior_secured" and b.collateral:
        items.append("Perfected first-ranking security over the collateral listed, with insurance")
    if rating.final.grade >= 7:
        items.append("Watchlist on day one; first review after 6 months")
    for e in exceptions:
        items.append(f"Exception approved: {e.label} ({e.actual} vs {e.limit})")
    return tuple(items)


def _triggers(cov: Covenants, rating: Rating) -> tuple[str, ...]:
    return (
        f"Leverage within 10% of the {cov.max_leverage:.2f}x covenant",
        f"Interest cover within 10% of the {cov.min_icr:.2f}x covenant",
        "Any payment more than 5 days late, or a returned payment",
        "Revolver utilisation above 90% or up more than 30 points in a quarter",
        "Revenue down more than 10% or EBITDA down more than 20% year on year",
        f"Internal grade {rating.final.grade + 2} or worse (two notches below origination)",
        "Late financial reporting, auditor qualification or management change",
    )


def decide(borrower: Borrower, policy: BankPolicy | None = None) -> CreditDecision:
    policy = policy or BankPolicy()
    industry = get_industry(borrower.industry)
    history = spread_history(borrower.financials)
    pf_financials = pro_forma(borrower.latest, borrower.request)
    pf = spread(pf_financials, borrower.financials[-2] if len(borrower.financials) > 1 else None)
    rating = rate(pf, history, industry, borrower.qualitative, borrower.kyc_flags)
    ead = exposure_at_default(borrower.request, policy)
    cover = loss_given_default(borrower.collateral, ead, borrower.request.seniority)
    ret = returns(borrower.request, rating.final.pd, cover.lgd, policy)
    capacity = debt_capacity(borrower.latest, borrower.request, industry.max_leverage, policy)
    exposure = borrower.existing_exposure + borrower.request.amount
    checks = _checks(borrower, industry, pf, rating, cover, ret, exposure, policy)
    hard = tuple(c for c in checks if not c.passed and c.hard)
    soft = tuple(c for c in checks if not c.passed and not c.hard)

    if hard:
        decision = DECLINE
        reasons = tuple(f"Hard stop: {c.label} ({c.actual} vs {c.limit})" for c in hard)
    elif len(soft) >= 3 or rating.final.grade >= policy.worst_grade:
        decision = REFER
        reasons = tuple(f"Exception: {c.label} ({c.actual} vs {c.limit})" for c in soft) or (
            f"Grade {rating.final.grade} needs committee sign-off",
        )
    elif soft:
        decision = APPROVE_WITH_CONDITIONS
        reasons = tuple(f"Exception: {c.label} ({c.actual} vs {c.limit})" for c in soft)
    else:
        decision = APPROVE
        reasons = ("All policy checks pass",)

    covenants = _covenants(pf, industry, rating.final.grade, policy)
    drawn_share = 1.0
    if borrower.request.facility_type == "revolver":
        drawn_share = borrower.request.expected_utilisation or 1.0
    fits_policy = (capacity.max_additional + borrower.request.refinances) / drawn_share
    hold_room = max(0.0, policy.hold_limit(rating.final.grade) - borrower.existing_exposure)
    recommended = max(0.0, min(borrower.request.amount, fits_policy, hold_room))
    approver = (
        "n/a (declined)"
        if decision == DECLINE
        else _approver(exposure, rating.final.grade, len(soft), policy)
    )
    return CreditDecision(
        borrower=borrower,
        industry=industry,
        history=history,
        pro_forma=pf,
        rating=rating,
        capacity=capacity,
        cover=cover,
        returns=ret,
        checks=checks,
        decision=decision,
        reasons=reasons,
        approver=approver,
        covenants=covenants,
        recommended_amount=recommended,
        recommended_margin=max(borrower.request.margin, ret.required_margin or 0.0),
        conditions=_conditions(borrower, rating, covenants, soft),
        risks=_risks(rating, borrower, cover),
        monitoring_triggers=_triggers(covenants, rating),
        total_exposure=exposure,
    )
