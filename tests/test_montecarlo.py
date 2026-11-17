import json

import pytest

from casemath.analysis.distributions import Normal, Triangular, Uniform
from casemath.analysis.model import Inputs
from casemath.analysis.montecarlo import histogram, percentile, render_histogram, simulate
from casemath.core import ValidationError


def profit(x: Inputs) -> float:
    return (x["price"] - x["unit_cost"]) * x["units"] - x["fixed"]


class TestPercentile:
    def test_interpolates(self) -> None:
        assert percentile([0, 10], 50) == 5
        assert percentile([1, 2, 3, 4, 5], 0) == 1
        assert percentile([1, 2, 3, 4, 5], 100) == 5
        assert percentile([7.0], 90) == 7

    def test_empty(self) -> None:
        with pytest.raises(ValidationError, match="no values"):
            percentile([], 50)

    def test_range(self) -> None:
        with pytest.raises(ValidationError, match="between 0 and 100"):
            percentile([1], 101)


class TestSimulate:
    def test_all_fixed_has_no_spread(self) -> None:
        sim = simulate(profit, {"price": 10, "unit_cost": 6, "units": 1_000, "fixed": 2_500})
        assert sim.mean == pytest.approx(1_500)
        assert sim.stdev == pytest.approx(0)
        assert sim.prob_below_threshold == 0

    def test_uniform_units(self) -> None:
        # Profit = 4 x units - 2,500 with units ~ U(0, 1,250): loss when units < 625, p = 0.5
        sim = simulate(
            profit,
            {"price": 10, "unit_cost": 6, "units": Uniform(0, 1_250), "fixed": 2_500},
            runs=20_000,
        )
        assert sim.prob_below_threshold == pytest.approx(0.5, abs=0.02)
        assert sim.mean == pytest.approx(0, abs=40)
        assert sim.deterministic == pytest.approx(0)
        assert sim.minimum >= -2_500
        assert sim.maximum <= 2_500

    def test_percentiles_ordered(self) -> None:
        sim = simulate(lambda x: x["a"], {"a": Normal(100, 15)}, runs=5_000)
        values = list(sim.percentiles.values())
        assert values == sorted(values)
        assert sim.p50 == pytest.approx(100, abs=1.5)
        low, high = sim.band_90
        assert low == pytest.approx(100 - 1.645 * 15, abs=2)
        assert high == pytest.approx(100 + 1.645 * 15, abs=2)

    def test_reproducible_with_seed(self) -> None:
        inputs = {"a": Triangular(1, 2, 5)}
        a = simulate(lambda x: x["a"], inputs, runs=100, seed=1)
        b = simulate(lambda x: x["a"], inputs, runs=100, seed=1)
        c = simulate(lambda x: x["a"], inputs, runs=100, seed=2)
        assert a == b
        assert a.mean != c.mean

    def test_custom_threshold(self) -> None:
        sim = simulate(lambda x: x["a"], {"a": Uniform(0, 1)}, runs=10_000, threshold=0.25)
        assert sim.prob_below_threshold == pytest.approx(0.25, abs=0.02)

    def test_json(self) -> None:
        sim = simulate(lambda x: x["a"], {"a": Uniform(0, 1)}, runs=10)
        assert set(json.loads(json.dumps(sim.to_dict()))["percentiles"]) >= {"p5", "p95"}

    def test_validation(self) -> None:
        with pytest.raises(ValidationError, match="inputs must not be empty"):
            simulate(profit, {})
        with pytest.raises(ValidationError, match="runs"):
            simulate(lambda x: x["a"], {"a": 1}, runs=1)


class TestHistogram:
    def test_counts_add_up(self) -> None:
        bins = histogram([float(v) for v in range(100)], bins=10)
        assert len(bins) == 10
        assert sum(b.count for b in bins) == 100
        assert bins[-1].count == 10  # max lands in the last bin

    def test_single_value(self) -> None:
        assert histogram([3.0, 3.0]) == histogram([3.0, 3.0], bins=5)
        assert histogram([3.0, 3.0])[0].count == 2

    def test_empty(self) -> None:
        with pytest.raises(ValidationError, match="no values"):
            histogram([])

    def test_render(self) -> None:
        lines = render_histogram(histogram([0.0, 0.0, 0.0, 1.0], bins=2), width=6)
        assert lines[0].endswith("###### 3")
        assert lines[1].endswith("## 1")

    def test_simulation_has_histogram(self) -> None:
        sim = simulate(lambda x: x["a"], {"a": Uniform(0, 1)}, runs=500)
        assert sum(b.count for b in sim.histogram) == 500
