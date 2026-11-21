"""Internal risk rating: a transparent scorecard mapped to a 10-grade master scale.

Each factor turns a raw value into a 0-100 score by straight-line
interpolation between a "weak" and a "strong" anchor, clamped at both ends.
The weighted score picks a grade; documented overrides can only notch it down.
Grades map to an indicative PD and an agency-style equivalent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from casemath.core.result import Result
from casemath.credit.analysis import Spread
from casemath.credit.model import Industry, Qualitative


@dataclass(frozen=True)
class Grade(Result):
    grade: int  # 1 best, 9 worst performing, 10 default
    equivalent: str
    pd: float  # one-year probability of default
    label: str


MASTER_SCALE: tuple[Grade, ...] = (
    Grade(1, "AAA/AA", 0.0003, "Minimal risk"),
    Grade(2, "A", 0.0006, "Low risk"),
    Grade(3, "BBB+/BBB", 0.0012, "Modest risk"),
    Grade(4, "BBB-", 0.0025, "Acceptable risk"),
    Grade(5, "BB+", 0.0050, "Moderate risk"),
    Grade(6, "BB", 0.0100, "Elevated risk"),
    Grade(7, "BB-/B+", 0.0200, "Watch"),
    Grade(8, "B", 0.0400, "Weak"),
    Grade(9, "CCC", 0.1500, "Substandard"),
    Grade(10, "D", 1.0000, "Default"),
)

# Lowest weighted score that earns each grade, best first; below the last is grade 9.
GRADE_FLOORS: tuple[float, ...] = (85, 77, 69, 61, 54, 47, 40, 32)


def grade(number: int) -> Grade:
    return MASTER_SCALE[min(max(number, 1), 10) - 1]


def grade_for_score(score: float) -> int:
    return next((i + 1 for i, floor in enumerate(GRADE_FLOORS) if score >= floor), 9)


def scale(value: float | None, weak: float, strong: float, log: bool = False) -> float:
    """0 at ``weak``, 100 at ``strong`` (either direction), clamped; None scores 0."""
    if value is None:
        return 0.0
    if log:
        value, weak, strong = (math.log10(max(v, 1e-9)) for v in (value, weak, strong))
    t = (value - weak) / (strong - weak)
    return 100 * min(max(t, 0.0), 1.0)


@dataclass(frozen=True)
class Factor(Result):
    key: str
    label: str
    group: str  # "financial" or "business"
    weight: float
    value: float | None
    display: str
    score: float  # 0-100
    contribution: float  # weight * score


@dataclass(frozen=True)
class Rating(Result):
    factors: tuple[Factor, ...]
    score: float
    model_grade: int
    overrides: tuple[str, ...]
    final: Grade

    @property
    def weakest(self) -> tuple[Factor, ...]:
        return tuple(sorted(self.factors, key=lambda f: f.score)[:3])


def _x(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.2f}x"


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def rate(
    pf: Spread,
    history: tuple[Spread, ...],
    industry: Industry,
    qual: Qualitative,
    kyc_flags: tuple[str, ...] = (),
) -> Rating:
    """Rate the borrower on its pro forma ratios (``pf``) and its track record."""
    leverage = pf.leverage if pf.ebitda > 0 else None
    raw: tuple[tuple[str, str, str, float, float | None, str, float], ...] = (
        (
            "leverage",
            "Debt / EBITDA (pro forma)",
            "financial",
            0.18,
            leverage,
            _x(leverage),
            scale(leverage, 6.0, 1.0) if leverage is not None else 0.0,
        ),
        (
            "icr",
            "Interest cover (pro forma)",
            "financial",
            0.10,
            pf.icr,
            _x(pf.icr),
            scale(pf.icr, 1.0, 8.0),
        ),
        (
            "dscr",
            "Debt service cover (pro forma)",
            "financial",
            0.12,
            pf.dscr,
            _x(pf.dscr),
            100.0 if pf.dscr is None and pf.cash_flow_available > 0 else scale(pf.dscr, 0.8, 2.5),
        ),
        (
            "margin",
            "EBITDA margin",
            "financial",
            0.08,
            pf.ebitda_margin,
            _pct(pf.ebitda_margin),
            scale(pf.ebitda_margin, 0.0, 0.25),
        ),
        (
            "size",
            "Scale (revenue)",
            "financial",
            0.07,
            pf.revenue,
            f"{pf.revenue / 1e6:,.0f}M",
            scale(pf.revenue, 10e6, 2e9, log=True),
        ),
        (
            "liquidity",
            "Current ratio",
            "financial",
            0.05,
            pf.current_ratio,
            _x(pf.current_ratio),
            50.0 if pf.current_ratio is None else scale(pf.current_ratio, 0.8, 2.0),
        ),
        (
            "management",
            "Management and governance",
            "business",
            0.12,
            float(qual.management),
            f"{qual.management}/5",
            (qual.management - 1) * 25.0,
        ),
        (
            "market",
            "Market position",
            "business",
            0.10,
            float(qual.market_position),
            f"{qual.market_position}/5",
            (qual.market_position - 1) * 25.0,
        ),
        (
            "industry",
            "Industry risk",
            "business",
            0.10,
            float(industry.risk),
            f"{industry.risk}/5 ({'cyclical' if industry.cyclical else 'defensive'})",
            (5 - industry.risk) * 25.0,
        ),
        (
            "reporting",
            "Financial reporting quality",
            "business",
            0.04,
            float(qual.financial_reporting),
            f"{qual.financial_reporting}/5",
            (qual.financial_reporting - 1) * 25.0,
        ),
        (
            "track_record",
            "Years in business",
            "business",
            0.04,
            qual.years_in_business,
            f"{qual.years_in_business:g} yrs",
            scale(qual.years_in_business, 2, 20),
        ),
    )
    factors = tuple(
        Factor(key, label, group, w, value, shown, s, w * s)
        for key, label, group, w, value, shown, s in raw
    )
    score = sum(f.contribution for f in factors)
    model_grade = grade_for_score(score)

    overrides: list[str] = []
    notches = 0
    if pf.ebitda <= 0:
        overrides.append("EBITDA is zero or negative: rated at least grade 8")
        model_floor = 8
    else:
        model_floor = 1
    if len(history) >= 2 and history[-2].ebitda > 0:
        change = history[-1].ebitda / history[-2].ebitda - 1
        if change < -0.15:
            notches += 1
            overrides.append(f"EBITDA fell {-change * 100:.0f}% last year: -1 notch")
    if pf.equity is not None and pf.equity <= 0:
        notches += 1
        overrides.append("Negative equity: -1 notch")
    if kyc_flags:
        notches += 1
        overrides.append("Open KYC / compliance flags: -1 notch pending clearance")
    final = min(max(model_grade + notches, model_floor), 9)
    return Rating(factors, score, model_grade, tuple(overrides), grade(final))
