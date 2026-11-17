"""Monte Carlo simulation: put ranges on the inputs, get a range on the answer.

A point estimate says "profit is $1.5M". A simulation says "profit is $1.5M on
average, there is a 22% chance of a loss, and the 90% band is -$0.4M to $3.1M",
which is what an investment committee actually needs.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Mapping
from dataclasses import dataclass

from casemath.analysis.distributions import Distribution, Fixed
from casemath.analysis.model import Model, evaluate
from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_count, require_number

PERCENTILES = (5, 10, 25, 50, 75, 90, 95)


def percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolated percentile of already-sorted values (pct in 0..100)."""
    if not sorted_values:
        raise ValidationError("cannot take a percentile of no values")
    pct = require_number("pct", pct)
    if not 0 <= pct <= 100:
        raise ValidationError(f"pct must be between 0 and 100, got {pct:g}")
    position = (len(sorted_values) - 1) * pct / 100
    lower = math.floor(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


@dataclass(frozen=True)
class Simulation(Result):
    runs: int
    seed: int | None
    mean: float
    stdev: float
    minimum: float
    maximum: float
    percentiles: dict[str, float]  # "p5", "p50", ...
    threshold: float
    prob_below_threshold: float
    deterministic: float  # the model at every input's mean, for comparison

    @property
    def p50(self) -> float:
        return self.percentiles["p50"]

    @property
    def band_90(self) -> tuple[float, float]:
        return self.percentiles["p5"], self.percentiles["p95"]


def simulate(
    model: Model,
    inputs: Mapping[str, Distribution | float],
    runs: int = 10_000,
    seed: int | None = 42,
    threshold: float = 0.0,
) -> Simulation:
    """Sample every input ``runs`` times, run the model, and summarise the outputs.

    Plain numbers in ``inputs`` are held fixed. ``threshold`` (default 0) sets
    the "probability below" line: with a profit model, that is the chance of a loss.
    """
    if not inputs:
        raise ValidationError("inputs must not be empty")
    runs = require_count("runs", runs, minimum=2)
    threshold = require_number("threshold", threshold)
    dists = {
        name: value if isinstance(value, Distribution) else Fixed(require_number(name, value))
        for name, value in inputs.items()
    }
    rng = random.Random(seed)
    outputs = sorted(
        evaluate(model, {name: d.sample(rng) for name, d in dists.items()}) for _ in range(runs)
    )
    below = sum(1 for v in outputs if v < threshold)
    return Simulation(
        runs=runs,
        seed=seed,
        mean=statistics.fmean(outputs),
        stdev=statistics.stdev(outputs),
        minimum=outputs[0],
        maximum=outputs[-1],
        percentiles={f"p{p}": percentile(outputs, p) for p in PERCENTILES},
        threshold=threshold,
        prob_below_threshold=below / runs,
        deterministic=evaluate(model, {name: d.mean for name, d in dists.items()}),
    )
