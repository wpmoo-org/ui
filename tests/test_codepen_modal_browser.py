from __future__ import annotations

import json
import re
import unittest
from html import unescape

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    ROOT,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    skip_if_browser_launch_is_sandboxed,
)


class CodePenModalBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright_manager.__exit__(None, None, None)

    def codepen_payload(self, component: str, title: str) -> dict[str, object]:
        source = ROOT.joinpath(
            f"site-dist/components/{component}/index.html"
        ).read_text(encoding="utf-8")
        for match in re.finditer(
            r'<textarea name="data" hidden>(.*?)</textarea>',
            source,
            re.DOTALL,
        ):
            payload = json.loads(unescape(match.group(1)).strip())
            if payload.get("title") == title:
                return payload
        raise AssertionError(f"CodePen payload not found: {title}")

    def render_component_codepen(self, payload: dict[str, object]):
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        page = context.new_page()
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
        page.add_script_tag(content=str(payload["js"]))
        prepare_page(page, CERTIFICATION_CASES[0])
        return context, page

    def assert_modal_covers_codepen_viewport(
        self,
        component: str,
        title: str,
        trigger_text: str,
    ) -> None:
        payload = self.codepen_payload(component, title)
        context, page = self.render_component_codepen(payload)
        try:
            evidence = BrowserEvidence(page)
            page.get_by_role("button", name=trigger_text).click()

            modal = page.locator(".modal.show")
            backdrop = page.locator(".modal-backdrop.show")
            expect(modal).to_have_count(1)
            expect(backdrop).to_have_count(1)

            geometry = page.evaluate(
                """
                () => {
                  const modal = document.querySelector(".modal.show");
                  const backdrop = document.querySelector(".modal-backdrop.show");
                  const dialog = document.querySelector(".modal.show .modal-dialog");
                  const modalRect = modal.getBoundingClientRect();
                  const backdropRect = backdrop.getBoundingClientRect();
                  const dialogRect = dialog.getBoundingClientRect();
                  return {
                    viewportWidth: window.innerWidth,
                    viewportHeight: window.innerHeight,
                    modalRect,
                    backdropRect,
                    dialogCenterX: dialogRect.left + dialogRect.width / 2,
                  };
                }
                """
            )

            self.assertGreaterEqual(
                geometry["modalRect"]["width"],
                geometry["viewportWidth"] - 1,
            )
            self.assertGreaterEqual(
                geometry["backdropRect"]["width"],
                geometry["viewportWidth"] - 1,
            )
            self.assertAlmostEqual(
                geometry["dialogCenterX"],
                geometry["viewportWidth"] / 2,
                delta=2,
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_dialog_codepen_modal_covers_the_viewport(self) -> None:
        self.assert_modal_covers_codepen_viewport(
            "dialog",
            "Moo UI Dialog - Basic",
            "Open dialog",
        )

    def test_alert_dialog_codepen_modal_covers_the_viewport(self) -> None:
        self.assert_modal_covers_codepen_viewport(
            "alert-dialog",
            "Moo UI Alert Dialog - Basic",
            "Discard draft",
        )

    def test_component_codepen_demo_adds_header_actions_without_settings(self) -> None:
        payload = self.codepen_payload("button", "Moo UI Button - Primary")
        self.assertNotIn("window.MooCodePenThemeBuilder =", str(payload["js"]))
        context, page = self.render_component_codepen(payload)
        try:
            evidence = BrowserEvidence(page)
            actions = page.locator(".moo-codepen-actions")
            settings = page.locator("[data-moo-codepen-settings-toggle]")
            theme = page.locator("[data-moo-codepen-theme-toggle]")
            github = page.locator(".moo-codepen-actions__github-link")

            expect(actions).to_have_count(1)
            expect(settings).to_have_count(0)
            expect(page.locator("#moo-codepen-settings")).to_have_count(0)
            expect(theme).to_have_attribute("aria-label", "Switch to dark mode")
            expect(github).to_have_attribute("href", "https://github.com/wpmoo-org/ui")
            expect(github).to_contain_text("wpmoo-org/ui")

            position = actions.evaluate(
                """
                (element) => {
                  const rect = element.getBoundingClientRect();
                  const styles = window.getComputedStyle(element);
                  return {
                    position: styles.position,
                    right: Math.round(window.innerWidth - rect.right),
                    top: Math.round(rect.top),
                    height: Math.round(rect.height),
                  };
                }
                """
            )
            self.assertEqual(position["position"], "fixed")
            self.assertEqual(position["right"], 16)
            self.assertEqual(position["top"], 16)
            self.assertEqual(position["height"], 32)

            theme.click()
            expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")
            expect(theme).to_have_attribute("aria-label", "Switch to light mode")
            theme.click()
            expect(page.locator("html")).to_have_attribute("data-bs-theme", "light")
            expect(theme).to_have_attribute("aria-label", "Switch to dark mode")

            evidence.assert_clean()
        finally:
            context.close()
