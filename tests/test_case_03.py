import json

import pytest

from casemath.cases import get_case, render_case, render_solution
from casemath.frameworks import check_mece


@pytest.fixture(scope="module")
def solution():  # type: ignore[no-untyped-def]
    return get_case("3").solve()


def test_headline(solution) -> None:  # type: ignore[no-untyped-def]
    answer = solution.answer
    assert answer["profit_today"] == pytest.approx(350_000)
    # -450 / 2,775 over 4 / 42
    assert answer["elasticity_small_business"] == pytest.approx(-1.7027, rel=1e-4)
    assert answer["elasticity_accounting_firms"] == pytest.approx(-7 / 33)
    assert answer["break_even_volume_change_15pct"] == pytest.approx(-1 / 6)


def test_uniform_rise_is_a_wash(solution) -> None:  # type: ignore[no-untyped-def]
    # Small businesses lose ~$38.3K, firms gain ~$38.8K
    assert answer_of(solution, "uniform_rise_contribution_change") == pytest.approx(
        501.23, abs=0.01
    )


def test_pro_tier(solution) -> None:  # type: ignore[no-untyped-def]
    # 8,000 x (1 - 0.2121 x 25%) x $40 - 8,000 x $30
    assert answer_of(solution, "pro_tier_contribution_change") == pytest.approx(63_030.30, abs=0.01)
    assert answer_of(solution, "recommended_profit") == pytest.approx(413_030.30, abs=0.01)
    assert answer_of(solution, "small_business_cut_contribution_change") == pytest.approx(
        5_124.32, abs=0.01
    )


def answer_of(solution, key: str) -> float:  # type: ignore[no-untyped-def]
    value = solution.answer[key]
    assert value is not None
    return float(value)


def test_text(solution) -> None:  # type: ignore[no-untyped-def]
    text = render_solution(solution)
    assert "a wash" in text
    assert solution.recommendation.startswith("Do not raise the price for everyone")
    assert len(solution.steps) == 12


def test_metadata() -> None:
    case = get_case("3")
    assert case.case_type == "Pricing"
    assert check_mece(case.structure()).ok
    assert len(case.data()["segments"]) == 2
    assert render_case(case).startswith("Case 3: LedgerLite")


def test_json(solution) -> None:  # type: ignore[no-untyped-def]
    assert json.loads(json.dumps(solution.to_dict()))["case_id"] == "3"
