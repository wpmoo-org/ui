import json
import re
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class AccordionPanelsBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.manager = sync_playwright()
        cls.playwright = cls.manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.manager.__exit__(None, None, None)
        cls.server.__exit__(None, None, None)

    def _page(self, width, theme, direction="ltr", catalog=False):
        page = self.browser.new_page(viewport={"width": width, "height": 900})
        evidence = BrowserEvidence(page)
        page.add_init_script("localStorage.setItem('moo:theme', " + json.dumps(theme) + ");")
        slug = "accordion-panels-rtl" if direction == "rtl" else "accordion-panels"
        route = "blocks/accordion-panels/" if catalog else f"blocks/previews/{slug}/"
        response = page.goto(f"{self.base_url}/site-dist/{route}", wait_until="networkidle")
        self.assertTrue(response.ok)
        expect(page.locator(".moo-ui").first).to_have_attribute("data-bs-theme", theme)
        return page, evidence

    def test_accepted_surface_borders_wrapping_and_containment(self):
        for width in (1440, 390):
            for theme in ("light", "dark"):
                for direction in ("ltr", "rtl"):
                    with self.subTest(width=width, theme=theme, direction=direction):
                        page, evidence = self._page(width, theme, direction)
                        try:
                            result = page.evaluate("""() => {
                              const items = [...document.querySelectorAll('.accordion-item')];
                              const probe = document.createElement('span');
                              probe.style.backgroundColor = 'rgb(from var(--bs-secondary-bg) r g b / 1)';
                              items[0].append(probe);
                              const surface = getComputedStyle(probe).backgroundColor;
                              probe.remove();
                              return {
                                overflow: document.documentElement.scrollWidth > innerWidth + 1,
                                items: items.map((item, index) => {
                                  const style = getComputedStyle(item), rect = item.getBoundingClientRect();
                                  const button = item.querySelector('.accordion-button');
                                  const title = button.querySelector('span').getBoundingClientRect();
                                  const icon = button.querySelector('svg').getBoundingClientRect();
                                  const rtl = getComputedStyle(button).direction === 'rtl';
                                  return {
                                    borders: ['Top', 'Right', 'Bottom', 'Left'].every(side =>
                                      parseFloat(style['border' + side + 'Width']) > 0 &&
                                      style['border' + side + 'Style'] === 'solid'),
                                    separate: index === 0 || rect.top > items[index - 1].getBoundingClientRect().bottom,
                                    contained: rect.left >= 0 && rect.right <= innerWidth + 1,
                                    clear: rtl ? title.left >= icon.right + 2 : title.right <= icon.left - 2,
                                    surface: getComputedStyle(button).backgroundColor === surface
                                  };
                                })
                              };
                            }""")
                            self.assertFalse(result["overflow"])
                            self.assertEqual(len(result["items"]), 4)
                            for item in result["items"]:
                                self.assertTrue(all(item.values()), item)
                            page.locator(".accordion-button").first.hover()
                            expect(page.locator(".accordion-button").first).to_have_css("text-decoration-line", "none")
                            evidence.assert_clean()
                        finally:
                            page.close()

    def test_native_indicator_keyboard_and_single_multiple_modes(self):
        for multiple in (True, False):
            with self.subTest(multiple=multiple):
                page, evidence = self._page(1440, "light", catalog=True)
                try:
                    group = page.locator("#panels-multiple" if multiple else "#panels-single")
                    plan = group.locator(".accordion-button").nth(0)
                    create = group.locator(".accordion-button").nth(1)
                    review = group.locator(".accordion-button").nth(2)
                    disabled = group.locator(".accordion-button").nth(3)
                    expect(disabled).to_be_disabled()
                    expect(review).to_have_attribute("aria-expanded", "true")
                    expect(review.locator("[data-accordion-plus]")).to_have_css("display", "none")
                    expect(plan.locator("[data-accordion-plus]")).not_to_have_css("display", "none")
                    plan.focus()
                    plan.press("Enter")
                    expect(plan).to_have_attribute("aria-expanded", "true")
                    expect(page.locator("#" + plan.get_attribute("aria-controls"))).not_to_have_class(re.compile(r"\bcollapsing\b"))
                    expect(plan.locator("[data-accordion-plus]")).to_have_css("display", "none")
                    create.click()
                    expect(create).to_have_attribute("aria-expanded", "true")
                    expect(page.locator("#" + create.get_attribute("aria-controls"))).not_to_have_class(re.compile(r"\bcollapsing\b"))
                    expect(plan).to_have_attribute("aria-expanded", str(multiple).lower())
                    expect(review).to_have_attribute("aria-expanded", str(multiple).lower())
                    create.press("Space")
                    expect(create).to_have_attribute("aria-expanded", "false")
                    expect(create.locator("[data-accordion-plus]")).not_to_have_css("display", "none")
                    evidence.assert_clean()
                finally:
                    page.close()
