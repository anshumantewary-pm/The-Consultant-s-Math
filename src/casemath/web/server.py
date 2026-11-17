"""HTTP server for the web page. Binds to localhost by default.

Routes:

* ``GET  /``                 the single-page app
* ``GET  /api/health``       ``{"ok": true, "version": ...}``
* ``POST /api/check``        check a drill answer
* ``POST /api/<command>``    run a CLI command with a JSON body (see ``api.call``)
"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from casemath import __version__
from casemath.web.api import ApiError, call, check_answer

MAX_BODY_BYTES = 64 * 1024


def page() -> bytes:
    return files("casemath.web").joinpath("index.html").read_bytes()


class Handler(BaseHTTPRequestHandler):
    server_version = f"casemath/{__version__}"

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet by default; the server object decides."""
        if getattr(self.server, "verbose", False):  # pragma: no cover - console noise only
            super().log_message(format, *args)

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, data: object) -> None:
        body = json.dumps(data, allow_nan=False).encode()
        self._send(status, body, "application/json")

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(HTTPStatus.OK, page(), "text/html; charset=utf-8")
        elif path == "/api/health":
            self._json(HTTPStatus.OK, {"ok": True, "version": __version__})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": f"no route {path}"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if not path.startswith("/api/"):
            self._json(HTTPStatus.NOT_FOUND, {"error": f"no route {path}"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_BODY_BYTES:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "bad or oversized Content-Length"})
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ApiError("body must be a JSON object")
            command = path.removeprefix("/api/")
            result = check_answer(body) if command == "check" else call(command, body)
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "body is not valid JSON"})
        except ApiError as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        else:
            self._json(HTTPStatus.OK, result)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    verbose = False


def make_server(host: str = "127.0.0.1", port: int = 8765, verbose: bool = False) -> Server:
    """Create (but do not start) the server. ``port=0`` picks a free port."""
    server = Server((host, port), Handler)
    server.verbose = verbose
    return server
