"""After the decision: monitor the live facility and drive it through collections.

``monitor(status)`` takes a facility on the books (its limit, outstanding,
covenants, collateral, the latest financials, days past due, utilisation and
any credit events) and returns:

* covenant tests with headroom,
* early-warning signals ranked by severity,
* a re-rated grade and the migration since origination,
* the regulatory buckets: US classification (Pass to Loss), IFRS 9 stage and
  RBI SMA/NPA bucket,
* the expected credit loss to provide for,
* a strategy (monitor, watchlist, remediate, restructure, recover) with a
  dated action plan, and the recovery value if the bank enforces.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_fraction, require_non_negative, require_positive
from casemath.credit.analysis import Spread, loss_given_default, spread_history
from casemath.credit.model import (
    SENIORITIES,
    Collateral,
    Financials,
    Qualitative,
    _check_keys,
    _section,
    _text,
    get_industry,
    parse_collateral,
    parse_financials_list,
    parse_qualitative,
)
from casemath.credit.rating import Grade, Rating, grade, rate

SEVERITIES = ("low", "medium", "high", "critical")

# Credit events an RM or a data feed can report, with their severity.
EVENTS: dict[str, tuple[str, str]] = {
    "late_reporting": ("medium", "Financial reporting delivered late"),
    "auditor_qualification": ("high", "Auditor qualified the accounts"),
    "management_change": ("medium", "Unplanned CEO or CFO change"),
    "key_customer_loss": ("high", "Loss of a key customer or contract"),
    "rating_downgrade": ("high", "External rating downgraded"),
    "payment_returned": ("high", "Payment returned or cheque bounced"),
    "tax_arrears": ("high", "Tax or statutory dues in arrears"),
    "legal_action": ("critical", "Creditor legal action or winding-up petition"),
    "cross_default": ("critical", "Default on debt with another lender"),
    "fraud_suspected": ("critical", "Suspected fraud or misrepresentation"),
}

STRATEGIES = ("monitor", "watchlist", "remediate", "restructure", "recover")


@dataclass(frozen=True)
class FacilityStatus(Result):
    borrower: str
    industry: str
    limit: float
    outstanding: float
    rate: float
    remaining_years: float
    origination_grade: int
    financials: tuple[Financials, ...]
    covenants: Mapping[str, float] = field(default_factory=dict)
    seniority: str = "senior_secured"
    collateral: tuple[Collateral, ...] = ()
    days_past_due: int = 0
    utilisation_history: tuple[float, ...] = ()  # drawn / limit, oldest first
    events: tuple[str, ...] = ()
    qualitative: Qualitative = field(default_factory=Qualitative)


@dataclass(frozen=True)
class CovenantTest(Result):
    name: str
    threshold: float
    actual: float | None
    headroom: float | None  # fraction of the threshold still available; negative is a breach
    breached: bool


@dataclass(frozen=True)
class Signal(Result):
    severity: str
    signal: str
    detail: str


@dataclass(frozen=True)
class Action(Result):
    day: int
    owner: str
    action: str


@dataclass(frozen=True)
class Monitoring(Result):
    status: FacilityStatus
    spread: Spread
    covenant_tests: tuple[CovenantTest, ...]
    signals: tuple[Signal, ...]
    rating: Rating
    current_grade: Grade
    migration: int  # notches worse since origination (negative is an upgrade)
    classification: str
    ifrs9_stage: int
    sma_bucket: str
    ecl: float
    lgd: float
    recovery_value: float
    strategy: str
    actions: tuple[Action, ...]


_COVENANTS = {
    "max_leverage": ("Debt / EBITDA", "max"),
    "min_icr": ("Interest cover", "min"),
    "min_dscr": ("DSCR", "min"),
}


def _test_covenants(s: Spread, covenants: Mapping[str, float]) -> tuple[CovenantTest, ...]:
    actuals = {"max_leverage": s.leverage, "min_icr": s.icr, "min_dscr": s.dscr}
    tests = []
    for key, threshold in covenants.items():
        label, kind = _COVENANTS[key]
        actual = actuals[key]
        if actual is None:
            # No EBITDA (leverage, cover) means the test fails; no debt service means DSCR passes.
            breached = key != "min_dscr" or s.cash_flow_available <= 0
            headroom = None
        elif kind == "max":
            headroom = (threshold - actual) / threshold
            breached = actual > threshold
        else:
            headroom = (actual - threshold) / threshold
            breached = actual < threshold
        tests.append(CovenantTest(label, threshold, actual, headroom, breached))
    return tuple(tests)


def _signals(
    st: FacilityStatus, history: tuple[Spread, ...], tests: tuple[CovenantTest, ...], migration: int
) -> list[Signal]:
    out: list[Signal] = []
    dpd = st.days_past_due
    if dpd > 90:
        out.append(Signal("critical", "Payment default", f"{dpd} days past due"))
    elif dpd > 60:
        out.append(Signal("critical", "Severe arrears", f"{dpd} days past due"))
    elif dpd > 30:
        out.append(Signal("high", "Arrears", f"{dpd} days past due"))
    elif dpd > 0:
        out.append(Signal("medium", "Payment late", f"{dpd} days past due"))
    for t in tests:
        if t.breached:
            out.append(
                Signal(
                    "high",
                    f"{t.name} covenant breached",
                    f"actual {_x(t.actual)} vs {t.threshold:.2f}x",
                )
            )
        elif t.headroom is not None and t.headroom < 0.10:
            out.append(
                Signal(
                    "medium",
                    f"{t.name} covenant headroom thin",
                    f"{t.headroom * 100:.0f}% headroom",
                )
            )
    if len(history) >= 2:
        prev, last = history[-2], history[-1]
        rev = last.revenue / prev.revenue - 1
        if rev < -0.10:
            out.append(Signal("medium", "Revenue decline", f"{rev * 100:.0f}% year on year"))
        if prev.ebitda > 0:
            change = last.ebitda / prev.ebitda - 1
            if change < -0.20:
                out.append(Signal("high", "EBITDA decline", f"{change * 100:.0f}% year on year"))
    latest = history[-1]
    if latest.current_ratio is not None and latest.current_ratio < 1.0:
        out.append(Signal("medium", "Tight liquidity", f"current ratio {_x(latest.current_ratio)}"))
    u = st.utilisation_history
    if u:
        if u[-1] > 0.90:
            out.append(Signal("medium", "Facility near fully drawn", f"{u[-1] * 100:.0f}% used"))
        if len(u) >= 2 and u[-1] - u[0] > 0.30:
            out.append(
                Signal(
                    "medium", "Utilisation rising fast", f"{u[0] * 100:.0f}% to {u[-1] * 100:.0f}%"
                )
            )
    if migration >= 3:
        out.append(Signal("critical", "Rating migration", f"{migration} notches since origination"))
    elif migration >= 2:
        out.append(Signal("high", "Rating migration", f"{migration} notches since origination"))
    for e in st.events:
        severity, label = EVENTS[e]
        out.append(Signal(severity, label, e))
    out.sort(key=lambda s: -SEVERITIES.index(s.severity))
    return out


def _x(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _count(signals: list[Signal], severity: str) -> int:
    return sum(1 for s in signals if s.severity == severity)


def _classify(dpd: int, grade_: int, signals: list[Signal], coverage: float) -> str:
    """US interagency classification, driven by arrears first and then by credit quality."""
    if dpd > 180 and coverage < 0.25:
        return "Loss"
    if dpd > 90:
        return "Doubtful" if coverage < 1.0 else "Substandard"
    if dpd > 30 or grade_ >= 9 or _count(signals, "critical"):
        return "Substandard"
    if grade_ >= 7 or _count(signals, "high"):
        return "Special Mention"
    return "Pass"


def _stage(dpd: int, grade_: int, migration: int, classification: str) -> int:
    if dpd > 90 or grade_ >= 10 or classification in ("Doubtful", "Loss"):
        return 3
    if dpd > 30 or migration >= 3 or classification in ("Special Mention", "Substandard"):
        return 2
    return 1


def _sma(dpd: int) -> str:
    if dpd > 90:
        return "NPA"
    if dpd > 60:
        return "SMA-2"
    if dpd > 30:
        return "SMA-1"
    if dpd > 0:
        return "SMA-0"
    return "Standard"


def _strategy(classification: str, signals: list[Signal], tests: tuple[CovenantTest, ...]) -> str:
    if classification in ("Doubtful", "Loss"):
        return "recover"
    if classification == "Substandard":
        return "restructure"
    if any(t.breached for t in tests):
        return "remediate"
    if signals:
        return "watchlist"
    return "monitor"


_PLAYBOOK: dict[str, tuple[tuple[int, str, str], ...]] = {
    "monitor": (
        (0, "Relationship manager", "No action; keep annual review on schedule"),
        (90, "Credit analyst", "Test covenants on next quarterly accounts"),
    ),
    "watchlist": (
        (0, "Credit officer", "Add to watchlist; move to monthly management information"),
        (14, "Relationship manager", "Meet management on the signals and get a written plan"),
        (30, "Credit analyst", "Re-forecast cash flow with a downside case; re-rate"),
        (90, "Credit committee", "Watchlist review: exit, hold or escalate"),
    ),
    "remediate": (
        (0, "Credit officer", "Reservation-of-rights letter on the covenant breach"),
        (7, "Relationship manager", "Request equity cure or sponsor support proposal"),
        (21, "Credit officer", "Waiver and covenant reset, priced: fee plus margin step-up"),
        (30, "Legal", "Amendment: tighter reporting, cash sweep, no further debt"),
        (90, "Credit analyst", "Re-test on next quarter; escalate if not cured"),
    ),
    "restructure": (
        (0, "Special assets", "Transfer to special assets; freeze undrawn commitments"),
        (7, "Special assets", "Appoint independent business review (IBR) at borrower cost"),
        (14, "Legal", "Standstill agreement with all lenders; information rights"),
        (30, "Valuer", "Independent revaluation of collateral"),
        (
            45,
            "Special assets",
            "Term sheet: amend and extend, amortisation holiday, collateral top-up, sponsor equity",
        ),
        (90, "Credit committee", "Approve restructuring or move to recovery"),
    ),
    "recover": (
        (0, "Special assets", "Default notice and acceleration; cancel undrawn limits"),
        (7, "Legal", "Enforce security: appoint receiver or start insolvency process"),
        (30, "Valuer", "Distressed valuation of collateral; compare enforce vs NPL sale"),
        (60, "Special assets", "Pursue guarantors; negotiate consensual sale if better"),
        (180, "Finance", "Write off the unrecovered balance once realisation is final"),
    ),
}


def monitor(st: FacilityStatus) -> Monitoring:
    industry = get_industry(st.industry)
    history = spread_history(st.financials)
    current = history[-1]
    tests = _test_covenants(current, st.covenants)
    rating = rate(current, history, industry, st.qualitative)
    model_grade = rating.final.grade
    if st.days_past_due > 90:
        model_grade = 10
    elif any(t.breached for t in tests):
        model_grade = max(model_grade, 7)
    migration = model_grade - st.origination_grade
    signals = _signals(st, history, tests, migration)
    cover = loss_given_default(st.collateral, st.outstanding, st.seniority)
    classification = _classify(st.days_past_due, model_grade, signals, cover.coverage)
    stage = _stage(st.days_past_due, model_grade, migration, classification)
    current_grade = grade(model_grade)
    pd = current_grade.pd
    if stage == 2:
        pd = 1 - (1 - pd) ** max(st.remaining_years, 1.0)  # lifetime PD
    elif stage == 3:
        pd = 1.0
    ecl = pd * cover.lgd * st.outstanding
    strategy = _strategy(classification, signals, tests)
    actions = tuple(Action(day, owner, text) for day, owner, text in _PLAYBOOK[strategy])
    return Monitoring(
        status=st,
        spread=current,
        covenant_tests=tests,
        signals=tuple(signals),
        rating=rating,
        current_grade=current_grade,
        migration=migration,
        classification=classification,
        ifrs9_stage=stage,
        sma_bucket=_sma(st.days_past_due),
        ecl=ecl,
        lgd=cover.lgd,
        recovery_value=st.outstanding * (1 - cover.lgd),
        strategy=strategy,
        actions=actions,
    )


# ---------------------------------------------------------------- parsing and rendering

_STATUS_KEYS = {
    "borrower",
    "industry",
    "limit",
    "outstanding",
    "rate",
    "remaining_years",
    "origination_grade",
    "financials",
    "covenants",
    "seniority",
    "collateral",
    "days_past_due",
    "utilisation_history",
    "events",
    "qualitative",
}


def status_from_dict(data: object) -> FacilityStatus:
    d: Mapping[str, Any] = _check_keys("facility", data, _STATUS_KEYS)
    industry = _text("industry", _section(d, "industry"))
    get_industry(industry)
    limit = require_positive("limit", _section(d, "limit"))
    outstanding = require_non_negative("outstanding", _section(d, "outstanding"))
    og = _section(d, "origination_grade")
    if isinstance(og, bool) or not isinstance(og, int) or not 1 <= og <= 9:
        raise ValidationError(f"origination_grade must be a whole number 1 to 9, got {og!r}")
    covenants = d.get("covenants", {})
    if not isinstance(covenants, Mapping):
        raise ValidationError("covenants must be an object")
    for key in covenants:
        if key not in _COVENANTS:
            raise ValidationError(f"unknown covenant {key!r}; use {', '.join(_COVENANTS)}")
    seniority = _text("seniority", d.get("seniority", "senior_secured"))
    if seniority not in SENIORITIES:
        raise ValidationError(f"seniority must be one of: {', '.join(SENIORITIES)}")
    dpd = d.get("days_past_due", 0)
    if isinstance(dpd, bool) or not isinstance(dpd, int) or dpd < 0:
        raise ValidationError(f"days_past_due must be a whole number >= 0, got {dpd!r}")
    usage = d.get("utilisation_history", [])
    if not isinstance(usage, list):
        raise ValidationError("utilisation_history must be a list of fractions")
    events = d.get("events", [])
    if not isinstance(events, list):
        raise ValidationError("events must be a list")
    for e in events:
        if e not in EVENTS:
            raise ValidationError(f"unknown event {e!r}; use {', '.join(EVENTS)}")
    return FacilityStatus(
        borrower=_text("borrower", _section(d, "borrower")),
        industry=industry,
        limit=limit,
        outstanding=outstanding,
        rate=require_non_negative("rate", d.get("rate", 0.0)),
        remaining_years=require_non_negative("remaining_years", d.get("remaining_years", 1.0)),
        origination_grade=og,
        financials=parse_financials_list(_section(d, "financials")),
        covenants={k: require_positive(f"covenants.{k}", v) for k, v in covenants.items()},
        seniority=seniority,
        collateral=parse_collateral(d.get("collateral")),
        days_past_due=dpd,
        utilisation_history=tuple(
            require_fraction(f"utilisation_history[{i}]", u) for i, u in enumerate(usage)
        ),
        events=tuple(events),
        qualitative=parse_qualitative(d.get("qualitative")),
    )


def render_monitoring(m: Monitoring) -> str:
    st, g = m.status, m.current_grade
    move = (
        "no change"
        if m.migration == 0
        else (
            f"{m.migration} notch(es) worse"
            if m.migration > 0
            else f"{-m.migration} notch(es) better"
        )
    )
    lines = [
        f"{st.borrower} · outstanding {st.outstanding / 1e6:,.1f}M of {st.limit / 1e6:,.1f}M",
        f"Grade           {g.grade} ({g.equivalent}), origination {st.origination_grade}: {move}",
        f"Classification  {m.classification} · IFRS 9 stage {m.ifrs9_stage} · {m.sma_bucket}",
        f"ECL provision   {m.ecl / 1e6:,.2f}M (LGD {m.lgd * 100:.1f}%)",
        f"Recovery value  {m.recovery_value / 1e6:,.1f}M if enforced",
        f"Strategy        {m.strategy.upper()}",
        "",
        "Covenants",
    ]
    for t in m.covenant_tests:
        head = "n/a" if t.headroom is None else f"{t.headroom * 100:+.0f}%"
        state = "BREACH" if t.breached else "ok"
        lines.append(f"  {t.name:<16} {_x(t.actual):>7} vs {t.threshold:.2f}x  {head:>5}  {state}")
    lines += ["", "Early-warning signals"]
    lines += [f"  [{s.severity.upper()}] {s.signal}: {s.detail}" for s in m.signals] or ["  none"]
    lines += ["", "Action plan"]
    lines += [f"  Day {a.day:>3}  {a.owner:<20} {a.action}" for a in m.actions]
    return "\n".join(lines)


__all__ = [
    "EVENTS",
    "STRATEGIES",
    "Action",
    "CovenantTest",
    "FacilityStatus",
    "Monitoring",
    "Signal",
    "monitor",
    "render_monitoring",
    "status_from_dict",
]
