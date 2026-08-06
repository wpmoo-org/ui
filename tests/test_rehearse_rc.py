"""Lock the RC rehearsal script: it must run clean against the current
tree, never touch npm publish/version/tag/push, and produce a tarball,
conformance kit, manifest, and attestation that all agree on version and
source commit — Task 4's actual acceptance criterion, checked directly
rather than trusted from the script's own summary line.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path

from tests.helpers import ROOT

SCRIPT = ROOT / "scripts" / "rehearse-rc.py"
OUT_DIR = ROOT / "dist" / "rc-rehearsal"
RUN_TIMEOUT_SECONDS = 300


class RehearseRcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        _, _, cls.body = source.partition('"""\n\nfrom __future__')
        cls.completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )

    def test_rehearsal_runs_clean_and_never_publishes(self) -> None:
        # Only the executable body is checked — the module docstring
        # legitimately explains what the script avoids doing.
        self.assertTrue(self.body, "could not isolate the script body from its docstring")
        # Matches the quoted argv token regardless of list-literal spacing,
        # e.g. both ["npm", "publish"] and ["npm","publish"].
        for forbidden in ('"publish"', '"push"', '"tag"'):
            self.assertNotIn(forbidden, self.body, forbidden)

        self.assertEqual(self.completed.returncode, 0, self.completed.stderr)
        self.assertIn("REHEARSAL OK", self.completed.stdout)

        # Stage B is fully wired now that Phase 6 Tasks 1 and 2 have both
        # landed - neither generator should be reported pending anymore.
        self.assertNotIn("pending", self.completed.stdout)

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
