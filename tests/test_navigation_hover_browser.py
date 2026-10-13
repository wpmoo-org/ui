import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class NavigationHoverBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright_manager.__exit__(None, None, None)
        cls.server.__exit__(None, None, None)

    def _page(self, theme, direction, vertical=False):
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        evidence = BrowserEvidence(page)
        response = page.goto(
            f"{self.base_url}/tests/fixtures/certification/navigation-hover.html",
            wait_until="networkidle",
        )
        self.assertTrue(response.ok)
        page.evaluate("""({theme, direction, vertical}) => {
          document.documentElement.dir = direction;
          document.querySelector('.moo-ui').dataset.bsTheme = theme;
          document.querySelector('#hover-navigation').classList.toggle('flex-column', vertical);
          document.querySelector('#hover-parent-item').classList.toggle('dropend', vertical);
        }""", {"theme": theme, "direction": direction, "vertical": vertical})
        return page, evidence

    def _background(self, page, selector, color):
        # Playwright polls the computed state with its bounded assertion timeout.
        expect(page.locator(selector)).to_have_css("background-color", color)

    def _active_color(self, page):
        return page.locator("#hover-navigation").evaluate("""element => {
          const probe = document.createElement('span');
          probe.style.backgroundColor = 'var(--bs-nav-pills-link-active-bg)';
          element.append(probe);
          const color = getComputedStyle(probe).backgroundColor;
          probe.remove();
          return color;
        }""")

    def test_dropdown_parent_keeps_highlight_through_submenu_hover(self):
        for theme in ("light", "dark"):
            for direction in ("ltr", "rtl"):
                for vertical in (False, True):
                    with self.subTest(theme=theme, direction=direction, vertical=vertical):
                        page, evidence = self._page(theme, direction, vertical)
                        try:
                            current = page.locator("#hover-current")
                            parent = page.locator("#hover-parent")
                            outside = page.locator("#hover-outside")
                            outside.hover()
                            color = self._active_color(page)
                            self.assertNotEqual(color, "rgba(0, 0, 0, 0)")
                            self._background(page, "#hover-current", color)
                            parent.click()
                            expect(page.locator("#hover-submenu")).to_be_visible()
                            self._background(page, "#hover-parent", color)
                            self._background(page, "#hover-current", "rgba(0, 0, 0, 0)")

                            page.locator("#hover-child").hover()
                            self._background(page, "#hover-parent", color)
                            self._background(page, "#hover-current", "rgba(0, 0, 0, 0)")
                            self.assertEqual(current.evaluate(
                                "element => getComputedStyle(element).getPropertyValue('--bs-nav-pills-link-active-bg').trim()"
                            ), "transparent")

                            submenu = page.locator("#hover-submenu").bounding_box()
                            page.mouse.move(submenu["x"] + submenu["width"] / 2, submenu["y"] + 2)
                            self._background(page, "#hover-parent", color)
                            self._background(page, "#hover-current", "rgba(0, 0, 0, 0)")
                            parent.hover()
                            self._background(page, "#hover-parent", color)
                            outside.hover()
                            self._background(page, "#hover-current", color)
                            self._background(page, "#hover-parent", "rgba(0, 0, 0, 0)")
                            expect(current).to_have_class("nav-link active")
                            expect(current).to_have_attribute("aria-current", "page")
                            page.keyboard.press("Escape")
                            expect(page.locator("#hover-submenu")).not_to_be_visible()
                            evidence.assert_clean()
                        finally:
                            page.close()

    def test_direct_disabled_and_nested_groups_keep_independent_current_states(self):
        for theme in ("light", "dark"):
            for direction in ("ltr", "rtl"):
                with self.subTest(theme=theme, direction=direction):
                    page, evidence = self._page(theme, direction)
                    try:
                        outside = page.locator("#hover-outside")
                        outside.hover()
                        current = page.locator("#hover-current")
                        color = self._active_color(page)
                        self._background(page, "#hover-current", color)
                        page.locator("#hover-direct-other").hover()
                        self._background(page, "#hover-direct-current", "rgba(0, 0, 0, 0)")
                        self._background(page, "#hover-current", color)
                        outside.hover()
                        self._background(page, "#hover-direct-current", color)
                        for selector in ("#hover-direct-disabled", "#hover-direct-disabled-button"):
                            disabled = page.locator(selector).bounding_box()
                            page.mouse.move(disabled["x"] + disabled["width"] / 2, disabled["y"] + disabled["height"] / 2)
                            self._background(page, "#hover-direct-current", color)
                            self._background(page, selector, "rgba(0, 0, 0, 0)")
                        for selector in ("#hover-disabled-item", "#hover-disabled-button-item"):
                            disabled = page.locator(selector).bounding_box()
                            page.mouse.move(disabled["x"] + disabled["width"] / 2, disabled["y"] + disabled["height"] / 2)
                            self._background(page, "#hover-current", color)
                            self._background(page, selector + " > .nav-link", "rgba(0, 0, 0, 0)")

                        page.locator("#hover-parent").click()
                        page.locator("#hover-nested-other").hover()
                        self._background(page, "#hover-nested-current", "rgba(0, 0, 0, 0)")
                        self._background(page, "#hover-current", "rgba(0, 0, 0, 0)")
                        self._background(page, "#hover-parent", color)
                        self._background(page, "#hover-direct-current", color)
                        page.locator("#hover-child").hover()
                        self._background(page, "#hover-nested-current", color)
                        self._background(page, "#hover-current", "rgba(0, 0, 0, 0)")
                        outside.hover()
                        self._background(page, "#hover-current", color)
                        evidence.assert_clean()
                    finally:
                        page.close()
