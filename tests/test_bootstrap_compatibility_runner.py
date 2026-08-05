"""Guard against the Bootstrap compatibility runner silently excluding
Playwright-based test modules.

This test exists because ``scripts/run-bootstrap-compatibility.py``
originally hard-coded a single module name (``tests.test_certification_browser``),
which silently excluded ``tests/test_datatable_browser.py`` from every
Bootstrap compatibility run — a gap that was only caught during the Phase 3
review.  The runner now uses ``unittest discover -p "test_*_browser.py"``,
so any future Playwright test module following the same naming convention
is picked up automatically.  This guard test locks that invariant: if a
new Playwright-based test module is added under a name that does *not*
match the runner's discovery glob, the suite fails before the next
compatibility run silently drops it.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run-bootstrap-compatibility.py"
TESTS_DIR = ROOT / "tests"

# The discovery glob the runner is expected to use.  If this ever changes
# in the runner script, update it here too — the test will fail and force
# a conscious review of which modules are included/excluded.
BROWSER_TEST_GLOB = "test_*_browser.py"


def _imports_playwright(path: Path) -> bool:
    """Return True when *path* has a real ``from playwright`` or
    ``import playwright`` statement, ignoring occurrences inside string
    literals by checking only lines that look like top-level or indented
    import statements."""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("from playwright", "import playwright")):
            return True
    return False


class BootstrapCompatibilityRunnerCoverageTest(unittest.TestCase):
    def test_runner_uses_discover_not_hardcoded_module(self) -> None:
        """The runner must use ``unittest discover`` rather than naming a
        single module, so that adding a new ``test_*_browser.py`` module
        automatically includes it in every Bootstrap compatibility lane."""
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            "discover",
            source,
            "run-bootstrap-compatibility.py must use 'unittest discover' "
            "to pick up all test_*_browser.py modules, not a hard-coded "
            "single module name.",
        )
        self.assertIn(
            BROWSER_TEST_GLOB,
            source,
            f"run-bootstrap-compatibility.py must use the {BROWSER_TEST_GLOB!r} "
            "discovery pattern so every Playwright browser test module is "
            "included in compatibility runs.",
        )

    def test_every_playwright_module_matches_runner_glob(self) -> None:
        """Every test module that imports ``playwright`` must match
        the runner's discovery glob.  If a new Playwright test module is
        added under a name like ``test_foo.py`` (without the ``_browser``
        suffix), this test fails and forces the author to either rename
        it or update the runner's pattern."""
        playwright_modules: list[str] = []
        for test_file in sorted(TESTS_DIR.glob("test_*.py")):
            if _imports_playwright(test_file):
                playwright_modules.append(test_file.name)

        self.assertGreater(
            len(playwright_modules),
            0,
            "Expected at least one Playwright-based test module under tests/",
        )

        glob_matches = {p.name for p in TESTS_DIR.glob(BROWSER_TEST_GLOB)}
        uncovered = [
            name for name in playwright_modules if name not in glob_matches
        ]
        self.assertEqual(
            uncovered,
            [],
            f"These Playwright test modules do not match the runner's "
            f"{BROWSER_TEST_GLOB!r} glob and will be silently excluded "
            f"from Bootstrap compatibility runs: {uncovered}. "
            f"Rename them to match the glob or update the runner.",
        )

    def test_no_non_playwright_module_matches_browser_glob(self) -> None:
        """Conversely, no module matching the glob should be a
        non-Playwright test — the compatibility runner rebuilds against a
        temporary Bootstrap checkout per version and must not waste that
        rebuild running unrelated tests."""
        glob_matches = sorted(TESTS_DIR.glob(BROWSER_TEST_GLOB))
        non_playwright: list[str] = []
        for match in glob_matches:
            if not _imports_playwright(match):
                non_playwright.append(match.name)

        self.assertEqual(
            non_playwright,
            [],
            f"These modules match {BROWSER_TEST_GLOB!r} but do not import "
            f"playwright, so they would waste the compatibility "
            f"runner's per-version rebuild: {non_playwright}.",
        )


if __name__ == "__main__":
    unittest.main()
