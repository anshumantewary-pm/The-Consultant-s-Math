import json

import pytest

from casemath.calculators import SizingSegment, bottom_up, top_down
from casemath.core import ValidationError


class TestTopDown:
    def test_funnel(self) -> None:
        size = top_down(
            population=1_000_000,
            filters=[("urban", 0.5), ("own a car", 0.2)],
            units_per_customer=4,
            price_per_unit=25,
        )
        assert size.customers == pytest.approx(100_000)
        assert size.units_per_year == pytest.approx(400_000)
        assert size.value_per_year == pytest.approx(10_000_000)
        labels = [step.label for step in size.steps]
        assert labels[0] == "Starting population"
        assert labels[1] == "x 50% urban"
        assert len(size.steps) == 5
        assert size.steps[-1].value == size.value_per_year

    def test_no_filters(self) -> None:
        assert top_down(100, [], 1, 1).value_per_year == 100

    def test_rejects_bad_filter(self) -> None:
        with pytest.raises(ValidationError, match="filter 'urban'"):
            top_down(100, [("urban", 1.5)], 1, 1)

    def test_json(self) -> None:
        size = top_down(100, [("a", 0.5)], 2, 3)
        assert json.loads(json.dumps(size.to_dict()))["value_per_year"] == 300


class TestBottomUp:
    def test_sum_of_segments(self) -> None:
        size = bottom_up(
            [
                SizingSegment("Small clinics", count=1_000, units_per_year=2, price_per_unit=500),
                SizingSegment("Hospitals", count=100, units_per_year=20, price_per_unit=450),
            ]
        )
        assert size.customers == 1_100
        assert size.units_per_year == 4_000
        assert size.value_per_year == 1_000_000 + 900_000
        assert size.steps[-1].label == "Total"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            bottom_up([])

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError, match=r"Bad\.count"):
            bottom_up([SizingSegment("Bad", -1, 1, 1)])
