"""Inputs to CreditDecision: the borrower file, the facility request and the bank's policy.

Everything here is plain data. ``borrower_from_dict`` and ``facility_from_dict``
turn a JSON document (the shape in ``examples/credit/``) into these dataclasses
and reject anything that does not make sense, naming the field that is wrong.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from casemath.core.errors import UnknownNameError, ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_fraction,
    require_non_negative,
    require_number,
    require_positive,
)

# ---------------------------------------------------------------- reference data


@dataclass(frozen=True)
class Industry(Result):
    """Indicative wholesale-credit view of a sector. Risk 1 is lowest, 5 highest."""

    key: str
    name: str
    risk: int
    max_leverage: float  # policy ceiling on debt / EBITDA
    cyclical: bool


INDUSTRIES: dict[str, Industry] = {
    i.key: i
    for i in (
        Industry("utilities", "Utilities / regulated infrastructure", 1, 6.0, False),
        Industry("healthcare", "Healthcare services and pharma", 2, 4.5, False),
        Industry("technology", "Technology and software", 2, 4.5, False),
        Industry("business_services", "Business services", 2, 4.0, False),
        Industry("consumer_staples", "Consumer staples / FMCG", 2, 4.0, False),
        Industry("manufacturing", "Industrial manufacturing", 3, 3.5, True),
        Industry("logistics", "Transport and logistics", 3, 3.5, True),
        Industry("retail", "Retail", 4, 3.0, True),
        Industry("construction", "Construction and engineering", 4, 3.0, True),
        Industry("energy", "Oil, gas and mining", 4, 3.0, True),
        Industry("real_estate", "Commercial real estate (operating)", 4, 8.0, True),
    )
}


def get_industry(key: str) -> Industry:
    try:
        return INDUSTRIES[key]
    except KeyError:
        known = ", ".join(INDUSTRIES)
        raise UnknownNameError(f"unknown industry {key!r}; choose one of: {known}") from None


# Haircut applied to the market value of each collateral type to get what the
# bank expects to realise in enforcement. Indicative, not a regulatory table.
COLLATERAL_HAIRCUTS: dict[str, float] = {
    "cash": 0.0,
    "securities": 0.15,
    "receivables": 0.25,
    "real_estate": 0.30,
    "equipment": 0.45,
    "inventory": 0.50,
    "intangibles": 0.80,
}

SENIORITIES = ("senior_secured", "senior_unsecured", "subordinated")
FACILITY_TYPES = ("term_loan", "revolver")


@dataclass(frozen=True)
class BankPolicy(Result):
    """The bank's credit appetite. Every threshold the decision uses lives here."""

    min_dscr: float = 1.25
    hard_min_dscr: float = 1.0
    min_icr: float = 3.0
    max_payback_years: float = 7.0
    worst_grade: int = 8  # grade 9 (CCC) and worse is outside appetite
    hurdle_raroc: float = 0.12
    capital_ratio: float = 0.105  # CET1 + buffers held against RWA
    tax_rate: float = 0.25
    funding_spread: float = 0.004  # bank's cost of funds above the base rate
    cost_to_serve: float = 0.003  # operating cost as a fraction of EAD per year
    revolver_ccf: float = 0.75  # credit conversion factor on undrawn commitments
    secured_coverage_from_grade: int = 6  # sub-investment-grade must be fully secured
    # (worst grade, max years) pairs: a grade must be <= the first value to get that tenor.
    max_tenor: tuple[tuple[int, float], ...] = ((3, 7.0), (5, 5.0), (6, 5.0), (7, 4.0), (8, 3.0))
    # (worst grade, max single-name exposure) pairs.
    hold_limits: tuple[tuple[int, float], ...] = (
        (3, 500e6),
        (5, 250e6),
        (6, 100e6),
        (7, 50e6),
        (8, 20e6),
    )
    # (max exposure, worst grade, approver), checked in order; the last tier catches all.
    authorities: tuple[tuple[float, int, str], ...] = (
        (25e6, 5, "Regional Credit Officer"),
        (100e6, 6, "Senior Credit Officer"),
        (250e6, 7, "Chief Credit Officer"),
        (float("inf"), 10, "Credit Committee"),
    )

    def tenor_limit(self, grade: int) -> float:
        return next((t for g, t in self.max_tenor if grade <= g), 0.0)

    def hold_limit(self, grade: int) -> float:
        return next((amount for g, amount in self.hold_limits if grade <= g), 0.0)


# ---------------------------------------------------------------- borrower file


@dataclass(frozen=True)
class Financials(Result):
    """One reporting period, in a single currency. Debt is gross, before cash."""

    period: str
    revenue: float
    ebitda: float
    interest_expense: float
    total_debt: float
    cash: float = 0.0
    capex: float = 0.0
    taxes: float = 0.0
    scheduled_principal: float = 0.0  # existing debt amortisation due next year
    current_assets: float | None = None
    current_liabilities: float | None = None
    equity: float | None = None


@dataclass(frozen=True)
class Collateral(Result):
    type: str
    value: float
    description: str = ""

    @property
    def haircut(self) -> float:
        return COLLATERAL_HAIRCUTS[self.type]

    @property
    def recoverable(self) -> float:
        return self.value * (1 - self.haircut)


@dataclass(frozen=True)
class Qualitative(Result):
    """Analyst scores, 1 (weak) to 5 (strong)."""

    management: int = 3
    market_position: int = 3
    financial_reporting: int = 3
    years_in_business: float = 10.0
    notes: str = ""


@dataclass(frozen=True)
class FacilityRequest(Result):
    amount: float
    tenor_years: float
    facility_type: str = "term_loan"
    seniority: str = "senior_secured"
    base_rate: float = 0.045
    margin: float = 0.025  # spread over the base rate charged to the borrower
    upfront_fee: float = 0.0  # fraction of the amount, paid once
    commitment_fee: float = 0.0  # fraction of the undrawn amount, per year
    amortisation: float = 0.0  # fraction of the amount repaid each year; 0 is a bullet
    expected_utilisation: float = 1.0  # revolvers: average drawn share
    refinances: float = 0.0  # existing debt this facility repays
    purpose: str = ""

    @property
    def all_in_rate(self) -> float:
        return self.base_rate + self.margin


@dataclass(frozen=True)
class Borrower(Result):
    name: str
    industry: str
    financials: tuple[Financials, ...]  # oldest first; the last one is the latest
    request: FacilityRequest
    collateral: tuple[Collateral, ...] = ()
    qualitative: Qualitative = field(default_factory=Qualitative)
    country: str = ""
    group: str = ""
    existing_exposure: float = 0.0  # other limits the bank already has to this name
    kyc_flags: tuple[str, ...] = ()  # sanctions, adverse media, unresolved KYC: hard stops
    description: str = ""

    @property
    def latest(self) -> Financials:
        return self.financials[-1]


# ---------------------------------------------------------------- parsing


def _section(data: Mapping[str, Any], key: str, default: object = None) -> Any:
    value = data.get(key, default)
    if value is None:
        raise ValidationError(f"missing {key!r}")
    return value


def _check_keys(where: str, data: object, allowed: set[str]) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ValidationError(f"{where} must be an object, got {type(data).__name__}")
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValidationError(f"{where}: unknown field(s) {', '.join(unknown)}")
    return data


def _text(where: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{where} must be text, got {type(value).__name__}")
    return value


def _score(where: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ValidationError(f"{where} must be a whole number from 1 to 5, got {value!r}")
    return value


def parse_financials(data: object, where: str = "financials") -> Financials:
    fields_ = set(Financials.__dataclass_fields__)
    d = _check_keys(where, data, fields_)
    optional = ("current_assets", "current_liabilities", "equity")
    kwargs: dict[str, Any] = {"period": _text(f"{where}.period", _section(d, "period"))}
    kwargs["revenue"] = require_positive(f"{where}.revenue", _section(d, "revenue"))
    kwargs["ebitda"] = require_number(f"{where}.ebitda", _section(d, "ebitda"))
    for key in ("interest_expense", "total_debt"):
        kwargs[key] = require_non_negative(f"{where}.{key}", _section(d, key))
    for key in ("cash", "capex", "taxes", "scheduled_principal"):
        if key in d:
            kwargs[key] = require_non_negative(f"{where}.{key}", d[key])
    for key in optional:
        if d.get(key) is not None:
            check = require_number if key == "equity" else require_non_negative
            kwargs[key] = check(f"{where}.{key}", d[key])
    return Financials(**kwargs)


def parse_financials_list(data: object) -> tuple[Financials, ...]:
    if not isinstance(data, list) or not data:
        raise ValidationError("financials must be a non-empty list of periods, oldest first")
    return tuple(parse_financials(p, f"financials[{i}]") for i, p in enumerate(data))


def parse_collateral(data: object) -> tuple[Collateral, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValidationError("collateral must be a list")
    items = []
    for i, raw in enumerate(data):
        where = f"collateral[{i}]"
        d = _check_keys(where, raw, {"type", "value", "description"})
        kind = _text(f"{where}.type", _section(d, "type"))
        if kind not in COLLATERAL_HAIRCUTS:
            known = ", ".join(COLLATERAL_HAIRCUTS)
            raise ValidationError(f"{where}.type {kind!r} is not one of: {known}")
        value = require_non_negative(f"{where}.value", _section(d, "value"))
        items.append(
            Collateral(kind, value, _text(f"{where}.description", d.get("description", "")))
        )
    return tuple(items)


def parse_qualitative(data: object) -> Qualitative:
    if data is None:
        return Qualitative()
    d = _check_keys("qualitative", data, set(Qualitative.__dataclass_fields__))
    kwargs: dict[str, Any] = {}
    for key in ("management", "market_position", "financial_reporting"):
        if key in d:
            kwargs[key] = _score(f"qualitative.{key}", d[key])
    if "years_in_business" in d:
        kwargs["years_in_business"] = require_non_negative(
            "qualitative.years_in_business", d["years_in_business"]
        )
    if "notes" in d:
        kwargs["notes"] = _text("qualitative.notes", d["notes"])
    return Qualitative(**kwargs)


def parse_request(data: object) -> FacilityRequest:
    d = _check_keys("request", data, set(FacilityRequest.__dataclass_fields__))
    kwargs: dict[str, Any] = {
        "amount": require_positive("request.amount", _section(d, "amount")),
        "tenor_years": require_positive("request.tenor_years", _section(d, "tenor_years")),
    }
    kind = _text("request.facility_type", d.get("facility_type", "term_loan"))
    if kind not in FACILITY_TYPES:
        raise ValidationError(f"request.facility_type must be one of: {', '.join(FACILITY_TYPES)}")
    seniority = _text("request.seniority", d.get("seniority", "senior_secured"))
    if seniority not in SENIORITIES:
        raise ValidationError(f"request.seniority must be one of: {', '.join(SENIORITIES)}")
    kwargs.update(facility_type=kind, seniority=seniority)
    for key in ("base_rate", "margin", "upfront_fee", "commitment_fee"):
        if key in d:
            kwargs[key] = require_non_negative(f"request.{key}", d[key])
    for key in ("amortisation", "expected_utilisation"):
        if key in d:
            kwargs[key] = require_fraction(f"request.{key}", d[key])
    if "refinances" in d:
        kwargs["refinances"] = require_non_negative("request.refinances", d["refinances"])
    if "purpose" in d:
        kwargs["purpose"] = _text("request.purpose", d["purpose"])
    return FacilityRequest(**kwargs)


_BORROWER_KEYS = {
    "name",
    "industry",
    "financials",
    "request",
    "collateral",
    "qualitative",
    "country",
    "group",
    "existing_exposure",
    "kyc_flags",
    "description",
}


def borrower_from_dict(data: object) -> Borrower:
    """Build and validate a ``Borrower`` from a JSON-shaped mapping."""
    d = _check_keys("borrower", data, _BORROWER_KEYS)
    industry = _text("industry", _section(d, "industry"))
    get_industry(industry)
    financials = parse_financials_list(_section(d, "financials"))
    request = parse_request(_section(d, "request"))
    if request.refinances > financials[-1].total_debt:
        raise ValidationError("request.refinances cannot exceed the latest total_debt")
    flags = d.get("kyc_flags", [])
    if not isinstance(flags, list):
        raise ValidationError("kyc_flags must be a list of text")
    return Borrower(
        name=_text("name", _section(d, "name")),
        industry=industry,
        financials=financials,
        request=request,
        collateral=parse_collateral(d.get("collateral")),
        qualitative=parse_qualitative(d.get("qualitative")),
        country=_text("country", d.get("country", "")),
        group=_text("group", d.get("group", "")),
        existing_exposure=require_non_negative("existing_exposure", d.get("existing_exposure", 0)),
        kyc_flags=tuple(_text(f"kyc_flags[{i}]", f) for i, f in enumerate(flags)),
        description=_text("description", d.get("description", "")),
    )
