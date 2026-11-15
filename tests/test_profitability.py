import json

import pytest

from casemath.calculators import (
    Segment,
    profit_bridge,
    profit_statement,
    segment_profitability,
)
from casemath.core import ValidationError


class TestProfitStatement:
    def test_basic_pnl(self) -> None:
        st = profit_statement(price=10, units=1_000, variable_cost_per_unit=6, fixed_costs=2_500)
        assert st.revenue == 10_000
        assert st.variable_costs == 6_000
        assert st.contribution == 4_000
        assert st.contribution_per_unit == 4
        assert st.contribution_margin == pytest.approx(0.4)
        assert st.total_costs == 8_500
        assert st.profit == 1_500
        assert st.profit_margin == pytest.approx(0.15)

    def test_loss(self) -> None:
        st = profit_statement(price=5, units=100, variable_cost_per_unit=4, fixed_costs=500)
        assert st.profit == -400
        assert st.profit_margin == pytest.approx(-0.8)

    def test_zero_revenue_gives_zero_margins(self) -> None:
        st = profit_statement(price=10, units=0, variable_cost_per_unit=6, fixed_costs=100)
        assert st.revenue == 0
        assert st.contribution_margin == 0
        assert st.profit_margin == 0
        assert st.profit == -100

    @pytest.mark.parametrize(
        "field", ["price", "units", "variable_cost_per_unit", "fixed_costs"]
    )
    def test_rejects_negative_inputs(self, field: str) -> None:
        kwargs = {"price": 10.0, "units": 1.0, "variable_cost_per_unit": 1.0, "fixed_costs": 1.0}
        kwargs[field] = -1.0
        with pytest.raises(ValidationError, match=field):
            profit_statement(**kwargs)

    def test_json_round_trip(self) -> None:
        st = profit_statement(10, 1_000, 6, 2_500)
        assert json.loads(json.dumps(st.to_dict()))["profit"] == 1_500


class TestProfitBridge:
    def test_effects_sum_to_change(self) -> None:
        before = profit_statement(10, 1_000, 6, 2_000)
        after = profit_statement(9, 1_200, 6.5, 2_300)
        bridge = profit_bridge(before, after)
        total = sum(bridge.effects.values())
        assert total == pytest.approx(bridge.profit_change)
        assert bridge.profit_change == pytest.approx(after.profit - before.profit)

    def test_individual_effects(self) -> None:
        before = profit_statement(10, 1_000, 6, 2_000)
        after = profit_statement(9, 1_200, 6.5, 2_300)
        bridge = profit_bridge(before, after)
        assert bridge.volume_effect == pytest.approx(4 * 200)
        assert bridge.price_effect == pytest.approx(-1 * 1_200)
        assert bridge.variable_cost_effect == pytest.approx(-0.5 * 1_200)
        assert bridge.fixed_cost_effect == pytest.approx(-300)
        assert bridge.biggest_driver == "price"

    def test_no_change(self) -> None:
        st = profit_statement(10, 1_000, 6, 2_000)
        bridge = profit_bridge(st, st)
        assert bridge.profit_change == 0
        assert all(value == 0 for value in bridge.effects.values())

    @pytest.mark.parametrize(
        ("after_args", "driver"),
        [
            ((10, 2_000, 6, 2_000), "volume"),
            ((10, 1_000, 8, 2_000), "variable_cost"),
            ((10, 1_000, 6, 5_000), "fixed_cost"),
        ],
    )
    def test_biggest_driver(self, after_args: tuple[float, ...], driver: str) -> None:
        before = profit_statement(10, 1_000, 6, 2_000)
        assert profit_bridge(before, profit_statement(*after_args)).biggest_driver == driver


class TestSegmentProfitability:
    def _segments(self) -> list[Segment]:
        return [
            Segment("Retail", price=20, units=1_000, variable_cost_per_unit=12, fixed_costs=3_000),
            Segment("Online", price=18, units=2_000, variable_cost_per_unit=10, fixed_costs=4_000),
            Segment("B2B", price=15, units=500, variable_cost_per_unit=14, fixed_costs=1_000),
        ]

    def test_totals_and_sorting(self) -> None:
        report = segment_profitability(self._segments(), shared_fixed_costs=2_000)
        assert [line.name for line in report.lines] == ["Online", "Retail", "B2B"]
        assert report.total_revenue == 20_000 + 36_000 + 7_500
        # Segment profits: Retail 5,000; Online 12,000; B2B -500 -> 16,500 - 2,000 shared
        assert report.total_profit == 14_500
        assert report.shared_fixed_costs == 2_000

    def test_shares_sum_to_one(self) -> None:
        report = segment_profitability(self._segments())
        assert sum(line.share_of_revenue for line in report.lines) == pytest.approx(1)
        assert sum(line.share_of_profit for line in report.lines) == pytest.approx(1)
        assert report.line("B2B").share_of_profit < 0

    def test_zero_totals(self) -> None:
        report = segment_profitability([Segment("A", 10, 0, 5, 0)])
        assert report.lines[0].share_of_revenue == 0
        assert report.lines[0].share_of_profit == 0

    def test_unknown_line(self) -> None:
        with pytest.raises(ValidationError, match="no segment named 'X'"):
            segment_profitability(self._segments()).line("X")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="segments must not be empty"):
            segment_profitability([])

    def test_rejects_duplicate_names(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            segment_profitability([Segment("A", 1, 1, 1), Segment("A", 2, 2, 2)])
