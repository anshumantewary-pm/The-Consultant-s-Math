"""Input checks shared by every calculator.

Each helper returns the value as a ``float`` so callers can write
``price = require_positive("price", price)`` and keep going.
"""

from __future__ import annotations

import math
from collections.abc import Sized

from casemath.core.errors import ValidationError


def _as_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValidationError(f"{name} must be a finite number, got {value}")
    return number


def require_number(name: str, value: object) -> float:
    """Any finite number, including negatives (e.g. a target loss)."""
    return _as_number(name, value)


def require_non_negative(name: str, value: object) -> float:
    number = _as_number(name, value)
    if number < 0:
        raise ValidationError(f"{name} must be >= 0, got {value}")
    return number


def require_positive(name: str, value: object) -> float:
    number = _as_number(name, value)
    if number <= 0:
        raise ValidationError(f"{name} must be > 0, got {value}")
    return number


def require_fraction(name: str, value: object) -> float:
    """A share or rate written as a fraction between 0 and 1 inclusive."""
    number = _as_number(name, value)
    if not 0 <= number <= 1:
        raise ValidationError(f"{name} must be between 0 and 1, got {value}")
    return number


def require_rate(name: str, value: object) -> float:
    """A growth rate; may be negative but not -100% or below."""
    number = _as_number(name, value)
    if number <= -1:
        raise ValidationError(f"{name} must be > -1 (i.e. above -100%), got {value}")
    return number


def require_non_empty(name: str, values: Sized) -> None:
    if len(values) == 0:
        raise ValidationError(f"{name} must not be empty")


def require_count(name: str, value: object, minimum: int = 1) -> int:
    """A whole number of things (periods, simulation runs, steps), at least ``minimum``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be a whole number, got {value!r}")
    if value < minimum:
        raise ValidationError(f"{name} must be >= {minimum}, got {value}")
    return value


def require_numbers(name: str, values: object) -> tuple[float, ...]:
    """A non-empty sequence of finite numbers, returned as a tuple of floats."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValidationError(f"{name} must be a list of numbers, got {type(values).__name__}")
    require_non_empty(name, values)
    return tuple(_as_number(f"{name}[{i}]", v) for i, v in enumerate(values))
