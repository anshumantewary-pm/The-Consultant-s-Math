"""What the analysis tools operate on: a model is a function of named inputs.

A ``Model`` takes a mapping like ``{"price": 10, "units": 1000}`` and returns
one number (profit, NPV, LTV...). Any calculator can be wrapped as a model
with a one-line lambda, so sensitivity, goal seek and simulation work on all
of them without knowing what they compute.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from casemath.core.errors import ValidationError
from casemath.core.validate import require_number

Inputs = Mapping[str, float]
Model = Callable[[Inputs], float]


def check_inputs(base: Inputs, names: Sequence[str] = ()) -> dict[str, float]:
    """Validate a base case and that every name in ``names`` is one of its inputs."""
    if not base:
        raise ValidationError("base inputs must not be empty")
    checked = {key: require_number(key, value) for key, value in base.items()}
    for name in names:
        if name not in checked:
            known = ", ".join(checked)
            raise ValidationError(f"unknown input {name!r}; the model's inputs are: {known}")
    return checked


def evaluate(model: Model, inputs: Inputs) -> float:
    """Run the model and insist on a finite number back."""
    return require_number("model output", model(inputs))
