from __future__ import annotations

import subprocess
import sys
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers import codepen_payload_from_output
from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    setup_codepen_page,
    ROOT,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


TOAST_PAGE_PATH = "/site-dist/components/toast/index.html"


class ToastBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        result = subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
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

    def test_codepen_demo_js_wires_toast_template_triggers(self) -> None:
        payload = codepen_payload_from_output(
            "components/toast.html",
            "Moo UI Toast - Basic",
        )
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page, evidence = setup_codepen_page(
                context,
                payload,
                base_url=self.base_url,
            )

            expect(page.locator("body")).to_have_attribute(
                "data-moo-codepen-toasts-ready",
                "true",
            )
            trigger = page.locator('[data-toast-target="#toast-basic-template"]')
            trigger.evaluate("element => element.click()")
            trigger.evaluate("element => element.click()")

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

    def test_codepen_generated_toast_close_restores_trigger_focus(self) -> None:
        payload = codepen_payload_from_output(
            "components/toast.html",
            "Moo UI Toast - Basic",
        )
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page, evidence = setup_codepen_page(
                context,
                payload,
                base_url=self.base_url,
                include_payload_js=False,
            )
            expect(page.locator("body")).to_have_attribute(
                "data-moo-codepen-toasts-ready",
                "true",
            )

            trigger = page.locator('[data-toast-target="#toast-basic-template"]')
            trigger.focus()
            trigger.click()

            generated = page.locator('.toast[data-toast-generated="true"]')
            expect(generated).to_have_count(1)
            dismiss = generated.locator('[data-bs-dismiss="toast"]')
            dismiss.focus()
            dismiss.press("Enter")

            expect(generated).to_have_count(0)
            expect(trigger).to_be_focused()
            evidence.assert_clean()
        finally:
            context.close()

    def test_codepen_limited_toast_keeps_keyboard_focus_until_dismissed(self) -> None:
        payload = codepen_payload_from_output(
            "components/toast.html",
            "Moo UI Toast - Basic",
        )
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page, evidence = setup_codepen_page(
                context,
                payload,
                base_url=self.base_url,
                include_payload_js=False,
            )
            expect(page.locator("body")).to_have_attribute(
                "data-moo-codepen-toasts-ready",
                "true",
            )

            trigger = page.locator('[data-toast-target="#toast-basic-template"]')
            trigger.focus()
            for _ in range(3):
                trigger.click()

            generated = page.locator('.toast[data-toast-generated="true"]')
            expect(generated).to_have_count(3)
            focused_toast = generated.nth(2)
            focused_toast_id = focused_toast.get_attribute("id")
            self.assertIsNotNone(focused_toast_id)
            dismiss = focused_toast.locator('[data-bs-dismiss="toast"]')
            dismiss.focus()
            expect(dismiss).to_be_focused()

            trigger.evaluate("element => element.click()")

            expect(generated).to_have_count(4)
            focused_toast = page.locator(f"#{focused_toast_id}")
            dismiss = focused_toast.locator('[data-bs-dismiss="toast"]')
            expect(focused_toast).to_have_attribute("data-toast-stack-limited", "")
            self.assertIsNone(focused_toast.get_attribute("inert"))
            expect(dismiss).to_be_focused()

            dismiss.press("Enter")

            expect(generated).to_have_count(3)
            expect(trigger).to_be_focused()
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
