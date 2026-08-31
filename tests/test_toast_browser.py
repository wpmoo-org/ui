from __future__ import annotations

import json
import re
import unittest
from html import unescape

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    ROOT,
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

    def toast_codepen_payload(self, title: str) -> dict[str, object]:
        source = (ROOT / "site-dist/components/toast/index.html").read_text(
            encoding="utf-8"
        )
        for match in re.finditer(
            r'<textarea name="data" hidden>(.*?)</textarea>',
            source,
            re.DOTALL,
        ):
            payload = json.loads(unescape(match.group(1)).strip())
            if payload.get("title") == title:
                return payload
        raise AssertionError(f"CodePen payload not found: {title}")

    def test_codepen_demo_js_wires_toast_template_triggers(self) -> None:
        payload = self.toast_codepen_payload("Moo UI Toast - Basic")
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            page.set_content(
                f"""
                <!doctype html>
                <html lang="en">
                  <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                  </head>
                  <body>
                    {payload["html"]}
                  </body>
                </html>
                """,
                wait_until="load",
            )
            page.add_style_tag(path=ROOT / "site-dist/assets/css/moo-ui.css")
            page.add_style_tag(path=ROOT / "site-dist/assets/css/codepen-demo.css")
            page.add_script_tag(path=ROOT / "site-dist/assets/js/bootstrap.bundle.min.js")
            page.add_script_tag(path=ROOT / "site-dist/assets/js/codepen-demo.js")
            payload_js = str(payload["js"])
            if payload_js.strip():
                page.add_script_tag(content=payload_js)
            prepare_page(page, CERTIFICATION_CASES[0])

            expect(page.locator("body")).to_have_attribute(
                "data-moo-codepen-toasts-ready",
                "true",
            )
            trigger = page.locator('[data-toast-target="#toast-basic-template"]')
            trigger.click()
            trigger.click()

            deck = page.locator(
                '.toast-container--stacked[data-toast-stack="deck"]'
                '[data-moo-codepen-toast-stack="shared"]'
            )
            generated = deck.locator('[data-toast-generated="true"]')
            template_deck = page.locator(
                '.toast-container--stacked[data-toast-stack="deck"]'
                ':has(> template#toast-basic-template)'
            )

            expect(deck).to_have_count(1)
            expect(generated).to_have_count(2)
            expect(template_deck.locator('[data-toast-generated="true"]')).to_have_count(0)
            self.assertEqual(
                generated.evaluate_all(
                    "elements => elements.map(element => element.dataset.toastStackIndex)"
                ),
                ["0", "1"],
            )
            evidence.assert_clean()
        finally:
            context.close()

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
