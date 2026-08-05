"""Deterministic packaging proof for the hash-locked conformance kit.

Task 8 acceptance: two independent packaging runs produce byte-identical
archives and identical hashes.  These tests lock that in CI, verify the
archive carries exactly the distributable kit (no evidence snapshots, no
test-only files), and prove an extracted artifact is self-sufficient:
its own host shell serves it and its own reference runner passes
against it.
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
from tests.test_host_shell import non_venv_interpreter, read_banner_line

SCRIPT = ROOT / "scripts" / "package-conformance-kit.py"
RUN_TIMEOUT_SECONDS = 240
PACKAGING_TIMEOUT_SECONDS = 120
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

    def test_two_cli_runs_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            out_dirs = []
            for name in ("first", "second"):
                out_dir = Path(scratch) / name
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--version",
                        VERSION,
                        "--out-dir",
                        str(out_dir),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=PACKAGING_TIMEOUT_SECONDS,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                out_dirs.append(out_dir)

            archive_name = f"moo-ui-conformance-kit-{VERSION}.tar.gz"
            first = (out_dirs[0] / archive_name).read_bytes()
            second = (out_dirs[1] / archive_name).read_bytes()
            self.assertEqual(first, second)
            first_sidecar = (out_dirs[0] / f"{archive_name}.sha256").read_text(
                encoding="utf-8"
            )
            second_sidecar = (out_dirs[1] / f"{archive_name}.sha256").read_text(
                encoding="utf-8"
            )
            self.assertEqual(first_sidecar, second_sidecar)
            digest = hashlib.sha256(first).hexdigest()
            self.assertEqual(first_sidecar, f"{digest}  {archive_name}\n")

    def test_symlinked_kit_content_is_rejected(self) -> None:
        probe = self.packaging.KIT_DIR / "fixtures" / "_symlink_probe.html"
        self.assertFalse(
            probe.exists() or probe.is_symlink(),
            f"reserved test probe already exists: {probe}",
        )
        probe.symlink_to(SCRIPT)
        self.addCleanup(probe.unlink, missing_ok=True)
        with self.assertRaises(ValueError):
            self.packaging.build_archive(VERSION)

    def test_unsafe_version_values_are_rejected(self) -> None:
        for bad in ("", "../outside", "1.0/../../x", "a\\b", "1.0..1"):
            with self.subTest(version=bad):
                with self.assertRaises(ValueError):
                    self.packaging.build_archive(bad)

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
            artifact_runner = (
                Path(scratch) / PREFIX / "conformance" / "runner" / "run.py"
            )
            server = subprocess.Popen(
                [interpreter, str(serve), "--port", "0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={"PATH": "/usr/bin:/bin"},
            )
            try:
                banner = read_banner_line(server)
                match = re.search(r"http://127\.0\.0\.1:(\d+)", banner)
                self.assertIsNotNone(match, banner)
                base_url = f"http://127.0.0.1:{match.group(1)}/fixtures"

                report_path = Path(scratch) / "artifact-report.json"
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(artifact_runner),
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
