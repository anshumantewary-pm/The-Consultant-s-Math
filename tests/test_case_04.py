import json

import pytest

from casemath.cases import get_case, render_case, render_solution
from casemath.frameworks import check_mece


@pytest.fixture(scope="module")
def solution():  # type: ignore[no-untyped-def]
    return get_case("4").solve()


def test_premium(solution) -> None:  # type: ignore[no-untyped-def]
    assert solution.answer["premium"] == pytest.approx(120e6)
    assert solution.answer["premium_pct"] == pytest.approx(0.30)


def test_synergies(solution) -> None:  # type: ignore[no-untyped-def]
    a = solution.answer
    assert a["run_rate_cost"] == pytest.approx(18e6)
    assert a["run_rate_revenue"] == pytest.approx(7.5e6)  # $30M x 25%
    assert a["synergy_value_plan"] == pytest.approx(174e6)  # 25.5 x 8 - 30
    assert a["synergy_value_risked"] == pytest.approx(144e6)  # 21.75 x 8 - 30
    assert a["synergy_value_cost_only"] == pytest.approx(114e6)  # 18 x 8 - 30
    assert a["payback_year"] == 3


def test_prices(solution) -> None:  # type: ignore[no-untyped-def]
    assert solution.answer["walk_away_price"] == pytest.approx(544e6)
    assert solution.answer["cost_only_price"] == pytest.approx(514e6)
    # The deal hinges on revenue synergies: cost synergies alone fall short of the premium.
    assert solution.answer["synergy_value_cost_only"] < solution.answer["premium"]


def test_text(solution) -> None:  # type: ignore[no-untyped-def]
    text = render_solution(solution)
    assert "$6.0M short of the premium" in text
    assert "Integration paid back in year (risked): 3" in text
    assert solution.recommendation.startswith("Proceed, but")


def test_metadata() -> None:
    case = get_case("4")
    assert case.case_type == "M&A"
    assert check_mece(case.structure()).ok
    assert len(case.data()["synergies"]) == 4
    assert render_case(case).startswith("Case 4: Northfield Foods")


def test_json(solution) -> None:  # type: ignore[no-untyped-def]
    assert json.loads(json.dumps(solution.to_dict()))["case_id"] == "4"
