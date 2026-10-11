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

    def test_initial_branch_push_scans_only_commits_not_in_default_branch(self) -> None:
        workflow = (ROOT / ".github/workflows/secret-scan.yml").read_text(encoding="utf-8")
        start = workflow.index('scan_range="$SCAN_HEAD"')
        end = workflow.index("/tmp/gitleaks git", start)
        snippet = workflow[start:end] + '\nprintf "%s" "$scan_range"\n'
        with tempfile.TemporaryDirectory(prefix="secret-scan-initial-branch-") as temporary:
            repo = Path(temporary)

            def git(*arguments: str, input_text: str | None = None) -> str:
                return subprocess.run(
                    ["git", *arguments], cwd=repo, input=input_text,
                    check=True, capture_output=True, text=True,
                ).stdout.strip()

            git("init", "--quiet")
            git("config", "user.name", "Range test")
            git("config", "user.email", "range@example.test")
            git("config", "commit.gpgsign", "false")
            git("commit", "--quiet", "--allow-empty", "-m", "Shared history")
            shared = git("rev-parse", "HEAD")
            git("commit", "--quiet", "--allow-empty", "-m", "First branch change")
            first = git("rev-parse", "HEAD")
            git("commit", "--quiet", "--allow-empty", "-m", "Second branch change")
            head = git("rev-parse", "HEAD")

            # The default branch may advance independently before the new
            # branch's first push; the common ancestor is the scan boundary.
            default_head = git(
                "commit-tree", git("rev-parse", "HEAD^{tree}"), "-p", shared,
                input_text="Independent default-branch change\n",
            )
            git("update-ref", "refs/remotes/origin/main", default_head)
            initial = "0" * 40
            for event, ref_type, ref_name, default_branch, base, expected_commits in (
                ("push", "branch", "dev", "main", initial, [head, first]),
                ("push", "branch", "dependabot/npm/group", "main", initial, [head, first]),
                ("push", "branch", "main", "main", initial, [head, first, shared]),
                ("push", "tag", "v1.1.0", "main", initial, [head, first, shared]),
                ("workflow_dispatch", "branch", "dev", "main", "", [head, first, shared]),
                ("push", "branch", "dev", "missing", initial, [head, first, shared]),
                ("push", "branch", "dev", "main", "f" * 40, [head, first, shared]),
            ):
                with self.subTest(event=event, ref_type=ref_type, ref_name=ref_name, default_branch=default_branch, base=base):
                    result = subprocess.run(
                        ["bash", "-eu", "-c", snippet], cwd=repo,
                        env={
                            **os.environ, "SCAN_BASE": base, "SCAN_HEAD": head,
                            "SCAN_EVENT_NAME": event, "SCAN_REF_TYPE": ref_type,
                            "SCAN_REF_NAME": ref_name, "SCAN_DEFAULT_BRANCH": default_branch,
                        },
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    scanned_commits = git("log", "--format=%H", result.stdout).splitlines()
                    self.assertEqual(scanned_commits, expected_commits)
