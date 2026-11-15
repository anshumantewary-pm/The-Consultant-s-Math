"""Shared result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    """Base for every calculator result. Gives a JSON-ready ``to_dict()``."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Step(Result):
    """One line of shown work: a label, its value and a unit for display."""

    label: str
    value: float
    unit: str = ""
