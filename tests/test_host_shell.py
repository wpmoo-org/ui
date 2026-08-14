"""Host-neutrality proof for the example host shell.

The host shell must serve the kit's fixtures with zero dependency on
Core's Jinja/Python build.  These tests spawn ``serve.py`` with an
interpreter outside the repository ``.venv`` and a stripped environment,
then drive the reference runner against the shell's real served URL —
the same proof a bridge or another project would repeat.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

from tests.helpers import ROOT
from tests.helpers.browser_harness import skip_if_browser_launch_is_sandboxed
from tests.helpers.host_process import non_venv_interpreter, read_banner_line

SERVE = ROOT / "conformance" / "host-shell" / "serve.py"
RUNNER = ROOT / "conformance" / "runner" / "run.py"
CONTRACT = ROOT / "conformance" / "contract" / "conformance-contract.json"
RUN_TIMEOUT_SECONDS = 240
ALLOWED_IMPORT_MODULES = {
    "__future__",
    "argparse",
    "http.server",
    "os",
    "pathlib",
    "socket",
    "sys",
}


def imported_modules(source: str) -> set:
    return {
        match.group(1)
        for match in re.finditer(
            r"(?m)^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)",
            source,
        )
    }


class HostShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        interpreter = non_venv_interpreter()
        if not interpreter:
            raise unittest.SkipTest("no interpreter outside the .venv available")
        cls.interpreter = interpreter
        cls.server = subprocess.Popen(
            [interpreter, str(SERVE), "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        try:
            banner = read_banner_line(cls.server)
        except Exception:
            cls.server.kill()
            raise
        match = re.search(r"http://127\.0\.0\.1:(\d+)", banner)
        if cls.server.poll() is not None or not match:
            cls.server.kill()
            raise AssertionError(
                f"host shell failed to start: {banner!r} "
                f"{cls.server.stderr.read()!r}"
            )
        cls.base_url = f"http://127.0.0.1:{match.group(1)}/fixtures"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.terminate()
        try:
            cls.server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait(timeout=10)

    def test_serve_py_imports_only_the_standard_library(self) -> None:
        source = SERVE.read_text(encoding="utf-8")
        self.assertEqual(imported_modules(source), ALLOWED_IMPORT_MODULES)

    def test_host_shell_serves_index_and_every_fixture(self) -> None:
        with urllib.request.urlopen(f"{self.base_url.rsplit('/', 1)[0]}/") as response:
            index = response.read().decode("utf-8")
        self.assertIn("Example Host Shell", index)

        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for fixture in contract["kit"]["fixtures"]:
            with urllib.request.urlopen(
                f"{self.base_url}/{fixture['path']}"
            ) as response:
                self.assertEqual(response.status, 200, fixture["path"])

    def test_runner_passes_against_the_host_shell(self) -> None:
        skip_if_browser_launch_is_sandboxed()
        with tempfile.TemporaryDirectory() as scratch:
            report_path = Path(scratch) / "host-shell-report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--base-url",
                    self.base_url,
                    "--report-out",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))

        summary = report["summary"]
        self.assertEqual(summary["result"], "pass")
        self.assertEqual(summary["assertionsFailed"], 0)
        self.assertEqual(summary["assertionsSkipped"], 0)
        self.assertGreater(summary["assertionsPassed"], 0)
        self.assertEqual(report["host"]["baseUrl"], self.base_url)


if __name__ == "__main__":
    unittest.main()
