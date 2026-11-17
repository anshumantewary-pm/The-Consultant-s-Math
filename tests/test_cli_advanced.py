"""CLI tests for the v0.2 commands: finance, pricing, unit economics and analysis."""

import json

import pytest

from casemath.cli import main

Capture = pytest.CaptureFixture[str]


def run(capsys: Capture, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def run_json(capsys: Capture, *argv: str) -> dict[str, object]:
    code, out, err = run(capsys, *argv, "--json")
    assert code == 0, err
    data = json.loads(out)
    assert isinstance(data, dict)
    return data


class TestInvest:
    def test_text(self, capsys: Capture) -> None:
        code, out, _ = run(capsys, "invest", "--rate", "0.1", "-1000", "500", "500", "500")
        assert code == 0
        assert "NPV                $243.43" in out
        assert "IRR                23.4%" in out
        assert "Payback            2.00 periods" in out
        assert "Decision (NPV > 0) invest" in out

    def test_never_pays_back(self, capsys: Capture) -> None:
        _, out, _ = run(capsys, "invest", "--rate", "0.1", "-1000", "100")
        assert "Payback            never" in out
        assert "do not invest" in out

    def test_no_irr(self, capsys: Capture) -> None:
        _, out, _ = run(capsys, "invest", "--rate", "0.1", "100", "100")
        assert "n/a (flows do not change sign)" in out

    def test_json(self, capsys: Capture) -> None:
        code, out, _ = run(capsys, "invest", "--json", "--rate", "0.1", "--", "-1e3", "1.2e3")
        assert code == 0
        data = json.loads(out)
        assert data["accept"] is True
        assert data["irr"] == pytest.approx(0.2)


class TestUnitEcon:
    ARGS = ("unit-econ", "--revenue", "100", "--margin", "0.8", "--churn", "0.04")

    def test_healthy(self, capsys: Capture) -> None:
        code, out, _ = run(capsys, *self.ARGS, "--cac", "600")
        assert code == 0
        assert "Lifetime value     $2,000.00" in out
        assert "LTV / CAC          3.33x" in out
        assert "Verdict            healthy" in out

    def test_unhealthy_reasons(self, capsys: Capture) -> None:
        _, out, _ = run(
            capsys, "unit-econ", "--revenue", "10", "--margin", "0.5", "--churn", "0.5",
            "--cac", "50",
        )  # fmt: skip
        assert "LTV/CAC below 3x; CAC not repaid" in out

    def test_json(self, capsys: Capture) -> None:
        data = run_json(capsys, *self.ARGS, "--cac", "1000", "--discount-rate", "0.01")
        assert data["healthy"] is False
        assert data["ltv"] == pytest.approx(1_616)

    def test_validation(self, capsys: Capture) -> None:
        code, _, err = run(capsys, *self.ARGS[:-2], "--churn", "0", "--cac", "1")
        assert code == 2
        assert "lasts forever" in err


class TestPricing:
    def test_change(self, capsys: Capture) -> None:
        code, out, _ = run(capsys, "pricing", "change", "--change", "-0.1", "--margin", "0.3")
        assert code == 0
        assert "Volume needed      +50.0%" in out

    def test_change_with_elasticity(self, capsys: Capture) -> None:
        data = run_json(
            capsys, "pricing", "change", "--change", "-0.1", "--margin", "0.3",
            "--elasticity", "-2",
        )  # fmt: skip
        assert data["expected_volume_change"] == pytest.approx(0.9**-2 - 1)
        _, out, _ = run(
            capsys, "pricing", "change", "--change", "-0.1", "--margin", "0.3",
            "--elasticity", "-6",
        )  # fmt: skip
        assert "worth it" in out

    def test_destroys_value(self, capsys: Capture) -> None:
        _, out, _ = run(
            capsys, "pricing", "change", "--change", "-0.1", "--margin", "0.3",
            "--elasticity", "-2",
        )  # fmt: skip
        assert "destroys value" in out

    def test_elasticity(self, capsys: Capture) -> None:
        _, out, _ = run(capsys, "pricing", "elasticity", "--points", "10,100,12,80")
        assert "-1.22 (elastic)" in out
        _, out, _ = run(capsys, "pricing", "elasticity", "--points", "10,100,12,98")
        assert "(inelastic)" in out

    def test_optimal_linear(self, capsys: Capture) -> None:
        data = run_json(
            capsys, "pricing", "optimal", "--points", "10,100,12,80", "--unit-cost", "4"
        )
        assert data["price"] == pytest.approx(12)
        _, out, _ = run(
            capsys, "pricing", "optimal", "--points", "10,100,12,80", "--unit-cost", "4"
        )
        assert "Optimal price      $12.00" in out

    def test_optimal_markup(self, capsys: Capture) -> None:
        _, out, _ = run(capsys, "pricing", "optimal", "--unit-cost", "10", "--elasticity", "-3")
        assert "Optimal price      $15.00  (markup 50%)" in out

    @pytest.mark.parametrize(
        ("argv", "message"),
        [
            (("pricing", "change", "--change", "-0.1"), "needs --margin"),
            (("pricing", "optimal", "--elasticity", "-3"), "needs --unit-cost"),
            (("pricing", "optimal", "--unit-cost", "4"), "--points P1,Q1,P2,Q2 or --elasticity"),
            (("pricing", "elasticity"), "--points PRICE1"),
            (("pricing", "elasticity", "--points", "1,2,3"), "four numbers"),
        ],
    )
    def test_errors(self, capsys: Capture, argv: tuple[str, ...], message: str) -> None:
        code, _, err = run(capsys, *argv)
        assert code == 2
        assert message in err
