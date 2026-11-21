"""Business advisor: company figures in, sector-aware diagnosis and suggestions out.

``assess(Profile(...))`` computes the headline ratios (gross, EBITDA and
operating-cost margins, growth), compares each with the sector's indicative
range, values the business on sector multiples, works out break-even revenue,
cash runway and (when given) unit economics, then turns every gap it finds into
a prioritised suggestion that uses the sector's own levers.

``parse_financials(csv_text)`` reads an uploaded CSV of ``metric,value`` rows
(or ``metric,year1,year2,...``: the last value is used and the one before it
becomes prior-year revenue) into the keyword arguments ``Profile`` takes.

The benchmark ranges are indicative rules of thumb for screening, not market
data for a specific company, region or date.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from casemath.calculators.unit_economics import unit_economics
from casemath.core.errors import UnknownNameError, ValidationError
from casemath.core.result import Result
from casemath.core.validate import require_non_negative, require_number, require_positive

Range = tuple[float, float]
Multiples = tuple[float, float, float]  # low, mid, high


@dataclass(frozen=True)
class Sector(Result):
    key: str
    name: str
    gross_margin: Range
    ebitda_margin: Range
    growth: Range
    opex_ratio: Range
    ev_revenue: Multiples
    ev_ebitda: Multiples
    kpis: tuple[str, ...]
    margin_levers: tuple[str, ...]
    cost_levers: tuple[str, ...]
    growth_levers: tuple[str, ...]


SECTORS: dict[str, Sector] = {
    s.key: s
    for s in (
        Sector(
            key="saas",
            name="SaaS / software",
            gross_margin=(0.70, 0.85),
            ebitda_margin=(0.10, 0.30),
            growth=(0.20, 0.50),
            opex_ratio=(0.45, 0.65),
            ev_revenue=(3.0, 6.0, 10.0),
            ev_ebitda=(15.0, 22.0, 30.0),
            kpis=("ARR growth", "Net revenue retention", "LTV/CAC", "CAC payback", "Rule of 40"),
            margin_levers=(
                "Move to value-based or usage-based pricing tiers",
                "Cut hosting cost per customer (reserved capacity, right-sizing)",
                "Automate onboarding and support to lower cost of service",
            ),
            cost_levers=(
                "Tie sales and marketing spend to CAC payback under 12 months",
                "Shift acquisition toward product-led and partner channels",
                "Review R&D headcount against the product roadmap",
            ),
            growth_levers=(
                "Expand within existing accounts: seats, modules, upsell",
                "Reduce churn with health scoring and customer success",
                "Open a new segment or geography with an existing product",
            ),
        ),
        Sector(
            key="ecommerce",
            name="E-commerce / D2C online",
            gross_margin=(0.30, 0.50),
            ebitda_margin=(0.03, 0.10),
            growth=(0.10, 0.30),
            opex_ratio=(0.25, 0.40),
            ev_revenue=(0.8, 1.5, 3.0),
            ev_ebitda=(10.0, 14.0, 20.0),
            kpis=(
                "Average order value",
                "Repeat purchase rate",
                "CAC",
                "Contribution margin/order",
            ),
            margin_levers=(
                "Raise average order value with bundles and free-shipping thresholds",
                "Renegotiate supplier and fulfilment rates; cut return rates",
                "Grow the share of private-label or higher-margin SKUs",
            ),
            cost_levers=(
                "Cap paid-media spend at a target contribution margin per order",
                "Consolidate warehouses and couriers by volume",
                "Clear slow-moving inventory to free working capital",
            ),
            growth_levers=(
                "Build repeat purchase with email, subscriptions and loyalty",
                "Add marketplaces as a second sales channel",
                "Use cohort data to double down on the best acquisition channels",
            ),
        ),
        Sector(
            key="retail",
            name="Retail (physical stores)",
            gross_margin=(0.25, 0.45),
            ebitda_margin=(0.05, 0.12),
            growth=(0.02, 0.08),
            opex_ratio=(0.18, 0.33),
            ev_revenue=(0.4, 0.8, 1.5),
            ev_ebitda=(6.0, 9.0, 12.0),
            kpis=("Same-store sales growth", "Sales per sq ft", "Inventory turns", "Shrinkage"),
            margin_levers=(
                "Optimise category mix toward higher-margin lines",
                "Reduce markdowns with better demand forecasting",
                "Tighten shrinkage controls",
            ),
            cost_levers=(
                "Renegotiate or exit loss-making leases",
                "Match staffing schedules to footfall",
                "Centralise purchasing to gain volume discounts",
            ),
            growth_levers=(
                "Add omnichannel: click-and-collect and online ordering",
                "Launch a loyalty programme to raise visit frequency",
                "Open stores only where payback is under 3 years",
            ),
        ),
        Sector(
            key="manufacturing",
            name="Manufacturing / industrial",
            gross_margin=(0.20, 0.40),
            ebitda_margin=(0.10, 0.18),
            growth=(0.03, 0.10),
            opex_ratio=(0.10, 0.22),
            ev_revenue=(0.8, 1.3, 2.0),
            ev_ebitda=(7.0, 10.0, 13.0),
            kpis=("Capacity utilisation", "OEE", "Scrap rate", "Inventory days", "Capex/revenue"),
            margin_levers=(
                "Raise capacity utilisation to spread fixed plant cost",
                "Pass input-cost inflation through with indexed pricing",
                "Cut scrap and rework with lean or Six Sigma",
            ),
            cost_levers=(
                "Dual-source critical raw materials",
                "Automate high-labour process steps where payback is under 3 years",
                "Reduce energy cost per unit",
            ),
            growth_levers=(
                "Move into higher-value engineered products or services",
                "Win export customers in adjacent markets",
                "Add aftermarket parts and maintenance contracts",
            ),
        ),
        Sector(
            key="restaurants",
            name="Restaurants / food service",
            gross_margin=(0.60, 0.70),
            ebitda_margin=(0.10, 0.18),
            growth=(0.03, 0.10),
            opex_ratio=(0.45, 0.58),
            ev_revenue=(1.0, 2.0, 3.0),
            ev_ebitda=(9.0, 13.0, 17.0),
            kpis=(
                "Food cost %",
                "Labour cost %",
                "Covers per day",
                "Average ticket",
                "Table turns",
            ),
            margin_levers=(
                "Re-engineer the menu: promote high-margin dishes, cut low sellers",
                "Keep food cost near 30% with portion control and supplier bids",
                "Reduce waste with prep forecasting",
            ),
            cost_levers=(
                "Schedule labour to hourly demand",
                "Renegotiate rent or delivery-platform commissions",
                "Share a central kitchen across outlets",
            ),
            growth_levers=(
                "Fill off-peak hours with promotions or catering",
                "Grow direct online ordering to avoid aggregator fees",
                "Expand through franchising once unit economics are proven",
            ),
        ),
        Sector(
            key="services",
            name="Professional services / consulting",
            gross_margin=(0.30, 0.50),
            ebitda_margin=(0.10, 0.20),
            growth=(0.05, 0.15),
            opex_ratio=(0.15, 0.30),
            ev_revenue=(0.8, 1.5, 2.5),
            ev_ebitda=(8.0, 11.0, 14.0),
            kpis=("Billable utilisation", "Realisation rate", "Revenue per FTE", "Debtor days"),
            margin_levers=(
                "Raise billable utilisation toward 75-80%",
                "Move from hourly to fixed-fee or value-based pricing",
                "Improve the leverage pyramid (more juniors per partner)",
            ),
            cost_levers=(
                "Cut non-billable overhead and office space",
                "Use offshore or freelance capacity for peaks",
                "Shorten debtor days with milestone billing",
            ),
            growth_levers=(
                "Productise repeatable services into packaged offers",
                "Cross-sell other practices into existing clients",
                "Build retainer revenue for predictability",
            ),
        ),
        Sector(
            key="healthcare",
            name="Healthcare services",
            gross_margin=(0.35, 0.60),
            ebitda_margin=(0.10, 0.20),
            growth=(0.05, 0.12),
            opex_ratio=(0.20, 0.40),
            ev_revenue=(1.5, 2.5, 4.0),
            ev_ebitda=(10.0, 14.0, 18.0),
            kpis=(
                "Bed or chair occupancy",
                "Revenue per patient",
                "Payer mix",
                "Claim denial rate",
            ),
            margin_levers=(
                "Improve payer mix and renegotiate insurer rates",
                "Raise occupancy or utilisation of equipment and clinicians",
                "Reduce claim denials with better coding",
            ),
            cost_levers=(
                "Group-purchase drugs and consumables",
                "Standardise clinical pathways to cut variation",
                "Use telehealth for follow-ups",
            ),
            growth_levers=(
                "Add higher-margin specialties or diagnostics",
                "Build referral networks with primary care",
                "Open satellite clinics in underserved catchments",
            ),
        ),
        Sector(
            key="fintech",
            name="Fintech / financial services",
            gross_margin=(0.50, 0.70),
            ebitda_margin=(0.05, 0.25),
            growth=(0.20, 0.40),
            opex_ratio=(0.30, 0.55),
            ev_revenue=(2.0, 4.0, 8.0),
            ev_ebitda=(12.0, 18.0, 25.0),
            kpis=("Take rate", "Payment volume", "Credit loss rate", "Revenue per user", "CAC"),
            margin_levers=(
                "Raise take rate with value-added services",
                "Lower processing and partner-bank costs as volume grows",
                "Tighten underwriting to cut credit losses",
            ),
            cost_levers=(
                "Automate KYC and compliance checks",
                "Move customer support to self-serve",
                "Negotiate volume tiers with payment networks",
            ),
            growth_levers=(
                "Cross-sell credit, insurance or wealth products to the user base",
                "Embed the product in partner platforms (B2B2C)",
                "Raise activation and engagement of dormant users",
            ),
        ),
        Sector(
            key="logistics",
            name="Logistics / transport",
            gross_margin=(0.15, 0.30),
            ebitda_margin=(0.06, 0.12),
            growth=(0.04, 0.10),
            opex_ratio=(0.06, 0.18),
            ev_revenue=(0.5, 1.0, 1.6),
            ev_ebitda=(7.0, 9.0, 12.0),
            kpis=(
                "Asset utilisation",
                "Cost per km or per drop",
                "On-time delivery",
                "Empty miles",
            ),
            margin_levers=(
                "Add fuel surcharges and index contracts to fuel price",
                "Cut empty miles with route optimisation and backhauls",
                "Price by lane profitability, drop unprofitable lanes",
            ),
            cost_levers=(
                "Improve fleet utilisation; lease rather than own for peaks",
                "Use telematics to reduce fuel and maintenance cost",
                "Automate warehouse picking",
            ),
            growth_levers=(
                "Add value-added services: warehousing, returns, cold chain",
                "Win long-term contracts with key shippers",
                "Enter high-growth e-commerce last-mile delivery",
            ),
        ),
        Sector(
            key="consumer",
            name="Consumer goods / FMCG",
            gross_margin=(0.40, 0.60),
            ebitda_margin=(0.12, 0.20),
            growth=(0.05, 0.15),
            opex_ratio=(0.22, 0.40),
            ev_revenue=(1.5, 2.5, 4.0),
            ev_ebitda=(12.0, 15.0, 20.0),
            kpis=("Distribution reach", "Rate of sale", "Trade spend %", "Brand share"),
            margin_levers=(
                "Run price-pack architecture: sizes and premium variants",
                "Cut trade spend that does not lift volume",
                "Reformulate or redesign packaging to lower unit cost",
            ),
            cost_levers=(
                "Consolidate SKUs; drop the long tail",
                "Optimise the distributor network and logistics",
                "Use contract manufacturing for volatile demand",
            ),
            growth_levers=(
                "Expand distribution into new outlets and regions",
                "Launch adjacent products under the same brand",
                "Grow quick-commerce and online channels",
            ),
        ),
    )
}


def get_sector(key: str) -> Sector:
    try:
        return SECTORS[key.strip().lower()]
    except KeyError:
        raise UnknownNameError(
            f"unknown sector {key!r}; choose from {', '.join(SECTORS)}"
        ) from None


# ---------------------------------------------------------------- inputs


@dataclass(frozen=True)
class Profile(Result):
    """One year of company figures. Only sector, revenue, cogs and opex are required.

    ``opex`` is operating cost excluding COGS, depreciation and interest, so
    revenue - cogs - opex is EBITDA. ``growth`` wins over ``prior_revenue``.
    ``arpu`` (monthly revenue per customer), ``churn`` (monthly) and ``cac``
    turn on the unit-economics check when all three are given.
    """

    sector: str
    revenue: float
    cogs: float
    opex: float
    name: str = "The company"
    prior_revenue: float | None = None
    growth: float | None = None
    cash: float | None = None
    debt: float = 0.0
    monthly_burn: float | None = None
    arpu: float | None = None
    churn: float | None = None
    cac: float | None = None


# ---------------------------------------------------------------- outputs


@dataclass(frozen=True)
class Metric(Result):
    key: str
    label: str
    value: float
    low: float | None = None
    high: float | None = None
    status: str = "info"  # "below", "within", "above" or "info"
    higher_is_better: bool = True

    @property
    def good(self) -> bool | None:
        if self.status == "within":
            return True
        if self.status in ("below", "above"):
            return (self.status == "above") == self.higher_is_better
        return None


@dataclass(frozen=True)
class Valuation(Result):
    method: str
    base: float
    low: float
    mid: float
    high: float


@dataclass(frozen=True)
class Suggestion(Result):
    priority: str  # "high", "medium", "low"
    area: str
    title: str
    detail: str
    actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Assessment(Result):
    profile: Profile
    sector: Sector
    gross_profit: float
    ebitda: float
    metrics: tuple[Metric, ...]
    valuations: tuple[Valuation, ...]
    equity_low: float
    equity_mid: float
    equity_high: float
    break_even_revenue: float | None
    revenue_gap: float | None
    runway_months: float | None
    unit_economics: dict[str, float | bool] | None
    score: int
    rating: str
    strengths: tuple[str, ...]
    suggestions: tuple[Suggestion, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------- logic


def _status(value: float, band: Range) -> str:
    low, high = band
    if value < low:
        return "below"
    if value > high:
        return "above"
    return "within"


def _optional(name: str, value: float | None, check: str = "non_negative") -> float | None:
    if value is None:
        return None
    if check == "positive":
        return require_positive(name, value)
    if check == "any":
        return require_number(name, value)
    return require_non_negative(name, value)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _money(x: float) -> str:
    sign = "-" if x < 0 else ""
    m = abs(x)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if m >= threshold:
            return f"{sign}{m / threshold:.1f}{suffix}"
    return f"{sign}{m:,.0f}"


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def assess(profile: Profile) -> Assessment:
    """Diagnose one company against its sector and return prioritised suggestions."""
    sector = get_sector(profile.sector)
    revenue = require_positive("revenue", profile.revenue)
    cogs = require_non_negative("cogs", profile.cogs)
    opex = require_non_negative("opex", profile.opex)
    debt = require_non_negative("debt", profile.debt)
    cash = _optional("cash", profile.cash)
    prior = _optional("prior_revenue", profile.prior_revenue, "positive")
    growth = _optional("growth", profile.growth, "any")
    burn = _optional("monthly_burn", profile.monthly_burn)
    if growth is None and prior is not None:
        growth = revenue / prior - 1

    gross_profit = revenue - cogs
    ebitda = gross_profit - opex
    gm = gross_profit / revenue
    em = ebitda / revenue
    opex_ratio = opex / revenue

    metrics = [
        Metric(
            "gross_margin",
            "Gross margin",
            gm,
            *sector.gross_margin,
            _status(gm, sector.gross_margin),
        ),
        Metric(
            "ebitda_margin",
            "EBITDA margin",
            em,
            *sector.ebitda_margin,
            _status(em, sector.ebitda_margin),
        ),
        Metric(
            "opex_ratio",
            "Operating costs / revenue",
            opex_ratio,
            *sector.opex_ratio,
            _status(opex_ratio, sector.opex_ratio),
            higher_is_better=False,
        ),
    ]
    if growth is not None:
        metrics.append(
            Metric(
                "growth", "Revenue growth", growth, *sector.growth, _status(growth, sector.growth)
            )
        )
        if sector.key in ("saas", "fintech"):
            rule40 = growth + em
            metrics.append(
                Metric(
                    "rule_of_40",
                    "Rule of 40 (growth + EBITDA margin)",
                    rule40,
                    0.40,
                    None,
                    "below" if rule40 < 0.40 else "within",
                )
            )
    leverage = debt / ebitda if ebitda > 0 and debt > 0 else None
    if leverage is not None:
        metrics.append(
            Metric(
                "leverage",
                "Debt / EBITDA",
                leverage,
                0.0,
                3.0,
                "above" if leverage > 3.0 else "within",
                higher_is_better=False,
            )
        )

    # Valuation on sector multiples.
    lo, mid, hi = sector.ev_revenue
    valuations = [Valuation("EV / Revenue", revenue, revenue * lo, revenue * mid, revenue * hi)]
    if ebitda > 0:
        lo, mid, hi = sector.ev_ebitda
        valuations.append(Valuation("EV / EBITDA", ebitda, ebitda * lo, ebitda * mid, ebitda * hi))
    ev_low = min(v.low for v in valuations)
    ev_high = max(v.high for v in valuations)
    ev_mid = sum(v.mid for v in valuations) / len(valuations)
    net_cash = (cash or 0.0) - debt
    equity = (
        max(ev_low + net_cash, 0.0),
        max(ev_mid + net_cash, 0.0),
        max(ev_high + net_cash, 0.0),
    )

    # Break-even: COGS treated as variable, operating costs as fixed.
    break_even = opex / gm if gm > 0 else None
    gap = break_even - revenue if break_even is not None and ebitda < 0 else None

    if burn is None and ebitda < 0:
        burn = -ebitda / 12
    runway = cash / burn if cash is not None and burn else None

    ue: dict[str, float | bool] | None = None
    if profile.arpu is not None and profile.churn is not None and profile.cac is not None:
        u = unit_economics(profile.arpu, gm, profile.churn, profile.cac)
        ue = {**u.to_dict(), "healthy": u.healthy}

    # Score: each benchmarked metric earns 100 (good), 70 (in range) or 25 (weak).
    points = [
        100 if m.good and m.status != "within" else 70 if m.good else 25
        for m in metrics
        if m.good is not None
    ]
    score = sum(points) / len(points)
    if runway is not None and runway < 12:
        score -= 15 if runway < 6 else 8
    if ue is not None and not ue["healthy"]:
        score -= 10
    if ebitda < 0:
        score -= 10
    final = round(min(max(score, 0.0), 100.0))
    rating = "Strong" if final >= 75 else "Fair" if final >= 50 else "Needs attention"

    strengths = tuple(
        f"{m.label} of {_pct(m.value) if m.key != 'leverage' else f'{m.value:.1f}x'} "
        f"is {'better than' if m.status != 'within' else 'within'} the {sector.name} range"
        for m in metrics
        if m.good
    )

    suggestions = _suggest(
        sector,
        revenue,
        gm,
        em,
        opex_ratio,
        growth,
        ebitda,
        break_even,
        gap,
        runway,
        leverage,
        ue,
        metrics,
    )

    return Assessment(
        profile=profile,
        sector=sector,
        gross_profit=gross_profit,
        ebitda=ebitda,
        metrics=tuple(metrics),
        valuations=tuple(valuations),
        equity_low=equity[0],
        equity_mid=equity[1],
        equity_high=equity[2],
        break_even_revenue=break_even,
        revenue_gap=gap,
        runway_months=runway,
        unit_economics=ue,
        score=final,
        rating=rating,
        strengths=strengths,
        suggestions=suggestions,
    )


def _suggest(
    sector: Sector,
    revenue: float,
    gm: float,
    em: float,
    opex_ratio: float,
    growth: float | None,
    ebitda: float,
    break_even: float | None,
    gap: float | None,
    runway: float | None,
    leverage: float | None,
    ue: dict[str, float | bool] | None,
    metrics: list[Metric],
) -> tuple[Suggestion, ...]:
    out: list[Suggestion] = []
    status = {m.key: m.status for m in metrics}
    gm_lo, gm_hi = sector.gross_margin

    if runway is not None and runway < 12:
        out.append(
            Suggestion(
                "high" if runway < 6 else "medium",
                "Cash",
                f"Extend cash runway ({runway:.1f} months left)",
                "Aim for at least 12-18 months of runway before the next raise or milestone.",
                (
                    "Start fundraising or arrange a credit line now",
                    "Cut discretionary spend and freeze non-critical hiring",
                    "Collect receivables faster and stretch payables where possible",
                ),
            )
        )
    if gap is not None and break_even is not None:
        out.append(
            Suggestion(
                "high",
                "Profitability",
                f"Close the {_money(gap)} revenue gap to break-even",
                f"At today's {_pct(gm)} gross margin you need {_money(break_even)} revenue "
                f"to cover "
                f"operating costs, {gap / revenue * 100:.0f}% more than now. "
                f"Each point of gross margin gained lowers that bar.",
                sector.margin_levers[:2] + sector.cost_levers[:1],
            )
        )
    if status["gross_margin"] == "below":
        lift = (gm_lo - gm) * revenue
        out.append(
            Suggestion(
                "high",
                "Gross margin",
                f"Lift gross margin from {_pct(gm)} toward the "
                f"{_pct(gm_lo)}-{_pct(gm_hi)} sector range",
                f"Reaching the bottom of the range adds about {_money(lift)} gross profit a year.",
                sector.margin_levers,
            )
        )
    if status["opex_ratio"] == "above":
        excess = (opex_ratio - sector.opex_ratio[1]) * revenue
        out.append(
            Suggestion(
                "high" if ebitda < 0 else "medium",
                "Operating costs",
                f"Operating costs are {_pct(opex_ratio)} of revenue, above the "
                f"{_pct(sector.opex_ratio[1])} sector ceiling",
                f"Bringing them to the ceiling frees about {_money(excess)} a year.",
                sector.cost_levers,
            )
        )
    if status["ebitda_margin"] == "below" and ebitda >= 0:
        out.append(
            Suggestion(
                "medium",
                "Profitability",
                f"EBITDA margin of {_pct(em)} trails the "
                f"{_pct(sector.ebitda_margin[0])} sector floor",
                "Combine a pricing review with a cost programme; check which products, customers "
                "or locations lose money.",
                sector.margin_levers[:1] + sector.cost_levers[:2],
            )
        )
    if growth is not None and status.get("growth") == "below":
        out.append(
            Suggestion(
                "medium",
                "Growth",
                f"Revenue growth of {_pct(growth)} is under the "
                f"{_pct(sector.growth[0])} sector norm",
                "Slow growth caps valuation multiples; pick one or two levers and size them.",
                sector.growth_levers,
            )
        )
    if status.get("rule_of_40") == "below" and growth is not None:
        out.append(
            Suggestion(
                "medium",
                "Efficiency",
                f"Rule of 40 score is {_pct(growth + em)}",
                "Investors expect growth plus EBITDA margin of at least 40%. Either accelerate "
                "growth or show a path to profitability.",
            )
        )
    if leverage is not None and leverage > 3.0:
        out.append(
            Suggestion(
                "medium",
                "Balance sheet",
                f"Debt is {leverage:.1f}x EBITDA",
                "Above about 3x lenders get cautious. Prioritise debt paydown or refinance at "
                "longer tenors before taking on new borrowing.",
            )
        )
    if ue is not None:
        ltv_cac = float(ue["ltv_to_cac"])
        payback = float(ue["cac_payback_periods"])
        if ltv_cac < 3:
            out.append(
                Suggestion(
                    "high" if ltv_cac < 1 else "medium",
                    "Unit economics",
                    f"LTV/CAC is {ltv_cac:.1f}x, under the 3x rule of thumb",
                    "Each new customer earns back too little of what it costs to win them.",
                    (
                        "Cut CAC: pause the most expensive channels",
                        "Raise ARPU with pricing or upsell",
                        "Reduce churn with onboarding and retention work",
                    ),
                )
            )
        if payback > 12:
            out.append(
                Suggestion(
                    "medium",
                    "Unit economics",
                    f"CAC payback is {payback:.0f} months",
                    "Paybacks over 12 months tie up cash in growth; target under 12.",
                )
            )
    if growth is not None and status.get("growth") == "above" and ebitda > 0:
        out.append(
            Suggestion(
                "low",
                "Valuation",
                "Growth above the sector range supports the upper end of the multiple range",
                "Document the growth drivers and retention data to back a premium valuation.",
            )
        )

    out.append(
        Suggestion(
            "low",
            "Sector playbook",
            f"Track the KPIs that matter in {sector.name}",
            ", ".join(sector.kpis) + ".",
            (sector.growth_levers[0], sector.margin_levers[0]),
        )
    )
    out.sort(key=lambda s: _PRIORITY_ORDER[s.priority])
    return tuple(out)


# ---------------------------------------------------------------- CSV upload

_ALIASES = {
    "name": ("name", "company", "company name", "business"),
    "sector": ("sector", "industry"),
    "revenue": ("revenue", "sales", "turnover", "total revenue", "net sales", "net revenue"),
    "cogs": ("cogs", "cost of goods sold", "cost of sales", "cost of revenue", "direct costs"),
    "opex": ("opex", "operating expenses", "operating costs", "sg&a", "sga", "overheads"),
    "prior_revenue": (
        "prior revenue",
        "previous revenue",
        "last year revenue",
        "prior year revenue",
    ),
    "growth": ("growth", "revenue growth", "yoy growth"),
    "cash": ("cash", "cash balance", "cash and equivalents"),
    "debt": ("debt", "total debt", "borrowings", "loans"),
    "monthly_burn": ("monthly burn", "burn", "burn rate"),
    "arpu": ("arpu", "monthly revenue per customer", "revenue per customer"),
    "churn": ("churn", "monthly churn", "churn rate"),
    "cac": ("cac", "customer acquisition cost"),
}
_LOOKUP = {alias: key for key, aliases in _ALIASES.items() for alias in aliases}
_TEXT_FIELDS = ("name", "sector")


def _number(raw: str) -> float | None:
    text = re.sub(r"[\s,$€£₹]", "", raw)
    if not text:
        return None
    scale = 1.0
    if text.endswith("%"):
        text, scale = text[:-1], 0.01
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text) * scale
    except ValueError:
        return None


def parse_financials(text: str) -> dict[str, float | str]:
    """Read ``metric,value[,value...]`` CSV rows into ``Profile`` keyword arguments.

    Unknown rows are ignored; a header row is skipped. With several values on
    the revenue row, the last is this year and the one before it prior year.
    """
    found: dict[str, float | str] = {}
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        key = _LOOKUP.get(re.sub(r"\s+", " ", row[0].strip().lower()))
        if key is None:
            continue
        cells = [c.strip() for c in row[1:] if c.strip()]
        if not cells:
            continue
        if key in _TEXT_FIELDS:
            found[key] = cells[-1].lower() if key == "sector" else cells[-1]
            continue
        values = [n for n in (_number(c) for c in cells) if n is not None]
        if not values:
            raise ValidationError(f"row {row[0]!r}: no number found in {', '.join(cells)}")
        found[key] = values[-1]
        if key == "revenue" and len(values) > 1 and "prior_revenue" not in found:
            found["prior_revenue"] = values[-2]
    if "sector" in found and found["sector"] not in SECTORS:
        sector = str(found["sector"])
        match = next((k for k, s in SECTORS.items() if sector in s.name.lower()), None)
        if match:
            found["sector"] = match
    return found
