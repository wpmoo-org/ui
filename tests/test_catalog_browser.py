from __future__ import annotations

from dataclasses import replace
import json
import time
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


HOME_PAGE_PATH = "/site-dist/index.html"


def load_home_page(page, base_url: str):
    response = page.goto(f"{base_url}{HOME_PAGE_PATH}", wait_until="domcontentloaded")
    expect(page.get_by_role("button", name="Search documentation")).to_be_visible()
    return response


class CatalogBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.addClassCleanup(cls.playwright_manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def test_external_state_restores_the_first_content_frame_and_sidebar_reload(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                expected = {
                    "theme": case.color_scheme,
                    "direction": case.direction,
                    "sidebar": "collapsed",
                    "builder": {
                        "baseColor": "mist",
                        "themeColor": "blue",
                        "chartColor": "azure",
                        "headingFont": "system",
                        "bodyFont": "geist",
                        "radius": "small",
                    },
                }
                context.add_init_script(
                    """
                    (() => {
                      const expected = """ + json.dumps(expected) + """;
                      if (!localStorage.getItem('moo:theme')) {
                        localStorage.setItem('moo:theme', expected.theme);
                      }
                      if (!localStorage.getItem('moo:direction')) {
                        localStorage.setItem('moo:direction', expected.direction);
                      }
                      if (!localStorage.getItem('moo-sidebar:catalog-shell')) {
                        localStorage.setItem('moo-sidebar:catalog-shell', expected.sidebar);
                      }
                      if (!localStorage.getItem('moo:theme-builder')) {
                        localStorage.setItem('moo:theme-builder', JSON.stringify(expected.builder));
                      }
                      const sample = () => {
                        const owner = document.querySelector('.moo-ui[data-moo-document-owner]');
                        const wrapper = document.querySelector('[data-sidebar-key="catalog-shell"]');
                        const heading = document.querySelector('main h1');
                        if (!heading?.getBoundingClientRect().height || !owner || !wrapper) {
                          requestAnimationFrame(sample);
                          return;
                        }
                        window.__catalogFirstContentFrame = {
                          theme: owner.dataset.bsTheme,
                          direction: document.documentElement.dir,
                          sidebar: wrapper.dataset.sidebarState,
                          ownerReady: owner.dataset.mooState === 'ready',
                          sidebarReady: wrapper.hasAttribute('data-sidebar-state-ready'),
                          builder: Object.fromEntries(Object.keys(expected.builder).map(key => [
                            key,
                            owner.dataset[`mooCatalogThemeBuilder${key[0].toUpperCase()}${key.slice(1)}`],
                          ])),
                        };
                      };
                      requestAnimationFrame(sample);
                    })();
                    """
                )
                try:
                    page = context.new_page()
                    evidence = BrowserEvidence(page)
                    state_requests = []

                    def delay_state(route) -> None:
                        state_requests.append(route.request.url)
                        # A slow cold fetch must not reveal unrestored content.
                        time.sleep(0.15)
                        route.continue_()

                    page.route("**/assets/js/state.js?*", delay_state)
                    page.route("**/assets/js/catalog-theme-state.js?*", delay_state)
                    response = page.goto(
                        f"{self.base_url}/site-dist/components/alert/",
                        wait_until="load",
                    )
                    self.assertIsNotNone(response)
                    self.assertTrue(response.ok)
                    expect(page.get_by_role("heading", name="Alert", level=1)).to_be_visible()
                    page.wait_for_function("window.__catalogFirstContentFrame")
                    first_frame = page.evaluate("window.__catalogFirstContentFrame")
                    self.assertEqual(first_frame, {
                        **expected,
                        "ownerReady": True,
                        "sidebarReady": True,
                    })
                    self.assertTrue(state_requests)
                    self.assertEqual(len(set(state_requests)), 2)
                    self.assertEqual(
                        {url.split("?", 1)[0].rsplit("/", 1)[-1] for url in state_requests},
                        {"state.js", "catalog-theme-state.js"},
                    )

                    if not case.is_mobile:
                        page.get_by_role("button", name="Toggle sidebar").first.click()
                        expect(page.locator('[data-sidebar-key="catalog-shell"]')).to_have_attribute(
                            "data-sidebar-state", "expanded",
                        )
                        page.reload(wait_until="load")
                        page.wait_for_function("window.__catalogFirstContentFrame")
                        self.assertEqual(
                            page.evaluate("window.__catalogFirstContentFrame.sidebar"),
                            "expanded",
                        )
                    changed_theme = "dark" if case.color_scheme == "light" else "light"
                    page.locator("[data-moo-theme]").click()
                    expect(page.locator(".moo-ui[data-moo-document-owner]")).to_have_attribute(
                        "data-bs-theme", changed_theme,
                    )
                    page.goto(f"{self.base_url}/site-dist/components/button/", wait_until="load")
                    expect(page.get_by_role("heading", name="Button", level=1)).to_be_visible()
                    expect(page.locator(".moo-ui[data-moo-document-owner]")).to_have_attribute(
                        "data-bs-theme", changed_theme,
                    )
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_command_palette_keyboard_navigation_keeps_active_item_clear_of_scroll_edges(
        self,
    ) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            response = load_home_page(page, self.base_url)
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            page.get_by_role("button", name="Search documentation").click()
            search = page.locator("#catalog-command input[type='search']")
            expect(search).to_have_attribute(
                "aria-activedescendant",
                "catalog-command-item-0",
            )

            for _ in range(8):
                search.press("ArrowDown")

            active_state = page.evaluate(
                """
                () => {
                  const body = document.querySelector(
                    "#catalog-command.show .moo-catalog__command-body"
                  );
                  const active = document.querySelector(
                    "#catalog-command.show [data-moo-command-item].active"
                  );
                  const bodyRect = body.getBoundingClientRect();
                  const activeRect = active.getBoundingClientRect();
                  const previous = active.previousElementSibling;
                  const previousRect = previous?.getBoundingClientRect();
                  return {
                    activeId: active.id,
                    activeText: active.textContent.trim(),
                    bottomGap: bodyRect.bottom - activeRect.bottom,
                    gapFromPrevious: previousRect ? activeRect.top - previousRect.bottom : null,
                    marginTop: getComputedStyle(active).marginTop,
                    scrollTop: body.scrollTop,
                  };
                }
                """
            )

            self.assertTrue(active_state["activeText"])
            self.assertTrue(
                active_state["activeId"].startswith("catalog-command-item-"),
                active_state,
            )
            self.assertGreaterEqual(active_state["bottomGap"], 8)
            self.assertEqual(active_state["marginTop"], "2px")
            self.assertGreaterEqual(active_state["gapFromPrevious"], 2)
            self.assertGreater(active_state["scrollTop"], 0)
            evidence.assert_clean()
        finally:
            context.close()

    def test_command_palette_preserves_its_theme_ring_and_regular_modal_elevation(self) -> None:
        for reference_case in CERTIFICATION_CASES:
            for theme in ("light", "dark"):
                case = replace(reference_case, color_scheme=theme)
                with self.subTest(viewport=case.name, theme=theme):
                    context = new_case_context(self.browser, case)
                    try:
                        page = context.new_page()
                        evidence = BrowserEvidence(page)
                        response = load_home_page(page, self.base_url)
                        self.assertIsNotNone(response)
                        self.assertTrue(response.ok)
                        prepare_page(page, case)

                        page.get_by_role("button", name="Search documentation").click()
                        search = page.locator("#catalog-command input[type='search']")
                        expect(search).to_be_focused()
                        surface = page.evaluate(
                            """
                            () => {
                              const content = document.querySelector(
                                '#catalog-command.show .modal-content'
                              );
                              const owner = content.closest('.moo-ui');
                              const probe = document.createElement('div');
                              probe.className = 'modal-content';
                              probe.style.color = 'var(--moo-border)';
                              owner.append(probe);
                              const ringColor = getComputedStyle(probe).color;
                              const regularShadow = getComputedStyle(probe).boxShadow;
                              probe.style.boxShadow = 'var(--bs-box-shadow-lg)';
                              const expectedRegularShadow = getComputedStyle(probe).boxShadow;
                              probe.remove();
                              const rect = content.getBoundingClientRect();
                              return {
                                shadow: getComputedStyle(content).boxShadow,
                                ringColor, regularShadow, expectedRegularShadow,
                                left: rect.left, right: rect.right, viewport: innerWidth,
                                top: rect.top, bottom: rect.bottom, viewportHeight: innerHeight,
                              };
                            }
                            """
                        )
                        self.assertTrue(
                            surface["shadow"].startswith(
                                f'{surface["ringColor"]} 0px 0px 0px 4px,'
                            ),
                            surface,
                        )
                        self.assertEqual(
                            surface["regularShadow"], surface["expectedRegularShadow"],
                        )
                        self.assertGreaterEqual(surface["left"], 4)
                        self.assertLessEqual(surface["right"], surface["viewport"] - 4)
                        self.assertGreaterEqual(surface["top"], 4)
                        self.assertLessEqual(surface["bottom"], surface["viewportHeight"] - 4)
                        search.press("Escape")
                        expect(page.locator("#catalog-command")).not_to_be_visible()
                        evidence.assert_clean()
                    finally:
                        context.close()

    def test_command_palette_body_omits_search_divider(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            response = load_home_page(page, self.base_url)
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            page.get_by_role("button", name="Search documentation").click()
            search = page.locator("#catalog-command input[type='search']")
            expect(search).to_have_attribute(
                "aria-activedescendant",
                "catalog-command-item-0",
            )

            palette_state = page.evaluate(
                """
                () => {
                  const modal = document.querySelector("#catalog-command.show");
                  const body = modal.querySelector(".moo-catalog__command-body");
                  const bodyStyle = getComputedStyle(body);
                  return {
                    bodyBorderTopWidth: bodyStyle.borderTopWidth,
                  };
                }
                """
            )

            self.assertEqual(palette_state["bodyBorderTopWidth"], "0px")
            evidence.assert_clean()
        finally:
            context.close()

    def test_primary_doc_toc_links_keep_minimum_touch_targets(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}/site-dist/installation/",
                wait_until="domcontentloaded",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])
            expect(page.get_by_role("heading", name="Installation", level=1)).to_be_visible()
            expect(page.locator(".moo-doc-toc")).to_be_visible()

            toc_link_sizes = page.locator(".moo-doc-toc .nav-link").evaluate_all(
                """
                links => links.map((link) => {
                  const rect = link.getBoundingClientRect();
                  return {
                    text: link.textContent.trim(),
                    width: rect.width,
                    height: rect.height,
                  };
                })
                """
            )

            self.assertGreaterEqual(len(toc_link_sizes), 4)
            for link in toc_link_sizes:
                with self.subTest(link=link["text"]):
                    self.assertGreaterEqual(link["width"], 24, link)
                    self.assertGreaterEqual(link["height"], 24, link)

            evidence.assert_clean()
        finally:
            context.close()

    def test_catalog_uses_shared_toc_tracking_for_docs_and_component_examples(self) -> None:
        for path in ("installation/", "components/accordion/"):
            with self.subTest(path=path):
                context = new_case_context(self.browser, CERTIFICATION_CASES[0])
                try:
                    page = context.new_page()
                    page.set_viewport_size({"width": 1440, "height": 900})
                    evidence = BrowserEvidence(page)
                    page.goto(f"{self.base_url}/site-dist/{path}")
                    prepare_page(page, CERTIFICATION_CASES[0])
                    toc = page.locator(".moo-doc-toc [data-toc]")
                    expect(toc).to_have_count(1)
                    links = toc.locator("a")
                    hrefs = links.evaluate_all("links => links.map(link => link.getAttribute('href'))")
                    self.assertGreater(len(hrefs), 2)
                    self.assertEqual(len(hrefs), len(set(hrefs)))
                    link = links.nth(1)
                    href = link.get_attribute("href")
                    link.click()
                    expect(page).to_have_url(f"{self.base_url}/site-dist/{path}{href}")
                    expect(link).to_have_attribute("aria-current", "location")
                    expect(toc).to_have_attribute("data-toc-marker", "")
                    marker_height = toc.evaluate("el => parseFloat(getComputedStyle(el, '::after').height)")
                    text_height = link.locator("span").evaluate("el => el.offsetHeight")
                    self.assertAlmostEqual(marker_height, text_height, delta=1)
                    page.locator("#main-content").evaluate("el => { el.scrollTop = el.scrollHeight; }")
                    expect(links.last).to_have_attribute("aria-current", "location")
                    self.assertEqual(page.evaluate("window.scrollY"), 0)
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_form_preview_field_wrappers_center_token_width_controls(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)

            for path, heading, preview_selector, control_selector in (
                (
                    "/site-dist/components/combobox/",
                    "Combobox",
                    ".moo-example__preview--narrow",
                    ".combobox",
                ),
                (
                    "/site-dist/components/datepicker/",
                    "Date Picker",
                    ".moo-example__preview--medium",
                    ".moo-datepicker",
                ),
            ):
                with self.subTest(path=path):
                    response = page.goto(
                        f"{self.base_url}{path}",
                        wait_until="domcontentloaded",
                    )
                    self.assertIsNotNone(response)
                    self.assertTrue(response.ok)
                    prepare_page(page, CERTIFICATION_CASES[0])
                    expect(page.get_by_role("heading", name=heading, level=1)).to_be_visible()

                    alignment = page.evaluate(
                        """
                        ([previewSelector, controlSelector]) => {
                          const preview = document.querySelector(
                            `.moo-component-examples > .moo-example__surface ${previewSelector}`
                          );
                          const control = preview?.querySelector(controlSelector);
                          if (!preview || !control) {
                            return null;
                          }
                          const previewRect = preview.getBoundingClientRect();
                          const controlRect = control.getBoundingClientRect();
                          const previewCenter = previewRect.left + previewRect.width / 2;
                          const controlCenter = controlRect.left + controlRect.width / 2;
                          return {
                            controlCenter,
                            controlWidth: controlRect.width,
                            delta: Math.abs(controlCenter - previewCenter),
                            previewCenter,
                            previewWidth: previewRect.width,
                          };
                        }
                        """,
                        [preview_selector, control_selector],
                    )

                    self.assertIsNotNone(alignment)
                    assert alignment is not None
                    self.assertGreater(alignment["controlWidth"], 0, alignment)
                    self.assertLessEqual(alignment["delta"], 1, alignment)

            evidence.assert_clean()
        finally:
            context.close()

    def test_sidebar_rail_hover_does_not_paint_over_identity_dropdown(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}/site-dist/blocks/previews/sidebar-floating/index.html",
                wait_until="domcontentloaded",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            trigger = page.locator(
                '[data-slot="sidebar-header"] .sidebar-menu-button--workspace'
            )
            menu = page.locator(
                '[data-slot="sidebar-header"] .dropdown-menu.show'
            )
            rail = page.locator("[data-sidebar-rail]")
            trigger.click()
            expect(menu).to_be_visible()

            rail.hover(force=True)
            rail_state = page.evaluate(
                """
                () => {
                  const menu = document.querySelector(
                    '[data-slot="sidebar-header"] .dropdown-menu.show'
                  );
                  const rail = document.querySelector('[data-sidebar-rail]');
                  const menuRect = menu.getBoundingClientRect();
                  const railRect = rail.getBoundingClientRect();
                  const point = {
                    x: railRect.left + railRect.width / 2,
                    y: menuRect.top + menuRect.height / 2,
                  };
                  const hit = document.elementFromPoint(point.x, point.y);
                  return {
                    railHovered: rail.matches(':hover'),
                    railLineInsideMenu: point.x > menuRect.left &&
                      point.x < menuRect.right &&
                      point.y > menuRect.top &&
                      point.y < menuRect.bottom,
                    topmostMenu: Boolean(hit?.closest(
                      '[data-slot="sidebar-header"] .dropdown-menu.show'
                    )),
                  };
                }
                """
            )

            self.assertTrue(rail_state["railHovered"], rail_state)
            self.assertTrue(rail_state["railLineInsideMenu"], rail_state)
            self.assertTrue(rail_state["topmostMenu"], rail_state)
            evidence.assert_clean()
        finally:
            context.close()

    def test_layout_page_starts_with_the_app_example_at_desktop_and_mobile(self) -> None:
        for viewport in ((1280, 900), (390, 844)):
            with self.subTest(viewport=viewport):
                context = new_case_context(self.browser, CERTIFICATION_CASES[0])
                try:
                    page = context.new_page()
                    evidence = BrowserEvidence(page)
                    failed_responses: list[str] = []
                    page.on(
                        "response",
                        lambda response: failed_responses.append(
                            f"{response.status} {response.url}"
                        )
                        if response.status >= 400
                        else None,
                    )
                    page.set_viewport_size(
                        {"width": viewport[0], "height": viewport[1]}
                    )
                    response = page.goto(
                        f"{self.base_url}/site-dist/layout/",
                        wait_until="domcontentloaded",
                    )
                    self.assertIsNotNone(response)
                    self.assertTrue(response.ok)
                    prepare_page(page, CERTIFICATION_CASES[0])
                    expect(
                        page.get_by_role("heading", name="Layout", level=1)
                    ).to_be_visible()
                    self.assertLessEqual(
                        page.evaluate("document.documentElement.scrollWidth"),
                        page.evaluate("document.documentElement.clientWidth"),
                    )
                    app_example = page.locator('[data-example="layout-app-example"]')
                    expect(app_example).to_have_count(1)
                    expect(app_example.locator(".moo-example__preview")).to_be_visible()
                    expect(app_example.locator(".moo-example__source")).to_have_count(1)
                    layout_examples = page.locator('[data-example^="layout-"]')
                    self.assertGreaterEqual(layout_examples.count(), 1)
                    self.assertEqual(
                        layout_examples.first.get_attribute("data-example"),
                        "layout-app-example",
                    )
                    expect(page.locator('.moo-doc-toc')).to_have_count(1)
                    section_widths = page.locator(".moo-doc-page > section").evaluate_all(
                        "sections => sections.map(section => section.getBoundingClientRect().width)"
                    )
                    self.assertTrue(section_widths)
                    self.assertLessEqual(
                        max(section_widths) - min(section_widths),
                        1,
                        section_widths,
                    )
                    app_source = app_example.locator(
                        ".moo-example__source"
                    ).text_content() or ""
                    for hook in (
                        'data-slot="sidebar-wrapper"',
                        'data-sidebar-key="app-shell"',
                        'data-slot="sidebar"',
                        'data-variant="floating"',
                        'class="sidebar-inner"',
                        'data-slot="page"',
                        'id="main-content"',
                    ):
                        with self.subTest(viewport=viewport, hook=hook):
                            self.assertIn(hook, app_source)
                    self.assertEqual(failed_responses, [])
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_doc_toc_hash_scrolls_catalog_main_below_header_without_window_reset(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1280, "height": 900})
            evidence = BrowserEvidence(page)
            response = page.goto(
                f"{self.base_url}/site-dist/layout/#grid",
                wait_until="domcontentloaded",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])
            expect(
                page.get_by_role("heading", name="Grid", level=2, exact=True)
            ).to_be_visible()
            page.wait_for_timeout(100)

            scroll_state = page.evaluate(
                """
                () => {
                  const pageRoot = document.querySelector('[data-slot="page"]');
                  const main = document.querySelector('#main-content');
                  const header = pageRoot?.querySelector(':scope > header');
                  const target = document.getElementById('grid');
                  return {
                    headerBottom: header?.getBoundingClientRect().bottom ?? null,
                    windowScrollY: window.scrollY,
                    pageScrollTop: pageRoot?.scrollTop ?? null,
                    mainScrollTop: main?.scrollTop ?? null,
                    targetTop: target?.getBoundingClientRect().top ?? null,
                    pageOverflowY: pageRoot ? getComputedStyle(pageRoot).overflowY : null,
                    mainOverflowY: main ? getComputedStyle(main).overflowY : null,
                  };
                }
                """
            )

            self.assertEqual(scroll_state["windowScrollY"], 0, scroll_state)
            self.assertEqual(scroll_state["pageScrollTop"], 0, scroll_state)
            self.assertGreater(scroll_state["mainScrollTop"], 0, scroll_state)
            self.assertEqual(scroll_state["pageOverflowY"], "visible", scroll_state)
            self.assertEqual(scroll_state["mainOverflowY"], "auto", scroll_state)
            self.assertLessEqual(
                abs(scroll_state["targetTop"] - scroll_state["headerBottom"]),
                2,
                scroll_state,
            )
            evidence.assert_clean()
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
