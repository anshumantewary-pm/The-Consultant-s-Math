"""Sensitivity analysis: which inputs move the answer, and by how much."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from casemath.analysis.model import Inputs, Model, check_inputs, evaluate
from casemath.core.result import Result
from casemath.core.validate import require_numbers


@dataclass(frozen=True)
class OneWay(Result):
    input: str
    values: tuple[float, ...]
    outputs: tuple[float, ...]
    base_value: float
    base_output: float


def one_way(model: Model, base: Inputs, name: str, values: Sequence[float]) -> OneWay:
    """Re-run ``model`` with ``name`` set to each of ``values``, holding the rest at base."""
    checked = check_inputs(base, [name])
    points = require_numbers("values", values)
    outputs = tuple(evaluate(model, {**checked, name: v}) for v in points)
    return OneWay(
        input=name,
        values=points,
        outputs=outputs,
        base_value=checked[name],
        base_output=evaluate(model, checked),
    )
