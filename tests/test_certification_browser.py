import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CANONICAL_BOOTSTRAP,
    CERTIFICATION_BOOTSTRAP_LANES,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    run_axe,
    serve_repository,
)


class CertificationBrowserHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
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

    def test_accordion_fixture_proves_data_api_state_and_keyboard_flow(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/accordion.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                first_trigger = page.locator("#certification-first-trigger")
                first_panel = page.locator("#certification-first")
                second_trigger = page.locator("#certification-second-trigger")
                second_panel = page.locator("#certification-second")
                self.assertEqual(first_trigger.get_attribute("aria-expanded"), "true")
                self.assertTrue(first_panel.evaluate("element => element.classList.contains('show')"))
                self.assertEqual(second_trigger.get_attribute("aria-expanded"), "false")
                self.assertEqual(
                    page.evaluate(
                        """
                        () => bootstrap.Collapse.getOrCreateInstance(
                          document.querySelector("#certification-second"),
                          { toggle: false },
                        )._config.parent?.id
                        """
                    ),
                    "certification-accordion",
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const panel = document.querySelector("#certification-second");
                      panel.addEventListener("shown.bs.collapse", resolve, { once: true });
                      document.querySelector("#certification-second-trigger").click();
                    })
                    """
                )
                expect(second_trigger).to_have_attribute("aria-expanded", "true")
                expect(first_trigger).to_have_attribute("aria-expanded", "false")
                self.assertTrue(second_panel.evaluate("element => element.classList.contains('show')"))
                self.assertFalse(first_panel.evaluate("element => element.classList.contains('show')"))

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const panel = document.querySelector("#certification-second");
                      panel.addEventListener("hidden.bs.collapse", resolve, { once: true });
                      document.querySelector("#certification-second-trigger").click();
                    })
                    """
                )
                expect(second_trigger).to_have_attribute("aria-expanded", "false")
                first_trigger.focus()
                first_trigger.press("Enter")
                expect(first_trigger).to_have_attribute("aria-expanded", "true")
                expect(first_panel).to_have_class("accordion-collapse collapse show")
                first_trigger.press("Space")
                expect(first_panel).to_have_class("accordion-collapse collapse")
                expect(first_trigger).to_have_attribute("aria-expanded", "false")
                self.assertTrue(
                    first_trigger.evaluate(
                        "element => document.activeElement === element"
                    )
                )

                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_canonical_bootstrap_lane_resolves_the_real_local_bundle(self) -> None:
        self.assertEqual(CERTIFICATION_BOOTSTRAP_LANES, (CANONICAL_BOOTSTRAP,))
        self.assertEqual(CANONICAL_BOOTSTRAP.version, "5.3.3")
        context = self.browser.new_context()
        response = context.request.get(CANONICAL_BOOTSTRAP.bundle_url(self.base_url))
        self.assertTrue(response.ok)
        self.assertIn("Bootstrap v5.3.3", response.text())
        context.close()

    def test_badge_fixture_proves_the_browser_evidence_pipeline(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/badge.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case, normalize_screenshot=True)

                self.assertEqual(page.locator("h1").count(), 1)
                self.assertEqual(page.locator(".badge").count(), 9)
                self.assertEqual(
                    page.locator(".visually-hidden").inner_text(),
                    "unread notifications",
                )
                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )

                violations = run_axe(page)
                self.assertEqual(
                    violations,
                    [],
                    "axe violations: "
                    + ", ".join(
                        str(violation.get("id", "unknown"))
                        for violation in violations
                    ),
                )

                badge_style = page.locator(".badge").first.evaluate(
                    """
                    element => {
                      const style = getComputedStyle(element);
                      return {
                        animationDuration: style.animationDuration,
                        transitionDuration: style.transitionDuration,
                      };
                    }
                    """
                )
                self.assertEqual(badge_style["animationDuration"], "0s")
                self.assertEqual(badge_style["transitionDuration"], "0s")
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


if __name__ == "__main__":
    unittest.main()
