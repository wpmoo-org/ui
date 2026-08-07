"""Lock the RC rehearsal script: it must run clean against the current
tree, never touch npm publish/version/tag/push, and produce a tarball,
conformance kit, manifest, and attestation that all agree on version and
source commit — Task 4's actual acceptance criterion, checked directly
rather than trusted from the script's own summary line.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tarfile
import unittest

from tests.helpers import ROOT

SCRIPT = ROOT / "scripts" / "rehearse-rc.py"
OUT_DIR = ROOT / "dist" / "rc-rehearsal"
RUN_TIMEOUT_SECONDS = 300


class RehearseRcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )

    def test_rehearsal_runs_clean_and_never_publishes(self) -> None:
        # AST-based rather than textual: a plain substring/token search on
        # "version" also matches package.json's ["version"] key lookup,
        # which has nothing to do with `npm version`. Instead, walk every
        # list literal in the script and flag any that pairs "npm" with a
        # mutating subcommand - the actual argv shape a subprocess call
        # would use. A module docstring is a single string node, not a
        # list literal, so it can't trip this even though it legitimately
        # names the same words while explaining what the script avoids.
        forbidden = {"publish", "push", "tag", "version"}
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.List):
                continue
            elements = [
                element.value
                for element in node.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if "npm" not in elements:
                continue
            hit = forbidden.intersection(elements)
            self.assertFalse(hit, f"npm argv list contains forbidden token(s): {hit}")

        self.assertEqual(self.completed.returncode, 0, self.completed.stderr)
        self.assertIn("REHEARSAL OK", self.completed.stdout)

        # Stage B is fully wired now that Phase 6 Tasks 1 and 2 have both
        # landed - neither generator should be reported pending anymore.
        # Matched against the script's own literal status lines rather than
        # the bare word "pending", so unrelated output can't collide.
        self.assertNotIn("manifest:        pending", self.completed.stdout)
        self.assertNotIn("attestation:     pending", self.completed.stdout)

    def test_artifacts_agree_on_version_and_source_commit(self) -> None:
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr)

        with tarfile.open(next(OUT_DIR.glob("*.tgz"))) as archive:
            package = json.loads(
                archive.extractfile("package/package.json").read()
            )
        manifest = json.loads(
            (OUT_DIR / "certification-manifest.json").read_text(encoding="utf-8")
        )
        attestation = json.loads(
            (OUT_DIR / "certification-attestation.json").read_text(encoding="utf-8")
        )

        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        self.assertEqual(package["version"], manifest["coreVersion"])
        self.assertEqual(package["version"], attestation["coreVersion"])
        self.assertEqual(attestation["sourceCommit"], head_commit)
        self.assertEqual(len(manifest["certifiedComponents"]), 42)
        self.assertEqual(len(attestation["components"]), 42)


if __name__ == "__main__":
    unittest.main()
