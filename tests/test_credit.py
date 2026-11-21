import copy
import json
from pathlib import Path
from typing import Any

import pytest

from casemath.cli import main
from casemath.core.errors import UnknownNameError, ValidationError
from casemath.credit import (
    APPROVE,
    APPROVE_WITH_CONDITIONS,
    DECLINE,
    MASTER_SCALE,
    REFER,
    BankPolicy,
    Collateral,
    FacilityRequest,
    Financials,
    borrower_from_dict,
    debt_capacity,
    decide,
    exposure_at_default,
    get_industry,
    grade,
    irb_capital,
    loss_given_default,
    monitor,
    pro_forma,
    render_memo,
    render_monitoring,
    returns,
    spread,
    status_from_dict,
)
from casemath.credit.rating import grade_for_score, scale

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "credit"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    return data


def fin(**overrides: Any) -> Financials:
    base: dict[str, Any] = {
        "period": "FY",
        "revenue": 100e6,
        "ebitda": 20e6,
        "interest_expense": 2e6,
        "total_debt": 40e6,
        "cash": 5e6,
        "capex": 4e6,
        "taxes": 2e6,
        "scheduled_principal": 4e6,
    }
    base.update(overrides)
    return Financials(**base)


# ---------------------------------------------------------------- analysis


def test_spread_ratios() -> None:
    s = spread(fin(current_assets=30e6, current_liabilities=20e6, equity=50e6), fin(revenue=80e6))
    assert s.leverage == pytest.approx(2.0)
    assert s.net_leverage == pytest.approx(35 / 20)
    assert s.icr == pytest.approx(10.0)
    assert s.cash_flow_available == pytest.approx(14e6)
    assert s.dscr == pytest.approx(14 / 6)
    assert s.free_cash_flow == pytest.approx(12e6)
    assert s.payback_years == pytest.approx(35 / 12)
    assert s.revenue_growth == pytest.approx(0.25)
    assert s.current_ratio == pytest.approx(1.5)
    assert s.gearing == pytest.approx(0.8)


def test_spread_handles_missing_and_negative_figures() -> None:
    s = spread(fin(ebitda=-1e6, interest_expense=0, scheduled_principal=0, equity=-5e6))
    assert s.leverage is None
    assert s.icr is None
    assert s.dscr is None
    assert s.payback_years is None
    assert s.gearing is None
    assert s.current_ratio is None
    assert s.revenue_growth is None


def test_pro_forma_refinances_pro_rata() -> None:
    req = FacilityRequest(
        amount=30e6, tenor_years=5, margin=0.02, base_rate=0.05, amortisation=0.1, refinances=20e6
    )
    pf = pro_forma(fin(), req)
    assert pf.total_debt == pytest.approx(50e6)
    assert pf.interest_expense == pytest.approx(1e6 + 30e6 * 0.07)
    assert pf.scheduled_principal == pytest.approx(2e6 + 3e6)


def test_pro_forma_revolver_uses_expected_draw_and_handles_no_debt() -> None:
    req = FacilityRequest(
        amount=10e6, tenor_years=3, facility_type="revolver", expected_utilisation=0.4
    )
    pf = pro_forma(fin(total_debt=0, interest_expense=0, scheduled_principal=0), req)
    assert pf.total_debt == pytest.approx(4e6)
    assert pf.interest_expense == pytest.approx(4e6 * req.all_in_rate)


def test_debt_capacity() -> None:
    req = FacilityRequest(
        amount=10e6, tenor_years=5, base_rate=0.05, margin=0.03, amortisation=0.12
    )
    cap = debt_capacity(fin(), req, max_leverage=3.0, policy=BankPolicy())
    assert cap.by_leverage == pytest.approx(20e6)
    assert cap.by_dscr == pytest.approx((14e6 / 1.25 - 6e6) / 0.20)
    assert cap.max_additional == pytest.approx(min(cap.by_leverage, cap.by_dscr))
    free = FacilityRequest(amount=1e6, tenor_years=1, base_rate=0, margin=0)
    assert debt_capacity(fin(), free, 3.0, BankPolicy()).by_dscr == float("inf")


def test_ead_and_lgd() -> None:
    policy = BankPolicy()
    assert exposure_at_default(FacilityRequest(10e6, 5), policy) == 10e6
    rcf = FacilityRequest(10e6, 3, facility_type="revolver", expected_utilisation=0.5)
    assert exposure_at_default(rcf, policy) == pytest.approx(5e6 + 0.75 * 5e6)
    collateral = (Collateral("real_estate", 10e6), Collateral("cash", 1e6))
    cover = loss_given_default(collateral, 16e6, "senior_secured")
    assert cover.recoverable == pytest.approx(8e6)
    assert cover.coverage == pytest.approx(0.5)
    assert cover.lgd == pytest.approx(0.5 * 0.20 + 0.5 * 0.40)
    assert loss_given_default(collateral, 1e6, "senior_secured").lgd == pytest.approx(0.20)
    unsecured = loss_given_default(collateral, 16e6, "subordinated")
    assert unsecured.recoverable == 0
    assert unsecured.lgd == pytest.approx(0.75)
    assert loss_given_default((), 0, "senior_secured").coverage == 0


def test_irb_capital_matches_basel_reference() -> None:
    # Basel corporate formula, PD 1%, LGD 45%, M 2.5: risk weight about 92.3%.
    k, rwa = irb_capital(0.01, 0.45, 100.0, 2.5)
    assert rwa == pytest.approx(92.32, abs=0.05)
    assert k == pytest.approx(rwa / 1250)
    # PD floor and maturity clamps.
    assert irb_capital(0.0, 0.45, 1, 10)[0] == pytest.approx(irb_capital(0.0005, 0.45, 1, 5)[0])


def test_returns_and_required_margin_hit_the_hurdle() -> None:
    policy = BankPolicy()
    req = FacilityRequest(50e6, 5, margin=0.02, upfront_fee=0.01)
    r = returns(req, 0.01, 0.35, policy)
    assert r.expected_loss == pytest.approx(0.01 * 0.35 * 50e6)
    assert r.fee_income == pytest.approx(50e6 * 0.01 / 5)
    assert r.required_margin is not None
    at_hurdle = returns(
        FacilityRequest(50e6, 5, margin=r.required_margin, upfront_fee=0.01), 0.01, 0.35, policy
    )
    assert at_hurdle.raroc == pytest.approx(policy.hurdle_raroc)
    undrawn = FacilityRequest(
        10e6, 3, facility_type="revolver", expected_utilisation=0.0, commitment_fee=0.005
    )
    u = returns(undrawn, 0.01, 0.4, policy)
    assert u.required_margin is None
    assert u.fee_income == pytest.approx(10e6 * 0.005)


# ---------------------------------------------------------------- rating


def test_master_scale_is_monotonic() -> None:
    pds = [g.pd for g in MASTER_SCALE]
    assert pds == sorted(pds)
    assert [g.grade for g in MASTER_SCALE] == list(range(1, 11))
    assert grade(0).grade == 1
    assert grade(42).grade == 10


def test_scale_and_grade_bands() -> None:
    assert scale(None, 0, 1) == 0
    assert scale(6.0, 6.0, 1.0) == 0
    assert scale(0.5, 6.0, 1.0) == 100
    assert scale(3.5, 6.0, 1.0) == pytest.approx(50)
    assert scale(100e6, 10e6, 1e9, log=True) == pytest.approx(50)
    assert grade_for_score(90) == 1
    assert grade_for_score(61) == 4
    assert grade_for_score(10) == 9


# ---------------------------------------------------------------- decisions


def test_strong_borrower_is_approved() -> None:
    d = decide(borrower_from_dict(load("northwind-industrial")))
    assert d.decision == APPROVE
    assert d.rating.final.grade == 4
    assert d.approver == "Senior Credit Officer"
    assert not d.exceptions
    assert not d.hard_stops
    assert d.recommended_amount == pytest.approx(75e6)
    assert d.total_exposure == pytest.approx(95e6)
    assert d.covenants.max_leverage >= d.pro_forma.leverage  # type: ignore[operator]
    assert d.covenants.reporting == "semi-annually"
    weights = sum(f.weight for f in d.rating.factors)
    assert weights == pytest.approx(1.0)
    assert d.rating.score == pytest.approx(sum(f.contribution for f in d.rating.factors))


def test_stretched_borrower_is_referred() -> None:
    d = decide(borrower_from_dict(load("coastal-retail")))
    assert d.decision == REFER
    assert {c.key for c in d.exceptions} == {"leverage", "dscr", "payback"}
    assert d.approver == "Credit Committee"
    assert d.recommended_amount == 0
    assert any("Watchlist" in c for c in d.conditions)


def test_kyc_and_weak_credit_is_declined() -> None:
    d = decide(borrower_from_dict(load("meridian-energy")))
    assert d.decision == DECLINE
    assert {c.key for c in d.hard_stops} == {"kyc", "appetite", "dscr_hard"}
    assert d.approver == "n/a (declined)"
    assert any("KYC" in o for o in d.rating.overrides)
    assert any("EBITDA fell" in o for o in d.rating.overrides)
    assert any("Bullet" in r.risk for r in d.risks)


def _borrower(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(load("northwind-industrial"))
    for key, value in changes.items():
        if key.startswith("request."):
            data["request"][key.split(".", 1)[1]] = value
        else:
            data[key] = value
    return data


def test_one_exception_means_conditions_and_a_higher_approver() -> None:
    d = decide(borrower_from_dict(_borrower(**{"request.tenor_years": 7})))
    assert d.decision == APPROVE_WITH_CONDITIONS
    assert [c.key for c in d.exceptions] == ["tenor"]
    assert d.approver == "Chief Credit Officer"
    assert any(c.startswith("Exception approved: Tenor") for c in d.conditions)


def test_low_margin_is_flagged_and_repriced() -> None:
    d = decide(borrower_from_dict(_borrower(**{"request.margin": 0.004, "request.upfront_fee": 0})))
    assert "raroc" in {c.key for c in d.exceptions}
    assert d.recommended_margin == d.returns.required_margin
    assert "Margin needed to meet the hurdle" in render_memo(d)


def test_grade_eight_is_referred_even_without_exceptions() -> None:
    policy = BankPolicy(worst_grade=4)
    d = decide(borrower_from_dict(load("northwind-industrial")), policy)
    assert d.decision == REFER
    assert d.reasons == ("Grade 4 needs committee sign-off",)


def test_negative_equity_and_loss_making_borrowers_are_notched() -> None:
    data = _borrower()
    data["financials"][-1].update(equity=-1e6, ebitda=-2e6)
    d = decide(borrower_from_dict(data))
    assert d.rating.final.grade >= 8
    assert any("Negative equity" in o for o in d.rating.overrides)
    assert any("EBITDA is zero or negative" in o for o in d.rating.overrides)
    assert d.decision == DECLINE


def test_amount_is_capped_by_policy_capacity() -> None:
    d = decide(borrower_from_dict(_borrower(**{"request.amount": 250e6})))
    assert d.recommended_amount < 250e6
    assert "Amount that fits policy" in render_memo(d)


def test_memo_contains_every_section_and_matches_the_decision() -> None:
    d = decide(borrower_from_dict(load("northwind-industrial")))
    memo = render_memo(d)
    for n in range(1, 13):
        assert f"## {n}. " in memo
    assert f"**Recommendation: {d.decision}**" in memo
    assert "FY2024 pro forma" in memo
    assert "Freehold plants (UK)" in memo


def test_memo_without_collateral_or_description() -> None:
    data = _borrower(collateral=[], description="")
    data["request"]["seniority"] = "senior_unsecured"
    memo = render_memo(decide(borrower_from_dict(data)))
    assert "No business description supplied." in memo


# ---------------------------------------------------------------- parsing


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"industry": "space"}, "unknown industry"),
        ({"surprise": 1}, "unknown field"),
        ({"financials": []}, "non-empty list"),
        ({"request.amount": -5}, "request.amount"),
        ({"request.facility_type": "lease"}, "facility_type"),
        ({"request.seniority": "junior"}, "seniority"),
        ({"request.amortisation": 2}, "amortisation"),
        ({"request.refinances": 1e12}, "refinances"),
        ({"collateral": [{"type": "art", "value": 1}]}, "collateral[0].type"),
        ({"collateral": {"type": "cash"}}, "collateral must be a list"),
        ({"qualitative": {"management": 9}}, "1 to 5"),
        ({"kyc_flags": "none"}, "kyc_flags"),
        ({"name": 5}, "name must be text"),
        ({"request": "big"}, "request must be an object"),
    ],
)
def test_bad_borrower_files_are_rejected(change: dict[str, Any], message: str) -> None:
    error = UnknownNameError if message == "unknown industry" else ValidationError
    with pytest.raises(error, match=message.replace("[", r"\[").replace("]", r"\]")):
        borrower_from_dict(_borrower(**change))


def test_missing_required_field() -> None:
    data = _borrower()
    del data["financials"][0]["ebitda"]
    with pytest.raises(ValidationError, match="ebitda"):
        borrower_from_dict(data)
    with pytest.raises(UnknownNameError):
        get_industry("nope")


def test_optional_borrower_fields_default() -> None:
    data = _borrower()
    for key in ("collateral", "qualitative", "kyc_flags", "group", "country"):
        data.pop(key, None)
    b = borrower_from_dict(data)
    assert b.collateral == ()
    assert b.qualitative.management == 3


# ---------------------------------------------------------------- collections


def test_watchlist_account_goes_to_restructuring() -> None:
    m = monitor(status_from_dict(load("coastal-retail-q3-review")))
    assert m.classification == "Substandard"
    assert m.ifrs9_stage == 2
    assert m.sma_bucket == "SMA-0"
    assert m.strategy == "restructure"
    assert all(t.breached for t in m.covenant_tests)
    signals = {s.signal for s in m.signals}
    assert {"Facility near fully drawn", "Utilisation rising fast", "Tight liquidity"} <= signals
    assert m.signals[0].severity in ("high", "critical")
    assert m.ecl > 0
    assert "RESTRUCTURE" in render_monitoring(m)


def test_defaulted_account_goes_to_recovery() -> None:
    m = monitor(status_from_dict(load("meridian-default")))
    assert m.current_grade.grade == 10
    assert m.classification == "Doubtful"
    assert m.ifrs9_stage == 3
    assert m.sma_bucket == "NPA"
    assert m.strategy == "recover"
    assert m.ecl == pytest.approx(m.lgd * m.status.outstanding)
    assert m.recovery_value == pytest.approx(m.status.outstanding * (1 - m.lgd))


def _status(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(load("coastal-retail-q3-review"))
    data.update(changes)
    return data


def _healthy() -> dict[str, Any]:
    good = {
        "period": "FY",
        "revenue": 500e6,
        "ebitda": 80e6,
        "interest_expense": 8e6,
        "total_debt": 150e6,
        "cash": 20e6,
        "capex": 10e6,
        "taxes": 8e6,
        "scheduled_principal": 10e6,
    }
    return _status(
        financials=[good],
        days_past_due=0,
        utilisation_history=[0.5],
        events=[],
        origination_grade=6,
        qualitative={"management": 4, "market_position": 4},
    )


def test_healthy_account_is_monitored() -> None:
    m = monitor(status_from_dict(_healthy()))
    assert m.classification == "Pass"
    assert m.ifrs9_stage == 1
    assert m.sma_bucket == "Standard"
    assert m.strategy == "monitor"
    assert not m.signals
    assert m.migration <= 0
    assert "none" in render_monitoring(m)


def test_thin_headroom_means_watchlist() -> None:
    data = _healthy()
    data["covenants"] = {"max_leverage": 1.95}
    m = monitor(status_from_dict(data))
    assert m.strategy == "watchlist"
    assert m.signals[0].signal.endswith("headroom thin")


def test_single_breach_means_remediation() -> None:
    data = _healthy()
    data["covenants"] = {"min_icr": 12.0}
    m = monitor(status_from_dict(data))
    assert m.strategy in ("remediate", "restructure")
    assert m.current_grade.grade >= 7


@pytest.mark.parametrize(
    ("dpd", "bucket"), [(5, "SMA-0"), (45, "SMA-1"), (75, "SMA-2"), (200, "NPA")]
)
def test_arrears_buckets(dpd: int, bucket: str) -> None:
    m = monitor(status_from_dict(_status(days_past_due=dpd)))
    assert m.sma_bucket == bucket


def test_loss_classification_when_unsecured_and_long_overdue() -> None:
    m = monitor(status_from_dict(_status(days_past_due=200, collateral=[])))
    assert m.classification == "Loss"
    assert m.strategy == "recover"


def test_well_secured_default_is_substandard_not_doubtful() -> None:
    m = monitor(
        status_from_dict(_status(days_past_due=100, collateral=[{"type": "cash", "value": 60e6}]))
    )
    assert m.classification == "Substandard"


def test_covenant_with_no_ebitda_fails() -> None:
    data = _healthy()
    data["financials"][0]["ebitda"] = -1e6
    data["covenants"] = {"max_leverage": 4.0, "min_dscr": 1.1}
    m = monitor(status_from_dict(data))
    leverage, dscr = m.covenant_tests
    assert leverage.breached
    assert leverage.headroom is None
    assert dscr.breached
    assert dscr.actual is not None
    assert dscr.actual < 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"origination_grade": 11}, "origination_grade"),
        ({"covenants": {"max_capex": 1}}, "unknown covenant"),
        ({"covenants": [1]}, "covenants must be an object"),
        ({"seniority": "junior"}, "seniority"),
        ({"days_past_due": -1}, "days_past_due"),
        ({"utilisation_history": 0.5}, "utilisation_history"),
        ({"utilisation_history": [1.5]}, "utilisation_history"),
        ({"events": "fraud"}, "events must be a list"),
        ({"events": ["alien_invasion"]}, "unknown event"),
    ],
)
def test_bad_status_files_are_rejected(change: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        status_from_dict(_status(**change))


# ---------------------------------------------------------------- CLI


def test_cli_credit_summary_and_memo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "memo.md"
    assert main(["credit", str(EXAMPLES / "northwind-industrial.json"), "--memo", str(out)]) == 0
    text = capsys.readouterr().out
    assert "Decision        Approve" in text
    assert "Credit memo written to" in text
    assert out.read_text(encoding="utf-8").startswith("# Credit Memo: Northwind")
    assert main(["credit", str(EXAMPLES / "coastal-retail.json"), "--memo", "-"]) == 0
    assert "# Credit Memo: Coastal Retail Group" in capsys.readouterr().out


def test_cli_credit_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["credit", str(EXAMPLES / "meridian-energy.json"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["decision"] == DECLINE
    assert data["memo_markdown"].startswith("# Credit Memo")
    assert data["returns"]["required_margin"] > 0


def test_cli_collect_and_industries(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["collect", str(EXAMPLES / "meridian-default.json"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["strategy"] == "recover"
    assert main(["industries"]) == 0
    assert "manufacturing" in capsys.readouterr().out


def test_cli_credit_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["credit", str(tmp_path / "missing.json")]) == 2
    assert "cannot read" in capsys.readouterr().err
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["collect", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().err
    target = tmp_path / "no-such-dir" / "memo.md"
    assert main(["credit", str(EXAMPLES / "northwind-industrial.json"), "--memo", str(target)]) == 2
    assert "cannot write" in capsys.readouterr().err
