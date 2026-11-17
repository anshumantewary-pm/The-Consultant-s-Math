import json
import math

import pytest

from casemath.core import (
    Step,
    UnknownCaseError,
    ValidationError,
    fmt_money,
    fmt_number,
    fmt_pct,
    fmt_signed_money,
)
from casemath.core import validate as v
from casemath.core.validate import require_count, require_numbers


class TestValidate:
    def test_accepts_ints_and_floats(self) -> None:
        assert v.require_number("x", 3) == 3.0
        assert v.require_number("x", -2.5) == -2.5

    @pytest.mark.parametrize("bad", ["10", None, True, [1]])
    def test_rejects_non_numbers(self, bad: object) -> None:
        with pytest.raises(ValidationError, match="x must be a number"):
            v.require_number("x", bad)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_rejects_non_finite(self, bad: float) -> None:
        with pytest.raises(ValidationError, match="finite"):
            v.require_number("x", bad)

    def test_non_negative(self) -> None:
        assert v.require_non_negative("units", 0) == 0
        with pytest.raises(ValidationError, match="units must be >= 0"):
            v.require_non_negative("units", -1)

    def test_positive(self) -> None:
        assert v.require_positive("price", 0.01) == 0.01
        with pytest.raises(ValidationError, match="price must be > 0"):
            v.require_positive("price", 0)

    @pytest.mark.parametrize("ok", [0, 0.5, 1])
    def test_fraction_ok(self, ok: float) -> None:
        assert v.require_fraction("share", ok) == ok

    @pytest.mark.parametrize("bad", [-0.01, 1.01])
    def test_fraction_bad(self, bad: float) -> None:
        with pytest.raises(ValidationError, match="between 0 and 1"):
            v.require_fraction("share", bad)

    def test_rate(self) -> None:
        assert v.require_rate("g", -0.5) == -0.5
        with pytest.raises(ValidationError, match="above -100%"):
            v.require_rate("g", -1)

    def test_non_empty(self) -> None:
        v.require_non_empty("shares", {"a": 1})
        with pytest.raises(ValidationError, match="must not be empty"):
            v.require_non_empty("shares", {})

    def test_validation_error_is_value_error(self) -> None:
        assert issubclass(ValidationError, ValueError)


class TestFormatting:
    def test_money(self) -> None:
        assert fmt_money(1234.5) == "$1,234.50"
        assert fmt_money(-20) == "-$20.00"
        assert fmt_money(10, currency="Rs ") == "Rs 10.00"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (950, "$950.00"),
            (1_200, "$1.2K"),
            (3_400_000, "$3.4M"),
            (2.5e9, "$2.5B"),
            (1e12, "$1.0T"),
        ],
    )
    def test_money_compact(self, value: float, expected: str) -> None:
        assert fmt_money(value, compact=True) == expected

    def test_pct(self) -> None:
        assert fmt_pct(0.256) == "25.6%"
        assert fmt_pct(0.5, digits=0) == "50%"

    def test_number(self) -> None:
        assert fmt_number(41666.67) == "41,667"
        assert fmt_number(2.345, digits=1) == "2.3"

    def test_signed_money(self) -> None:
        assert fmt_signed_money(500) == "+$500.00"
        assert fmt_signed_money(-200) == "-$200.00"


def test_step_is_json_serialisable() -> None:
    step = Step("Revenue", 100.0, "$")
    expected = {"label": "Revenue", "value": 100.0, "unit": "$"}
    assert json.loads(json.dumps(step.to_dict())) == expected


def test_unknown_case_error_message() -> None:
    assert str(UnknownCaseError("no case 'x'")) == "no case 'x'"
    assert str(UnknownCaseError()) == "unknown case"


class TestRequireCount:
    def test_accepts_whole_numbers(self) -> None:
        assert require_count("runs", 5) == 5
        assert require_count("periods", 0, minimum=0) == 0

    @pytest.mark.parametrize("bad", [0, -3, 2.5, True, "4"])
    def test_rejects(self, bad: object) -> None:
        with pytest.raises(ValidationError, match="runs"):
            require_count("runs", bad)


class TestRequireNumbers:
    def test_returns_floats(self) -> None:
        assert require_numbers("flows", [1, 2.5]) == (1.0, 2.5)

    @pytest.mark.parametrize(
        ("bad", "message"),
        [([], "must not be empty"), ("12", "list of numbers"), ([1, "x"], r"flows\[1\]")],
    )
    def test_rejects(self, bad: object, message: str) -> None:
        with pytest.raises(ValidationError, match=message):
            require_numbers("flows", bad)
