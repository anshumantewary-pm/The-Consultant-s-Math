"""Command-line interface: ``casemath <command> [options] [--json]``.

Every handler takes parsed arguments and returns an ``Output``: the text to
print and the data to emit with ``--json``. Handlers never print; ``main`` does.
The two exceptions are interactive by nature: ``drill`` (without ``--reveal``)
and ``serve``, which prints its URL and then runs until Ctrl-C.
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
from casemath.analysis import (
    MODELS,
    BuiltinModel,
    get_model,
    goal_seek,
    parse_distribution,
    simulate,
    tornado,
)
from casemath.analysis.montecarlo import render_histogram
from casemath.calculators import (
    break_even_analysis,
    hhi,
    investment_appraisal,
    market_share,
    optimal_price_linear,
    price_change_impact,
    price_elasticity,
    profit_bridge,
    profit_maximising_price,
    profit_statement,
    relative_market_share,
    share_table,
    synergy_value,
    top_down,
    unit_economics,
    units_for_target_profit,
)
from casemath.cases import get_case, list_cases, render_case, render_solution
from casemath.cases.base import format_step
from casemath.core.errors import CaseMathError, ValidationError
from casemath.core.formatting import fmt_money, fmt_number, fmt_pct, fmt_signed_money
from casemath.drill import TOPICS, generate, run_drill
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


def _points(raw: str | None) -> tuple[float, float, float, float]:
    if raw is None:
        raise ValidationError("--points PRICE1,UNITS1,PRICE2,UNITS2 is required here")
    parts = raw.split(",")
    try:
        p1, q1, p2, q2 = (float(p) for p in parts)
    except ValueError:
        raise ValidationError(
            f"--points must be four numbers PRICE1,UNITS1,PRICE2,UNITS2, got {raw!r}"
        ) from None
    return p1, q1, p2, q2


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


def _optional(value: float | None, render: Callable[[float], str], never: str = "never") -> str:
    return never if value is None else render(value)


def _years(value: float) -> str:
    return f"{value:.2f} periods"


def _invest(args: argparse.Namespace) -> Output:
    a = investment_appraisal(args.rate, args.flows)
    lines = [
        f"Discount rate      {fmt_pct(a.rate)}",
        f"NPV                {fmt_money(a.npv)}",
        f"IRR                {_optional(a.irr, fmt_pct, 'n/a (flows do not change sign)')}",
        f"Profitability idx  {_optional(a.profitability_index, lambda v: f'{v:.2f}x', 'n/a')}",
        f"Payback            {_optional(a.simple_payback, _years)}",
        f"Discounted payback {_optional(a.discounted_payback, _years)}",
        f"Decision (NPV > 0) {'invest' if a.accept else 'do not invest'}",
    ]
    return Output("\n".join(lines), {**a.to_dict(), "accept": a.accept})


def _unit_econ(args: argparse.Namespace) -> Output:
    ue = unit_economics(args.revenue, args.margin, args.churn, args.cac, args.discount_rate)
    verdict = "healthy" if ue.healthy else "unhealthy"
    reasons = []
    if ue.ltv_to_cac < 3:
        reasons.append("LTV/CAC below 3x")
    if not ue.payback_within_lifetime:
        reasons.append("CAC not repaid before the average customer churns")
    lines = [
        f"Customer lifetime  {fmt_number(ue.lifetime_periods, 1)} periods",
        f"Lifetime value     {fmt_money(ue.ltv)}",
        f"CAC                {fmt_money(ue.cac)}",
        f"LTV / CAC          {ue.ltv_to_cac:.2f}x",
        f"CAC payback        {fmt_number(ue.cac_payback_periods, 1)} periods",
        f"Verdict            {verdict}" + (f" ({'; '.join(reasons)})" if reasons else ""),
    ]
    return Output("\n".join(lines), {**ue.to_dict(), "healthy": ue.healthy})


def _optimal_price(args: argparse.Namespace) -> Output:
    if args.points is not None:
        opt = optimal_price_linear(*_points(args.points), unit_cost=args.unit_cost)
        lines = [
            f"Demand             Q = {fmt_number(opt.intercept, 1)} - "
            f"{fmt_number(opt.slope, 2)} x P",
            f"Choke price        {fmt_money(opt.choke_price)}",
            f"Optimal price      {fmt_money(opt.price)}",
            f"Units at optimum   {fmt_number(opt.units, 1)}",
            f"Contribution       {fmt_money(opt.contribution)}",
        ]
        return Output("\n".join(lines), opt.to_dict())
    if args.elasticity is None:
        raise ValidationError("optimal-price needs --points P1,Q1,P2,Q2 or --elasticity")
    price = profit_maximising_price(args.unit_cost, args.elasticity)
    return Output(
        f"Optimal price      {fmt_money(price)}  (markup {price / args.unit_cost - 1:.0%})",
        {"price": price, "elasticity": args.elasticity, "unit_cost": args.unit_cost},
    )


def _pair(raw: str, kind: str) -> tuple[float, float]:
    """``LOW:HIGH`` -> (low, high)."""
    low, sep, high = raw.partition(":")
    try:
        if not sep:
            raise ValueError
        return float(low), float(high)
    except ValueError:
        raise ValidationError(f"{kind} must look like LOW:HIGH, got {raw!r}") from None


def _model_and_base(args: argparse.Namespace) -> tuple[BuiltinModel, dict[str, float]]:
    model = get_model(args.model)
    base = dict(model.defaults)
    for raw in args.set:
        name, value = _key_value(raw, "--set")
        if name not in base:
            raise ValidationError(
                f"--set {name}: model {model.name!r} has inputs {', '.join(base)}"
            )
        base[name] = value
    return model, base


def _fmt_output(model: BuiltinModel, value: float) -> str:
    return f"{value:.2f}x" if model.output.endswith("CAC") else fmt_money(value)


def _models(args: argparse.Namespace) -> Output:
    lines = []
    for m in MODELS.values():
        inputs = ", ".join(f"{k}={v:,.10g}" for k, v in m.defaults.items())
        lines += [f"{m.name:<8} {m.description}", f"         defaults: {inputs}"]
    data = {m.name: {"description": m.description, "defaults": m.defaults} for m in MODELS.values()}
    return Output("\n".join(lines), data)


def _sensitivity(args: argparse.Namespace) -> Output:
    model, base = _model_and_base(args)
    ranges = None
    if args.range:
        ranges = {}
        for raw in args.range:
            name, _, bounds = raw.partition("=")
            ranges[name.strip()] = _pair(bounds, f"--range {name}")
    t = tornado(model.function, base, ranges, pct=args.pct)
    widest = t.bars[0].swing or 1.0
    lines = [f"{model.output} at base case: {_fmt_output(model, t.base_output)}", ""]
    for bar in t.bars:
        length = round(30 * bar.swing / widest)
        lines.append(
            f"{bar.input:<14} {'#' * length:<30} {_fmt_output(model, bar.output_at_low)} to "
            f"{_fmt_output(model, bar.output_at_high)}  ({bar.low_value:g} to {bar.high_value:g})"
        )
    lines += ["", f"Most sensitive: {t.most_sensitive}"]
    return Output("\n".join(lines), {**t.to_dict(), "most_sensitive": t.most_sensitive})


def _goalseek(args: argparse.Namespace) -> Output:
    model, base = _model_and_base(args)
    low, high = _pair(args.between, "--between")
    result = goal_seek(model.function, base, args.vary, args.target, low, high)
    text = (
        f"{args.vary} = {result.value:,.6g} gives {model.output} = "
        f"{_fmt_output(model, result.output)}"
    )
    return Output(text, result.to_dict())


def _simulate(args: argparse.Namespace) -> Output:
    model, base = _model_and_base(args)
    inputs: dict[str, Any] = dict(base)
    for raw in args.dist:
        name, sep, spec = raw.partition("=")
        if not sep or name.strip() not in base:
            raise ValidationError(
                f"--dist must look like NAME=SPEC with NAME one of {', '.join(base)}, got {raw!r}"
            )
        inputs[name.strip()] = parse_distribution(spec)
    sim = simulate(model.function, inputs, runs=args.runs, seed=args.seed, threshold=args.threshold)

    def fmt(value: float) -> str:
        return _fmt_output(model, value)

    low, high = sim.band_90
    lines = [
        f"Runs               {sim.runs:,} (seed {sim.seed})",
        f"Deterministic      {fmt(sim.deterministic)}",
        f"Mean               {fmt(sim.mean)}",
        f"Median             {fmt(sim.p50)}",
        f"90% range          {fmt(low)} to {fmt(high)}",
        f"{f'P({model.output} < {args.threshold:g})':<19}{fmt_pct(sim.prob_below_threshold)}",
        "",
        *render_histogram(sim.histogram),
    ]
    return Output("\n".join(lines), sim.to_dict())


def _price(args: argparse.Namespace) -> Output:
    if args.elasticity is None:
        if args.test is None:
            raise ValidationError("give --elasticity, or --test OLD_UNITS,NEW_UNITS to measure it")
        parts = args.test.split(",")
        try:
            old_units, new_units = (float(p) for p in parts)
        except ValueError:
            raise ValidationError(
                f"--test must be OLD_UNITS,NEW_UNITS, got {args.test!r}"
            ) from None
        elasticity = price_elasticity(args.price, old_units, args.new_price, new_units)
    else:
        elasticity = args.elasticity
    c = price_change_impact(
        args.price, args.units, args.variable_cost, args.new_price, elasticity, args.fixed_costs
    )
    verdict = "pays off" if c.pays_off else "does not pay off"
    text = "\n".join(
        [
            f"Price change       {fmt_pct(c.price_change)}",
            f"Elasticity         {c.elasticity:.2f}",
            f"Expected volume    {fmt_pct(c.expected_volume_change)}",
            f"Break-even volume  {fmt_pct(c.break_even_volume_change)}",
            f"Profit before      {fmt_money(c.before.profit)}",
            f"Profit after       {fmt_money(c.after.profit)}",
            f"Change             {fmt_signed_money(c.profit_change)}  ({verdict})",
        ]
    )
    return Output(text, {**c.to_dict(), "pays_off": c.pays_off})


def _synergy(args: argparse.Namespace) -> Output:
    value = synergy_value(args.run_rate, args.multiple, args.one_off)
    data: dict[str, float | bool] = {"synergy_value": value}
    lines = [f"Synergy value      {fmt_money(value)}"]
    if args.premium is not None:
        headroom = value - args.premium
        data |= {"premium": args.premium, "headroom": headroom, "justified": headroom >= 0}
        verdict = "justified" if headroom >= 0 else "not justified by synergies"
        lines.append(f"Headroom vs premium {fmt_signed_money(headroom)}  ({verdict})")
    return Output("\n".join(lines), data)


def _drill(args: argparse.Namespace) -> Output:
    questions = generate(args.topic, args.count, args.seed)
    data = [q.to_dict() for q in questions]
    if args.reveal or args.json:
        lines = []
        for i, q in enumerate(questions, start=1):
            lines += [f"Q{i} [{q.topic}] {q.prompt}", f"   {q.shown_answer()}  ({q.explanation})"]
        return Output("\n".join(lines), data)
    score = run_drill(questions, input, print)
    text = f"\nScore: {score.correct}/{score.asked}"
    if score.asked:
        text += f" ({fmt_pct(score.accuracy, 0)})"
    return Output(text, data)


def _serve(args: argparse.Namespace) -> Output:
    from casemath.web.server import make_server  # web imports cli, so import late

    try:
        server = make_server(args.host, args.port, verbose=args.verbose)
    except OSError as error:
        raise ValidationError(f"cannot listen on {args.host}:{args.port}: {error}") from None
    shown_host = "localhost" if args.host in ("127.0.0.1", "0.0.0.0", "") else args.host
    url = f"http://{shown_host}:{server.server_port}/"
    print(f"casemath web UI on {url}  (Ctrl-C to stop)", flush=True)
    if args.open:
        import webbrowser

        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return Output("stopped", {"url": url})


# ---------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="casemath",
        description=(
            "Consulting case math: profitability, break-even, market share, sizing, "
            "pricing and M&A synergies."
        ),
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

    p = add("invest", _invest, "NPV, IRR, profitability index and payback of a cash-flow series")
    p.add_argument("--rate", type=float, required=True, help="discount rate per period, e.g. 0.1")
    p.add_argument(
        "flows",
        nargs="+",
        type=float,
        metavar="FLOW",
        help="period 0 first (usually negative); put -- before flows like -1e6",
    )

    p = add("unit-econ", _unit_econ, "customer lifetime value, LTV/CAC and CAC payback")
    p.add_argument("--revenue", type=float, required=True, help="revenue per customer per period")
    p.add_argument("--margin", type=float, required=True, help="gross margin as a fraction")
    p.add_argument("--churn", type=float, required=True, help="customers lost per period, 0..1")
    p.add_argument("--cac", type=float, required=True, help="cost to acquire one customer")
    p.add_argument("--discount-rate", type=float, default=0.0, help="per period (default 0)")

    p = add("optimal-price", _optimal_price, "profit-maximising price (two points or elasticity)")
    p.add_argument("--unit-cost", type=float, required=True, help="variable cost per unit")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--points", metavar="P1,Q1,P2,Q2", help="two observed price/volume points")
    group.add_argument("--elasticity", type=float, help="constant elasticity, below -1")

    add("models", _models, "list the built-in models used by sensitivity, goalseek and simulate")

    def model_command(name: str, handler: Handler, help_text: str) -> argparse.ArgumentParser:
        p = add(name, handler, help_text)
        p.add_argument("model", choices=list(MODELS), help="built-in model (see 'models')")
        p.add_argument(
            "--set", action="append", default=[], metavar="NAME=VALUE", help="override an input"
        )
        return p

    p = model_command(
        "sensitivity", _sensitivity, "tornado: rank inputs by how much they move the answer"
    )
    p.add_argument("--range", action="append", default=[], metavar="NAME=LOW:HIGH")
    p.add_argument("--pct", type=float, default=0.10, help="swing when no --range (default 0.10)")

    p = model_command("goalseek", _goalseek, "find the input value that hits a target output")
    p.add_argument("--vary", required=True, metavar="NAME", help="input to solve for")
    p.add_argument("--target", type=float, default=0.0, help="output to hit (default 0)")
    p.add_argument("--between", required=True, metavar="LOW:HIGH", help="search bracket")

    p = model_command("simulate", _simulate, "Monte Carlo: ranges on inputs -> range on the answer")
    p.add_argument(
        "--dist",
        action="append",
        default=[],
        metavar="NAME=SPEC",
        help="uncertain input, e.g. units=tri:30000:40000:45000 or price=normal:10:0.5",
    )
    p.add_argument("--runs", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--threshold", type=float, default=0.0, help="report P(output < this)")

    p = add("tree", _tree, "the profitability issue tree, with a MECE check")
    p.add_argument("--price", type=float)
    p.add_argument("--units", type=float)
    p.add_argument("--variable-cost", type=float)
    p.add_argument("--fixed-costs", type=float)
    p.add_argument("--hints", action="store_true", help="show the question to ask at each node")

    p = add("price", _price, "will a price change pay off? elasticity and break-even volume")
    p.add_argument("--price", type=float, required=True, help="current price")
    p.add_argument("--new-price", type=float, required=True)
    p.add_argument("--units", type=float, required=True, help="current volume")
    p.add_argument("--variable-cost", type=float, required=True, help="per unit")
    p.add_argument("--fixed-costs", type=float, default=0.0)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--elasticity", type=float, help="e.g. -1.5")
    group.add_argument("--test", metavar="OLD_UNITS,NEW_UNITS",
                       help="measure elasticity from a test at --price vs --new-price")  # fmt: skip

    p = add("synergy", _synergy, "value of M&A synergies vs the premium paid")
    p.add_argument("--run-rate", type=float, required=True, help="annual profit synergies")
    p.add_argument("--multiple", type=float, required=True, help="valuation multiple, e.g. 8")
    p.add_argument("--one-off", type=float, default=0.0, help="one-off integration costs")
    p.add_argument("--premium", type=float, help="premium over standalone value")

    p = add("drill", _drill, "practice questions with checked answers")
    p.add_argument("--topic", choices=list(TOPICS), help="default: a mix of every topic")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--seed", type=int, help="same seed, same questions")
    p.add_argument("--reveal", action="store_true", help="print questions with answers, no quiz")

    p = add("serve", _serve, "run the local web UI (calculators, cases, drill)")
    p.add_argument("--host", default="127.0.0.1", help="default: localhost only")
    p.add_argument("--port", type=int, default=8765, help="0 picks a free port")
    p.add_argument("--open", action="store_true", help="open it in your browser")
    p.add_argument("--verbose", action="store_true", help="log each request")

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
