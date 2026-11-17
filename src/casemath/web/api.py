"""The JSON API behind the web page.

``call("breakeven", {"fixed_costs": 100000, "price": 10, "variable_cost": 6})``
runs exactly what ``casemath breakeven --fixed-costs 100000 ... --json`` runs:
the body is turned into CLI arguments and parsed by the CLI's own parser, so
the web page and the CLI can never disagree about validation or results.
"""

from __future__ import annotations

import argparse
import contextlib
import io
from collections.abc import Mapping
from typing import Any

from casemath.cli import Output, build_parser
from casemath.core.errors import CaseMathError
from casemath.drill import Question, is_correct, parse_answer

# Body keys that map to positional arguments instead of --flags.
_POSITIONAL = {"hhi": ("players",), "case": ("action", "id")}
# Commands the web page may call. ``drill`` always returns an answer key;
# ``serve`` is left out on purpose.
COMMANDS = (
    "profit",
    "bridge",
    "breakeven",
    "share",
    "hhi",
    "size",
    "tree",
    "price",
    "synergy",
    "drill",
    "case",
)


class ApiError(Exception):
    """A bad request: unknown command, bad arguments or invalid input. HTTP 400."""


def _scalar(key: str, value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ApiError(f"{key} must be a number or text, got {type(value).__name__}")
    return str(value)


def to_argv(command: str, body: Mapping[str, Any]) -> list[str]:
    """``{"variable_cost": 6, "hints": true}`` -> ``["--variable-cost", "6", "--hints"]``."""
    if command not in COMMANDS:
        raise ApiError(f"unknown command {command!r}; choose from {', '.join(COMMANDS)}")
    positional = _POSITIONAL.get(command, ())
    argv = [command]
    for key in positional:
        value = body.get(key)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        argv += [_scalar(key, v) for v in values]
    for key, value in body.items():
        if key in positional or value is None or value is False:
            continue
        flag = "--" + key.replace("_", "-")
        if value is True:
            argv.append(flag)
        elif isinstance(value, list):
            for item in value:
                argv += [flag, _scalar(key, item)]
        else:
            # "=" keeps negative numbers (an elasticity of -1.5) from looking like flags.
            argv.append(f"{flag}={_scalar(key, value)}")
    argv.append("--json")
    return argv


def call(command: str, body: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run one command; return ``{"text": ..., "data": ...}`` or raise ``ApiError``."""
    argv = to_argv(command, body or {})
    parser = build_parser()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            args: argparse.Namespace = parser.parse_args(argv)
    except SystemExit:
        # argparse prints "usage: ...\ncasemath x: error: <reason>"; keep the reason.
        message = stderr.getvalue().strip().splitlines()
        raise ApiError(
            message[-1].split("error: ", 1)[-1] if message else "bad arguments"
        ) from None
    try:
        output: Output = args.handler(args)
    except CaseMathError as error:
        raise ApiError(str(error)) from None
    return {"text": output.text.strip(), "data": output.data}


def check_answer(body: Mapping[str, Any]) -> dict[str, Any]:
    """Check one drill answer. Body: ``{"question": {...}, "answer": "$1.2M"}``."""
    raw_question = body.get("question")
    raw_answer = body.get("answer")
    if not isinstance(raw_question, dict) or not isinstance(raw_answer, str):
        raise ApiError('body must be {"question": {...}, "answer": "text"}')
    try:
        question = Question(
            topic=str(raw_question["topic"]),
            prompt=str(raw_question["prompt"]),
            answer=float(raw_question["answer"]),
            unit=str(raw_question["unit"]),
            explanation=str(raw_question["explanation"]),
            tolerance=float(raw_question.get("tolerance", 0.01)),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ApiError(f"question is missing or has a bad field: {error}") from None
    try:
        value = parse_answer(raw_answer, question.unit)
    except CaseMathError as error:
        raise ApiError(str(error)) from None
    return {
        "correct": is_correct(question, value),
        "parsed": value,
        "answer": question.answer,
        "shown_answer": question.shown_answer(),
        "explanation": question.explanation,
    }
