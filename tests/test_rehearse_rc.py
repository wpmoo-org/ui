"""Lock the RC rehearsal script: it must run clean against the current
tree and never touch npm publish, npm version, or git tags.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import ROOT

SCRIPT = ROOT / "scripts" / "rehearse-rc.py"
RUN_TIMEOUT_SECONDS = 300


class RehearseRcTests(unittest.TestCase):
    def test_rehearsal_runs_clean_and_never_publishes(self) -> None:
        # Only the executable body is checked — the module docstring
        # legitimately explains what the script avoids doing.
        source = SCRIPT.read_text(encoding="utf-8")
        _, _, body = source.partition('"""\n\nfrom __future__')
        self.assertTrue(body, "could not isolate the script body from its docstring")
        # Matches the quoted argv token regardless of list-literal spacing,
        # e.g. both ["npm", "publish"] and ["npm","publish"].
        for forbidden in ('"publish"', '"push"', '"tag"'):
            self.assertNotIn(forbidden, body, forbidden)

        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("REHEARSAL OK", completed.stdout)
        self.assertIn("package version:", completed.stdout)
        self.assertIn("source commit:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
