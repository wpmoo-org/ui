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


TOAST_PAGE_PATH = "/site-dist/components/toast/index.html"


class ToastBrowserTests(unittest.TestCase):
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

    def test_toasts_from_different_examples_share_one_viewport_stack(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}{TOAST_PAGE_PATH}",
                wait_until="networkidle",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            triggers = page.locator("button[data-toast-target]")
            triggers.nth(0).click()
            triggers.nth(1).click()

            generated_toasts = page.locator('.toast[data-toast-generated="true"]')
            expect(generated_toasts).to_have_count(2)
            stack_state = page.evaluate(
                """
                () => {
                  const toasts = Array.from(
                    document.querySelectorAll('.toast[data-toast-generated="true"]')
                  );
                  const parents = Array.from(new Set(
                    toasts.map((toast) => toast.parentElement)
                  ));
                  return {
                    parentCount: parents.length,
                    parentIsBodyChild: parents[0]?.parentElement === document.body,
                    parentInsidePreview: Boolean(
                      parents[0]?.closest('.moo-example__preview')
                    ),
                    indexes: toasts.map((toast) => toast.dataset.toastStackIndex),
                  };
                }
                """
            )

            self.assertEqual(stack_state["parentCount"], 1)
            self.assertTrue(stack_state["parentIsBodyChild"])
            self.assertFalse(stack_state["parentInsidePreview"])
            self.assertEqual(stack_state["indexes"], ["0", "1"])
            evidence.assert_clean()
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
