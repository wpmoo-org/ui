from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler

from tests.helpers import DIST, ROOT


def load_dev_module():
    module_path = ROOT / "dev.py"
    assert module_path.exists(), "dev.py should exist"
    spec = importlib.util.spec_from_file_location("moo_dev", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DevRunnerTests(unittest.TestCase):
    def test_help_lists_dev_server_options(self) -> None:
        result = subprocess.run(
            [sys.executable, "dev.py", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--host", result.stdout)
        self.assertIn("--port", result.stdout)
        self.assertIn("--open", result.stdout)

    def test_parser_defaults_match_documented_local_url(self) -> None:
        dev = load_dev_module()

        args = dev.create_parser().parse_args([])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 4173)
        self.assertFalse(args.open)

    def test_display_url_uses_localhost_for_loopback_host(self) -> None:
        dev = load_dev_module()

        self.assertEqual(
            dev.display_url("127.0.0.1", 4173),
            "http://localhost:4173/",
        )

    def test_server_handler_serves_dist_as_root(self) -> None:
        dev = load_dev_module()

        handler = dev.create_handler()

        self.assertIsInstance(handler, partial)
        self.assertIs(handler.func, SimpleHTTPRequestHandler)
        self.assertEqual(handler.keywords, {"directory": str(DIST)})


if __name__ == "__main__":
    unittest.main()
