import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest

from casemath import __version__
from casemath.cli import main
from casemath.web import ApiError, call, check_answer, make_server
from casemath.web.api import to_argv
from casemath.web.server import MAX_BODY_BYTES, Server


class TestToArgv:
    def test_flags(self) -> None:
        argv = to_argv("price", {"price": 40, "elasticity": -1.5, "fixed_costs": None})
        assert argv == ["price", "--price=40", "--elasticity=-1.5", "--json"]

    def test_bools_and_lists(self) -> None:
        argv = to_argv("size", {"filter": ["a=0.5", "b=0.2"], "x": True, "y": False})
        assert argv == ["size", "--filter", "a=0.5", "--filter", "b=0.2", "--x", "--json"]

    def test_positionals(self) -> None:
        assert to_argv("case", {"action": "solve", "id": 3}) == ["case", "solve", "3", "--json"]
        assert to_argv("hhi", {"players": ["A=1", "B=2"]}) == ["hhi", "A=1", "B=2", "--json"]

    def test_serve_is_not_callable(self) -> None:
        with pytest.raises(ApiError, match="unknown command 'serve'"):
            to_argv("serve", {})

    def test_bad_value(self) -> None:
        with pytest.raises(ApiError, match="price must be a number or text"):
            to_argv("profit", {"price": {"a": 1}})


class TestCall:
    def test_matches_cli(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["breakeven", "--fixed-costs", "100000", "--price", "10", "--variable-cost", "6",
              "--json"])  # fmt: skip
        cli_data = json.loads(capsys.readouterr().out)
        result = call("breakeven", {"fixed_costs": 100000, "price": 10, "variable_cost": 6})
        assert result["data"] == cli_data
        assert "Break-even units   25,000.00" in result["text"]

    def test_negative_number(self) -> None:
        body = {
            "price": 40,
            "new_price": 50,
            "units": 8000,
            "variable_cost": 10,
            "elasticity": -0.2,
        }
        assert call("price", body)["data"]["pays_off"] is True

    def test_case_and_drill(self) -> None:
        cases = call("case", {"action": "list"})["data"]
        assert [c["id"] for c in cases] == ["1", "2", "3", "4", "5", "6"]
        questions = call("drill", {"count": 3, "seed": 1})["data"]
        assert len(questions) == 3

    def test_argparse_error(self) -> None:
        with pytest.raises(ApiError, match="required: --fixed-costs"):
            call("breakeven", {"price": 10})

    def test_choice_error(self) -> None:
        with pytest.raises(ApiError, match="invalid choice"):
            call("case", {"action": "delete"})

    def test_validation_error(self) -> None:
        with pytest.raises(ApiError, match="every unit loses money"):
            call("breakeven", {"fixed_costs": 1, "price": 5, "variable_cost": 6})


QUESTION: dict[str, Any] = {
    "topic": "share", "prompt": "p?", "answer": 0.25, "unit": "%", "explanation": "e",
}  # fmt: skip


class TestCheck:
    def test_right_and_wrong(self) -> None:
        assert check_answer({"question": QUESTION, "answer": "25"})["correct"] is True
        wrong = check_answer({"question": QUESTION, "answer": "30%"})
        assert wrong["correct"] is False
        assert wrong["shown_answer"] == "25.0%"

    @pytest.mark.parametrize(
        ("body", "match"),
        [
            ({"answer": "1"}, "body must be"),
            ({"question": {"topic": "x"}, "answer": "1"}, "missing or has a bad field"),
            ({"question": {**QUESTION, "answer": "x"}, "answer": "1"}, "bad field"),
            ({"question": QUESTION, "answer": "abc"}, "could not read"),
        ],
    )
    def test_errors(self, body: dict[str, Any], match: str) -> None:
        with pytest.raises(ApiError, match=match):
            check_answer(body)


@pytest.fixture(scope="module")
def server() -> Iterator[str]:
    srv = make_server(port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def request(url: str, body: bytes | None = None, headers: dict[str, str] | None = None,
            method: str | None = None) -> tuple[int, str, bytes]:  # fmt: skip
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.headers["Content-Type"], resp.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers["Content-Type"], error.read()


def post(url: str, data: object) -> tuple[int, Any]:
    status, _, body = request(url, json.dumps(data).encode(), {"Content-Type": "application/json"})
    return status, json.loads(body)


class TestServer:
    def test_page(self, server: str) -> None:
        status, kind, body = request(server + "/")
        assert status == 200
        assert kind.startswith("text/html")
        assert b"<title>casemath</title>" in body

    def test_health(self, server: str) -> None:
        status, _, body = request(server + "/api/health")
        assert status == 200
        assert json.loads(body) == {"ok": True, "version": __version__}

    def test_get_404(self, server: str) -> None:
        assert request(server + "/nope")[0] == 404

    def test_post_command(self, server: str) -> None:
        status, data = post(server + "/api/case", {"action": "solve", "id": "3"})
        assert status == 200
        assert data["data"]["case_id"] == "3"

    def test_post_check(self, server: str) -> None:
        q = QUESTION
        status, data = post(server + "/api/check", {"question": q, "answer": "25%"})
        assert status == 200
        assert data["correct"] is True

    def test_post_errors(self, server: str) -> None:
        assert post(server + "/api/breakeven", {"price": 1})[0] == 400
        assert post(server + "/api/profit", [1, 2]) == (
            400,
            {"error": "body must be a JSON object"},
        )
        assert post(server + "/other", {})[0] == 404
        status, _, body = request(server + "/api/profit", b"{not json", method="POST")
        assert status == 400
        assert b"not valid JSON" in body

    def test_empty_body_uses_defaults(self, server: str) -> None:
        status, _, body = request(server + "/api/drill", b"", method="POST")
        assert status == 200
        assert len(json.loads(body)["data"]) == 5

    @pytest.mark.parametrize("length", ["abc", str(MAX_BODY_BYTES + 1)])
    def test_bad_length(self, server: str, length: str) -> None:
        status, _, body = request(
            server + "/api/profit", b"{}", {"Content-Length": length}, method="POST"
        )
        assert status == 400
        assert b"Content-Length" in body


class TestServeCommand:
    def test_runs_until_interrupt(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        opened: list[str] = []

        def stop(self: Server) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(Server, "serve_forever", stop)
        monkeypatch.setattr("webbrowser.open", opened.append)
        code = main(["serve", "--port", "0", "--open"])
        out = capsys.readouterr().out
        assert code == 0
        assert out.startswith("casemath web UI on http://localhost:")
        assert len(opened) == 1
        assert opened[0].startswith("http://localhost:")
        assert out.rstrip().endswith("stopped")

    def test_port_in_use(self, capsys: pytest.CaptureFixture[str]) -> None:
        busy = make_server(port=0)
        try:
            code = main(["serve", "--port", str(busy.server_port)])
        finally:
            busy.server_close()
        assert code == 2
        assert "cannot listen on 127.0.0.1" in capsys.readouterr().err
