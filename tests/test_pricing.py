import json

import pytest

from casemath.calculators import (
    break_even_volume_change,
    optimal_price_linear,
    price_change_impact,
    price_elasticity,
    profit_maximising_price,
    volume_after_price_change,
)
from casemath.core import ValidationError


class TestElasticity:
    def test_worked_example(self) -> None:
        # Units -10% on midpoint (-100 / 950), price +9.52% (4 / 42)
        assert price_elasticity(40, 1000, 44, 900) == pytest.approx(-1.1053, rel=1e-4)

    def test_symmetric(self) -> None:
        assert price_elasticity(40, 1000, 44, 900) == pytest.approx(
            price_elasticity(44, 900, 40, 1000)
        )

    def test_volume_to_zero(self) -> None:
        assert price_elasticity(10, 100, 20, 0) == pytest.approx(-3.0)

    @pytest.mark.parametrize(
        ("args", "match"),
        [
            ((10, 100, 10, 90), "must differ"),
            ((10, 0, 12, 0), "not both be 0"),
            ((0, 100, 12, 90), "price_before"),
            ((10, -1, 12, 90), "units_before"),
        ],
    )
    def test_errors(self, args: tuple[float, float, float, float], match: str) -> None:
        with pytest.raises(ValidationError, match=match):
            price_elasticity(*args)


class TestBreakEvenVolume:
    def test_price_rise(self) -> None:
        # 75% margin, +15%: -0.15 / 0.90
        assert break_even_volume_change(40, 10, 0.15) == pytest.approx(-1 / 6)

    def test_price_cut(self) -> None:
        # 30% margin, -10%: 0.10 / 0.20 -> must gain 50% more volume
        assert break_even_volume_change(10, 7, -0.10) == pytest.approx(0.5)

    def test_cut_below_cost(self) -> None:
        with pytest.raises(ValidationError, match="above variable_cost_per_unit"):
            break_even_volume_change(10, 7, -0.4)

    def test_rate_floor(self) -> None:
        with pytest.raises(ValidationError, match="price_change"):
            break_even_volume_change(10, 7, -1)


class TestPriceChangeImpact:
    def test_inelastic_rise_pays(self) -> None:
        c = price_change_impact(40, 8000, 10, 50, -0.2, fixed_costs=100_000)
        assert c.price_change == pytest.approx(0.25)
        assert c.expected_volume_change == pytest.approx(-0.05)
        assert c.after.units == pytest.approx(7600)
        assert c.contribution_change == pytest.approx(7600 * 40 - 8000 * 30)
        assert c.profit_change == pytest.approx(c.contribution_change)
        assert c.pays_off
        assert c.break_even_volume_change == pytest.approx(-0.25)

    def test_elastic_rise_loses(self) -> None:
        c = price_change_impact(40, 1000, 10, 46, -2.0)
        assert not c.pays_off
        assert c.expected_volume_change < c.break_even_volume_change

    def test_volume_below_zero(self) -> None:
        with pytest.raises(ValidationError, match="linear model"):
            price_change_impact(10, 100, 5, 20, -1.5)

    def test_json(self) -> None:
        data = json.loads(json.dumps(price_change_impact(10, 100, 5, 11, -1).to_dict()))
        assert data["after"]["price"] == 11


class TestOptimalPrice:
    def test_markup_rule(self) -> None:
        # e = -2: P = 2 x VC
        assert profit_maximising_price(10, -2) == pytest.approx(20)

    @pytest.mark.parametrize("e", [-1, -0.5, 0.3])
    def test_inelastic(self, e: float) -> None:
        with pytest.raises(ValidationError, match="elastic demand"):
            profit_maximising_price(10, e)


class TestVolumeAfterPriceChange:
    def test_constant_elasticity(self) -> None:
        assert volume_after_price_change(1_000, 0.10, -2) == pytest.approx(1_000 * 1.1**-2)

    def test_rejects_price_to_zero(self) -> None:
        with pytest.raises(ValidationError, match="above -100%"):
            volume_after_price_change(1_000, -1, -2)


class TestOptimalPriceLinear:
    def test_optimum(self) -> None:
        # Q = 200 - 10P (points (10, 100) and (12, 80)); cost 4 -> P* = (20 + 4) / 2 = 12
        opt = optimal_price_linear(10, 100, 12, 80, unit_cost=4)
        assert opt.choke_price == pytest.approx(20)
        assert opt.price == pytest.approx(12)
        assert opt.units == pytest.approx(80)
        assert opt.contribution == pytest.approx(640)

    def test_is_a_maximum(self) -> None:
        opt = optimal_price_linear(10, 100, 12, 80, unit_cost=4)
        for p in (opt.price - 0.5, opt.price + 0.5):
            assert (p - 4) * (opt.intercept - opt.slope * p) < opt.contribution

    def test_same_price(self) -> None:
        with pytest.raises(ValidationError, match="must differ"):
            optimal_price_linear(10, 100, 10, 80, 4)

    def test_upward_demand(self) -> None:
        with pytest.raises(ValidationError, match="demand must fall"):
            optimal_price_linear(10, 100, 12, 120, 4)

    def test_cost_above_choke(self) -> None:
        with pytest.raises(ValidationError, match="choke price"):
            optimal_price_linear(10, 100, 12, 80, 25)
