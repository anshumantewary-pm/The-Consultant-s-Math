"""Sensitivity analysis: which inputs move the answer, and by how much."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from casemath.analysis.model import Inputs, Model, check_inputs, evaluate
from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_number, require_numbers, require_positive


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


@dataclass(frozen=True)
class TornadoBar(Result):
    input: str
    low_value: float
    high_value: float
    output_at_low: float
    output_at_high: float

    @property
    def swing(self) -> float:
        """Width of the bar: how far the output moves across the input's range."""
        return abs(self.output_at_high - self.output_at_low)


@dataclass(frozen=True)
class Tornado(Result):
    base_output: float
    bars: tuple[TornadoBar, ...]  # widest first

    @property
    def most_sensitive(self) -> str:
        return self.bars[0].input


def tornado(
    model: Model,
    base: Inputs,
    ranges: Mapping[str, tuple[float, float]] | None = None,
    pct: float = 0.10,
) -> Tornado:
    """Swing each input between a low and a high value; rank inputs by output swing.

    Pass explicit ``ranges`` ({name: (low, high)}), or leave them out to move every
    input by +/- ``pct`` of its base value. This is the chart that tells you
    where to spend diligence time: the top bar is the assumption that matters.
    """
    checked = check_inputs(base)
    if ranges is None:
        pct = require_positive("pct", pct)
        ranges = {k: (v * (1 - pct), v * (1 + pct)) for k, v in checked.items() if v != 0}
        if not ranges:
            raise ValidationError("every base input is zero; give explicit ranges")
    check_inputs(checked, list(ranges))
    bars = []
    for name, (low, high) in ranges.items():
        low = require_number(f"{name} low", low)
        high = require_number(f"{name} high", high)
        bars.append(
            TornadoBar(
                input=name,
                low_value=low,
                high_value=high,
                output_at_low=evaluate(model, {**checked, name: low}),
                output_at_high=evaluate(model, {**checked, name: high}),
            )
        )
    bars.sort(key=lambda bar: bar.swing, reverse=True)
    return Tornado(base_output=evaluate(model, checked), bars=tuple(bars))
