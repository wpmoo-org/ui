from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SecretScanTests(unittest.TestCase):
    def test_scan_range_handles_missing_initial_and_available_base_commits(self) -> None:
        workflow = (ROOT / ".github/workflows/secret-scan.yml").read_text(encoding="utf-8")
        start_marker = 'scan_range="$SCAN_HEAD"'
        end_marker = "/tmp/gitleaks git"
        for marker in (start_marker, end_marker):
            self.assertIn(marker, workflow, f"Secret scan workflow must contain {marker!r}")
        start = workflow.index(start_marker)
        self.assertIn(end_marker, workflow[start:], "Secret scan command must follow range selection")
        end = workflow.index(end_marker, start)
        snippet = workflow[start:end] + '\nprintf "%s" "$scan_range"\n'
        with tempfile.TemporaryDirectory(prefix="secret-scan-range-") as temporary:
            repo = Path(temporary)
            for arguments in (
                ("init", "--quiet"),
                ("config", "core.hooksPath", "/dev/null"),
                ("config", "user.name", "Range test"),
                ("config", "user.email", "range@example.test"),
                ("config", "commit.gpgsign", "false"),
                ("commit", "--quiet", "--allow-empty", "-m", "Initial fixture"),
            ):
                subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            for base, expected in (
                ("", head),
                ("0" * 40, head),
                ("f" * 40, head),
                (head, f"{head}..{head}"),
            ):
                with self.subTest(base=base):
                    result = subprocess.run(
                        ["bash", "-eu", "-c", snippet], cwd=repo,
                        env={**os.environ, "SCAN_BASE": base, "SCAN_HEAD": head},
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)
