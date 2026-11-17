"""Scenario analysis: named sets of overrides on a base case, side by side."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from casemath.analysis.model import Inputs, Model, check_inputs, evaluate
from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_fraction


@dataclass(frozen=True)
class ScenarioRow(Result):
    name: str
    overrides: dict[str, float]
    output: float
    change_vs_base: float
    probability: float | None


@dataclass(frozen=True)
class ScenarioTable(Result):
    base_output: float
    rows: tuple[ScenarioRow, ...]
    expected_value: float | None  # probability-weighted, when probabilities are given

    @property
    def worst(self) -> ScenarioRow:
        return min(self.rows, key=lambda r: r.output)

    @property
    def best(self) -> ScenarioRow:
        return max(self.rows, key=lambda r: r.output)


def compare_scenarios(
    model: Model,
    base: Inputs,
    scenarios: Mapping[str, Mapping[str, float]],
    probabilities: Mapping[str, float] | None = None,
) -> ScenarioTable:
    """Run each scenario (base inputs with its overrides applied).

    With ``probabilities`` for every scenario, summing to 1, the table also
    carries the probability-weighted expected value.
    """
    if not scenarios:
        raise ValidationError("scenarios must not be empty")
    checked = check_inputs(base)
    base_output = evaluate(model, checked)
    if probabilities is not None:
        missing = set(scenarios) ^ set(probabilities)
        if missing:
            raise ValidationError(
                f"probabilities and scenarios must name the same cases; mismatch: "
                f"{', '.join(sorted(missing))}"
            )
        weights = {k: require_fraction(f"probability of {k}", v) for k, v in probabilities.items()}
        if abs(sum(weights.values()) - 1) > 1e-9:
            raise ValidationError(f"probabilities must sum to 1, got {sum(weights.values()):g}")
    rows = []
    for name, overrides in scenarios.items():
        unknown = set(overrides) - set(checked)
        if unknown:
            raise ValidationError(
                f"scenario {name!r} overrides unknown input(s): {', '.join(sorted(unknown))}"
            )
        changes = check_inputs({**checked, **overrides})
        override_values = {k: changes[k] for k in overrides}
        output = evaluate(model, changes)
        rows.append(
            ScenarioRow(
                name=name,
                overrides=override_values,
                output=output,
                change_vs_base=output - base_output,
                probability=None if probabilities is None else float(probabilities[name]),
            )
        )
    expected = (
        None if probabilities is None else sum(r.output * (r.probability or 0.0) for r in rows)
    )
    return ScenarioTable(base_output=base_output, rows=tuple(rows), expected_value=expected)
