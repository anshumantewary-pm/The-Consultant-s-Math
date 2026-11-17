import pytest

from casemath.analysis.goal_seek import goal_seek
from casemath.analysis.model import Inputs
from casemath.calculators import npv
from casemath.core import ValidationError


def profit(x: Inputs) -> float:
    return (x["price"] - x["unit_cost"]) * x["units"] - x["fixed"]


BASE = {"price": 10.0, "unit_cost": 6.0, "units": 1_000.0, "fixed": 2_500.0}


class TestGoalSeek:
    def test_break_even_units(self) -> None:
        result = goal_seek(profit, BASE, "units", target=0, low=0, high=10_000)
        assert result.value == pytest.approx(625)
        assert result.output == pytest.approx(0, abs=1e-6)
        assert result.iterations > 0

    def test_price_for_target_profit(self) -> None:
        result = goal_seek(profit, BASE, "price", target=4_000, low=6, high=50)
        assert result.value == pytest.approx(12.5)

    def test_decreasing_model(self) -> None:
        # Fixed costs that wipe out profit: output falls as the input rises.
        result = goal_seek(profit, BASE, "fixed", target=0, low=0, high=10_000)
        assert result.value == pytest.approx(4_000)

    def test_hits_edge_exactly(self) -> None:
        result = goal_seek(profit, BASE, "units", target=-2_500, low=0, high=10)
        assert result.value == 0
        assert result.iterations == 0

    def test_irr_as_goal_seek(self) -> None:
        def project(x: Inputs) -> float:
            return npv(x["rate"], [-1_000, 500, 500, 500])

        result = goal_seek(project, {"rate": 0.1}, "rate", target=0, low=0, high=1)
        assert result.value == pytest.approx(0.23375, abs=1e-5)

    def test_no_crossing(self) -> None:
        with pytest.raises(ValidationError, match="widen the bracket"):
            goal_seek(profit, BASE, "units", target=0, low=1_000, high=2_000)

    def test_bad_bracket(self) -> None:
        with pytest.raises(ValidationError, match="must be below"):
            goal_seek(profit, BASE, "units", target=0, low=5, high=5)

    def test_does_not_converge(self) -> None:
        with pytest.raises(ValidationError, match="did not converge"):
            goal_seek(profit, BASE, "units", 0, 0, 10_000, tolerance=1e-30, max_iterations=3)
