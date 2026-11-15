"""The standard profitability framework as an issue tree.

    Profit = Revenue - Costs
      Revenue = Price x Volume
        Volume = Market size x Market share
      Costs = Fixed costs + Variable costs
        Variable costs = Variable cost per unit x Volume

Each node carries the question you would ask the interviewer at that point.
"""

from __future__ import annotations

from collections.abc import Mapping

from casemath.core.validate import require_non_empty, require_non_negative
from casemath.frameworks.issue_tree import Node, branch, leaf


def profitability_tree(
    price: float | None = None,
    units: float | None = None,
    variable_cost_per_unit: float | None = None,
    fixed_costs: float | None = None,
) -> Node:
    """The classic tree. Pass numbers to fill the leaves; leave them out for a blank framework.

    ``units`` fills Volume directly; without it Volume is split into market size x share.
    """
    for name, value in (
        ("price", price),
        ("units", units),
        ("variable_cost_per_unit", variable_cost_per_unit),
        ("fixed_costs", fixed_costs),
    ):
        if value is not None:
            require_non_negative(name, value)

    def volume() -> Node:
        if units is not None:
            return leaf("Volume", units, "Are we selling more or fewer units? Why?")
        return branch(
            "Volume",
            "product",
            leaf("Market size", hint="Is the whole market growing or shrinking?"),
            leaf("Market share", hint="Are we winning or losing against competitors?"),
            hint="Are we selling more or fewer units? Why?",
        )

    revenue = branch(
        "Revenue",
        "product",
        leaf("Price", price, "Have we or competitors changed prices? Mix shift?"),
        volume(),
        hint="Which product lines, regions or channels changed?",
    )
    costs = branch(
        "Costs",
        "sum",
        leaf("Fixed costs", fixed_costs, "Rent, salaries, overhead: any step changes?"),
        branch(
            "Variable costs",
            "product",
            leaf(
                "Variable cost per unit",
                variable_cost_per_unit,
                "Inputs, labour, freight per unit: what moved?",
            ),
            volume(),
        ),
        hint="Which cost line grew faster than revenue?",
    )
    return branch(
        "Profit", "difference", revenue, costs, hint="Compare to last year and to competitors."
    )


def breakdown_tree(label: str, total: float | None, parts: Mapping[str, float]) -> Node:
    """A one-level ``sum`` split with a stated total, ready for ``check_mece``.

    Example: revenue of 100 split by channel into Retail 60 + Online 30 -> flags 10 missing.
    """
    require_non_empty("parts", parts)
    if total is not None:
        require_non_negative("total", total)
    return branch(label, "sum", *(leaf(k, v) for k, v in parts.items()), value=total)
