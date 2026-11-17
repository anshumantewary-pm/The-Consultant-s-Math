"""Drill mode: random practice questions with checked answers.

Questions are generated from the calculators, so the answer key is always the
library's own math. A ``seed`` makes a drill repeatable (handy for study groups:
everyone gets the same questions).

``run_drill`` does the asking; it takes ``ask`` and ``say`` callables so the
CLI can pass ``input`` and ``print`` and tests can pass fakes.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from casemath.calculators.breakeven import break_even_units, payback_period
from casemath.calculators.growth import cagr
from casemath.calculators.market_share import relative_market_share, required_share
from casemath.calculators.market_sizing import top_down
from casemath.calculators.pricing import break_even_volume_change, price_elasticity
from casemath.calculators.profitability import profit_statement
from casemath.calculators.synergy import synergy_value
from casemath.core.errors import ValidationError
from casemath.core.formatting import fmt_money, fmt_number, fmt_pct
from casemath.core.result import Result


@dataclass(frozen=True)
class Question(Result):
    topic: str
    prompt: str
    answer: float
    unit: str  # "$", "%", "x", "units", "years" or ""
    explanation: str
    tolerance: float = 0.01  # relative; mental math rounds, so allow a little slack

    def shown_answer(self) -> str:
        return format_value(self.answer, self.unit)


def format_value(value: float, unit: str) -> str:
    if unit == "$":
        return fmt_money(value, compact=abs(value) >= 1e6)
    if unit == "%":
        return fmt_pct(value)
    if unit == "x":
        return f"{value:.2f}x"
    digits = 0 if abs(value) >= 100 else 2
    return fmt_number(value, digits) + (f" {unit}" if unit else "")


# ---------------------------------------------------------------- generators

Generator = Callable[[random.Random], Question]


def _profit(rng: random.Random) -> Question:
    price = rng.choice((5, 8, 10, 12, 20, 25, 40, 50))
    cost = price * rng.choice((0.4, 0.5, 0.6, 0.7))
    units = rng.choice((10, 20, 50, 80, 100, 250)) * 1_000
    fixed = round(units * (price - cost) * rng.choice((0.3, 0.5, 0.7, 0.9)), -3)
    st = profit_statement(price, units, cost, fixed)
    return Question(
        "profit",
        f"Price {fmt_money(price)}, variable cost {fmt_money(cost)} a unit, "
        f"{fmt_number(units)} units, fixed costs {fmt_money(fixed, compact=True)}. Profit?",
        st.profit,
        "$",
        f"({fmt_money(price)} - {fmt_money(cost)}) x {fmt_number(units)} - "
        f"{fmt_money(fixed, compact=True)} = {fmt_money(st.profit, compact=True)}",
    )


def _breakeven(rng: random.Random) -> Question:
    price = rng.choice((10, 15, 20, 25, 40, 50, 80, 100))
    cost = price * rng.choice((0.2, 0.4, 0.5, 0.6, 0.75))
    fixed = rng.choice((60, 120, 240, 300, 500, 900)) * 1_000
    units = break_even_units(fixed, price, cost)
    return Question(
        "breakeven",
        f"Fixed costs {fmt_money(fixed, compact=True)}, price {fmt_money(price)}, "
        f"variable cost {fmt_money(cost)}. Break-even units?",
        units,
        "units",
        f"{fmt_money(fixed, compact=True)} / ({fmt_money(price)} - {fmt_money(cost)}) "
        f"= {fmt_number(units)} units",
    )


def _payback(rng: random.Random) -> Question:
    investment = rng.choice((2, 5, 6, 10, 12, 30)) * 1_000_000
    cash = investment / rng.choice((2, 2.5, 3, 4, 5, 8))
    years = payback_period(investment, cash)
    return Question(
        "payback",
        f"An investment of {fmt_money(investment, compact=True)} returns "
        f"{fmt_money(cash, compact=True)} a year. Payback in years?",
        years,
        "years",
        f"{fmt_money(investment, compact=True)} / {fmt_money(cash, compact=True)} "
        f"= {years:.2f} years",
    )


def _share(rng: random.Random) -> Question:
    market = rng.choice((200, 400, 500, 800, 1_200)) * 1_000_000
    target = market * rng.choice((0.05, 0.08, 0.1, 0.15, 0.25))
    share = required_share(target, market)
    return Question(
        "share",
        f"The market is {fmt_money(market, compact=True)}. What share is needed for "
        f"{fmt_money(target, compact=True)} of revenue? (answer in %)",
        share,
        "%",
        f"{fmt_money(target, compact=True)} / {fmt_money(market, compact=True)} = {fmt_pct(share)}",
    )


def _relative_share(rng: random.Random) -> Question:
    rival = rng.choice((40, 60, 80, 120, 200))
    company = rival * rng.choice((0.25, 0.5, 0.75, 1.5, 2.0))
    relative = relative_market_share(company, rival)
    return Question(
        "share",
        f"Your sales are ${fmt_number(company)}M; the largest rival's are ${fmt_number(rival)}M. "
        "Relative market share? (answer as a multiple)",
        relative,
        "x",
        f"{fmt_number(company)} / {fmt_number(rival)} = {relative:.2f}x",
    )


def _sizing(rng: random.Random) -> Question:
    population = rng.choice((10, 20, 50, 100, 330)) * 1_000_000
    users = rng.choice((0.1, 0.2, 0.25, 0.4, 0.5))
    per_year = rng.choice((2, 4, 6, 12, 24, 52))
    price = rng.choice((2, 5, 10, 15, 30))
    size = top_down(population, [("buyers", users)], per_year, price)
    return Question(
        "sizing",
        f"{fmt_number(population / 1e6)}M people, {fmt_pct(users, 0)} buy, {per_year} times a "
        f"year, at {fmt_money(price)} each. Market size in $?",
        size.value_per_year,
        "$",
        f"{fmt_number(population / 1e6)}M x {fmt_pct(users, 0)} x {per_year} x {fmt_money(price)} "
        f"= {fmt_money(size.value_per_year, compact=True)}",
        tolerance=0.02,
    )


def _growth(rng: random.Random) -> Question:
    start = rng.choice((10, 20, 50, 100))
    rate = rng.choice((0.05, 0.1, 0.15, 0.2, 0.25))
    years = rng.choice((2, 3, 4, 5))
    end = round(start * (1 + rate) ** years, 1)
    growth = cagr(start, end, years)
    return Question(
        "growth",
        f"Revenue grew from ${start}M to ${end:g}M over {years} years. CAGR? (answer in %)",
        growth,
        "%",
        f"({end:g} / {start}) ^ (1/{years}) - 1 = {fmt_pct(growth)}",
        tolerance=0.03,
    )


def _pricing(rng: random.Random) -> Question:
    price = rng.choice((10, 20, 40, 50, 100))
    margin = rng.choice((0.2, 0.25, 0.3, 0.4, 0.5, 0.6))
    change = rng.choice((0.05, 0.1, 0.2, 0.25))
    cost = price * (1 - margin)
    limit = break_even_volume_change(price, cost, change)
    return Question(
        "pricing",
        f"Contribution margin is {fmt_pct(margin, 0)}. Price rises {fmt_pct(change, 0)}. "
        "How much volume can you lose before contribution falls? (answer in %, as a loss)",
        -limit,
        "%",
        f"{fmt_pct(change, 0)} / ({fmt_pct(margin, 0)} + {fmt_pct(change, 0)}) "
        f"= {fmt_pct(-limit)} of volume",
    )


def _elasticity(rng: random.Random) -> Question:
    price = rng.choice((10, 20, 40, 50))
    rise = rng.random() < 0.5
    new_price = price * rng.choice((1.1, 1.2) if rise else (0.9, 0.8))
    units = rng.choice((1_000, 2_000, 5_000, 10_000))
    # Volume moves against price, as it does for almost every product.
    new_units = units * rng.choice((0.7, 0.8, 0.9, 0.95) if rise else (1.05, 1.1, 1.3))
    e = price_elasticity(price, units, new_price, new_units)
    return Question(
        "pricing",
        f"Price moved {fmt_money(price)} to {fmt_money(new_price)}; volume went "
        f"{fmt_number(units)} to {fmt_number(new_units)}. Arc (midpoint) elasticity?",
        e,
        "",
        f"% change in units / % change in price, each on the midpoint: {e:.2f}",
        tolerance=0.03,
    )


def _synergy(rng: random.Random) -> Question:
    run_rate = rng.choice((5, 10, 15, 20, 25)) * 1_000_000
    multiple = rng.choice((6, 8, 10, 12))
    one_off = run_rate * rng.choice((1, 1.5, 2))
    value = synergy_value(run_rate, multiple, one_off)
    return Question(
        "synergy",
        f"Run-rate synergies {fmt_money(run_rate, compact=True)} a year, valued at {multiple}x, "
        f"with {fmt_money(one_off, compact=True)} of one-off integration costs. "
        "Most premium you can pay?",
        value,
        "$",
        f"{fmt_money(run_rate, compact=True)} x {multiple} - {fmt_money(one_off, compact=True)} "
        f"= {fmt_money(value, compact=True)}",
    )


TOPICS: dict[str, tuple[Generator, ...]] = {
    "profit": (_profit,),
    "breakeven": (_breakeven, _payback),
    "share": (_share, _relative_share),
    "sizing": (_sizing,),
    "growth": (_growth,),
    "pricing": (_pricing, _elasticity),
    "synergy": (_synergy,),
}


def generate(topic: str | None = None, count: int = 5, seed: int | None = None) -> list[Question]:
    """``count`` questions on ``topic`` (or a mix of all topics when ``None``)."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValidationError(f"count must be a whole number >= 1, got {count!r}")
    if topic is not None and topic not in TOPICS:
        raise ValidationError(f"unknown topic {topic!r}; choose from {', '.join(TOPICS)}")
    rng = random.Random(seed)
    pool = TOPICS[topic] if topic else tuple(g for gens in TOPICS.values() for g in gens)
    return [rng.choice(pool)(rng) for _ in range(count)]


# ---------------------------------------------------------------- answers

_SCALE = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}
_NUMBER = re.compile(r"^(-?\d+(?:\.\d+)?|-?\.\d+)([kmbt])?(%|x)?$")


def parse_answer(raw: str, unit: str = "") -> float:
    """Read what a person types: ``$1.2M``, ``41,667``, ``25%``, ``2.5x``, ``-16.7``.

    For ``%`` questions a bare number is read as percentage points (``25`` = 25%).
    """
    text = raw.strip().lower().replace(",", "").replace("$", "").replace(" ", "")
    for word in ("units", "unit", "years", "year", "yrs", "yr"):
        text = text.removesuffix(word)
    match = _NUMBER.match(text)
    if not match:
        raise ValidationError(f"could not read {raw!r} as a number")
    number, scale, suffix = match.groups()
    value = float(number) * (_SCALE[scale] if scale else 1.0)
    if suffix == "%" or unit == "%":
        value /= 100
    return value


def is_correct(question: Question, answer: float) -> bool:
    if question.answer == 0:
        return abs(answer) < 1e-9
    return abs(answer - question.answer) <= question.tolerance * abs(question.answer)


@dataclass(frozen=True)
class DrillScore(Result):
    asked: int
    correct: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.asked if self.asked else 0.0


def run_drill(
    questions: Sequence[Question],
    ask: Callable[[str], str],
    say: Callable[[str], None],
) -> DrillScore:
    """Ask each question, check the answer, explain it. Empty input skips; ``q`` quits.

    An unreadable answer is asked again. End of input (Ctrl-D) quits.
    """
    asked = correct = 0
    for number, question in enumerate(questions, start=1):
        say(f"\nQ{number} [{question.topic}] {question.prompt}")
        while True:
            try:
                raw = ask("> ")
            except EOFError:
                return DrillScore(asked, correct)
            if raw.strip().lower() in ("q", "quit", "exit"):
                return DrillScore(asked, correct)
            if not raw.strip():
                say(f"  Skipped. Answer: {question.shown_answer()}  ({question.explanation})")
                asked += 1
                break
            try:
                value = parse_answer(raw, question.unit)
            except ValidationError as error:
                say(f"  {error}; try again, press Enter to skip, or q to quit")
                continue
            asked += 1
            if is_correct(question, value):
                correct += 1
                say(f"  Correct: {question.shown_answer()}")
            else:
                say(f"  Not quite. Answer: {question.shown_answer()}  ({question.explanation})")
            break
    return DrillScore(asked, correct)
