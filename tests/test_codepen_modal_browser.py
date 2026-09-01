from __future__ import annotations

import subprocess
import sys
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers import codepen_payload_from_output
from tests.helpers.browser_harness import (
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    ROOT,
    setup_codepen_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class CodePenModalBrowserTests(unittest.TestCase):
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
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.addClassCleanup(cls.playwright_manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def codepen_payload(self, component: str, title: str) -> dict[str, object]:
        return codepen_payload_from_output(
            f"components/{component}/index.html",
            title,
        )

    def render_component_codepen(self, payload: dict[str, object]):
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        page, evidence = setup_codepen_page(
            context,
            payload,
            base_url=self.base_url,
        )
        return context, page, evidence

    def assert_modal_covers_codepen_viewport(
        self,
        component: str,
        title: str,
        trigger_text: str,
        *,
        keyboard_dismisses: bool = True,
    ) -> None:
        payload = self.codepen_payload(component, title)
        context, page, evidence = self.render_component_codepen(payload)
        try:
            page.evaluate(
                """
                () => {
                  const target = document.createElement("button");
                  target.id = "outside-modal-target";
                  target.type = "button";
                  target.textContent = "Outside target";
                  target.style.position = "fixed";
                  target.style.inset = "1rem auto auto 1rem";
                  target.addEventListener("click", () => {
                    window.__outsideModalTargetClicked = true;
                  });
                  document.body.appendChild(target);
                }
                """
            )
            trigger = page.get_by_role("button", name=trigger_text)
            trigger.click()

            modal = page.locator(".modal.show")
            backdrop = page.locator(".modal-backdrop.show")
            expect(modal).to_have_count(1)
            expect(backdrop).to_have_count(1)
            expect(modal).to_be_visible()
            expect(backdrop).to_be_visible()

            self.assertFalse(
                page.evaluate(
                    """
                    () => {
                      const target = document.querySelector("#outside-modal-target");
                      const rect = target.getBoundingClientRect();
                      const topElement = document.elementFromPoint(
                        rect.left + rect.width / 2,
                        rect.top + rect.height / 2
                      );
                      return target === topElement || target.contains(topElement);
                    }
                    """
                )
            )
            self.assertFalse(
                page.evaluate("() => window.__outsideModalTargetClicked === true")
            )

            positioning = page.evaluate(
                """
                () => {
                  const modal = document.querySelector(".modal.show");
                  const backdrop = document.querySelector(".modal-backdrop.show");
                  return {
                    modalPosition: window.getComputedStyle(modal).position,
                    backdropPosition: window.getComputedStyle(backdrop).position,
                  };
                }
                """
            )
            self.assertEqual(positioning["modalPosition"], "fixed")
            self.assertEqual(positioning["backdropPosition"], "fixed")
            evidence.assert_clean()
            page.keyboard.press("Escape")
            if keyboard_dismisses:
                expect(page.locator(".modal.show")).to_have_count(0)
            else:
                expect(page.locator(".modal.show")).to_have_count(1)
                page.get_by_role("button", name="Cancel").click()
                expect(page.locator(".modal.show")).to_have_count(0)
            expect(trigger).to_be_focused()
        finally:
            context.close()

    def _assert_chart_runtime(self, page) -> None:
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

    def _assert_combobox_runtime(self, page) -> None:
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

    def _assert_context_menu_runtime(self, page) -> None:
        page.locator("#context-menu-basic-surface").click(button="right")
        expect(page.locator(".context-menu-menu.show")).to_have_count(1)
        expect(page.locator("[data-context-menu-fallback]")).to_have_attribute(
            "aria-expanded",
            "true",
        )

    def _assert_datepicker_runtime(self, page) -> None:
        page.locator("[data-datepicker-trigger]").first.click()
        expect(page.locator("[data-datepicker-popover]:not([hidden])")).to_have_count(1)
        expect(page.locator("[data-calendar-day]").first).to_be_visible()

    def _assert_slider_runtime(self, page) -> None:
        page.locator("[data-slider-input]").first.evaluate(
            """
            (element) => {
              element.value = "75";
              element.dispatchEvent(new Event("input", { bubbles: true }));
            }
            """
        )
        expect(page.locator("[data-slider-output]").first).to_have_text("75")

    def test_js_component_codepen_payloads_initialize_component_runtimes(self) -> None:
        cases = [
            ("chart", "Moo UI Basic"),
            ("combobox", "Moo UI Combobox - Basic"),
            ("context-menu", "Moo UI Context Menu - Basic"),
            ("datepicker", "Moo UI Date Picker - Basic"),
            ("slider", "Moo UI Slider - Default"),
        ]
        runtime_checks = {
            "chart": self._assert_chart_runtime,
            "combobox": self._assert_combobox_runtime,
            "context-menu": self._assert_context_menu_runtime,
            "datepicker": self._assert_datepicker_runtime,
            "slider": self._assert_slider_runtime,
        }

        for component, title in cases:
            with self.subTest(component=component):
                payload = self.codepen_payload(component, title)
                self.assertEqual(str(payload["js"]).strip(), "")
                context, page, evidence = self.render_component_codepen(payload)
                try:
                    runtime_checks[component](page)
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
                payload = codepen_payload_from_output(page_path, title)
                context, page, evidence = self.render_component_codepen(payload)
                try:
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
        context, page, evidence = self.render_component_codepen(payload)
        try:
            page.get_by_role("button", name="Show Toast").click()

            expect(page.locator(".toast.show")).to_have_count(1)
            expect(page.locator(".toast.show .toast-body")).to_contain_text(
                "Sunday, December 3 at 9:00 AM"
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_codepen_bootstrap_failure_preserves_foreign_script_and_clears_toast_queue(self) -> None:
        payload = self.codepen_payload("toast", "Moo UI Toast - Basic")
        bootstrap_cdn = "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js"
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        context.route(bootstrap_cdn, lambda route: route.abort())
        try:
            page, _evidence = setup_codepen_page(
                context,
                payload,
                base_url=self.base_url,
                bootstrap_src=bootstrap_cdn,
                include_payload_js=False,
            )

            expect(page.locator('script[data-foreign-bootstrap="true"]')).to_have_count(1)
            # The Bootstrap bundle fails asynchronously; the toast queue flag is
            # cleared only after the failure handler runs, so wait for that.
            expect(page.locator("body")).not_to_have_attribute(
                "data-moo-codepen-toasts-queued"
            )
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
            keyboard_dismisses=False,
        )

    def test_component_codepen_demo_adds_header_actions_without_settings(self) -> None:
        payload = self.codepen_payload("button", "Moo UI Button - Primary")
        self.assertNotIn("window.MooCodePenThemeBuilder =", str(payload["js"]))
        context, page, evidence = self.render_component_codepen(payload)
        try:
            actions = page.locator(".moo-codepen-actions")
            settings = page.locator("[data-moo-codepen-settings-toggle]")
            theme = page.locator("[data-moo-codepen-theme-toggle]")
            github = page.locator(".moo-codepen-actions__github-link")

            expect(actions).to_have_count(1)
            expect(settings).to_have_count(0)
            expect(page.locator("#moo-codepen-settings")).to_have_count(0)
            expect(theme).to_have_attribute("aria-label", "Switch to dark mode")
            expect(github).to_have_attribute("href", "https://github.com/wpmoo-org/ui")
            expect(github).to_have_attribute("aria-label", "wpmoo-org/ui on GitHub")
            expect(github).to_contain_text("wpmoo-org/ui")
            self.assertIsNone(github.get_attribute("role"))
            expect(page.locator(".moo-codepen-footer")).to_contain_text(
                "Button component."
            )

            placement = actions.evaluate(
                """
                (element) => {
                  const rect = element.getBoundingClientRect();
                  const styles = window.getComputedStyle(element);
                  const demoContent = Array.from(document.body.children).find((child) => {
                    return !child.matches(
                      ".moo-codepen-actions, .moo-codepen-signature, .moo-codepen-footer, script, style"
                    );
                  });
                  const contentRect = demoContent.getBoundingClientRect();
                  return {
                    position: styles.position,
                    visible:
                      rect.width > 0 &&
                      rect.height > 0 &&
                      rect.left >= 0 &&
                      rect.top >= 0 &&
                      rect.right <= window.innerWidth &&
                      rect.bottom <= window.innerHeight,
                    clearOfContent:
                      rect.right <= contentRect.left ||
                      rect.left >= contentRect.right ||
                      rect.bottom <= contentRect.top ||
                      rect.top >= contentRect.bottom,
                  };
                }
                """
            )
            self.assertEqual(placement["position"], "fixed")
            self.assertTrue(placement["visible"])
            self.assertTrue(placement["clearOfContent"])

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
            expect(github).to_have_css("background-color", normal_colors["bodyColor"])
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
            expect(github).to_have_css("background-color", normal_colors["bodyColor"])
            hover_colors = github_colors()
            self.assertEqual(hover_colors["background"], normal_colors["bodyColor"])
            self.assertEqual(hover_colors["color"], normal_colors["bodyBackground"])

            theme.click()
            expect(page.locator("html")).to_have_attribute("data-bs-theme", "light")
            expect(theme).to_have_attribute("aria-label", "Switch to dark mode")

            evidence.assert_clean()
        finally:
            context.close()
