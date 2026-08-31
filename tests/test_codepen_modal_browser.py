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
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class CodePenModalBrowserTests(unittest.TestCase):
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

    def codepen_payload_from_page(self, page_path: str, title: str) -> dict[str, object]:
        source = ROOT.joinpath(f"site-dist/{page_path}").read_text(encoding="utf-8")
        for match in re.finditer(
            r'<textarea name="data" hidden>(.*?)</textarea>',
            source,
            re.DOTALL,
        ):
            payload = json.loads(unescape(match.group(1)).strip())
            if payload.get("title") == title:
                return payload
        raise AssertionError(f"CodePen payload not found: {title}")

    def codepen_payload(self, component: str, title: str) -> dict[str, object]:
        return self.codepen_payload_from_page(
            f"components/{component}/index.html",
            title,
        )

    def render_component_codepen(self, payload: dict[str, object]):
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        page = context.new_page()
        response = page.goto(f"{self.base_url}/site-dist/index.html", wait_until="load")
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
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
        page.add_script_tag(content=f'window.MooCodePenRuntimeBaseUrl = "{self.base_url}/";')
        page.add_script_tag(path=ROOT / "site-dist/assets/js/codepen-demo.js")
        payload_js = self.remap_codepen_package_imports(str(payload["js"]))
        if payload_js.strip():
            page.add_script_tag(content=payload_js)
        prepare_page(page, CERTIFICATION_CASES[0])
        return context, page

    def remap_codepen_package_imports(self, script: str) -> str:
        return re.sub(
            r"https://unpkg\.com/@wpmoo/ui@[^/]+/dist/js/",
            f"{self.base_url}/dist/js/",
            script,
        )

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

    def test_js_component_codepen_payloads_initialize_component_runtimes(self) -> None:
        cases = [
            ("chart", "Moo UI Basic"),
            ("combobox", "Moo UI Combobox - Basic"),
            ("context-menu", "Moo UI Context Menu - Basic"),
            ("datepicker", "Moo UI Date Picker - Basic"),
            ("slider", "Moo UI Slider - Default"),
        ]

        for component, title in cases:
            with self.subTest(component=component):
                payload = self.codepen_payload(component, title)
                context, page = self.render_component_codepen(payload)
                try:
                    evidence = BrowserEvidence(page)

                    if component == "chart":
                        page.wait_for_function(
                            """
                            () => {
                              const canvas = document.querySelector(".chart canvas");
                              if (!canvas || !canvas.width || !canvas.height) {
                                return false;
                              }
                              const data = canvas
                                .getContext("2d")
                                .getImageData(0, 0, canvas.width, canvas.height)
                                .data;
                              return data.some((channel) => channel !== 0);
                            }
                            """,
                            timeout=5000,
                        )
                    elif component == "combobox":
                        combobox_input = page.locator(".combobox-input").first
                        combobox_input.click()
                        expect(page.locator(".combobox-menu.show")).to_have_count(1)
                        combobox_input.fill("Ada")
                        page.get_by_role("option", name="Ada Lovelace").click()
                        expect(combobox_input).to_have_value("Ada Lovelace")
                        self.assertEqual(
                            page.locator('input[type="hidden"][name="reviewer"]').input_value(),
                            "ada",
                        )
                    elif component == "context-menu":
                        page.locator("#context-menu-basic-surface").click(button="right")
                        expect(page.locator(".context-menu-menu.show")).to_have_count(1)
                        expect(page.locator("[data-context-menu-fallback]")).to_have_attribute(
                            "aria-expanded",
                            "true",
                        )
                    elif component == "datepicker":
                        page.locator("[data-datepicker-trigger]").first.click()
                        expect(
                            page.locator("[data-datepicker-popover]:not([hidden])")
                        ).to_have_count(1)
                        expect(page.locator("[data-calendar-day]").first).to_be_visible()
                    elif component == "slider":
                        page.locator("[data-slider-input]").first.evaluate(
                            """
                            (element) => {
                              element.value = "75";
                              element.dispatchEvent(new Event("input", { bubbles: true }));
                            }
                            """
                        )
                        expect(page.locator("[data-slider-output]")).to_have_text("75")

                    evidence.assert_clean()
                finally:
                    context.close()

    def test_dashboard_datatable_codepen_payloads_initialize_runtime(self) -> None:
        cases = [
            ("examples/dashboard/tasks/index.html", "Moo UI \u2014 Tasks"),
            ("examples/dashboard/users/index.html", "Moo UI \u2014 Users"),
        ]

        for page_path, title in cases:
            with self.subTest(page=page_path):
                payload = self.codepen_payload_from_page(page_path, title)
                context, page = self.render_component_codepen(payload)
                try:
                    evidence = BrowserEvidence(page)
                    search = page.locator("[data-datatable-search]").first
                    empty = page.locator("[data-datatable-empty]").first
                    summary = page.locator("[data-datatable-results-summary]").first

                    expect(empty).to_be_hidden()
                    search.fill("zzzz-no-matching-row")
                    expect(empty).to_be_visible()
                    expect(empty.locator(".datatable-empty-title")).to_have_text(
                        "No matching results"
                    )
                    expect(summary).to_have_text("No results")

                    evidence.assert_clean()
                finally:
                    context.close()

    def test_toast_codepen_demo_button_shows_toast(self) -> None:
        payload = self.codepen_payload("toast", "Moo UI Toast - Basic")
        context, page = self.render_component_codepen(payload)
        try:
            evidence = BrowserEvidence(page)
            page.get_by_role("button", name="Show Toast").click()

            expect(page.locator(".toast.show")).to_have_count(1)
            expect(page.locator(".toast.show .toast-body")).to_contain_text(
                "Sunday, December 3 at 9:00 AM"
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
            expect(page.locator(".moo-codepen-footer")).to_contain_text(
                "Button component."
            )

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

            def github_colors() -> dict[str, str]:
                return github.evaluate(
                    """
                    (element) => {
                      const probe = document.createElement("span");
                      const button = window.getComputedStyle(element);
                      const body = window.getComputedStyle(document.body);
                      probe.style.position = "fixed";
                      probe.style.inset = "auto";
                      probe.style.backgroundColor = "color-mix(in srgb, var(--bs-body-color) 88%, var(--bs-body-bg))";
                      document.body.appendChild(probe);
                      const expected = window.getComputedStyle(probe).backgroundColor;
                      probe.remove();
                      return {
                        background: button.backgroundColor,
                        color: button.color,
                        bodyBackground: body.backgroundColor,
                        bodyColor: body.color,
                        mixedBodyColor: expected,
                      };
                    }
                    """
                )

            normal_colors = github_colors()
            self.assertEqual(
                normal_colors["background"],
                normal_colors["mixedBodyColor"],
            )
            self.assertEqual(normal_colors["color"], normal_colors["bodyBackground"])
            github.hover()
            hover_colors = github_colors()
            self.assertEqual(hover_colors["background"], normal_colors["bodyColor"])
            self.assertEqual(hover_colors["color"], normal_colors["bodyBackground"])

            theme.click()
            expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")
            expect(theme).to_have_attribute("aria-label", "Switch to light mode")
            page.mouse.move(0, 0)

            normal_colors = github_colors()
            self.assertEqual(
                normal_colors["background"],
                normal_colors["mixedBodyColor"],
            )
            self.assertEqual(normal_colors["color"], normal_colors["bodyBackground"])
            github.hover()
            hover_colors = github_colors()
            self.assertEqual(hover_colors["background"], normal_colors["bodyColor"])
            self.assertEqual(hover_colors["color"], normal_colors["bodyBackground"])

            theme.click()
            expect(page.locator("html")).to_have_attribute("data-bs-theme", "light")
            expect(theme).to_have_attribute("aria-label", "Switch to dark mode")

            evidence.assert_clean()
        finally:
            context.close()
