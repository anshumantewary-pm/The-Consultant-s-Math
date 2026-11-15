"""Exception hierarchy. The CLI catches ``CaseMathError`` and nothing else."""

from __future__ import annotations


class CaseMathError(Exception):
    """Base class for every error casemath raises on purpose."""


class ValidationError(CaseMathError, ValueError):
    """An input value makes no sense for the calculation (e.g. negative units)."""


class UnknownCaseError(CaseMathError, KeyError):
    """A practice case id was not found in the registry."""

    def __str__(self) -> str:
        # KeyError wraps its message in quotes; show it plainly instead.
        return str(self.args[0]) if self.args else "unknown case"
