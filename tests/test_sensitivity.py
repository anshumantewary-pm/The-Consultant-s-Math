import pytest

from casemath.analysis.model import Inputs, check_inputs, evaluate
from casemath.analysis.sensitivity import one_way
from casemath.core import ValidationError


def profit(x: Inputs) -> float:
    return (x["price"] - x["unit_cost"]) * x["units"] - x["fixed"]


BASE = {"price": 10.0, "unit_cost": 6.0, "units": 1_000.0, "fixed": 2_500.0}


class TestModelHelpers:
    def test_check_inputs_converts(self) -> None:
        assert check_inputs({"a": 1}) == {"a": 1.0}

    def test_empty_base(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            check_inputs({})

    def test_unknown_name(self) -> None:
        with pytest.raises(ValidationError, match=r"unknown input 'margin'.*price"):
            check_inputs(BASE, ["margin"])

    def test_non_finite_output(self) -> None:
        with pytest.raises(ValidationError, match="model output"):
            evaluate(lambda _: float("nan"), BASE)


class TestOneWay:
    def test_price_sweep(self) -> None:
        result = one_way(profit, BASE, "price", [9, 10, 11])
        assert result.outputs == (500, 1_500, 2_500)
        assert result.base_value == 10
        assert result.base_output == 1_500

    def test_does_not_mutate_base(self) -> None:
        base = dict(BASE)
        one_way(profit, base, "units", [0])
        assert base == BASE

    def test_rejects_empty_values(self) -> None:
        with pytest.raises(ValidationError, match="values must not be empty"):
            one_way(profit, BASE, "price", [])
