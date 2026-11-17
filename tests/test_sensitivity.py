import pytest

from casemath.analysis.model import Inputs, check_inputs, evaluate
from casemath.analysis.sensitivity import one_way, tornado, two_way
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


class TestTornado:
    def test_default_ten_percent(self) -> None:
        t = tornado(profit, BASE)
        assert t.base_output == 1_500
        # Price +/-1 moves profit +/-1,000; cost +/-0.6 -> 600; units +/-100 -> 400; fixed 250.
        assert [b.input for b in t.bars] == ["price", "unit_cost", "units", "fixed"]
        assert t.bars[0].swing == pytest.approx(2_000)
        assert t.most_sensitive == "price"

    def test_explicit_ranges(self) -> None:
        t = tornado(profit, BASE, {"units": (0, 3_000), "price": (9.5, 10.5)})
        assert t.most_sensitive == "units"
        assert t.bars[0].output_at_low == -2_500
        assert len(t.bars) == 2

    def test_skips_zero_inputs_by_default(self) -> None:
        t = tornado(profit, {**BASE, "fixed": 0})
        assert "fixed" not in [b.input for b in t.bars]

    def test_all_zero(self) -> None:
        with pytest.raises(ValidationError, match="explicit ranges"):
            tornado(lambda x: x["a"], {"a": 0})

    def test_unknown_range_name(self) -> None:
        with pytest.raises(ValidationError, match="unknown input"):
            tornado(profit, BASE, {"margin": (0, 1)})

    def test_bad_pct(self) -> None:
        with pytest.raises(ValidationError, match="pct"):
            tornado(profit, BASE, pct=0)


class TestTwoWay:
    def test_grid(self) -> None:
        t = two_way(profit, BASE, ("price", [9, 11]), ("units", [500, 1_500]))
        assert t.grid == ((-1_000, 2_000), (0, 5_000))
        assert t.count_at_least() == 3
        assert t.count_at_least(threshold=2_500) == 1

    def test_same_input_twice(self) -> None:
        with pytest.raises(ValidationError, match="different inputs"):
            two_way(profit, BASE, ("price", [1]), ("price", [2]))

    def test_empty_axis(self) -> None:
        with pytest.raises(ValidationError, match="column values"):
            two_way(profit, BASE, ("price", [1]), ("units", []))
