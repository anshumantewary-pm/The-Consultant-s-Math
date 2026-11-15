"""Structured thinking: issue trees, the profitability framework, and the MECE checker."""

from casemath.frameworks.issue_tree import (
    Node,
    branch,
    computed_value,
    evaluate,
    find,
    leaf,
    render,
    walk,
)
from casemath.frameworks.mece import MeceIssue, MeceReport, check_mece
from casemath.frameworks.profitability import breakdown_tree, profitability_tree

__all__ = [
    "MeceIssue",
    "MeceReport",
    "Node",
    "branch",
    "breakdown_tree",
    "check_mece",
    "computed_value",
    "evaluate",
    "find",
    "leaf",
    "profitability_tree",
    "render",
    "walk",
]
