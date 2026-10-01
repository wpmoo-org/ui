"""Accepted contained Sidebar behavior using native macros without a server."""

import unittest
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers.browser_harness import BrowserEvidence, launch_certification_browser


ROOT = Path(__file__).resolve().parents[1]


class ContainedSidebarBrowserTests(unittest.TestCase):
    CSS_PATH = ROOT / "dist/assets/css/moo-ui.css"

    def test_mobile_drawer_preserves_document_scroll_and_desktop_containment(self):
        template = create_environment().from_string(
            (ROOT / "tests/fixtures/certification/layout-app.html.jinja").read_text()
        )
        # Read the real compiled assets once so a concurrent watch build cannot
        # replace a file between requests within this certification matrix.
        assets = {
            "/dist/assets/css/moo-ui.css": (self.CSS_PATH.read_bytes(), "text/css"),
            "/vendor/bootstrap/dist/js/bootstrap.bundle.min.js": (
                (ROOT / "vendor/bootstrap/dist/js/bootstrap.bundle.min.js").read_bytes(),
                "text/javascript",
            ),
            "/dist/js/sidebar.js": ((ROOT / "dist/js/sidebar.js").read_bytes(), "text/javascript"),
        }
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for theme in ("light", "dark"):
                    for direction in ("ltr", "rtl"):
                        for side in ("left", "right"):
                            for variant in ("sidebar", "floating", "inset"):
                                for collapsible in ("icon", "offcanvas", "none"):
                                    with self.subTest(theme=theme, direction=direction, side=side,
                                                      variant=variant, collapsible=collapsible):
                                        html = template.render(
                                            fixture_shell_mode="contained", fixture_side=side,
                                            fixture_direction=direction, fixture_variant=variant,
                                            fixture_collapsible=collapsible, fixture_long_navigation=True,
                                        )
                                        context = browser.new_context(
                                            viewport={"width": 390, "height": 480},
                                            color_scheme=theme, reduced_motion="reduce",
                                        )
                                        try:
                                            page = context.new_page()
                                            evidence = BrowserEvidence(page)

                                            def serve(route):
                                                path = urlparse(route.request.url).path
                                                if path == "/contained.html":
                                                    route.fulfill(body=html, content_type="text/html")
                                                    return
                                                if path in assets:
                                                    body, content_type = assets[path]
                                                    route.fulfill(body=body, content_type=content_type)
                                                else:
                                                    route.fulfill(status=404, body="Missing fixture asset")

                                            page.route("http://moo-core.invalid/**", serve)
                                            page.goto("http://moo-core.invalid/contained.html", wait_until="load")
                                            try:
                                                page.wait_for_function("document.body.dataset.layoutReady === 'true'")
                                            except Exception:
                                                evidence.assert_clean()
                                                raise
                                            sidebar = page.locator('[data-slot="sidebar"]')
                                            trigger = page.locator('[data-slot="page"] [data-sidebar-trigger]')
                                            content = sidebar.locator('[data-slot="sidebar-content"]')
                                            expect(sidebar).to_be_hidden()
                                            self.assertEqual(sidebar.evaluate("e => getComputedStyle(e).position"), "fixed")
                                            header = page.locator('[data-slot="page"]').get_by_role("banner")
                                            self.assertAlmostEqual(header.bounding_box()["y"], 0, delta=1)
                                            trigger.press("Enter")
                                            expect(sidebar).to_have_attribute("role", "dialog")
                                            expect(sidebar).to_have_attribute("aria-modal", "true")
                                            expect(trigger).to_have_attribute("aria-expanded", "true")
                                            page.wait_for_function("document.querySelector('[data-slot=sidebar]').classList.contains('show') && !document.querySelector('[data-slot=sidebar]').classList.contains('showing')")
                                            box = sidebar.bounding_box()
                                            self.assertAlmostEqual(box["height"], 480, delta=1)
                                            edge = box["x"] if side == "left" else 390 - box["x"] - box["width"]
                                            self.assertAlmostEqual(edge, 0, delta=1)
                                            self.assertTrue(content.evaluate("e => e.scrollHeight > e.clientHeight"))
                                            content.evaluate("e => e.scrollTop = e.scrollHeight")
                                            self.assertGreater(content.evaluate("e => e.scrollTop"), 0)
                                            sidebar.locator('[data-sidebar-trigger]').focus()
                                            page.keyboard.press("Shift+Tab")
                                            self.assertTrue(sidebar.evaluate("e => e.contains(document.activeElement)"))
                                            sidebar.get_by_role("button", name="Open account menu").focus()
                                            page.keyboard.press("Tab")
                                            self.assertTrue(sidebar.evaluate("e => e.contains(document.activeElement)"))
                                            page.keyboard.press("Escape")
                                            expect(sidebar).to_be_hidden()
                                            expect(trigger).to_be_focused()
                                            expect(trigger).to_have_attribute("aria-expanded", "false")
                                            self.assertEqual(page.locator("main").evaluate("e => getComputedStyle(e).overflowY"), "visible")
                                            page.evaluate("window.scrollTo(0, 320)")
                                            self.assertGreater(page.evaluate("window.scrollY"), 0)
                                            self.assertEqual(page.locator("main").evaluate("e => e.scrollTop"), 0)
                                            page.evaluate("window.scrollTo(0, 0)")
                                            page.set_viewport_size({"width": 992, "height": 844})
                                            page.wait_for_function("getComputedStyle(document.querySelector('[data-slot=sidebar]')).position === 'relative'")
                                            expect(sidebar).to_be_visible()
                                            app_height = page.locator('[data-layout="app"]').bounding_box()["height"]
                                            host_height = page.locator('#layout-certification-host').bounding_box()["height"]
                                            self.assertAlmostEqual(app_height, host_height, delta=1)
                                            self.assertLess(app_height, 844)
                                            self.assertEqual(page.locator("main").evaluate("e => getComputedStyle(e).overflowY"), "auto")
                                            page.set_viewport_size({"width": 991, "height": 844})
                                            page.wait_for_function("getComputedStyle(document.querySelector('[data-slot=sidebar]')).position === 'fixed'")
                                            expect(sidebar).to_be_hidden()
                                            self.assertEqual(page.locator("main").evaluate("e => getComputedStyle(e).overflowY"), "visible")
                                            self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))
                                            evidence.assert_clean()
                                        finally:
                                            context.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
