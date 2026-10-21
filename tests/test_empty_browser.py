from __future__ import annotations

import sass
from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase
from tests.helpers.browser_harness import (
    BrowserCase,
    BrowserEvidence,
    launch_certification_browser,
    new_case_context,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class EmptyBrowserTests(CatalogTestCase):
    def test_standard_surface_icon_and_utility_overrides(self):
        skip_if_browser_launch_is_sandboxed()
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        template = create_environment().from_string(
            '{% from "components/empty.html.jinja" import empty %}'
            '{% from "components/button.html.jinja" import button %}'
            '{% set icon %}{{ render_icon("folder", "inline-start") }}{% endset %}'
            '{% set action %}{{ button("Create item", variant="outline") }}{% endset %}'
            '{{ empty("No items yet", description="Create your first item to get started.", '
            'icon=icon, action=action) }}'
            '{{ empty("No matching results", description="Clear the filters to see all items.", '
            'icon=icon, action=action, '
            'extra_class="border-0 bg-body-tertiary text-start align-items-start p-0") }}'
        )
        markup = template.render()
        # Scoped Core is an extension over the host's native Bootstrap CSS.
        bootstrap_css = sass.compile(filename=str(ROOT / "vendor/bootstrap/scss/bootstrap.scss"))
        with serve_repository() as base_url, sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for stylesheet in ("moo-ui.css", "moo.css"):
                    for width, theme, direction in (
                        (1200, "light", "ltr"),
                        (1200, "dark", "ltr"),
                        (390, "light", "rtl"),
                        (390, "dark", "rtl"),
                    ):
                        with self.subTest(stylesheet=stylesheet, width=width, theme=theme):
                            case = BrowserCase(
                                "empty", {"width": width, "height": 844}, theme, direction,
                            )
                            context = new_case_context(browser, case)
                            try:
                                page = context.new_page()
                                evidence = BrowserEvidence(page)
                                page.set_content(
                                    '<html lang="en" dir="%s" data-bs-theme="%s"><head>'
                                    '<style>%s</style>'
                                    '<link rel="stylesheet" href="%s/dist/assets/css/%s">'
                                    '</head><body><main class="moo-ui" data-bs-theme="%s" '
                                    'dir="%s">%s</main></body></html>'
                                    % (
                                        direction, theme, bootstrap_css if stylesheet == "moo.css" else "",
                                        base_url, stylesheet, theme, direction, markup,
                                    ),
                                    wait_until="networkidle",
                                )
                                standard = page.locator(".empty-state").nth(0)
                                customized = page.locator(".empty-state").nth(1)
                                expect(standard).to_have_css("border-style", "dashed")
                                expect(standard).to_have_css("direction", direction)
                                expect(standard).to_have_css("align-items", "center")
                                icon = standard.locator(".empty-state-icon > svg")
                                expect(icon).to_have_attribute("aria-hidden", "true")
                                # Icon dimensions and surface padding share the
                                # configured Bootstrap spacing scale.
                                spacing = standard.evaluate(
                                    "el => parseFloat(getComputedStyle(el).paddingTop)",
                                )
                                self.assertGreater(spacing, 0)
                                geometry = icon.bounding_box()
                                self.assertAlmostEqual(geometry["width"], spacing, delta=1)
                                self.assertAlmostEqual(geometry["height"], geometry["width"], delta=1)
                                expect(customized).to_have_css("border-style", "none")
                                expect(customized).to_have_css("padding-top", "0px")
                                expect(customized).to_have_css("align-items", "flex-start")
                                # The shared logical utility follows the owner in
                                # both distributions, including RTL embedded hosts.
                                expect(customized).to_have_css("text-align", "start")
                                alignment = customized.evaluate("""el => {
                                    const header=el.querySelector('.empty-state-header');
                                    const heading=header.querySelector('h3');
                                    const range=document.createRange();
                                    range.selectNodeContents(heading);
                                    const text=range.getBoundingClientRect(),bounds=header.getBoundingClientRect();
                                    const left=text.left-bounds.left,right=bounds.right-text.right;
                                    return getComputedStyle(el).direction==='rtl'
                                        ? {start:right,end:left} : {start:left,end:right};
                                }""")
                                self.assertLess(alignment["start"], alignment["end"])
                                expect(customized.locator(".empty-state-header")).to_have_css(
                                    "align-items", "flex-start",
                                )
                                self.assertLessEqual(
                                    page.evaluate("document.documentElement.scrollWidth"), width,
                                )
                                page.keyboard.press("Tab")
                                expect(standard.get_by_role("button", name="Create item")).to_be_focused()
                                evidence.assert_clean()
                            finally:
                                context.close()
            finally:
                browser.close()
