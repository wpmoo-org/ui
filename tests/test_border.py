from __future__ import annotations

from pathlib import Path

import build
import sass
from playwright.sync_api import sync_playwright

from tests.helpers import CatalogTestCase
from tests.helpers.browser_harness import (
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class BorderTests(CatalogTestCase):
    def test_utility_archive_has_canonical_metadata_and_registered_links(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        utilities = build.load_utilities()
        self.assertIn("border", {item["slug"] for item in utilities})
        archive = self.read_output("utils/index.html")
        self.assertIn('href="https://ui.wpmoo.org/utils/"', archive)
        for utility in utilities:
            with self.subTest(utility=utility["slug"]):
                self.assertIn(f'href="../utils/{utility["slug"]}/"', archive)
                self.assertTrue(
                    (build.SITE_DIST / "utils" / utility["slug"] / "index.html").is_file()
                )
        metadata = build.page_metadata(
            build.PAGES / "utils/index.html.jinja",
            Path("utils/index.html"),
            build.load_entries(build.SITE_REGISTRY, "sections.json"),
            build.load_catalog(),
            utilities,
            build.load_blocks(),
            build.load_layouts(),
        )
        self.assertEqual(metadata["slug"], "utilities")
        self.assertEqual(metadata["kind"], "doc")

    def test_utilities_menu_keeps_one_current_child_and_native_collapse(self) -> None:
        skip_if_browser_launch_is_sandboxed()
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        with serve_repository() as base_url, sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                page = browser.new_page(reduced_motion="reduce")
                for route in ("", "border/", "scroll-fade/"):
                    with self.subTest(route=route):
                        response = page.goto(f"{base_url}/site-dist/utils/{route}")
                        self.assertIsNotNone(response)
                        self.assertTrue(response.ok)
                        menu = page.locator("#shell-utilities-menu")
                        current = menu.locator('[aria-current="page"]')
                        self.assertEqual(current.count(), 1)
                        self.assertEqual(
                            current.get_attribute("href"),
                            "../../utils/" + route if route else "../utils/",
                        )
                        self.assertEqual(menu.locator("a").count(), 3)
                        if not route:
                            self.assertEqual(page.locator(".moo-doc-layout").count(), 1)
                            pagination = page.get_by_role("article").get_by_role(
                                "navigation", name="Docs pagination"
                            )
                            self.assertEqual(
                                [
                                    label.strip()
                                    for label in pagination.get_by_role("link").all_text_contents()
                                ],
                                ["Charts", "Border"],
                            )
                        trigger = page.get_by_role("button", name="Utilities", exact=True)
                        self.assertEqual(trigger.get_attribute("aria-expanded"), "true")
                        trigger.click()
                        menu.wait_for(state="hidden")
                        self.assertEqual(trigger.get_attribute("aria-expanded"), "false")
                        # Bootstrap ignores another toggle until Collapse settles.
                        page.locator("#shell-utilities-menu.collapsing").wait_for(state="detached")
                        trigger.press("Enter")
                        menu.wait_for(state="visible")
                        self.assertEqual(trigger.get_attribute("aria-expanded"), "true")
                command = page.locator("#catalog-command")
                self.assertEqual(command.locator('a[href="../../utils/"]').count(), 1)
            finally:
                browser.close()

    def test_dashed_cards_preserve_component_geometry_and_owner_scope(self) -> None:
        skip_if_browser_launch_is_sandboxed()
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        environment = build.create_environment()
        fixture = environment.from_string("""
          {% from "components/card.html.jinja" import card %}
          {% from "components/button.html.jinja" import button %}
          <div class="moo-ui" data-bs-theme="{{ theme }}" dir="{{ direction }}">
            {% for name, extra in [("normal", ""), ("dashed", " border-dashed")] %}
              <div id="{{ name }}">
                {% call card(size="sm", extra_class="p-0" ~ extra, body_class="p-0") %}
                  {{ button("Add item", variant="ghost", extra_class="w-100 p-3") }}
                {% endcall %}
              </div>
            {% endfor %}
          </div>
          {% for name, extra in [("outside-normal", ""), ("outside-dashed", " border-dashed")] %}
            <div id="{{ name }}">
              {% call card(size="sm", extra_class="p-0" ~ extra, body_class="p-0") %}
                {{ button("Add item", variant="ghost", extra_class="w-100 p-3") }}
              {% endcall %}
            </div>
          {% endfor %}
        """)
        bootstrap_css = sass.compile(
            filename=str(build.ROOT / "vendor/bootstrap/scss/bootstrap.scss"),
            output_style="expanded",
        )
        with serve_repository() as base_url, sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for recipe in ("full", "scoped"):
                    for case in CERTIFICATION_CASES:
                        with self.subTest(recipe=recipe, case=case.name):
                            context = new_case_context(browser, case)
                            try:
                                page = context.new_page()
                                css = (
                                    "site-dist/assets/css/moo-ui.css"
                                    if recipe == "full"
                                    else "site-dist/assets/css/moo.css"
                                )
                                links = f'<link rel="stylesheet" href="{base_url}/{css}">'
                                if recipe == "scoped":
                                    links = f"<style>{bootstrap_css}</style>" + links
                                page.set_content(
                                    "<!doctype html><html><head>" + links + "</head><body>"
                                    + fixture.render(theme=case.color_scheme, direction=case.direction)
                                    + "</body></html>",
                                    wait_until="load",
                                )
                                styles = page.evaluate("""() => {
                                  const read = (id) => {
                                    const card = document.querySelector(`#${id} .card`);
                                    const style = getComputedStyle(card);
                                    const rect = card.getBoundingClientRect();
                                    return {
                                      borderStyle: style.borderStyle,
                                      borderWidth: style.borderWidth,
                                      borderColor: style.borderColor,
                                      borderRadius: style.borderRadius,
                                      width: rect.width,
                                      height: rect.height,
                                    };
                                  };
                                  return {
                                    normal: read('normal'),
                                    dashed: read('dashed'),
                                    outsideNormal: read('outside-normal'),
                                    outsideDashed: read('outside-dashed'),
                                  };
                                }""")
                                self.assertEqual(styles["normal"].pop("borderStyle"), "solid")
                                self.assertEqual(styles["dashed"].pop("borderStyle"), "dashed")
                                self.assertEqual(styles["outsideNormal"], styles["outsideDashed"])
                                self.assertEqual(styles["normal"], styles["dashed"])
                            finally:
                                context.close()
            finally:
                browser.close()
