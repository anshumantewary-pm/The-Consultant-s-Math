"""What a practice case is, and how its solution is presented."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from casemath.core.formatting import fmt_money, fmt_number, fmt_pct
from casemath.core.result import Result, Step
from casemath.frameworks.issue_tree import Node, render


@dataclass(frozen=True)
class Solution(Result):
    case_id: str
    title: str
    steps: tuple[Step, ...]
    findings: tuple[str, ...]
    recommendation: str
    answer: dict[str, float | None] = field(default_factory=dict)  # None = "never"


class Case(ABC):
    """A case: a prompt, the data an interviewer would hand over, and a worked solution."""

    id: ClassVar[str]
    title: ClassVar[str]
    case_type: ClassVar[str]
    skills: ClassVar[tuple[str, ...]]
    prompt: ClassVar[str]

    @abstractmethod
    def data(self) -> dict[str, Any]:
        """The exhibits, as plain data."""

    @abstractmethod
    def structure(self) -> Node:
        """The issue tree a strong candidate would draw before doing any math."""

    @abstractmethod
    def solve(self) -> Solution:
        """Run the numbers and return steps, findings and a recommendation."""


def format_step(step: Step) -> str:
    if step.unit == "$":
        shown = fmt_money(step.value)
    elif step.unit == "%":
        shown = fmt_pct(step.value)
    elif step.unit == "x":
        shown = f"{step.value:.2f}x"
    else:
        digits = 2 if abs(step.value) < 100 and step.value != int(step.value) else 0
        shown = fmt_number(step.value, digits) + (f" {step.unit}" if step.unit else "")
    return f"{step.label}: {shown}"


def render_case(case: Case) -> str:
    lines = [f"Case {case.id}: {case.title}", f"Type: {case.case_type}", ""]
    lines += [case.prompt.strip(), "", "Suggested structure:", render(case.structure())]
    return "\n".join(lines)


def render_solution(solution: Solution) -> str:
    lines = [f"Case {solution.case_id}: {solution.title}", "", "Steps"]
    lines += [f"  {i}. {format_step(s)}" for i, s in enumerate(solution.steps, start=1)]
    lines += ["", "Findings"]
    lines += [f"  - {finding}" for finding in solution.findings]
    lines += ["", "Recommendation", f"  {solution.recommendation}"]
    return "\n".join(lines)
