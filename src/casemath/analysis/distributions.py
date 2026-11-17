"""Uncertain inputs for Monte Carlo simulation.

Each distribution draws from a ``random.Random`` passed in by the simulator,
so a seed makes a whole run reproducible. Stdlib only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_non_negative, require_number


@dataclass(frozen=True)
class Distribution(Result):
    """Base class. Subclasses implement ``sample`` and ``mean``."""

    def sample(self, rng: random.Random) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def mean(self) -> float:  # pragma: no cover - abstract
        raise NotImplementedError


@dataclass(frozen=True)
class Fixed(Distribution):
    """No uncertainty: always ``value``."""

    value: float

    def __post_init__(self) -> None:
        require_number("value", self.value)

    def sample(self, rng: random.Random) -> float:
        return float(self.value)

    @property
    def mean(self) -> float:
        return float(self.value)


@dataclass(frozen=True)
class Uniform(Distribution):
    """Every value between ``low`` and ``high`` equally likely."""

    low: float
    high: float

    def __post_init__(self) -> None:
        if require_number("low", self.low) > require_number("high", self.high):
            raise ValidationError(f"low ({self.low:g}) must not exceed high ({self.high:g})")

    def sample(self, rng: random.Random) -> float:
        return rng.uniform(self.low, self.high)

    @property
    def mean(self) -> float:
        return (self.low + self.high) / 2


@dataclass(frozen=True)
class Triangular(Distribution):
    """Low / most likely / high: the natural way to write down an expert's guess."""

    low: float
    mode: float
    high: float

    def __post_init__(self) -> None:
        low = require_number("low", self.low)
        mode = require_number("mode", self.mode)
        high = require_number("high", self.high)
        if not low <= mode <= high:
            raise ValidationError(f"need low <= mode <= high, got {low:g}, {mode:g}, {high:g}")

    def sample(self, rng: random.Random) -> float:
        return rng.triangular(self.low, self.high, self.mode)

    @property
    def mean(self) -> float:
        return (self.low + self.mode + self.high) / 3


@dataclass(frozen=True)
class Normal(Distribution):
    """Bell curve, optionally clipped to [floor, ceiling] (e.g. a share stays in 0..1)."""

    mu: float
    sigma: float
    floor: float | None = None
    ceiling: float | None = None

    def __post_init__(self) -> None:
        require_number("mu", self.mu)
        require_non_negative("sigma", self.sigma)
        if self.floor is not None and self.ceiling is not None and self.floor > self.ceiling:
            raise ValidationError("floor must not exceed ceiling")

    def sample(self, rng: random.Random) -> float:
        value = rng.gauss(self.mu, self.sigma)
        if self.floor is not None:
            value = max(self.floor, value)
        if self.ceiling is not None:
            value = min(self.ceiling, value)
        return value

    @property
    def mean(self) -> float:
        """The unclipped mean; clipping shifts the true mean slightly."""
        return float(self.mu)


_SHAPES: dict[str, tuple[type[Distribution], tuple[int, ...]]] = {
    "fixed": (Fixed, (1,)),
    "uniform": (Uniform, (2,)),
    "tri": (Triangular, (3,)),
    "triangular": (Triangular, (3,)),
    "normal": (Normal, (2, 3, 4)),
}


def parse_distribution(spec: str) -> Distribution:
    """Read the CLI form: ``5``, ``uniform:4:6``, ``tri:4:5:7``, ``normal:5:0.5[:lo[:hi]]``."""
    kind, sep, rest = spec.strip().partition(":")
    if not sep:
        try:
            return Fixed(float(kind))
        except ValueError:
            raise ValidationError(
                f"{spec!r} is neither a number nor KIND:ARGS (kinds: {', '.join(_SHAPES)})"
            ) from None
    if kind not in _SHAPES:
        raise ValidationError(f"unknown distribution {kind!r}; use one of: {', '.join(_SHAPES)}")
    try:
        numbers = [float(p) for p in rest.split(":")]
    except ValueError:
        raise ValidationError(
            f"distribution {spec!r} must have only numbers after {kind}:"
        ) from None
    cls, counts = _SHAPES[kind]
    if len(numbers) not in counts:
        expected = " or ".join(str(c) for c in counts)
        raise ValidationError(f"{kind} takes {expected} number(s), got {len(numbers)} in {spec!r}")
    return cls(*numbers)
