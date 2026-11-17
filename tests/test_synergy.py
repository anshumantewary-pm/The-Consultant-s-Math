import json

import pytest

from casemath.calculators import (
    SynergyItem,
    acquisition_premium,
    synergy_schedule,
    synergy_value,
)
from casemath.core import ValidationError

ITEMS = (
    SynergyItem("Procurement", 10.0),
    SynergyItem("Cross-sell", 40.0, kind="revenue", margin=0.25),
)


class TestSynergyItem:
    def test_profit_run_rate(self) -> None:
        assert ITEMS[0].profit_run_rate == 10
        assert ITEMS[1].profit_run_rate == 10
        haircut = SynergyItem("Cross-sell", 40.0, kind="revenue", margin=0.25, probability=0.5)
        assert haircut.profit_run_rate == 5

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"name": " ", "run_rate": 1}, "blank"),
            ({"name": "a", "run_rate": -1}, "run_rate"),
            ({"name": "a", "run_rate": 1, "kind": "tax"}, "kind"),
            ({"name": "a", "run_rate": 1, "margin": 0.5}, "revenue synergies only"),
            ({"name": "a", "run_rate": 1, "kind": "revenue", "margin": 2}, "margin"),
            ({"name": "a", "run_rate": 1, "probability": 1.5}, "probability"),
        ],
    )
    def test_errors(self, kwargs: dict[str, object], match: str) -> None:
        with pytest.raises(ValidationError, match=match):
            SynergyItem(**kwargs)  # type: ignore[arg-type]


class TestSchedule:
    def test_worked_example(self) -> None:
        plan = synergy_schedule(ITEMS, [0.5, 1.0, 1.0], [15.0, 5.0])
        assert plan.run_rate_cost == 10
        assert plan.run_rate_revenue == 10
        assert plan.run_rate_total == 20
        assert plan.integration_costs == 20
        assert [y.net for y in plan.years] == [-5, 15, 20]
        assert [y.cumulative for y in plan.years] == [-5, 10, 30]
        assert plan.payback_year == 2
        assert json.loads(json.dumps(plan.to_dict()))["years"][2]["integration_costs"] == 0

    def test_never_pays_back(self) -> None:
        plan = synergy_schedule(ITEMS, [0.1, 0.2], [100.0])
        assert plan.payback_year is None

    @pytest.mark.parametrize(
        ("items", "phase", "costs", "match"),
        [
            ((), [1.0], [], "items"),
            (ITEMS, [], [], "phase_in"),
            (ITEMS, [1.5], [], r"phase_in\[0\]"),
            (ITEMS, [1.0], [-1.0], r"integration_costs\[0\]"),
            (ITEMS, [1.0], [1.0, 1.0], "only 1"),
            ((ITEMS[0], ITEMS[0]), [1.0], [], "duplicate"),
        ],
    )
    def test_errors(
        self,
        items: tuple[SynergyItem, ...],
        phase: list[float],
        costs: list[float],
        match: str,
    ) -> None:
        with pytest.raises(ValidationError, match=match):
            synergy_schedule(items, phase, costs)


def test_synergy_value() -> None:
    assert synergy_value(20, 8, 30) == 130
    assert synergy_value(20, 8) == 160
    with pytest.raises(ValidationError, match="multiple"):
        synergy_value(20, -1)


def test_premium() -> None:
    assert acquisition_premium(520, 400) == pytest.approx(0.3)
    with pytest.raises(ValidationError, match="standalone_value"):
        acquisition_premium(520, 0)
