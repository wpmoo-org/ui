from __future__ import annotations

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import CatalogTestCase
from tests.helpers.browser_harness import (
    BrowserCase,
    launch_certification_browser,
    new_case_context,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class TabsHeightBrowserTests(CatalogTestCase):
    def test_content_height_tracks_active_panel_and_default_stays_stable(self):
        skip_if_browser_launch_is_sandboxed()
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        template = create_environment().from_string(
            '{% from "components/tabs.html.jinja" import tabs %}'
            '{{ tabs("height-tabs", items, height=height, orientation=orientation) }}'
        )
        items = [
            {'id': 'short', 'title': 'Short', 'content': '<p>Short content</p>'},
            {'id': 'long', 'title': 'Long', 'content': '<p>Long content</p>' * 12},
        ]
        with serve_repository() as base_url, sync_playwright() as playwright:
            response = playwright.request.new_context()
            try:
                self.assertTrue(response.get(f"{base_url}/dist/assets/css/moo-ui.css").ok)
            finally:
                response.dispose()
            browser = launch_certification_browser(playwright)
            try:
                for width, theme, direction, orientation in (
                    (1200, 'light', 'ltr', 'horizontal'),
                    (390, 'dark', 'rtl', 'vertical'),
                ):
                    case = BrowserCase('tabs-height', {'width': width, 'height': 844}, theme, direction)
                    for height in ('content', 'stable'):
                        with self.subTest(width=width, height=height):
                            context = new_case_context(browser, case)
                            try:
                                page = context.new_page()
                                markup = template.render(items=items, height=height, orientation=orientation)
                                page.set_content(
                                    f'<html dir="{direction}" data-bs-theme="{theme}"><head>'
                                    f'<link rel="stylesheet" href="{base_url}/dist/assets/css/moo-ui.css">'
                                    f'</head><body><div class="moo-ui">{markup}</div>'
                                    f'<script src="{base_url}/vendor/bootstrap/dist/js/bootstrap.bundle.min.js">'
                                    '</script></body></html>',
                                    wait_until='networkidle',
                                )
                                short = page.locator('#height-tabs-short-pane')
                                long = page.locator('#height-tabs-long-pane')
                                content = page.locator('#height-tabs-content')
                                initial = content.bounding_box()['height']
                                page.get_by_role('tab', name='Long', exact=True).click()
                                expect(page.get_by_role('tab', name='Long', exact=True)).to_have_attribute('aria-selected', 'true')
                                expect(long).to_be_visible()
                                expanded = content.bounding_box()['height']
                                if height == 'content':
                                    self.assertGreater(expanded, initial + 100)
                                    self.assertAlmostEqual(expanded, long.bounding_box()['height'], delta=1)
                                    self.assertEqual(short.evaluate('(el) => el.getBoundingClientRect().height'), 0)
                                else:
                                    self.assertAlmostEqual(expanded, initial, delta=1)
                                page.get_by_role('tab', name='Short', exact=True).click()
                                expect(short).to_be_visible()
                                self.assertAlmostEqual(content.bounding_box()['height'], initial, delta=1)
                            finally:
                                context.close()
            finally:
                browser.close()
