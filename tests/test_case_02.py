import json

import pytest

from casemath.cases import get_case, list_cases, render_case, render_solution
from casemath.cases.case_02_market_entry import _scenario
from casemath.core import UnknownCaseError
from casemath.frameworks import check_mece


@pytest.fixture(scope="module")
def solution():  # type: ignore[no-untyped-def]
    return get_case("2").solve()


def test_market_size(solution) -> None:  # type: ignore[no-untyped-def]
    # 50,000 EVs x 30% x 72 sessions = 1.08M sessions; x $8 = $8.64M
    assert solution.answer["market_sessions"] == pytest.approx(1_080_000)
    assert solution.answer["market_value"] == pytest.approx(8_640_000)
    assert solution.steps[1].label == "x 30% use public fast charging"
    assert solution.steps[1].unit == "EVs"


def test_competition(solution) -> None:  # type: ignore[no-untyped-def]
    # 45^2 + 30^2 + 10 x 2.5^2
    assert solution.answer["hhi"] == pytest.approx(2_987.5)


def test_break_even(solution) -> None:  # type: ignore[no-untyped-def]
    assert solution.answer["break_even_sessions"] == pytest.approx(800_000 / 3)
    assert solution.answer["break_even_share"] == pytest.approx(0.2469, abs=1e-4)
    # 8% x (1.6 / 1.25)^3
    assert solution.answer["final_share"] == pytest.approx(0.08 * (1.6 / 1.25) ** 3)


def test_scenarios(solution) -> None:  # type: ignore[no-untyped-def]
    a = solution.answer
    assert a["base_break_even_year"] == 4
    assert a["base_payback_years"] == pytest.approx(7.643, abs=1e-3)
    assert a["base_passes"] == 0
    assert a["fleet_break_even_year"] == 3
    assert a["fleet_payback_years"] == pytest.approx(3.561, abs=1e-3)
    assert a["fleet_passes"] == 1


def test_minimum_anchor(solution) -> None:  # type: ignore[no-untyped-def]
    # Payback test binds: (2M / 5 - 261,683.2) / $2 = 69,158.4 -> 69,159
    assert solution.answer["min_anchor_sessions"] == 69_159


def test_recommendation(solution) -> None:  # type: ignore[no-untyped-def]
    assert solution.recommendation.startswith("Do not enter on retail demand alone")
    text = render_solution(solution)
    assert "highly concentrated" in text
    assert "That fails the board's rule" in text


def test_scenario_that_never_pays_back() -> None:
    scenario = _scenario("Empty", (0.0, 0.0), 0.0)
    assert scenario.break_even_year is None
    assert scenario.payback_years is None
    assert not scenario.passes


def test_structure_and_registry() -> None:
    case = get_case("2")
    assert check_mece(case.structure()).ok
    assert "fleet_anchor" in case.data()
    assert "Should VoltWay enter?" in render_case(case)
    assert [c.id for c in list_cases()] == ["1", "2"]
    with pytest.raises(UnknownCaseError, match="available: 1, 2"):
        get_case("9")


def test_json(solution) -> None:  # type: ignore[no-untyped-def]
    assert json.loads(json.dumps(solution.to_dict()))["case_id"] == "2"
