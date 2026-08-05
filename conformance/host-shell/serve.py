#!/usr/bin/env python3
"""Example host shell for the Moo UI Generic Host Conformance Kit.

This file is the entire host: a standard-library-only static server that
mounts the kit's five canonical fixtures (``../fixtures/``) under the
``/fixtures`` URL prefix and serves one host-owned landing page at ``/``.
It has no Jinja, no Core build tooling, and no repository imports — a
real host (a bridge, another project) can replace it with any static
file serving as long as the fixtures keep their relative layout.

Run it with the system interpreter, deliberately not the repo .venv:

    /usr/bin/python3 serve.py --port 8124

Then point the reference runner at the mount prefix:

    python conformance/runner/run.py \
        --base-url http://127.0.0.1:8124/fixtures
"""

from __future__ import annotations

import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = SHELL_DIR.parent / "fixtures"
MOUNT_PREFIX = "/fixtures"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class HostShellHandler(BaseHTTPRequestHandler):
    server_version = "MooUIHostShell/1.0"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path in ("", "/", "/index.html"):
            self._send_relative(SHELL_DIR, "index.html")
        elif path.startswith(MOUNT_PREFIX + "/"):
            self._send_relative(FIXTURES_DIR, path[len(MOUNT_PREFIX) + 1:])
        else:
            self.send_error(404, "Not Found")

    def _send_relative(self, root: Path, relative: str) -> None:
        root_real = os.path.realpath(root)
        resolved = os.path.realpath(os.path.join(root_real, relative))
        if resolved != root_real and not resolved.startswith(root_real + os.sep):
            self.send_error(404, "Not Found")
            return
        if not os.path.isfile(resolved):
            self.send_error(404, "Not Found")
            return
        content_type = CONTENT_TYPES.get(
            os.path.splitext(resolved)[1], "application/octet-stream"
        )
        with open(resolved, "rb") as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        # The example host stays quiet; the runner owns the reporting.
        pass


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Example host shell: stdlib-only static serving of the kit."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8124)
    args = parser.parse_args(argv)

    if not FIXTURES_DIR.is_dir():
        parser.exit(2, f"fixtures directory not found: {FIXTURES_DIR}\n")

    server = ThreadingHTTPServer((args.host, args.port), HostShellHandler)
    host, port = server.server_address
    print(
        f"moo-ui host shell serving on http://{host}:{port} "
        f"(fixtures mounted at {MOUNT_PREFIX})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
