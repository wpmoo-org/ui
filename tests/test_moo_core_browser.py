from __future__ import annotations

from playwright.sync_api import sync_playwright

from tests.helpers import CatalogTestCase
from tests.helpers.browser_harness import (
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class MooOwnerIsolationBrowserTests(CatalogTestCase):
    def test_nested_resolved_owners_isolate_state_but_class_only_portals_inherit(self) -> None:
        skip_if_browser_launch_is_sandboxed()
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        with serve_repository() as base_url, sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                page = browser.new_page()
                response = page.goto(
                    f"{base_url}/tests/fixtures/owner-isolation.html",
                    wait_until="load",
                )
                self.assertIsNotNone(response)
                assert response is not None
                self.assertTrue(response.ok)

                colors = page.evaluate(
                    """
                () => {
                  const read = (id) => {
                    const root = document.getElementById(id);
                    const select = root.querySelector('[data-owner-probe="select"]');
                    const toggle = root.querySelector('[data-owner-probe="switch"]');
                    const close = root.querySelector('[data-owner-probe="close"]');
                    const card = root.querySelector('[data-owner-probe="card"]');
                    const rootStyle = getComputedStyle(root);
                    const selectStyle = getComputedStyle(select);
                    const toggleStyle = getComputedStyle(toggle);
                    const closeStyle = getComputedStyle(close);
                    const cardStyle = getComputedStyle(card);
                    return {
                      colorScheme: rootStyle.colorScheme,
                      selectIndicator: selectStyle.getPropertyValue('--bs-form-select-bg-img'),
                      switchIndicator: toggleStyle.getPropertyValue('--bs-form-switch-bg'),
                      closeColor: closeStyle.color,
                      closeFilter: closeStyle.filter,
                      cardBackground: cardStyle.backgroundColor,
                      cardSpacing: cardStyle.getPropertyValue('--moo-card-spacing'),
                    };
                  };
                  const host = document.getElementById('host-probe');
                  return {
                    hostCardSpacing: getComputedStyle(host).getPropertyValue('--moo-card-spacing'),
                    outer: read('outer-owner'),
                    portal: read('class-only-portal'),
                    inner: read('inner-owner'),
                  };
                }
                """
                )
            finally:
                browser.close()

        self.assertEqual(colors["hostCardSpacing"].strip(), "")
        self.assertEqual(colors["outer"]["colorScheme"], "dark")
        self.assertEqual(colors["portal"]["colorScheme"], "dark")
        self.assertEqual(colors["inner"]["colorScheme"], "light")
        self.assertIn("dee2e6", colors["outer"]["selectIndicator"])
        self.assertIn("dee2e6", colors["portal"]["selectIndicator"])
        self.assertIn("343a40", colors["inner"]["selectIndicator"])
        self.assertIn("255", colors["outer"]["switchIndicator"])
        self.assertIn("255", colors["portal"]["switchIndicator"])
        self.assertIn("10", colors["inner"]["switchIndicator"])
        self.assertEqual(colors["outer"]["closeFilter"], "none")
        self.assertEqual(colors["portal"]["closeFilter"], "none")
        self.assertEqual(colors["inner"]["closeFilter"], "none")
        self.assertEqual(colors["outer"]["closeColor"], colors["portal"]["closeColor"])
        self.assertNotEqual(colors["outer"]["closeColor"], colors["inner"]["closeColor"])
        self.assertEqual(colors["outer"]["cardBackground"], colors["portal"]["cardBackground"])
        self.assertNotEqual(colors["outer"]["cardBackground"], colors["inner"]["cardBackground"])
