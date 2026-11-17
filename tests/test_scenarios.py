import pytest

from casemath.analysis.model import Inputs
from casemath.analysis.scenarios import compare_scenarios
from casemath.core import ValidationError


def profit(x: Inputs) -> float:
    return (x["price"] - x["unit_cost"]) * x["units"] - x["fixed"]


BASE = {"price": 10.0, "unit_cost": 6.0, "units": 1_000.0, "fixed": 2_500.0}
SCENARIOS = {
    "downside": {"units": 700.0, "unit_cost": 6.5},
    "base": {},
    "upside": {"units": 1_300.0},
}


class TestCompareScenarios:
    def test_rows(self) -> None:
        table = compare_scenarios(profit, BASE, SCENARIOS)
        outputs = {r.name: r.output for r in table.rows}
        assert outputs == {"downside": -50, "base": 1_500, "upside": 2_700}
        assert table.worst.name == "downside"
        assert table.best.name == "upside"
        assert table.rows[0].change_vs_base == -1_550
        assert table.expected_value is None

    def test_expected_value(self) -> None:
        table = compare_scenarios(
            profit, BASE, SCENARIOS, {"downside": 0.25, "base": 0.5, "upside": 0.25}
        )
        assert table.expected_value == pytest.approx(-50 * 0.25 + 1_500 * 0.5 + 2_700 * 0.25)

    def test_probabilities_must_sum_to_one(self) -> None:
        with pytest.raises(ValidationError, match="sum to 1"):
            compare_scenarios(
                profit, BASE, SCENARIOS, {"downside": 0.5, "base": 0.5, "upside": 0.5}
            )

    def test_probabilities_must_match(self) -> None:
        with pytest.raises(ValidationError, match="mismatch: upside"):
            compare_scenarios(profit, BASE, SCENARIOS, {"downside": 0.5, "base": 0.5})

    def test_unknown_override(self) -> None:
        with pytest.raises(ValidationError, match="unknown input"):
            compare_scenarios(profit, BASE, {"x": {"margin": 1.0}})

    def test_empty(self) -> None:
        with pytest.raises(ValidationError, match="scenarios must not be empty"):
            compare_scenarios(profit, BASE, {})
