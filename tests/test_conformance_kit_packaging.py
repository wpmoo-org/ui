"""Deterministic packaging proof for the hash-locked conformance kit.

Task 8 acceptance: two independent packaging runs produce byte-identical
archives and identical hashes.  These tests lock that in CI, verify the
archive carries exactly the distributable kit (no evidence snapshots, no
test-only files), and prove an extracted artifact is self-sufficient:
its own host shell serves it and the reference runner passes against it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT
from tests.test_host_shell import non_venv_interpreter

SCRIPT = ROOT / "scripts" / "package-conformance-kit.py"
RUNNER = ROOT / "conformance" / "runner" / "run.py"
RUN_TIMEOUT_SECONDS = 240
VERSION = "1.0"
PREFIX = f"moo-ui-conformance-kit-{VERSION}"


def load_packaging():
    spec = importlib.util.spec_from_file_location(
        "package_conformance_kit", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packaging = load_packaging()
        cls.archive = cls.packaging.build_archive(VERSION)

    def test_two_builds_are_byte_identical(self) -> None:
        first = self.packaging.build_archive(VERSION)
        second = self.packaging.build_archive(VERSION)
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            hashlib.sha256(second).hexdigest(),
        )

    def test_archive_contains_exactly_the_distributable_kit(self) -> None:
        expected = {
            f"{PREFIX}/conformance/{path.relative_to(self.packaging.KIT_DIR).as_posix()}"
            for path in self.packaging.kit_files()
        }
        with tarfile.open(fileobj=io.BytesIO(self.archive)) as tar:
            names = {member.name for member in tar.getmembers()}
        self.assertEqual(names, expected)
        for forbidden in ("/reports/", "__pycache__"):
            self.assertFalse(
                any(forbidden in name for name in names), forbidden
            )
        for required in (
            f"{PREFIX}/conformance/contract/conformance-contract.json",
            f"{PREFIX}/conformance/contract/report.schema.json",
            f"{PREFIX}/conformance/fixtures/static-primitives.html",
            f"{PREFIX}/conformance/runner/run.py",
            f"{PREFIX}/conformance/host-shell/serve.py",
        ):
            self.assertIn(required, names)

    def test_extracted_artifact_is_self_sufficient(self) -> None:
        interpreter = non_venv_interpreter()
        if not interpreter:
            raise unittest.SkipTest("no interpreter outside the .venv available")

        with tempfile.TemporaryDirectory() as scratch:
            with tarfile.open(
                fileobj=io.BytesIO(self.archive)
            ) as tar:
                tar.extractall(scratch)
            serve = (
                Path(scratch) / PREFIX / "conformance" / "host-shell" / "serve.py"
            )
            server = subprocess.Popen(
                [interpreter, str(serve), "--port", "0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={"PATH": "/usr/bin:/bin"},
            )
            try:
                banner = server.stdout.readline()
                match = re.search(r"http://127\.0\.0\.1:(\d+)", banner)
                self.assertIsNotNone(match, banner)
                base_url = f"http://127.0.0.1:{match.group(1)}/fixtures"

                report_path = Path(scratch) / "artifact-report.json"
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(RUNNER),
                        "--base-url",
                        base_url,
                        "--report-out",
                        str(report_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=RUN_TIMEOUT_SECONDS,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                report = json.loads(report_path.read_text(encoding="utf-8"))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
                server.stdout.close()
                server.stderr.close()

        self.assertEqual(report["summary"]["result"], "pass")
        self.assertEqual(report["summary"]["assertionsFailed"], 0)
        self.assertEqual(report["summary"]["assertionsSkipped"], 0)


if __name__ == "__main__":
    unittest.main()
