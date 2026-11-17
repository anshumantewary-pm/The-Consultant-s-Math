import json
from collections.abc import Iterator

import pytest

from casemath.core import ValidationError
from casemath.drill import (
    TOPICS,
    DrillScore,
    Question,
    format_value,
    generate,
    is_correct,
    parse_answer,
    run_drill,
)


class TestGenerate:
    def test_seed_is_repeatable(self) -> None:
        assert generate(count=10, seed=42) == generate(count=10, seed=42)

    def test_different_seeds_differ(self) -> None:
        assert generate(count=10, seed=1) != generate(count=10, seed=2)

    @pytest.mark.parametrize("topic", list(TOPICS))
    def test_every_topic_many_seeds(self, topic: str) -> None:
        for seed in range(100):
            for q in generate(topic, 3, seed):
                assert q.prompt.endswith("?") or q.prompt.endswith(")")
                assert q.explanation
                assert is_correct(q, q.answer)
                json.dumps(q.to_dict(), allow_nan=False)

    def test_mixed_topics(self) -> None:
        topics = {q.topic for q in generate(count=200, seed=0)}
        assert topics == set(TOPICS) | {"payback"}  # payback lives under "breakeven"

    def test_elasticity_is_negative(self) -> None:
        for seed in range(200):
            for q in generate("pricing", 2, seed):
                if "elasticity" in q.prompt:
                    assert q.answer < 0

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [({"count": 0}, "count"), ({"count": True}, "count"), ({"topic": "tax"}, "topic")],
    )
    def test_errors(self, kwargs: dict[str, object], match: str) -> None:
        with pytest.raises(ValidationError, match=match):
            generate(**kwargs)  # type: ignore[arg-type]


class TestParse:
    @pytest.mark.parametrize(
        ("raw", "unit", "expected"),
        [
            ("$1.2M", "$", 1.2e6),
            ("41,667", "units", 41_667),
            ("41,667 units", "units", 41_667),
            ("3.5 years", "years", 3.5),
            ("25%", "%", 0.25),
            ("25", "%", 0.25),
            ("25%", "", 0.25),
            ("2.5x", "x", 2.5),
            ("-1.7", "", -1.7),
            (".5", "", 0.5),
            ("300k", "$", 300_000),
            ("1b", "$", 1e9),
        ],
    )
    def test_ok(self, raw: str, unit: str, expected: float) -> None:
        assert parse_answer(raw, unit) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", ["", "abc", "1.2.3", "5 apples"])
    def test_bad(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="could not read"):
            parse_answer(raw)


def test_is_correct_tolerance() -> None:
    q = Question("t", "p?", 100.0, "", "e")
    assert is_correct(q, 100.9)
    assert not is_correct(q, 102)
    zero = Question("t", "p?", 0.0, "$", "e")
    assert is_correct(zero, 0)
    assert not is_correct(zero, 0.01)


@pytest.mark.parametrize(
    ("value", "unit", "shown"),
    [
        (2.5e6, "$", "$2.5M"),
        (12.5, "$", "$12.50"),
        (0.256, "%", "25.6%"),
        (1.5, "x", "1.50x"),
        (41_666.7, "units", "41,667 units"),
        (-1.7, "", "-1.70"),
    ],
)
def test_format_value(value: float, unit: str, shown: str) -> None:
    assert format_value(value, unit) == shown


def fake_input(*answers: str):  # type: ignore[no-untyped-def]
    it: Iterator[str] = iter(answers)

    def ask(_prompt: str) -> str:
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    return ask


QUESTIONS = [
    Question("profit", "Q one?", 100.0, "$", "because"),
    Question("share", "Q two?", 0.25, "%", "because"),
    Question("growth", "Q three?", 3.0, "x", "because"),
]


class TestRunDrill:
    def test_mix_of_outcomes(self) -> None:
        said: list[str] = []
        score = run_drill(QUESTIONS, fake_input("100", "oops", "30", ""), said.append)
        assert score == DrillScore(asked=3, correct=1)
        text = "\n".join(said)
        assert "Correct: $100.00" in text
        assert "could not read 'oops'" in text
        assert "Not quite. Answer: 25.0%" in text
        assert "Skipped. Answer: 3.00x" in text

    def test_quit(self) -> None:
        score = run_drill(QUESTIONS, fake_input("100", "q"), lambda _: None)
        assert score == DrillScore(asked=1, correct=1)
        assert score.accuracy == 1.0

    def test_eof(self) -> None:
        score = run_drill(QUESTIONS, fake_input(), lambda _: None)
        assert score == DrillScore(asked=0, correct=0)
        assert score.accuracy == 0.0
