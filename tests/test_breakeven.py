import pytest

from casemath.calculators import (
    break_even_analysis,
    break_even_price,
    break_even_revenue,
    break_even_units,
    margin_of_safety,
    operating_leverage,
    payback_period,
    units_for_target_profit,
)
from casemath.core import ValidationError


class TestBreakEvenUnits:
    def test_classic(self) -> None:
        assert break_even_units(fixed_costs=100_000, price=10, variable_cost_per_unit=6) == 25_000

    def test_fractional(self) -> None:
        assert break_even_units(1_000, 7, 4) == pytest.approx(333.333, rel=1e-4)

    def test_zero_fixed_costs(self) -> None:
        assert break_even_units(0, 10, 6) == 0

    @pytest.mark.parametrize(("price", "cost"), [(6, 6), (5, 6)])
    def test_no_break_even_when_unit_margin_not_positive(self, price: float, cost: float) -> None:
        with pytest.raises(ValidationError, match="no break-even"):
            break_even_units(1_000, price, cost)

    def test_rejects_negative_fixed_costs(self) -> None:
        with pytest.raises(ValidationError, match="fixed_costs"):
            break_even_units(-1, 10, 6)


def test_break_even_revenue() -> None:
    # 40% contribution margin -> 100,000 / 0.4
    assert break_even_revenue(100_000, 10, 6) == pytest.approx(250_000)


class TestTargetProfit:
    def test_target(self) -> None:
        assert units_for_target_profit(20_000, 100_000, 10, 6) == 30_000

    def test_acceptable_loss(self) -> None:
        assert units_for_target_profit(-20_000, 100_000, 10, 6) == 20_000

    def test_floor_at_zero(self) -> None:
        assert units_for_target_profit(-500_000, 100_000, 10, 6) == 0


class TestBreakEvenPrice:
    def test_price(self) -> None:
        assert break_even_price(fixed_costs=50_000, units=10_000, variable_cost_per_unit=3) == 8

    def test_rejects_zero_units(self) -> None:
        with pytest.raises(ValidationError, match="units must be > 0"):
            break_even_price(50_000, 0, 3)


class TestMarginOfSafety:
    def test_positive(self) -> None:
        assert margin_of_safety(expected_units=40_000, break_even=25_000) == pytest.approx(0.375)

    def test_negative_when_below_break_even(self) -> None:
        assert margin_of_safety(20_000, 25_000) == pytest.approx(-0.25)


class TestPayback:
    def test_payback(self) -> None:
        assert payback_period(investment=500_000, cash_flow_per_period=125_000) == 4

    @pytest.mark.parametrize("flow", [0, -10])
    def test_never_paid_back(self, flow: float) -> None:
        with pytest.raises(ValidationError, match="never paid back"):
            payback_period(500_000, flow)


class TestAnalysis:
    def test_full(self) -> None:
        a = break_even_analysis(100_000, 10, 6, expected_units=40_000)
        assert a.break_even_units == 25_000
        assert a.break_even_units_whole == 25_000
        assert a.break_even_revenue == 250_000
        assert a.contribution_per_unit == 4
        assert a.contribution_margin == pytest.approx(0.4)
        assert a.margin_of_safety == pytest.approx(0.375)

    def test_rounds_up_to_whole_units(self) -> None:
        a = break_even_analysis(1_000, 7, 4)
        assert a.break_even_units_whole == 334
        assert a.expected_units is None
        assert a.margin_of_safety is None


class TestOperatingLeverage:
    def test_dol(self) -> None:
        # Contribution 160,000, profit 60,000: DOL 2.67
        assert operating_leverage(10, 40_000, 6, 100_000) == pytest.approx(160 / 60)

    def test_predicts_profit_sensitivity(self) -> None:
        dol = operating_leverage(10, 40_000, 6, 100_000)
        base = 40_000 * 4 - 100_000
        bumped = 40_400 * 4 - 100_000
        assert (bumped - base) / base == pytest.approx(dol * 0.01)

    def test_below_break_even(self) -> None:
        with pytest.raises(ValidationError, match="above break-even"):
            operating_leverage(10, 20_000, 6, 100_000)
