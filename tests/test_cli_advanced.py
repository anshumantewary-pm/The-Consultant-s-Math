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
