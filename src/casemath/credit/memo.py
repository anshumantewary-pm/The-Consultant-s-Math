"""Render a ``CreditDecision`` as a credit memo (Markdown) and a short text summary.

The memo follows the section order a wholesale credit committee expects. Every
figure comes from the decision object, so the memo can never disagree with
the decision it documents.
"""

from __future__ import annotations

from casemath.credit.analysis import Spread
from casemath.credit.decision import CreditDecision


def _m(value: float | None) -> str:
    return "n/a" if value is None else f"{value / 1e6:,.1f}"


def _x(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}x"


def _m2(value: float) -> str:
    return f"{value / 1e6:,.2f}"


def _pct(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


def _bps(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 1e4:.0f} bp"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _spread_rows(spreads: tuple[Spread, ...]) -> list[list[str]]:
    def row(label: str, values: list[str]) -> list[str]:
        return [label, *values]

    return [
        row("Revenue (M)", [_m(s.revenue) for s in spreads]),
        row("Revenue growth", [_pct(s.revenue_growth) for s in spreads]),
        row("EBITDA (M)", [_m(s.ebitda) for s in spreads]),
        row("EBITDA margin", [_pct(s.ebitda_margin) for s in spreads]),
        row("Total debt (M)", [_m(s.total_debt) for s in spreads]),
        row("Net debt (M)", [_m(s.net_debt) for s in spreads]),
        row("Debt / EBITDA", [_x(s.leverage) for s in spreads]),
        row("Net debt / EBITDA", [_x(s.net_leverage) for s in spreads]),
        row("Interest cover", [_x(s.icr) for s in spreads]),
        row("DSCR", [_x(s.dscr) for s in spreads]),
        row("Free cash flow (M)", [_m(s.free_cash_flow) for s in spreads]),
        row("Current ratio", [_x(s.current_ratio) for s in spreads]),
    ]


def render_memo(d: CreditDecision) -> str:
    b, r, req = d.borrower, d.rating, d.borrower.request
    g = r.final
    facility = req.facility_type.replace("_", " ")
    out: list[str] = [
        f"# Credit Memo: {b.name}",
        "",
        f"**Recommendation: {d.decision}** · Internal grade **{g.grade}** ({g.equivalent}, "
        f"PD {_pct(g.pd, 2)}) · Approver: **{d.approver}**",
        "",
        *_table(
            ["Item", "Detail"],
            [
                ["Borrower", b.name + (f" ({b.group})" if b.group else "")],
                ["Industry", d.industry.name],
                ["Country", b.country or "n/a"],
                ["Facility", f"{_m(req.amount)}M {req.seniority.replace('_', ' ')} {facility}"],
                [
                    "Tenor / repayment",
                    f"{req.tenor_years:g} years, "
                    + (f"{_pct(req.amortisation)} a year" if req.amortisation else "bullet"),
                ],
                [
                    "Pricing",
                    f"Base {_pct(req.base_rate)} + {_bps(req.margin)}; "
                    f"upfront fee {_pct(req.upfront_fee, 2)}",
                ],
                ["Purpose", req.purpose or "n/a"],
                ["Total exposure after deal", f"{_m(d.total_exposure)}M"],
            ],
        ),
        "",
        "## 1. Executive summary",
        "",
    ]
    pf = d.pro_forma
    out.append(
        f"{b.name} requests a {_m(req.amount)}M {facility}. Pro forma leverage is "
        f"{_x(pf.leverage)} against an industry ceiling of {_x(d.industry.max_leverage)}, "
        f"interest cover {_x(pf.icr)} and DSCR {_x(pf.dscr)}. The scorecard gives "
        f"{r.score:.0f}/100, grade {g.grade} ({g.label.lower()}). Expected loss is "
        f"{_m2(d.returns.expected_loss)}M a year and RAROC {_pct(d.returns.raroc)}."
    )
    out += ["", "Decision drivers:", ""] + [f"- {reason}" for reason in d.reasons]
    if d.recommended_amount < req.amount:
        out += ["", f"Amount that fits policy and the hold limit: **{_m(d.recommended_amount)}M**."]
    if d.recommended_margin > req.margin:
        out += [f"Margin needed to meet the hurdle: **{_bps(d.recommended_margin)}**."]

    out += ["", "## 2. Borrower overview", ""]
    out.append(b.description or "No business description supplied.")
    q = b.qualitative
    out += [
        "",
        f"Management {q.management}/5 · market position {q.market_position}/5 · "
        f"reporting quality {q.financial_reporting}/5 · {q.years_in_business:g} years trading.",
    ]
    if q.notes:
        out += ["", q.notes]

    spreads = (*d.history, pf)
    out += ["", "## 3. Financial analysis", ""]
    out += _table(["Metric", *[s.period for s in spreads]], _spread_rows(spreads))

    c = d.capacity
    out += [
        "",
        "## 4. Debt capacity and repayment",
        "",
        f"- New money requested: {_m(c.requested_additional)}M",
        f"- Headroom to the {_x(d.industry.max_leverage)} leverage ceiling: {_m(c.by_leverage)}M",
        f"- Headroom to the minimum DSCR at the requested terms: {_m(c.by_dscr)}M",
        f"- Debt capacity within policy: **{_m(c.max_additional)}M**",
        "- Payback of net debt from free cash flow: "
        + ("n/a" if pf.payback_years is None else f"{pf.payback_years:.1f} years"),
        "",
        "## 5. Risk rating",
        "",
    ]
    out += _table(
        ["Factor", "Value", "Weight", "Score", "Points"],
        [
            [f.label, f.display, _pct(f.weight), f"{f.score:.0f}", f"{f.contribution:.1f}"]
            for f in r.factors
        ],
    )
    out += [
        "",
        f"Weighted score {r.score:.1f} gives model grade {r.model_grade}; final grade "
        f"{g.grade} ({g.equivalent}, one-year PD {_pct(g.pd, 2)}).",
    ]
    out += [f"- Override: {o}" for o in r.overrides]

    cv = d.cover
    out += ["", "## 6. Collateral and loss given default", ""]
    if b.collateral:
        out += _table(
            ["Collateral", "Market value (M)", "Haircut", "Recoverable (M)"],
            [
                [
                    c.description or c.type.replace("_", " "),
                    _m(c.value),
                    _pct(c.haircut),
                    _m(c.recoverable),
                ]
                for c in b.collateral
            ],
        )
        out.append("")
    out.append(
        f"Recoverable value counted: {_m(cv.recoverable)}M, covering {_x(cv.coverage)} of "
        f"EAD {_m(d.returns.ead)}M. LGD {_pct(cv.lgd)}."
    )

    rt = d.returns
    out += ["", "## 7. Pricing and returns", ""]
    out += _table(
        ["Line (one year)", "Amount (M)"],
        [
            ["Net interest income", _m2(rt.net_interest_income)],
            ["Fees", _m2(rt.fee_income)],
            ["Operating cost", _m2(-rt.operating_cost)],
            ["Expected loss", _m2(-rt.expected_loss)],
            ["Profit after tax", _m2(rt.profit_after_tax)],
            ["Risk-weighted assets (IRB)", _m2(rt.rwa)],
            ["Capital allocated", _m2(rt.capital)],
            ["RAROC", _pct(rt.raroc)],
        ],
    )
    out += ["", f"Margin that meets the hurdle: {_bps(rt.required_margin)}."]

    out += ["", "## 8. Policy compliance", ""]
    out += _table(
        ["Check", "Actual", "Limit", "Result"],
        [
            [
                ch.label,
                ch.actual,
                ch.limit,
                "Pass" if ch.passed else ("FAIL (hard stop)" if ch.hard else "Exception"),
            ]
            for ch in d.checks
        ],
    )

    cov = d.covenants
    out += [
        "",
        "## 9. Proposed structure and covenants",
        "",
        f"- Maximum Debt / EBITDA: {cov.max_leverage:.2f}x",
        f"- Minimum interest cover: {cov.min_icr:.2f}x",
        f"- Minimum DSCR: {cov.min_dscr:.2f}x",
        f"- Testing and reporting: {cov.reporting}",
        "",
        "## 10. Key risks and mitigants",
        "",
    ]
    out += _table(["Risk", "Mitigant"], [[k.risk, k.mitigant] for k in d.risks] or [["None", "-"]])
    out += ["", "## 11. Conditions", ""] + [f"- {item}" for item in d.conditions]
    out += ["", "## 12. Monitoring and early-warning triggers", ""]
    out += [f"- {t}" for t in d.monitoring_triggers]
    out += [
        "",
        "---",
        "_Prepared by CreditDecision. Figures are computed from the borrower file; the "
        "scorecard, haircuts and limits are indicative defaults set in BankPolicy._",
        "",
    ]
    return "\n".join(out)


def render_summary(d: CreditDecision) -> str:
    g, pf, rt = d.rating.final, d.pro_forma, d.returns
    lines = [
        f"{d.borrower.name} · {d.industry.name}",
        f"Decision        {d.decision}",
        f"Approver        {d.approver}",
        f"Grade           {g.grade} ({g.equivalent}), PD {_pct(g.pd, 2)}, "
        f"score {d.rating.score:.0f}",
        f"Pro forma       leverage {_x(pf.leverage)}  ICR {_x(pf.icr)}  DSCR {_x(pf.dscr)}",
        f"LGD / EL        {_pct(d.cover.lgd)} / {_m2(rt.expected_loss)}M",
        f"RAROC           {_pct(rt.raroc)} (margin for hurdle {_bps(rt.required_margin)})",
        f"Fits policy     {_m(d.recommended_amount)}M of {_m(d.borrower.request.amount)}M",
        "",
    ]
    lines += [f"  - {reason}" for reason in d.reasons]
    return "\n".join(lines)
