from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


class CatalogBuildTests(unittest.TestCase):
    def run_build(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def read_output(self, relative_path: str) -> str:
        return (DIST / relative_path).read_text(encoding="utf-8")

    def test_build_creates_static_entrypoints(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "index.html").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.css").is_file())
        self.assertTrue((DIST / "assets/css/catalog.css").is_file())
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js").is_file()
        )


if __name__ == "__main__":
    unittest.main()
