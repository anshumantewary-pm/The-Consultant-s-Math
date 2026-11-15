import json

import pytest

from casemath.cases import get_case, render_case, render_solution
from casemath.frameworks import check_mece


@pytest.fixture(scope="module")
def solution():  # type: ignore[no-untyped-def]
    return get_case("1").solve()


def test_headline_numbers(solution) -> None:  # type: ignore[no-untyped-def]
    answer = solution.answer
    assert answer["profit_year_1"] == pytest.approx(10_000_000)
    assert answer["profit_year_2"] == pytest.approx(6_225_000)
    assert answer["profit_change"] == pytest.approx(-3_775_000)


def test_drivers(solution) -> None:  # type: ignore[no-untyped-def]
    answer = solution.answer
    assert answer["juice_cost_effect"] == pytest.approx(-2_745_000)
    assert answer["energy_price_effect"] == pytest.approx(-2_320_000)
    assert answer["energy_volume_effect"] == pytest.approx(1_200_000)
    # Juice is the single biggest driver.
    assert abs(answer["juice_cost_effect"]) > abs(
        answer["energy_price_effect"] + answer["energy_volume_effect"]
    )


def test_break_even_insights(solution) -> None:  # type: ignore[no-untyped-def]
    # 7.5M old contribution / $1.10 new unit margin
    assert solution.answer["energy_units_needed"] == pytest.approx(6_818_181.8, rel=1e-6)
    # $1.95 new cost + $1.00 old unit margin
    assert solution.answer["juice_price_needed"] == pytest.approx(2.95)


def test_findings_and_recommendation(solution) -> None:  # type: ignore[no-untyped-def]
    text = render_solution(solution)
    assert "73% of the" in text  # juice share of the decline
    assert "MECE check" in text
    assert solution.recommendation.startswith("Fix Juice first")
    assert len(solution.steps) == 15


def test_case_metadata_and_structure() -> None:
    case = get_case("1")
    assert case.case_type == "Profitability"
    assert check_mece(case.structure()).ok
    assert len(case.data()["year_1"]) == 3
    rendered = render_case(case)
    assert rendered.startswith("Case 1: Brewline Beverages")
    assert "Suggested structure:" in rendered


def test_solution_is_json(solution) -> None:  # type: ignore[no-untyped-def]
    data = json.loads(json.dumps(solution.to_dict()))
    assert data["case_id"] == "1"
    assert data["steps"][0]["label"] == "Year 1 revenue"
