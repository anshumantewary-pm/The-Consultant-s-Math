import json

import pytest

from casemath.advisor import SECTORS, Profile, assess, get_sector, parse_financials
from casemath.cli import main
from casemath.core.errors import UnknownNameError, ValidationError


def saas(**overrides: object) -> Profile:
    base: dict[str, object] = {
        "sector": "saas",
        "name": "Acme",
        "revenue": 4_200_000,
        "cogs": 1_260_000,
        "opex": 3_600_000,
        "prior_revenue": 3_000_000,
        "cash": 1_500_000,
        "arpu": 500,
        "churn": 0.025,
        "cac": 9000,
    }
    base.update(overrides)
    return Profile(**base)  # type: ignore[arg-type]


def keys(result: object) -> list[str]:
    return [s.area for s in result.suggestions]  # type: ignore[attr-defined]


def test_every_sector_has_consistent_ranges() -> None:
    for s in SECTORS.values():
        for low, high in (s.gross_margin, s.ebitda_margin, s.growth, s.opex_ratio):
            assert low < high
        assert s.ev_revenue[0] < s.ev_revenue[1] < s.ev_revenue[2]
        assert s.ev_ebitda[0] < s.ev_ebitda[1] < s.ev_ebitda[2]
        assert s.kpis
        assert s.margin_levers
        assert s.cost_levers
        assert s.growth_levers


def test_get_sector_is_case_insensitive_and_rejects_unknown() -> None:
    assert get_sector(" SaaS ").key == "saas"
    with pytest.raises(UnknownNameError, match="unknown sector"):
        get_sector("mining")


def test_loss_making_saas() -> None:
    r = assess(saas())
    by_key = {m.key: m for m in r.metrics}
    assert by_key["gross_margin"].value == pytest.approx(0.70)
    assert by_key["growth"].value == pytest.approx(0.40)
    assert by_key["ebitda_margin"].status == "below"
    assert by_key["opex_ratio"].status == "above"
    assert by_key["opex_ratio"].good is False
    assert by_key["rule_of_40"].status == "below"
    assert r.ebitda == pytest.approx(-660_000)
    assert r.break_even_revenue == pytest.approx(3_600_000 / 0.7)
    assert r.revenue_gap == pytest.approx(3_600_000 / 0.7 - 4_200_000)
    assert r.runway_months == pytest.approx(1_500_000 / 55_000)
    assert [v.method for v in r.valuations] == ["EV / Revenue"]
    assert r.equity_low == pytest.approx(4_200_000 * 3 + 1_500_000)
    assert r.unit_economics is not None
    assert r.unit_economics["healthy"] is False
    assert r.rating == "Needs attention"
    assert r.suggestions[0].priority == "high"
    assert "Unit economics" in keys(r)
    assert r.suggestions[-1].area == "Sector playbook"
    priorities = [s.priority for s in r.suggestions]
    assert priorities == sorted(priorities, key=["high", "medium", "low"].index)


def test_healthy_company_scores_strong() -> None:
    r = assess(
        Profile(sector="consumer", revenue=10e6, cogs=4e6, opex=3e6, growth=0.2, cash=2e6, debt=1e6)
    )
    assert r.rating == "Strong"
    assert r.score >= 75
    assert r.strengths
    assert {v.method for v in r.valuations} == {"EV / Revenue", "EV / EBITDA"}
    assert r.revenue_gap is None
    assert r.runway_months is None  # profitable and no burn given
    assert "Valuation" in keys(r)
    leverage = next(m for m in r.metrics if m.key == "leverage")
    assert leverage.status == "within"


def test_weak_profitable_company_gets_margin_growth_and_debt_advice() -> None:
    r = assess(
        Profile(sector="manufacturing", revenue=10e6, cogs=8.5e6, opex=1.2e6, growth=0.01, debt=5e6)
    )
    areas = keys(r)
    assert "Gross margin" in areas
    assert "Growth" in areas
    assert "Balance sheet" in areas
    assert "Profitability" in areas  # EBITDA below floor but positive
    gm = next(s for s in r.suggestions if s.area == "Gross margin")
    assert gm.actions == SECTORS["manufacturing"].margin_levers


def test_short_runway_is_high_priority_and_given_burn_is_used() -> None:
    r = assess(saas(cash=300_000, monthly_burn=100_000, arpu=None))
    assert r.runway_months == pytest.approx(3)
    assert r.suggestions[0].area == "Cash"
    assert r.suggestions[0].priority == "high"
    assert r.unit_economics is None
    medium = assess(saas(cash=900_000, monthly_burn=100_000))
    cash = next(s for s in medium.suggestions if s.area == "Cash")
    assert cash.priority == "medium"


def test_very_poor_unit_economics_are_high_priority() -> None:
    r = assess(saas(cac=30_000))
    ue = next(s for s in r.suggestions if s.title.startswith("LTV/CAC"))
    assert ue.priority == "high"


def test_zero_gross_margin_has_no_break_even() -> None:
    r = assess(Profile(sector="retail", revenue=100, cogs=100, opex=10))
    assert r.break_even_revenue is None
    assert r.revenue_gap is None


def test_growth_overrides_prior_revenue_and_metric_good_is_none_for_info() -> None:
    r = assess(saas(growth=0.1))
    assert next(m for m in r.metrics if m.key == "growth").value == pytest.approx(0.1)
    from casemath.advisor import Metric

    assert Metric("x", "X", 1.0).good is None
    assert Metric("x", "X", 2.0, 0, 1, "above").good is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("revenue", 0), ("cogs", -1), ("opex", -1), ("debt", -1), ("cash", -1), ("prior_revenue", 0)],
)
def test_bad_inputs_raise(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        assess(saas(**{field: value}))


def test_to_dict_is_json_ready() -> None:
    json.dumps(assess(saas()).to_dict(), allow_nan=False)


def test_parse_financials_multi_year_csv() -> None:
    text = (
        "metric,2024,2025\n"
        "\n"
        "Company,Acme Cloud\n"
        "Industry,SaaS\n"
        'Total Revenue,"$3,000,000","₹4,200,000"\n'
        "Cost of Sales,,1260000\n"
        "SG&A,,(3600000)\n"
        "churn,,2.5%\n"
        "notes,ignored\n"
        "cash,\n"
    )
    found = parse_financials(text)
    assert found == {
        "name": "Acme Cloud",
        "sector": "saas",
        "revenue": 4_200_000,
        "prior_revenue": 3_000_000,
        "cogs": 1_260_000,
        "opex": -3_600_000,
        "churn": pytest.approx(0.025),
    }


def test_parse_financials_maps_sector_names_and_rejects_text_numbers() -> None:
    assert parse_financials("sector,Restaurants")["sector"] == "restaurants"
    assert parse_financials("sector,Something else")["sector"] == "something else"
    with pytest.raises(ValidationError, match="no number"):
        parse_financials("revenue,lots")


def test_cli_advise_text_and_json(capsys: pytest.CaptureFixture[str], tmp_path: object) -> None:
    argv = ["advise", "--sector", "saas", "--revenue", "4200000", "--cogs", "1260000"]
    argv += ["--opex", "3600000", "--prior-revenue", "3000000", "--cash", "1500000"]
    argv += ["--arpu", "500", "--churn", "0.025", "--cac", "9000"]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert "Health score" in out
    assert "[HIGH]" in out
    assert "LTV / CAC" in out
    assert "Cash runway" in out
    assert "Break-even rev" in out
    assert main(["advise", "--json", *argv[1:]]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["sector"]["key"] == "saas"


def test_cli_advise_from_file_with_override(capsys: pytest.CaptureFixture[str], tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "f.csv"
    path.write_text(
        "sector,manufacturing\nrevenue,10000000\ncogs,8500000\nopex,1200000\ndebt,5000000\n"
    )
    assert main(["advise", "--file", str(path), "--name", "Mill"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Mill")
    assert "Debt / EBITDA" in out
    assert "EV / EBITDA" in out


def test_cli_advise_errors(capsys: pytest.CaptureFixture[str], tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert main(["advise", "--sector", "saas"]) == 2
    assert "missing --revenue, --cogs, --opex" in capsys.readouterr().err
    assert main(["advise", "--file", str(tmp_path / "nope.csv")]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_cli_sectors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sectors"]) == 0
    assert "saas" in capsys.readouterr().out
    assert main(["sectors", "--json"]) == 0
    assert set(json.loads(capsys.readouterr().out)) == set(SECTORS)
