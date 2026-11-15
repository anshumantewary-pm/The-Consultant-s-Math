"""Market share, relative share, concentration (HHI) and share projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from casemath.calculators.growth import grow
from casemath.core.errors import ValidationError
from casemath.core.result import Result
from casemath.core.validate import (
    require_non_empty,
    require_non_negative,
    require_positive,
    require_rate,
)


def market_share(company_revenue: float, market_size: float) -> float:
    """Company sales / total market sales, as a fraction."""
    company_revenue = require_non_negative("company_revenue", company_revenue)
    market_size = require_positive("market_size", market_size)
    if company_revenue > market_size:
        raise ValidationError(
            f"company_revenue ({company_revenue:g}) cannot exceed market_size ({market_size:g})"
        )
    return company_revenue / market_size


def relative_market_share(company_revenue: float, largest_competitor_revenue: float) -> float:
    """Company sales / largest rival's sales. Above 1 means you lead the market (BCG matrix)."""
    company_revenue = require_non_negative("company_revenue", company_revenue)
    largest_competitor_revenue = require_positive(
        "largest_competitor_revenue", largest_competitor_revenue
    )
    return company_revenue / largest_competitor_revenue


def required_share(target_revenue: float, market_size: float) -> float:
    """Share of the market you must win to hit ``target_revenue``. Can exceed 1 (= impossible)."""
    target_revenue = require_non_negative("target_revenue", target_revenue)
    market_size = require_positive("market_size", market_size)
    return target_revenue / market_size


@dataclass(frozen=True)
class ShareRow(Result):
    name: str
    revenue: float
    share: float
    relative_share: float | None  # None when there is no rival with sales


@dataclass(frozen=True)
class ShareTable(Result):
    rows: tuple[ShareRow, ...]
    total: float

    @property
    def leader(self) -> str:
        return self.rows[0].name

    def shares(self) -> dict[str, float]:
        return {row.name: row.share for row in self.rows}


def share_table(revenues: Mapping[str, float]) -> ShareTable:
    """Shares for every player, largest first.

    ``relative_share`` compares each player to the biggest *other* player,
    so the leader's value is above 1 and everyone else's is below or equal to 1.
    """
    require_non_empty("revenues", revenues)
    clean = {
        name: require_non_negative(f"revenues[{name!r}]", rev) for name, rev in revenues.items()
    }
    total = sum(clean.values())
    if total == 0:
        raise ValidationError("revenues must not all be zero")
    ordered = sorted(clean.items(), key=lambda item: item[1], reverse=True)

    runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
    rows = []
    for index, (name, revenue) in enumerate(ordered):
        rival = ordered[0][1] if index else runner_up
        rows.append(
            ShareRow(
                name=name,
                revenue=revenue,
                share=revenue / total,
                relative_share=revenue / rival if rival else None,
            )
        )
    return ShareTable(rows=tuple(rows), total=total)


@dataclass(frozen=True)
class Concentration(Result):
    hhi: float
    band: str
    top_share: float
    players: int


# Bands from the 2023 US DOJ/FTC Merger Guidelines.
HIGHLY_CONCENTRATED = 1_800
MODERATELY_CONCENTRATED = 1_000


def hhi(shares: Mapping[str, float]) -> Concentration:
    """Herfindahl-Hirschman Index from shares given as fractions (0.3 = 30%).

    HHI = sum of (share in percent)^2, from near 0 (fragmented) to 10,000 (monopoly).
    Shares may sum to less than 1 (unlisted fringe is ignored) but not more.
    """
    require_non_empty("shares", shares)
    values = [require_non_negative(f"shares[{name!r}]", s) for name, s in shares.items()]
    if sum(values) > 1 + 1e-9:
        raise ValidationError(f"shares sum to {sum(values):.3f}; they must not exceed 1")
    index = sum((s * 100) ** 2 for s in values)
    if index > HIGHLY_CONCENTRATED:
        band = "highly concentrated"
    elif index >= MODERATELY_CONCENTRATED:
        band = "moderately concentrated"
    else:
        band = "unconcentrated"
    return Concentration(hhi=index, band=band, top_share=max(values), players=len(values))


@dataclass(frozen=True)
class ShareProjection(Result):
    years: tuple[int, ...]
    company_revenue: tuple[float, ...]
    market_size: tuple[float, ...]
    share: tuple[float, ...]

    @property
    def final_share(self) -> float:
        return self.share[-1]


def project_share(
    company_revenue: float,
    market_size: float,
    company_growth: float,
    market_growth: float,
    years: int,
) -> ShareProjection:
    """Year-by-year share if company and market each grow at a constant rate.

    You gain share only when you grow faster than the market.
    """
    market_share(company_revenue, market_size)  # validates both and the ratio
    require_rate("company_growth", company_growth)
    require_rate("market_growth", market_growth)
    if isinstance(years, bool) or not isinstance(years, int) or years < 0:
        raise ValidationError(f"years must be a whole number >= 0, got {years}")

    span = tuple(range(years + 1))
    company = tuple(grow(company_revenue, company_growth, y) for y in span)
    market = tuple(grow(market_size, market_growth, y) for y in span)
    return ShareProjection(
        years=span,
        company_revenue=company,
        market_size=market,
        share=tuple(c / m for c, m in zip(company, market, strict=True)),
    )
