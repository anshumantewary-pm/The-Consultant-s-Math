import json

import pytest

from casemath.cases import get_case, render_case, render_solution
from casemath.cases.case_05_saas_pricing import ltv_to_cac
from casemath.frameworks import check_mece


@pytest.fixture(scope="module")
def answer() -> dict[str, float | None]:
    return get_case("5").solve().answer


def test_cut_does_not_pay(answer: dict[str, float | None]) -> None:
    # -17.5% at 80% margin: 0.175 / 0.625 = 28% needed; test gave 470/400 - 1 = 17.5%
    assert answer["price_change"] == pytest.approx(-0.175)
    assert answer["volume_needed"] == pytest.approx(0.28)
    assert answer["volume_observed"] == pytest.approx(0.175)
    assert answer["volume_observed"] < answer["volume_needed"]  # type: ignore[operator]


def test_inelastic(answer: dict[str, float | None]) -> None:
    assert answer["elasticity"] == pytest.approx(-0.8391, abs=1e-4)


def test_unit_economics(answer: dict[str, float | None]) -> None:
    # $96 margin / 3% churn = $3,200; / $1,800 = 1.78x; at $99: $75 / 0.03 / 1,800
    assert answer["ltv_now"] == pytest.approx(3_200)
    assert answer["ltv_to_cac_now"] == pytest.approx(3_200 / 1_800)
    assert answer["ltv_to_cac_cut"] == pytest.approx(2_500 / 1_800)
    assert answer["cac_payback_months"] == pytest.approx(18.75)


def test_optimal_price(answer: dict[str, float | None]) -> None:
    # Q = 800 - (10/3) P -> choke $240; (240 + 24) / 2 = $132; LTV/CAC = 108 / 0.03 / 1,800
    assert answer["optimal_price"] == pytest.approx(132)
    assert answer["ltv_to_cac_at_optimum"] == pytest.approx(2.0)


def test_targets(answer: dict[str, float | None]) -> None:
    # 96 / churn / 1,800 = 3 -> churn = 1.778%; 3,200 / CAC = 3 -> CAC = 1,066.67
    assert answer["target_churn"] == pytest.approx(96 / 5_400, abs=1e-7)
    assert answer["target_cac"] == pytest.approx(3_200 / 3, abs=1e-4)


def test_margin_lost_on_base(answer: dict[str, float | None]) -> None:
    assert answer["monthly_margin_lost_on_base"] == pytest.approx(105_000)


def test_model() -> None:
    assert ltv_to_cac({"price": 120, "cost_to_serve": 24, "churn": 0.03, "cac": 1_800}) == (
        pytest.approx(3_200 / 1_800)
    )


def test_narrative() -> None:
    solution = get_case("5").solve()
    text = render_solution(solution)
    assert "Do not cut the price" in text
    assert "Price is the biggest single lever" in text
    assert json.loads(json.dumps(solution.to_dict(), allow_nan=False))["case_id"] == "5"


def test_structure_is_mece() -> None:
    case = get_case("5")
    assert check_mece(case.structure()).ok
    assert "$99" in render_case(case)
    assert case.data()["test_signups_per_month"] == {"120": 400.0, "99": 470.0}
