"""Display helpers. Math stays in floats; rounding happens only here."""

from __future__ import annotations

_SUFFIXES = ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K"))


def fmt_money(value: float, currency: str = "$", compact: bool = False) -> str:
    """``1234.5`` -> ``$1,234.50``; with ``compact=True`` -> ``$1.2K``."""
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if compact:
        for threshold, suffix in _SUFFIXES:
            if magnitude >= threshold:
                return f"{sign}{currency}{magnitude / threshold:.1f}{suffix}"
    return f"{sign}{currency}{magnitude:,.2f}"


def fmt_pct(fraction: float, digits: int = 1) -> str:
    """``0.256`` -> ``25.6%``."""
    return f"{fraction * 100:.{digits}f}%"


def fmt_number(value: float, digits: int = 0) -> str:
    """``41666.67`` -> ``41,667``."""
    return f"{value:,.{digits}f}"


def fmt_signed_money(value: float, currency: str = "$") -> str:
    """Always show a sign; useful for bridges: ``+$500.00`` / ``-$200.00``."""
    prefix = "+" if value >= 0 else "-"
    return f"{prefix}{currency}{abs(value):,.2f}"
