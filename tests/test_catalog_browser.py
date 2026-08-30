from __future__ import annotations

import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


HOME_PAGE_PATH = "/site-dist/index.html"


class CatalogBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright_manager.__exit__(None, None, None)
        cls.server.__exit__(None, None, None)

    def test_command_palette_keyboard_navigation_keeps_active_item_clear_of_scroll_edges(
        self,
    ) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}{HOME_PAGE_PATH}",
                wait_until="networkidle",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            page.get_by_role("button", name="Search documentation").click()
            search = page.locator("#catalog-command input[type='search']")
            expect(search).to_have_attribute(
                "aria-activedescendant",
                "catalog-command-item-0",
            )

            for _ in range(8):
                search.press("ArrowDown")

            active_state = page.evaluate(
                """
                () => {
                  const body = document.querySelector(
                    "#catalog-command.show .moo-catalog__command-body"
                  );
                  const active = document.querySelector(
                    "#catalog-command.show [data-moo-command-item].active"
                  );
                  const bodyRect = body.getBoundingClientRect();
                  const activeRect = active.getBoundingClientRect();
                  const previous = active.previousElementSibling;
                  const previousRect = previous?.getBoundingClientRect();
                  return {
                    activeText: active.textContent.trim(),
                    bottomGap: bodyRect.bottom - activeRect.bottom,
                    gapFromPrevious: previousRect ? activeRect.top - previousRect.bottom : null,
                    marginTop: getComputedStyle(active).marginTop,
                    scrollTop: body.scrollTop,
                  };
                }
                """
            )

            self.assertEqual(active_state["activeText"], "Overview")
            self.assertGreaterEqual(active_state["bottomGap"], 8)
            self.assertEqual(active_state["marginTop"], "2px")
            self.assertGreaterEqual(active_state["gapFromPrevious"], 2)
            self.assertGreater(active_state["scrollTop"], 0)
            evidence.assert_clean()
        finally:
            context.close()

    def test_command_palette_body_omits_search_divider(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}{HOME_PAGE_PATH}",
                wait_until="networkidle",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            page.get_by_role("button", name="Search documentation").click()
            search = page.locator("#catalog-command input[type='search']")
            expect(search).to_have_attribute(
                "aria-activedescendant",
                "catalog-command-item-0",
            )

            palette_state = page.evaluate(
                """
                () => {
                  const modal = document.querySelector("#catalog-command.show");
                  const body = modal.querySelector(".moo-catalog__command-body");
                  const bodyStyle = getComputedStyle(body);
                  return {
                    bodyBorderTopWidth: bodyStyle.borderTopWidth,
                  };
                }
                """
            )

            self.assertEqual(palette_state["bodyBorderTopWidth"], "0px")
            evidence.assert_clean()
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
