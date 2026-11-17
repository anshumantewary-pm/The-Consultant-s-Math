import random
import statistics

import pytest

from casemath.analysis.distributions import (
    Distribution,
    Fixed,
    Normal,
    Triangular,
    Uniform,
    parse_distribution,
)
from casemath.core import ValidationError


def draws(dist: Distribution, n: int = 20_000) -> list[float]:
    rng = random.Random(7)
    return [dist.sample(rng) for _ in range(n)]


class TestShapes:
    def test_fixed(self) -> None:
        assert set(draws(Fixed(3), 10)) == {3}
        assert Fixed(3).mean == 3

    def test_uniform(self) -> None:
        values = draws(Uniform(4, 6))
        assert min(values) >= 4
        assert max(values) <= 6
        assert statistics.fmean(values) == pytest.approx(Uniform(4, 6).mean, abs=0.02)

    def test_triangular(self) -> None:
        dist = Triangular(4, 5, 9)
        values = draws(dist)
        assert min(values) >= 4
        assert max(values) <= 9
        assert statistics.fmean(values) == pytest.approx(dist.mean, abs=0.03)

    def test_normal(self) -> None:
        values = draws(Normal(10, 2))
        assert statistics.fmean(values) == pytest.approx(10, abs=0.05)
        assert statistics.stdev(values) == pytest.approx(2, abs=0.05)
        assert Normal(10, 2).mean == 10

    def test_normal_clipped(self) -> None:
        values = draws(Normal(0.5, 1, floor=0, ceiling=1))
        assert min(values) == 0
        assert max(values) == 1

    def test_seed_reproducible(self) -> None:
        assert draws(Normal(0, 1), 5) == draws(Normal(0, 1), 5)


class TestValidation:
    def test_uniform_order(self) -> None:
        with pytest.raises(ValidationError, match="must not exceed"):
            Uniform(6, 4)

    def test_triangular_order(self) -> None:
        with pytest.raises(ValidationError, match="low <= mode <= high"):
            Triangular(4, 10, 9)

    def test_normal_sigma(self) -> None:
        with pytest.raises(ValidationError, match="sigma"):
            Normal(0, -1)

    def test_normal_bounds(self) -> None:
        with pytest.raises(ValidationError, match="floor"):
            Normal(0, 1, floor=2, ceiling=1)

    def test_fixed_finite(self) -> None:
        with pytest.raises(ValidationError, match="value"):
            Fixed(float("inf"))


class TestParse:
    @pytest.mark.parametrize(
        ("spec", "expected"),
        [
            ("5", Fixed(5)),
            ("fixed:5", Fixed(5)),
            ("uniform:4:6", Uniform(4, 6)),
            ("tri:4:5:7", Triangular(4, 5, 7)),
            ("triangular:4:5:7", Triangular(4, 5, 7)),
            ("normal:5:0.5", Normal(5, 0.5)),
            ("normal:0.3:0.1:0:1", Normal(0.3, 0.1, 0, 1)),
        ],
    )
    def test_valid(self, spec: str, expected: object) -> None:
        assert parse_distribution(spec) == expected

    @pytest.mark.parametrize(
        ("spec", "message"),
        [
            ("abc", "neither a number"),
            ("beta:1:2", "unknown distribution"),
            ("tri:1:x:3", "only numbers"),
            ("tri:1:2", "takes 3 number"),
        ],
    )
    def test_invalid(self, spec: str, message: str) -> None:
        with pytest.raises(ValidationError, match=message):
            parse_distribution(spec)
