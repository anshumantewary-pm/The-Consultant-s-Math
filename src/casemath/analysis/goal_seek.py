"""Goal seek: what value of one input makes the model hit a target?

"What price do we need for a 20% margin?" "How many sessions until NPV is
zero?" Bisection on a bracket, so it works for any continuous model whose
output crosses the target inside the bracket.
"""

from __future__ import annotations

from dataclasses import dataclass

from casemath.analysis.model import Inputs, Model, check_inputs, evaluate
from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_count, require_number, require_positive


@dataclass(frozen=True)
class GoalSeek(Result):
    input: str
    target: float
    value: float
    output: float
    iterations: int


def goal_seek(
    model: Model,
    base: Inputs,
    name: str,
    target: float,
    low: float,
    high: float,
    tolerance: float = 1e-9,
    max_iterations: int = 200,
) -> GoalSeek:
    """Find the value of ``name`` in [low, high] where ``model`` equals ``target``."""
    checked = check_inputs(base, [name])
    target = require_number("target", target)
    low = require_number("low", low)
    high = require_number("high", high)
    tolerance = require_positive("tolerance", tolerance)
    max_iterations = require_count("max_iterations", max_iterations)
    if low >= high:
        raise ValidationError(f"low ({low:g}) must be below high ({high:g})")

    def gap(x: float) -> float:
        return evaluate(model, {**checked, name: x}) - target

    g_low, g_high = gap(low), gap(high)
    for edge, g in ((low, g_low), (high, g_high)):
        if g == 0:
            return GoalSeek(name, target, edge, target, 0)
    if (g_low < 0) == (g_high < 0):
        raise ValidationError(
            f"the output does not cross {target:g} between {name} = {low:g} and {high:g} "
            f"(gaps {g_low:,.4g} and {g_high:,.4g}); widen the bracket"
        )
    for iteration in range(1, max_iterations + 1):
        mid = (low + high) / 2
        g_mid = gap(mid)
        if g_mid == 0 or (high - low) / 2 < tolerance:
            return GoalSeek(name, target, mid, g_mid + target, iteration)
        if (g_mid < 0) == (g_low < 0):
            low, g_low = mid, g_mid
        else:
            high = mid
    raise ValidationError(f"goal seek did not converge in {max_iterations} iterations")
