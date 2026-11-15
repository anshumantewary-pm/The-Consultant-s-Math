"""Issue trees: a question split into branches, optionally with numbers.

A node is either a *leaf* (``op is None``), which may carry a value, or a
*branch* that combines its children with an operator:

* ``sum``        parent = child1 + child2 + ...
* ``difference`` parent = child1 - child2 - ...   (Profit = Revenue - Costs)
* ``product``    parent = child1 x child2 x ...   (Revenue = Price x Volume)

A branch may also carry a stated ``value`` (e.g. the reported total). The MECE
checker compares that against what the children actually add up to.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Literal

from casemath.core.errors import ValidationError
from casemath.core.result import Result

Op = Literal["sum", "difference", "product"]
OPS: tuple[Op, ...] = ("sum", "difference", "product")
_SYMBOL = {"sum": "+", "difference": "-", "product": "x"}


@dataclass(frozen=True)
class Node(Result):
    label: str
    op: Op | None = None
    children: tuple[Node, ...] = field(default_factory=tuple)
    value: float | None = None
    hint: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValidationError("node label must not be blank")
        if self.op is not None and self.op not in OPS:
            raise ValidationError(f"op must be one of {OPS}, got {self.op!r}")
        if self.op is None and self.children:
            raise ValidationError(f"leaf {self.label!r} has children but no op")

    @property
    def is_leaf(self) -> bool:
        return self.op is None


def leaf(label: str, value: float | None = None, hint: str = "") -> Node:
    return Node(label=label, value=value, hint=hint)


def branch(label: str, op: Op, *children: Node, value: float | None = None, hint: str = "") -> Node:
    return Node(label=label, op=op, children=tuple(children), value=value, hint=hint)


def combine(op: Op, values: list[float]) -> float:
    if op == "sum":
        return math.fsum(values)
    if op == "difference":
        return values[0] - math.fsum(values[1:])
    return math.prod(values)


def computed_value(node: Node) -> float | None:
    """What the children add up to, or None if any leaf below has no value.

    For a leaf this is just its own value.
    """
    if node.is_leaf:
        return node.value
    if not node.children:
        return None
    parts = [evaluate(child) for child in node.children]
    if any(part is None for part in parts):
        return None
    assert node.op is not None
    return combine(node.op, [p for p in parts if p is not None])


def evaluate(node: Node) -> float | None:
    """Value of a node: its stated value if present, else what its children compute."""
    if node.value is not None:
        return node.value
    return computed_value(node)


def walk(node: Node, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Node]]:
    """Depth-first ``(path, node)`` pairs, path including the node's own label."""
    here = (*path, node.label)
    yield here, node
    for child in node.children:
        yield from walk(child, here)


def find(node: Node, *path: str) -> Node:
    """Follow labels down from ``node``: ``find(tree, "Revenue", "Price")``."""
    current = node
    for label in path:
        for child in current.children:
            if child.label == label:
                current = child
                break
        else:
            raise ValidationError(f"{current.label!r} has no child {label!r}")
    return current


def render(node: Node, fmt: str = "{:,.2f}", show_hints: bool = False) -> str:
    """ASCII tree, e.g.::

    Profit [-] = 1,500.00
    ├── Revenue [x] = 10,000.00
    │   ├── Price = 10.00
    """
    lines: list[str] = []

    def describe(n: Node) -> str:
        text = n.label
        if n.op is not None:
            text += f" [{_SYMBOL[n.op]}]"
        number = evaluate(n)
        if number is not None:
            text += " = " + fmt.format(number)
        if show_hints and n.hint:
            text += f"  ({n.hint})"
        return text

    def visit(n: Node, prefix: str, is_last: bool, is_root: bool) -> None:
        if is_root:
            lines.append(describe(n))
            child_prefix = ""
        else:
            lines.append(prefix + ("└── " if is_last else "├── ") + describe(n))
            child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(n.children):
            visit(child, child_prefix, i == len(n.children) - 1, False)

    visit(node, "", True, True)
    return "\n".join(lines)
