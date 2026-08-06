"""Engine-selection tests for the certification browser harness.

The nightly matrix runs the browser suite across Chromium, Firefox, and
WebKit via ``MOO_UI_BROWSER_ENGINE``. These tests lock the selection logic
without launching a browser, so they stay fast and run even in the
Chromium-only PR gate: an unknown engine must fail loudly rather than fall
back to a silently different engine.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tests.helpers.browser_harness import launch_certification_browser


class BrowserHarnessEngineSelectionTests(unittest.TestCase):
    def test_unsupported_engine_fails_loudly(self) -> None:
        with mock.patch.dict(os.environ, {"MOO_UI_BROWSER_ENGINE": "netscape"}):
            with self.assertRaises(AssertionError) as context:
                launch_certification_browser(object())
        self.assertIn("Unsupported browser engine", str(context.exception))

    def test_default_engine_is_chromium(self) -> None:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key != "MOO_UI_BROWSER_ENGINE"
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            # The engine check passes for the default and proceeds toward a
            # Chromium launch; stub the launcher so no browser actually starts.
            playwright = mock.Mock()
            launch_certification_browser(playwright)
        playwright.chromium.launch.assert_called_once()
        playwright.firefox.launch.assert_not_called()
        playwright.webkit.launch.assert_not_called()

    def test_supported_non_chromium_engines_use_selected_launcher(self) -> None:
        for engine in ("firefox", "webkit"):
            with self.subTest(engine=engine):
                playwright = mock.Mock()
                with mock.patch.dict(os.environ, {"MOO_UI_BROWSER_ENGINE": engine}):
                    launch_certification_browser(playwright)
                getattr(playwright, engine).launch.assert_called_once_with()
                for other_engine in {"chromium", "firefox", "webkit"} - {engine}:
                    getattr(playwright, other_engine).launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
