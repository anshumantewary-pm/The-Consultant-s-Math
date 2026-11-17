import json
import subprocess
import sys

import pytest

from casemath import __version__
from casemath.cases import list_cases
from casemath.cli import main


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def run_json(capsys: pytest.CaptureFixture[str], *argv: str) -> object:
    code, out, _ = run(capsys, *argv, "--json")
    assert code == 0
    return json.loads(out)


class TestProfit:
    def test_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(
            capsys, "profit", "--price", "10", "--units", "1000",
            "--variable-cost", "6", "--fixed-costs", "2500",
        )  # fmt: skip
        assert code == 0
        assert "Profit             $1,500.00  (15.0%)" in out

    def test_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(
            capsys, "profit", "--price", "10", "--units", "1000", "--variable-cost", "6"
        )
        assert isinstance(data, dict)
        assert data["profit"] == 4000


class TestBridge:
    def test_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(
            capsys, "bridge", "--before", "10,1000,6,2000", "--after", "9,1200,6.5,2300"
        )
        assert code == 0
        assert "price            -$1,200.00" in out
        assert "Biggest driver     price" in out

    def test_bridge_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(capsys, "bridge", "--before", "10,1000,6,2000", "--after", "10,2000,6,2000")
        assert isinstance(data, dict)
        assert data["biggest_driver"] == "volume"

    @pytest.mark.parametrize("bad", ["1,2,3", "a,b,c,d"])
    def test_bad_input(self, capsys: pytest.CaptureFixture[str], bad: str) -> None:
        code, _, err = run(capsys, "bridge", "--before", bad, "--after", "1,1,1,1")
        assert code == 2
        assert err.startswith("error: --before")


class TestBreakeven:
    def test_full(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(
            capsys, "breakeven", "--fixed-costs", "100000", "--price", "10",
            "--variable-cost", "6", "--expected-units", "40000", "--target-profit", "20000",
        )  # fmt: skip
        assert code == 0
        assert "Break-even units   25,000.00  (sell 25,000)" in out
        assert "Margin of safety   37.5%" in out
        assert "Units for target   30,000.00" in out

    def test_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(
            capsys, "breakeven", "--fixed-costs", "1000", "--price", "7", "--variable-cost", "4",
            "--target-profit", "500",
        )  # fmt: skip
        assert isinstance(data, dict)
        assert data["break_even_units_whole"] == 334
        assert data["units_for_target_profit"] == 500

    def test_no_break_even(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, err = run(
            capsys, "breakeven", "--fixed-costs", "100", "--price", "5", "--variable-cost", "6"
        )
        assert code == 2
        assert out == ""
        assert "no break-even" in err


class TestShare:
    def test_share(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(
            capsys, "share", "--company", "60", "--market", "400", "--largest-rival", "40"
        )
        assert code == 0
        assert "Market share       15.0%" in out
        assert "Relative share     1.50x" in out

    def test_share_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert run_json(capsys, "share", "--company", "50", "--market", "400") == {
            "market_share": 0.125
        }


class TestHHI:
    def test_hhi(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(capsys, "hhi", "A=30", "B=30", "C=20", "D=20")
        assert code == 0
        assert "HHI 2,600: highly concentrated" in out

    def test_hhi_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(capsys, "hhi", "Solo Co=5")
        assert isinstance(data, dict)
        assert data["hhi"] == 10_000
        assert data["table"]["rows"][0]["relative_share"] is None

    @pytest.mark.parametrize("bad", ["A", "=5", "A=x"])
    def test_bad_player(self, capsys: pytest.CaptureFixture[str], bad: str) -> None:
        code, _, err = run(capsys, "hhi", bad)
        assert code == 2
        assert "player" in err


def test_size(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(
        capsys, "size", "--population", "1000000", "--filter", "urban=0.5",
        "--filter", "own a car=0.2", "--units-per-customer", "4", "--price", "25",
    )  # fmt: skip
    assert code == 0
    assert "x 20% own a car: 100,000 people" in out
    assert out.strip().endswith("$10,000,000.00")


class TestTree:
    def test_blank_with_hints(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(capsys, "tree", "--hints")
        assert code == 0
        assert "Profit [-]" in out
        assert "MECE check passed" in out

    def test_with_numbers_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(
            capsys, "tree", "--price", "10", "--units", "100", "--variable-cost", "6",
            "--fixed-costs", "100",
        )  # fmt: skip
        assert isinstance(data, dict)
        assert data["mece"]["issues"] == []
        assert data["tree"]["label"] == "Profit"


class TestCase:
    def test_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(capsys, "case", "list")
        assert code == 0
        assert "1  Profitability" in out
        assert "2  Market entry" in out

    def test_list_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(capsys, "case", "list")
        assert isinstance(data, list)
        assert [c["id"] for c in data] == [c.id for c in list_cases()]

    def test_show(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = run(capsys, "case", "show", "2")
        assert code == 0
        assert "Suggested structure:" in out

    def test_show_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(capsys, "case", "show", "1")
        assert isinstance(data, dict)
        assert len(data["data"]["year_2"]) == 3

    @pytest.mark.parametrize("case_id", [c.id for c in list_cases()])
    def test_solve(self, capsys: pytest.CaptureFixture[str], case_id: str) -> None:
        code, out, _ = run(capsys, "case", "solve", case_id)
        assert code == 0
        assert "Recommendation" in out

    def test_solve_json_is_strict(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = run_json(capsys, "case", "solve", "2")
        assert isinstance(data, dict)
        assert data["answer"]["min_anchor_sessions"] == 69_159

    def test_missing_id(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, _, err = run(capsys, "case", "solve")
        assert code == 2
        assert "needs a case id" in err

    def test_unknown_id(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, _, err = run(capsys, "case", "solve", "42")
        assert code == 2
        assert "no case '42'" in err


def test_argparse_errors_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["profit", "--price", "10"])
    assert exc.value.code == 2


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_python_dash_m() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "casemath", "case", "list"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Brewline" in result.stdout


def test_ensure_utf8_reconfigures_legacy_encodings() -> None:
    import io

    from casemath.cli import ensure_utf8

    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    ensure_utf8(stream)
    assert stream.encoding == "utf-8"
    ensure_utf8(object())  # non-text streams are left alone


def test_tree_survives_a_cp1252_pipe() -> None:
    env = {**__import__("os").environ, "PYTHONIOENCODING": "cp1252"}
    result = subprocess.run(
        [sys.executable, "-m", "casemath", "tree"],
        capture_output=True,
        check=True,
        env=env,
    )
    assert "├──".encode() in result.stdout
