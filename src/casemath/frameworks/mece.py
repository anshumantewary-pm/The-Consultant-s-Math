"""MECE checker: Mutually Exclusive, Collectively Exhaustive.

A machine cannot judge whether a split is *sensible*; that stays with you.
What it can catch are the mechanical failures:

* **single_split**     a branch with one child is a rename, not a split
* **empty_branch**     a branch with an operator but no children
* **duplicate**        two siblings with the same label overlap (not ME)
* **missing_bucket**   parts add to less than the stated total (not CE)
* **double_count**     parts add to more than the stated total (not ME)
* **mismatch**         for x / - nodes, parts do not reproduce the stated value
"""

from __future__ import annotations

from dataclasses import dataclass

from casemath.core.result import Result
from casemath.frameworks.issue_tree import Node, computed_value, walk


@dataclass(frozen=True)
class MeceIssue(Result):
    kind: str
    path: str
    message: str


@dataclass(frozen=True)
class MeceReport(Result):
    issues: tuple[MeceIssue, ...]
    nodes_checked: int

    @property
    def ok(self) -> bool:
        return not self.issues

    def kinds(self) -> set[str]:
        return {issue.kind for issue in self.issues}

    def summary(self) -> str:
        if self.ok:
            return f"MECE check passed ({self.nodes_checked} nodes)."
        lines = [f"MECE check found {len(self.issues)} issue(s):"]
        lines += [f"  - [{i.kind}] {i.path}: {i.message}" for i in self.issues]
        return "\n".join(lines)


def check_mece(root: Node, tolerance: float = 0.005) -> MeceReport:
    """Check every branch. ``tolerance`` is relative (0.005 = 0.5% rounding allowed)."""
    issues: list[MeceIssue] = []
    count = 0
    for path, node in walk(root):
        count += 1
        where = " > ".join(path)
        if node.is_leaf:
            continue
        if not node.children:
            issues.append(MeceIssue("empty_branch", where, "has an operator but no branches"))
            continue
        if len(node.children) == 1:
            issues.append(
                MeceIssue(
                    "single_split",
                    where,
                    f"splits into only {node.children[0].label!r}; a split needs 2+ branches",
                )
            )

        seen: dict[str, str] = {}
        for child in node.children:
            key = child.label.strip().casefold()
            if key in seen:
                issues.append(
                    MeceIssue("duplicate", where, f"{child.label!r} appears more than once")
                )
            seen[key] = child.label

        if node.value is None:
            continue
        parts = computed_value(node)
        if parts is None:
            continue
        gap = node.value - parts
        if abs(gap) <= tolerance * max(abs(node.value), 1.0):
            continue
        if node.op == "sum" and gap > 0:
            issues.append(
                MeceIssue(
                    "missing_bucket",
                    where,
                    f"branches add to {parts:,.2f} but the total is {node.value:,.2f}; "
                    f"{gap:,.2f} is unexplained (not collectively exhaustive)",
                )
            )
        elif node.op == "sum":
            issues.append(
                MeceIssue(
                    "double_count",
                    where,
                    f"branches add to {parts:,.2f}, more than the total {node.value:,.2f}; "
                    f"{-gap:,.2f} is counted twice (not mutually exclusive)",
                )
            )
        else:
            issues.append(
                MeceIssue(
                    "mismatch",
                    where,
                    f"branches give {parts:,.2f} but the stated value is {node.value:,.2f}",
                )
            )
    return MeceReport(issues=tuple(issues), nodes_checked=count)
