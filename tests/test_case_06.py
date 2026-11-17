import json

import pytest

from casemath.cases import get_case, render_case, render_solution
from casemath.cases.case_06_automation_investment import BASE, cash_flows, loss_probability
from casemath.frameworks import check_mece


@pytest.fixture(scope="module")
def answer() -> dict[str, float | None]:
    return get_case("6").solve().answer


def test_cash_flows() -> None:
    flows = cash_flows(BASE)
    assert flows[0] == -12_000_000
    assert flows[1] == pytest.approx(2_600_000)  # 3.2M - 0.6M
    assert flows[2] == pytest.approx(3_328_000 - 600_000)
    assert flows[7] == pytest.approx(3_200_000 * 1.04**6 - 600_000 + 1_000_000)


def test_appraisal(answer: dict[str, float | None]) -> None:
    assert answer["npv"] == pytest.approx(3_456_238.73, abs=0.01)
    assert answer["irr"] == pytest.approx(0.16472, abs=1e-5)
    assert answer["payback_years"] == pytest.approx(4.2581, abs=1e-4)
    assert answer["discounted_payback_years"] == pytest.approx(5.4793, abs=1e-4)


def test_scenarios(answer: dict[str, float | None]) -> None:
    assert answer["downside_npv"] == pytest.approx(-2_393_650.65, abs=0.01)
    assert answer["expected_npv"] == pytest.approx(3_131_176.30, abs=0.01)


def test_break_even_savings(answer: dict[str, float | None]) -> None:
    assert answer["break_even_savings"] == pytest.approx(2_583_123.51, abs=0.01)


def test_risk(answer: dict[str, float | None]) -> None:
    # Seeded, so exact; the skewed savings range drags the mean well below the base case.
    assert answer["prob_loss"] == pytest.approx(0.2088, abs=0.005)
    assert answer["simulated_mean_npv"] < answer["npv"]  # type: ignore[operator]
    assert answer["passes_board_rule"] == 0


def test_max_capex(answer: dict[str, float | None]) -> None:
    max_capex = answer["max_capex"]
    assert max_capex == pytest.approx(11_120_000, rel=0.002)
    assert loss_probability({"capex": max_capex - 2_000}) <= 0.10  # type: ignore[operator]
    assert loss_probability({"capex": 12_000_000}) > 0.10
    assert answer["discount_needed"] == pytest.approx(1 - max_capex / 12_000_000)  # type: ignore[operator]


def test_narrative() -> None:
    solution = get_case("6").solve()
    text = render_solution(solution)
    assert "Do not sign at $12M" in text
    assert "fails the board's 10% risk rule" in text
    assert json.loads(json.dumps(solution.to_dict(), allow_nan=False))["case_id"] == "6"


def test_structure_and_data() -> None:
    case = get_case("6")
    assert check_mece(case.structure()).ok
    assert "robotic picking" in render_case(case)
    assert json.dumps(case.data())  # serialisable, including distributions
