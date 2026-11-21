"""Spreading, pro forma debt capacity, loss parameters, regulatory capital and RAROC.

Every function is pure and every number it returns can be traced to a formula
in this file, which is the point: a credit memo built from these figures needs
no "the model said so".
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

from casemath.core.result import Result
from casemath.credit.model import BankPolicy, Collateral, FacilityRequest, Financials

_N = NormalDist()

# Loss given default on the unsecured part of the exposure, by seniority
# (Basel foundation-IRB style: 40% senior unsecured, 75% subordinated).
UNSECURED_LGD = {"senior_secured": 0.40, "senior_unsecured": 0.40, "subordinated": 0.75}
SECURED_LGD_FLOOR = 0.20  # Basel III F-IRB secured LGD for receivables and real estate
PD_FLOOR = 0.0005  # Basel III corporate PD floor (5 bp)


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None


@dataclass(frozen=True)
class Spread(Result):
    """Standard ratios for one period (or the pro forma year)."""

    period: str
    revenue: float
    ebitda: float
    ebitda_margin: float
    revenue_growth: float | None
    total_debt: float
    net_debt: float
    interest: float
    debt_service: float
    cash_flow_available: float  # EBITDA - capex - taxes: cash available to service debt
    free_cash_flow: float  # after interest
    leverage: float | None  # total debt / EBITDA; None when EBITDA <= 0
    net_leverage: float | None
    icr: float | None  # EBITDA / interest
    dscr: float | None  # cash flow available / (interest + scheduled principal)
    payback_years: float | None  # net debt / free cash flow
    current_ratio: float | None
    gearing: float | None  # debt / equity; None when equity is missing or not positive
    equity: float | None


def spread(f: Financials, prior: Financials | None = None) -> Spread:
    cfads = f.ebitda - f.capex - f.taxes
    debt_service = f.interest_expense + f.scheduled_principal
    fcf = cfads - f.interest_expense
    net_debt = f.total_debt - f.cash
    gearing = None
    if f.equity is not None and f.equity > 0:
        gearing = f.total_debt / f.equity
    current = None
    if f.current_assets is not None and f.current_liabilities is not None:
        current = _ratio(f.current_assets, f.current_liabilities)
    return Spread(
        period=f.period,
        revenue=f.revenue,
        ebitda=f.ebitda,
        ebitda_margin=f.ebitda / f.revenue,
        revenue_growth=(f.revenue / prior.revenue - 1) if prior else None,
        total_debt=f.total_debt,
        net_debt=net_debt,
        interest=f.interest_expense,
        debt_service=debt_service,
        cash_flow_available=cfads,
        free_cash_flow=fcf,
        leverage=_ratio(f.total_debt, f.ebitda),
        net_leverage=_ratio(max(net_debt, 0.0), f.ebitda),
        icr=_ratio(f.ebitda, f.interest_expense) if f.ebitda > 0 else None,
        dscr=_ratio(cfads, debt_service) if debt_service > 0 else None,
        payback_years=_ratio(max(net_debt, 0.0), fcf) if fcf > 0 else None,
        current_ratio=current,
        gearing=gearing,
        equity=f.equity,
    )


def spread_history(financials: Sequence[Financials]) -> tuple[Spread, ...]:
    return tuple(spread(f, financials[i - 1] if i > 0 else None) for i, f in enumerate(financials))


def pro_forma(latest: Financials, request: FacilityRequest) -> Financials:
    """The latest year restated as if the new facility were in place all year.

    Refinanced debt goes away together with its share of interest and
    amortisation; the new facility adds its drawn amount, interest at the
    all-in rate and its own scheduled amortisation.
    """
    kept = 1.0
    if latest.total_debt > 0:
        kept = (latest.total_debt - request.refinances) / latest.total_debt
    drawn = request.amount
    if request.facility_type == "revolver":
        drawn = request.amount * request.expected_utilisation
    return Financials(
        period=f"{latest.period} pro forma",
        revenue=latest.revenue,
        ebitda=latest.ebitda,
        interest_expense=latest.interest_expense * kept + drawn * request.all_in_rate,
        total_debt=latest.total_debt - request.refinances + drawn,
        cash=latest.cash,
        capex=latest.capex,
        taxes=latest.taxes,
        scheduled_principal=latest.scheduled_principal * kept
        + request.amount * request.amortisation,
        current_assets=latest.current_assets,
        current_liabilities=latest.current_liabilities,
        equity=latest.equity,
    )


@dataclass(frozen=True)
class DebtCapacity(Result):
    """How much more senior debt the borrower can carry within policy."""

    by_leverage: float  # extra debt until debt / EBITDA hits the industry ceiling
    by_dscr: float  # extra debt (at the requested terms) until DSCR hits the minimum
    max_additional: float
    requested_additional: float  # new money: amount drawn less debt refinanced


def debt_capacity(
    latest: Financials, request: FacilityRequest, max_leverage: float, policy: BankPolicy
) -> DebtCapacity:
    by_leverage = max(0.0, max_leverage * latest.ebitda - latest.total_debt)
    cfads = latest.ebitda - latest.capex - latest.taxes
    headroom = cfads / policy.min_dscr - latest.interest_expense - latest.scheduled_principal
    service_per_unit = request.all_in_rate + request.amortisation
    by_dscr = max(0.0, headroom / service_per_unit) if service_per_unit > 0 else math.inf
    drawn = request.amount
    if request.facility_type == "revolver":
        drawn = request.amount * request.expected_utilisation
    return DebtCapacity(
        by_leverage=by_leverage,
        by_dscr=by_dscr,
        max_additional=min(by_leverage, by_dscr),
        requested_additional=drawn - request.refinances,
    )


@dataclass(frozen=True)
class CollateralCover(Result):
    market_value: float
    recoverable: float
    coverage: float  # recoverable / EAD
    lgd: float


def exposure_at_default(request: FacilityRequest, policy: BankPolicy) -> float:
    if request.facility_type == "term_loan":
        return request.amount
    drawn = request.amount * request.expected_utilisation
    return drawn + policy.revolver_ccf * (request.amount - drawn)


def loss_given_default(
    collateral: Sequence[Collateral], ead: float, seniority: str
) -> CollateralCover:
    """Secured part loses the floor; the rest loses the unsecured LGD for its rank.

    Collateral counts only for senior secured lending: a subordinated or
    unsecured lender has no first claim on it.
    """
    market = sum(c.value for c in collateral)
    recoverable = sum(c.recoverable for c in collateral) if seniority == "senior_secured" else 0.0
    coverage = recoverable / ead if ead > 0 else 0.0
    secured = min(1.0, coverage)
    lgd = secured * SECURED_LGD_FLOOR + (1 - secured) * UNSECURED_LGD[seniority]
    return CollateralCover(market, recoverable, coverage, lgd)


def irb_capital(pd: float, lgd: float, ead: float, maturity: float) -> tuple[float, float]:
    """Basel IRB corporate formula: capital requirement K and risk-weighted assets.

    ``maturity`` is clamped to Basel's 1 to 5 years. Returns ``(K, RWA)`` where
    ``RWA = K * 12.5 * EAD``.
    """
    pd = min(max(pd, PD_FLOOR), 0.9999)
    m = min(max(maturity, 1.0), 5.0)
    weight = (1 - math.exp(-50 * pd)) / (1 - math.exp(-50))
    r = 0.12 * weight + 0.24 * (1 - weight)
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    conditional = _N.cdf((_N.inv_cdf(pd) + math.sqrt(r) * _N.inv_cdf(0.999)) / math.sqrt(1 - r))
    k = (lgd * conditional - pd * lgd) * (1 + (m - 2.5) * b) / (1 - 1.5 * b)
    return k, k * 12.5 * ead


@dataclass(frozen=True)
class Returns(Result):
    ead: float
    expected_loss: float
    rwa: float
    capital: float
    net_interest_income: float
    fee_income: float
    operating_cost: float
    profit_after_tax: float
    raroc: float
    required_margin: float | None  # margin that exactly hits the hurdle; None if nothing drawn


def returns(request: FacilityRequest, pd: float, lgd: float, policy: BankPolicy) -> Returns:
    """One representative year of the facility's risk-adjusted return on capital."""
    ead = exposure_at_default(request, policy)
    drawn = request.amount
    if request.facility_type == "revolver":
        drawn = request.amount * request.expected_utilisation
    expected_loss = max(pd, PD_FLOOR) * lgd * ead
    _, rwa = irb_capital(pd, lgd, ead, request.tenor_years)
    capital = rwa * policy.capital_ratio
    spread_earned = request.margin - policy.funding_spread
    nii = drawn * spread_earned
    fees = request.amount * request.upfront_fee / request.tenor_years
    fees += (request.amount - drawn) * request.commitment_fee
    opex = ead * policy.cost_to_serve
    profit = (nii + fees - opex - expected_loss) * (1 - policy.tax_rate)
    raroc = profit / capital if capital > 0 else math.inf
    # Solve hurdle * capital = (drawn * (m - fs) + fees - opex - EL) * (1 - t) for m.
    needed_pre_tax = policy.hurdle_raroc * capital / (1 - policy.tax_rate)
    shortfall = needed_pre_tax - fees + opex + expected_loss
    required = max(shortfall / drawn + policy.funding_spread, 0.0) if drawn > 0 else None
    return Returns(
        ead=ead,
        expected_loss=expected_loss,
        rwa=rwa,
        capital=capital,
        net_interest_income=nii,
        fee_income=fees,
        operating_cost=opex,
        profit_after_tax=profit,
        raroc=raroc,
        required_margin=required,
    )
