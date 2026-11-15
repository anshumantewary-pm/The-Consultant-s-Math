"""Command-line interface: ``casemath <command> [options] [--json]``.

Every handler takes parsed arguments and returns an ``Output``: the text to
print and the data to emit with ``--json``. Handlers never print; ``main`` does.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from casemath import __version__
from casemath.calculators import (
    break_even_analysis,
    hhi,
    market_share,
    profit_bridge,
    profit_statement,
    relative_market_share,
    share_table,
    top_down,
    units_for_target_profit,
)
from casemath.cases import get_case, list_cases, render_case, render_solution
from casemath.cases.base import format_step
from casemath.core.errors import CaseMathError, ValidationError
from casemath.core.formatting import fmt_money, fmt_number, fmt_pct, fmt_signed_money
from casemath.frameworks import check_mece, profitability_tree, render


@dataclass(frozen=True)
class Output:
    text: str
    data: Any


Handler = Callable[[argparse.Namespace], Output]


# ---------------------------------------------------------------- parsing helpers


def _key_value(raw: str, kind: str) -> tuple[str, float]:
    name, sep, number = raw.rpartition("=")
    if not sep or not name.strip():
        raise ValidationError(f"{kind} must look like NAME=NUMBER, got {raw!r}")
    try:
        return name.strip(), float(number)
    except ValueError:
        raise ValidationError(f"{kind} {raw!r}: {number!r} is not a number") from None


def _unit_economics(raw: str, kind: str) -> tuple[float, float, float, float]:
    parts = raw.split(",")
    if len(parts) != 4:
        raise ValidationError(f"{kind} must be PRICE,UNITS,VARIABLE_COST,FIXED_COSTS, got {raw!r}")
    try:
        price, units, cost, fixed = (float(p) for p in parts)
    except ValueError:
        raise ValidationError(f"{kind} {raw!r} must contain only numbers") from None
    return price, units, cost, fixed


# ---------------------------------------------------------------- handlers


def _profit(args: argparse.Namespace) -> Output:
    st = profit_statement(args.price, args.units, args.variable_cost, args.fixed_costs)
    text = "\n".join(
        [
            f"Revenue            {fmt_money(st.revenue)}",
            f"Variable costs     {fmt_money(st.variable_costs)}",
            f"Contribution       {fmt_money(st.contribution)}  ({fmt_pct(st.contribution_margin)})",
            f"Fixed costs        {fmt_money(st.fixed_costs)}",
            f"Profit             {fmt_money(st.profit)}  ({fmt_pct(st.profit_margin)})",
        ]
    )
    return Output(text, st.to_dict())


def _bridge(args: argparse.Namespace) -> Output:
    before = profit_statement(*_unit_economics(args.before, "--before"))
    after = profit_statement(*_unit_economics(args.after, "--after"))
    bridge = profit_bridge(before, after)
    lines = [f"Profit before      {fmt_money(bridge.profit_before)}"]
    lines += [f"  {name:<16} {fmt_signed_money(v)}" for name, v in bridge.effects.items()]
    lines += [
        f"Profit after       {fmt_money(bridge.profit_after)}",
        f"Biggest driver     {bridge.biggest_driver}",
    ]
    return Output("\n".join(lines), {**bridge.to_dict(), "biggest_driver": bridge.biggest_driver})


def _breakeven(args: argparse.Namespace) -> Output:
    a = break_even_analysis(args.fixed_costs, args.price, args.variable_cost, args.expected_units)
    data = a.to_dict()
    lines = [
        f"Contribution/unit  {fmt_money(a.contribution_per_unit)}  "
        f"({fmt_pct(a.contribution_margin)})",
        f"Break-even units   {fmt_number(a.break_even_units, 2)}  "
        f"(sell {a.break_even_units_whole:,})",
        f"Break-even revenue {fmt_money(a.break_even_revenue)}",
    ]
    if a.margin_of_safety is not None:
        lines.append(f"Margin of safety   {fmt_pct(a.margin_of_safety)}")
    if args.target_profit is not None:
        target = units_for_target_profit(
            args.target_profit, args.fixed_costs, args.price, args.variable_cost
        )
        data["units_for_target_profit"] = target
        lines.append(f"Units for target   {fmt_number(target, 2)}")
    return Output("\n".join(lines), data)


def _share(args: argparse.Namespace) -> Output:
    share = market_share(args.company, args.market)
    data: dict[str, float] = {"market_share": share}
    lines = [f"Market share       {fmt_pct(share)}"]
    if args.largest_rival is not None:
        relative = relative_market_share(args.company, args.largest_rival)
        data["relative_market_share"] = relative
        lines.append(f"Relative share     {relative:.2f}x")
    return Output("\n".join(lines), data)


def _hhi(args: argparse.Namespace) -> Output:
    revenues = dict(_key_value(raw, "player") for raw in args.players)
    table = share_table(revenues)
    concentration = hhi(table.shares())
    lines = [f"{row.name:<20} {fmt_pct(row.share):>7}" for row in table.rows]
    lines += ["", f"HHI {fmt_number(concentration.hhi)}: {concentration.band}"]
    return Output("\n".join(lines), {"table": table.to_dict(), **concentration.to_dict()})


def _size(args: argparse.Namespace) -> Output:
    filters = [_key_value(raw, "--filter") for raw in args.filter]
    size = top_down(args.population, filters, args.units_per_customer, args.price)
    text = "\n".join(format_step(step) for step in size.steps)
    return Output(text, size.to_dict())


def _tree(args: argparse.Namespace) -> Output:
    tree = profitability_tree(args.price, args.units, args.variable_cost, args.fixed_costs)
    report = check_mece(tree)
    text = render(tree, show_hints=args.hints) + "\n\n" + report.summary()
    return Output(text, {"tree": tree.to_dict(), "mece": report.to_dict()})


def _case(args: argparse.Namespace) -> Output:
    if args.action == "list":
        cases = list_cases()
        lines = [f"{c.id}  {c.case_type:<14} {c.title}" for c in cases]
        data = [{"id": c.id, "type": c.case_type, "title": c.title} for c in cases]
        return Output("\n".join(lines), data)
    if args.id is None:
        raise ValidationError(f"'case {args.action}' needs a case id, e.g. 'case {args.action} 1'")
    case = get_case(args.id)
    if args.action == "show":
        return Output(render_case(case), {"id": case.id, "prompt": case.prompt.strip(),
                                          "data": case.data()})  # fmt: skip
    solution = case.solve()
    return Output(render_solution(solution), solution.to_dict())


# ---------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="casemath",
        description="Consulting case math: profitability, break-even, market share, sizing.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def add(name: str, handler: Handler, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, parents=[common], help=help_text, description=help_text)
        p.set_defaults(handler=handler)
        return p

    p = add("profit", _profit, "one-period P&L from unit economics")
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--units", type=float, required=True)
    p.add_argument("--variable-cost", type=float, required=True, help="per unit")
    p.add_argument("--fixed-costs", type=float, default=0.0)

    p = add("bridge", _bridge, "split a profit change into price/volume/cost effects")
    p.add_argument("--before", required=True, metavar="P,Q,V,F")
    p.add_argument("--after", required=True, metavar="P,Q,V,F")

    p = add("breakeven", _breakeven, "break-even units and revenue")
    p.add_argument("--fixed-costs", type=float, required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--variable-cost", type=float, required=True, help="per unit")
    p.add_argument("--expected-units", type=float, help="adds margin of safety")
    p.add_argument("--target-profit", type=float, help="adds units needed for this profit")

    p = add("share", _share, "market share and relative market share")
    p.add_argument("--company", type=float, required=True, help="company sales")
    p.add_argument("--market", type=float, required=True, help="total market sales")
    p.add_argument("--largest-rival", type=float, help="largest competitor's sales")

    p = add("hhi", _hhi, "share table and Herfindahl-Hirschman concentration index")
    p.add_argument("players", nargs="+", metavar="NAME=SALES")

    p = add("size", _size, "top-down market sizing")
    p.add_argument("--population", type=float, required=True)
    p.add_argument("--filter", action="append", default=[], metavar="LABEL=FRACTION")
    p.add_argument("--units-per-customer", type=float, required=True, help="per year")
    p.add_argument("--price", type=float, required=True, help="per unit")

    p = add("tree", _tree, "the profitability issue tree, with a MECE check")
    p.add_argument("--price", type=float)
    p.add_argument("--units", type=float)
    p.add_argument("--variable-cost", type=float)
    p.add_argument("--fixed-costs", type=float)
    p.add_argument("--hints", action="store_true", help="show the question to ask at each node")

    p = add("case", _case, "list, show or solve the practice cases")
    p.add_argument("action", choices=["list", "show", "solve"])
    p.add_argument("id", nargs="?")

    return parser


def ensure_utf8(stream: object) -> None:
    """Windows pipes default to cp1252, which cannot print the tree's box characters."""
    if isinstance(stream, io.TextIOWrapper) and (stream.encoding or "").lower() not in (
        "utf-8",
        "utf8",
    ):
        stream.reconfigure(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8(sys.stdout)
    args = build_parser().parse_args(argv)
    try:
        output: Output = args.handler(args)
    except CaseMathError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(output.data, indent=2, allow_nan=False))
    else:
        print(output.text)
    return 0
