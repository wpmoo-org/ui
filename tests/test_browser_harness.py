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

from tests.helpers.browser_harness import (
    BrowserCase,
    launch_certification_browser,
    new_case_context,
)


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
            if key not in {"MOO_UI_BROWSER_ENGINE", "MOO_UI_BROWSER_CHANNEL"}
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            # The engine check passes for the default and proceeds toward a
            # Chromium launch; stub the launcher so no browser actually starts.
            playwright = mock.Mock()
            launch_certification_browser(playwright)
        playwright.chromium.launch.assert_called_once_with()
        playwright.firefox.launch.assert_not_called()
        playwright.webkit.launch.assert_not_called()

    def test_chromium_channel_can_select_branded_or_bundled_browser(self) -> None:
        for channel, expected_kwargs in (
            ("chrome", {"channel": "chrome"}),
            ("bundled", {}),
            ("playwright", {}),
        ):
            with self.subTest(channel=channel):
                playwright = mock.Mock()
                with mock.patch.dict(
                    os.environ,
                    {
                        "MOO_UI_BROWSER_ENGINE": "chromium",
                        "MOO_UI_BROWSER_CHANNEL": channel,
                    },
                ):
                    launch_certification_browser(playwright)
                playwright.chromium.launch.assert_called_once_with(**expected_kwargs)
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


class NewCaseContextEngineOptionsTests(unittest.TestCase):
    """Lock the is_mobile/has_touch guard added for Firefox: it rejects
    those context options ("options.isMobile is not supported in Firefox"),
    so new_case_context must omit them only on that engine."""

    MOBILE_CASE = BrowserCase(
        name="mobile-dark-rtl",
        viewport={"width": 390, "height": 844},
        color_scheme="dark",
        direction="rtl",
        is_mobile=True,
        has_touch=True,
    )

    def _browser_named(self, engine: str) -> mock.Mock:
        browser = mock.Mock()
        browser.browser_type.name = engine
        return browser

    def test_firefox_omits_mobile_and_touch_options(self) -> None:
        browser = self._browser_named("firefox")
        new_case_context(browser, self.MOBILE_CASE)
        _, kwargs = browser.new_context.call_args
        self.assertNotIn("is_mobile", kwargs)
        self.assertNotIn("has_touch", kwargs)
        self.assertEqual(kwargs["viewport"], self.MOBILE_CASE.viewport)

    def test_chromium_and_webkit_include_mobile_and_touch_options(self) -> None:
        for engine in ("chromium", "webkit"):
            with self.subTest(engine=engine):
                browser = self._browser_named(engine)
                new_case_context(browser, self.MOBILE_CASE)
                _, kwargs = browser.new_context.call_args
                self.assertEqual(kwargs["is_mobile"], True)
                self.assertEqual(kwargs["has_touch"], True)


if __name__ == "__main__":
    unittest.main()
