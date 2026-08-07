"""Lock the RC rehearsal script: it must run clean against the current
tree, never touch npm publish/version/tag/push, and produce a tarball,
conformance kit, manifest, and attestation that all agree on version and
source commit — Task 4's actual acceptance criterion, checked directly
rather than trusted from the script's own summary line.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import tarfile
import unittest

from tests.helpers import ROOT

SCRIPT = ROOT / "scripts" / "rehearse-rc.py"
OUT_DIR = ROOT / "dist" / "rc-rehearsal"
# Generous relative to rehearse-rc.py's own internal DEFAULT_TIMEOUT_SECONDS
# (600s per command): the script runs several such commands in sequence on
# a cold cache (build.py, two npm packs, two npm installs, the conformance
# kit, and both certification generators), so the outer budget must cover
# more than one worst-case internal timeout.
RUN_TIMEOUT_SECONDS = 900


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
        # landed - assert the summary names each generator's real output
        # path and that the file actually exists, rather than merely that
        # it doesn't say "pending"; a script that renamed the placeholder
        # text, or reported a path it never wrote, would slip past a
        # padded-text-only check but not this one.
        manifest_path = OUT_DIR / "certification-manifest.json"
        attestation_path = OUT_DIR / "certification-attestation.json"
        self.assertIn(str(manifest_path), self.completed.stdout)
        self.assertTrue(manifest_path.is_file(), manifest_path)
        self.assertIn(str(attestation_path), self.completed.stdout)
        self.assertTrue(attestation_path.is_file(), attestation_path)

    def test_artifacts_agree_on_version_and_source_commit(self) -> None:
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr)

        tarball = next(OUT_DIR.glob("*.tgz"))
        with tarfile.open(tarball) as archive:
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
        self.assertEqual(
            attestation["package"]["sha256"],
            hashlib.sha256(tarball.read_bytes()).hexdigest(),
        )
        self.assertEqual(len(manifest["certifiedComponents"]), 42)
        self.assertEqual(len(attestation["components"]), 42)


if __name__ == "__main__":
    unittest.main()
