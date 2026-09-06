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


def load_home_page(page, base_url: str):
    response = page.goto(f"{base_url}{HOME_PAGE_PATH}", wait_until="domcontentloaded")
    expect(page.get_by_role("button", name="Search documentation")).to_be_visible()
    return response


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
            response = load_home_page(page, self.base_url)
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
            response = load_home_page(page, self.base_url)
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

    def test_primary_doc_toc_links_keep_minimum_touch_targets(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}/site-dist/installation/",
                wait_until="domcontentloaded",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])
            expect(page.get_by_role("heading", name="Installation", level=1)).to_be_visible()
            expect(page.locator(".moo-doc-toc")).to_be_visible()

            toc_link_sizes = page.locator(".moo-doc-toc .nav-link").evaluate_all(
                """
                links => links.map((link) => {
                  const rect = link.getBoundingClientRect();
                  return {
                    text: link.textContent.trim(),
                    width: rect.width,
                    height: rect.height,
                  };
                })
                """
            )

            self.assertGreaterEqual(len(toc_link_sizes), 4)
            for link in toc_link_sizes:
                with self.subTest(link=link["text"]):
                    self.assertGreaterEqual(link["width"], 24, link)
                    self.assertGreaterEqual(link["height"], 24, link)

            evidence.assert_clean()
        finally:
            context.close()

    def test_form_preview_field_wrappers_center_token_width_controls(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)

            for path, heading, preview_selector, control_selector in (
                (
                    "/site-dist/components/combobox/",
                    "Combobox",
                    ".moo-example__preview--narrow",
                    ".combobox",
                ),
                (
                    "/site-dist/components/datepicker/",
                    "Date Picker",
                    ".moo-example__preview--medium",
                    ".moo-datepicker",
                ),
            ):
                with self.subTest(path=path):
                    response = page.goto(
                        f"{self.base_url}{path}",
                        wait_until="domcontentloaded",
                    )
                    self.assertIsNotNone(response)
                    self.assertTrue(response.ok)
                    prepare_page(page, CERTIFICATION_CASES[0])
                    expect(page.get_by_role("heading", name=heading, level=1)).to_be_visible()

                    alignment = page.evaluate(
                        """
                        ([previewSelector, controlSelector]) => {
                          const preview = document.querySelector(
                            `.moo-component-examples > .moo-example__surface ${previewSelector}`
                          );
                          const control = preview?.querySelector(controlSelector);
                          if (!preview || !control) {
                            return null;
                          }
                          const previewRect = preview.getBoundingClientRect();
                          const controlRect = control.getBoundingClientRect();
                          const previewCenter = previewRect.left + previewRect.width / 2;
                          const controlCenter = controlRect.left + controlRect.width / 2;
                          return {
                            controlCenter,
                            controlWidth: controlRect.width,
                            delta: Math.abs(controlCenter - previewCenter),
                            previewCenter,
                            previewWidth: previewRect.width,
                          };
                        }
                        """,
                        [preview_selector, control_selector],
                    )

                    self.assertIsNotNone(alignment)
                    assert alignment is not None
                    self.assertGreater(alignment["controlWidth"], 0, alignment)
                    self.assertLessEqual(alignment["delta"], 1, alignment)

            evidence.assert_clean()
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
