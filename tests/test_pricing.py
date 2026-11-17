import pytest

from casemath.calculators.pricing import (
    arc_elasticity,
    breakeven_volume_change,
    markup_price,
    optimal_price_linear,
    volume_after_price_change,
)
from casemath.core import ValidationError


class TestArcElasticity:
    def test_elastic(self) -> None:
        # 10 -> 12 (+18.2% midpoint), 100 -> 80 (-22.2%): -1.22
        assert arc_elasticity(10, 100, 12, 80) == pytest.approx(-1.2222, abs=1e-4)

    def test_symmetric(self) -> None:
        assert arc_elasticity(10, 100, 12, 80) == pytest.approx(arc_elasticity(12, 80, 10, 100))

    def test_same_price(self) -> None:
        with pytest.raises(ValidationError, match="must differ"):
            arc_elasticity(10, 100, 10, 80)

    def test_zero_units(self) -> None:
        with pytest.raises(ValidationError, match="both be zero"):
            arc_elasticity(10, 0, 12, 0)


class TestBreakevenVolumeChange:
    def test_price_cut(self) -> None:
        assert breakeven_volume_change(-0.10, 0.30) == pytest.approx(0.5)

    def test_price_rise_can_lose_volume(self) -> None:
        # +10% at 30% margin: can lose 25% of volume and still earn the same.
        assert breakeven_volume_change(0.10, 0.30) == pytest.approx(-0.25)

    def test_impossible(self) -> None:
        with pytest.raises(ValidationError, match="no volume increase"):
            breakeven_volume_change(-0.30, 0.30)


class TestVolumeAfterPriceChange:
    def test_constant_elasticity(self) -> None:
        assert volume_after_price_change(1_000, 0.10, -2) == pytest.approx(1_000 * 1.1**-2)

    def test_rejects_price_to_zero(self) -> None:
        with pytest.raises(ValidationError, match="above -100%"):
            volume_after_price_change(1_000, -1, -2)


class TestMarkupPrice:
    def test_lerner(self) -> None:
        # e = -3: P = c x 3 / 2
        assert markup_price(10, -3) == pytest.approx(15)

    @pytest.mark.parametrize("e", [-1, -0.5, 0.2])
    def test_inelastic_rejected(self, e: float) -> None:
        with pytest.raises(ValidationError, match="below -1"):
            markup_price(10, e)


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
