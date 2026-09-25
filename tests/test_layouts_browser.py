from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserCase,
    BrowserEvidence,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


LAYOUT_CASES = (
    BrowserCase(
        name="desktop-light-ltr",
        viewport={"width": 1040, "height": 844},
        color_scheme="light",
        direction="ltr",
    ),
    BrowserCase(
        name="desktop-dark-rtl",
        viewport={"width": 1040, "height": 844},
        color_scheme="dark",
        direction="rtl",
    ),
    BrowserCase(
        name="mobile-dark-rtl",
        viewport={"width": 390, "height": 844},
        color_scheme="dark",
        direction="rtl",
        is_mobile=True,
        has_touch=True,
    ),
)


ROOT = Path(__file__).resolve().parents[1]


class LayoutBrowserTests(unittest.TestCase):
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

    def _open(
        self,
        fixture: str,
        case: BrowserCase,
        query: str = "",
        init_script: str | None = None,
    ):
        context = new_case_context(self.browser, case)
        if init_script:
            context.add_init_script(init_script)
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
        evidence.failed_responses = failed_responses
        response = page.goto(
            f"{self.base_url}/site-dist/tests/fixtures/certification/{fixture}.html{query}",
            wait_until="networkidle",
        )
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, case)
        return context, page, evidence

    def test_document_owner_prepaint_applies_stored_theme_before_external_asset(self) -> None:
        def open_catalog(*, theme: str, direction: str):
            context = new_case_context(self.browser, LAYOUT_CASES[0])
            context.add_init_script(
                "\n".join(
                    (
                        f"localStorage.setItem('moo:theme', {json.dumps(theme)});",
                        f"localStorage.setItem('moo:direction', {json.dumps(direction)});",
                    )
                )
            )
            page = context.new_page()
            evidence = BrowserEvidence(page)
            prepaint_requests: list[str] = []
            page.on(
                "request",
                lambda request: prepaint_requests.append(request.url)
                if re.search(r"/assets/js/theme-prepaint\.js(?:\?.*)?$", request.url)
                else None,
            )
            response = page.goto(
                f"{self.base_url}/site-dist/introduction/index.html",
                wait_until="networkidle",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            return context, page, evidence, prepaint_requests

        context, page, evidence, prepaint_requests = open_catalog(
            theme="dark", direction="rtl"
        )
        try:
            self.assertEqual(prepaint_requests, [])

            surface = page.evaluate(
                """
                () => {
                  const owner = document.body.firstElementChild;
                  const rect = owner.getBoundingClientRect();
                  const points = [
                    [1, 1],
                    [window.innerWidth - 2, 1],
                    [1, window.innerHeight - 2],
                    [window.innerWidth - 2, window.innerHeight - 2],
                  ];
                  return {
                    bodyTheme: document.body.getAttribute("data-bs-theme"),
                    htmlLang: document.documentElement.lang,
                    htmlTheme: document.documentElement.getAttribute("data-bs-theme"),
                    htmlDirection: document.documentElement.dir,
                    ownerTheme: owner.getAttribute("data-bs-theme"),
                    prepaint: owner.dataset.mooPrepaint,
                    coversViewport: rect.width >= window.innerWidth && rect.height >= window.innerHeight,
                    noBodyStrip: points.every(([x, y]) => owner.contains(document.elementFromPoint(x, y))),
                  };
                }
                """
            )
            self.assertEqual(surface["htmlLang"], "en")
            self.assertEqual(surface["htmlDirection"], "rtl")
            self.assertIsNone(surface["htmlTheme"])
            self.assertIsNone(surface["bodyTheme"])
            self.assertEqual(surface["ownerTheme"], "dark")
            self.assertEqual(surface["prepaint"], "ready")
            self.assertTrue(surface["coversViewport"])
            self.assertTrue(surface["noBodyStrip"])
            evidence.assert_clean()
        finally:
            context.close()

        context, page, evidence, prepaint_requests = open_catalog(
            theme="not-a-theme", direction="sideways"
        )
        try:
            self.assertEqual(prepaint_requests, [])
            surface = page.evaluate(
                """
                () => ({
                  direction: document.documentElement.dir,
                  ownerTheme: document.body.firstElementChild?.getAttribute("data-bs-theme"),
                  prepaint: document.body.firstElementChild?.dataset.mooPrepaint,
                })
                """
            )
            self.assertEqual(surface["direction"], "ltr")
            self.assertEqual(surface["ownerTheme"], "light")
            self.assertEqual(surface["prepaint"], "ready")
            evidence.assert_clean()
        finally:
            context.close()

    def test_catalog_builder_tokens_exist_before_deferred_catalog_runtime(self) -> None:
        context = new_case_context(self.browser, LAYOUT_CASES[0])
        context.add_init_script(
            "\n".join(
                (
                    "localStorage.setItem('moo:theme', 'dark');",
                    "localStorage.setItem('moo:theme-builder', JSON.stringify({",
                    "  schemaVersion: 1,",
                    "  baseColor: 'mist',",
                    "  themeColor: 'blue',",
                    "  chartColor: 'neutral',",
                    "  headingFont: 'default',",
                    "  bodyFont: 'default',",
                    "  radius: 'default',",
                    "}));",
                )
            )
        )
        catalog_prepaint_source = (
            ROOT / "site/static/js/catalog-prepaint.js"
        ).read_text(encoding="utf-8")

        def capture_builder_tokens(route) -> None:
            route.fulfill(
                status=200,
                content_type="application/javascript",
                body="""
                window.__catalogBuilderBeforeRuntime = (() => {
                  const owner = document.querySelector('.moo-ui[data-bs-theme]');
                  const tokens = owner ? getComputedStyle(owner) : null;
                  return {
                    baseColor: owner?.dataset.mooCatalogThemeBuilderBaseColor,
                    themeColor: owner?.dataset.mooCatalogThemeBuilderThemeColor,
                    primary: tokens?.getPropertyValue("--bs-primary").trim(),
                    surface: tokens?.getPropertyValue("--moo-surface").trim(),
                  };
                })();
                """
                + catalog_prepaint_source,
            )

        context.route(
            re.compile(r".*/assets/js/catalog-prepaint\.js(?:\?.*)?$"),
            capture_builder_tokens,
        )
        page = context.new_page()
        evidence = BrowserEvidence(page)
        try:
            response = page.goto(
                f"{self.base_url}/site-dist/introduction/index.html",
                wait_until="networkidle",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            builder_before_runtime = page.evaluate(
                "() => window.__catalogBuilderBeforeRuntime"
            )
            self.assertEqual(builder_before_runtime["baseColor"], "mist")
            self.assertEqual(builder_before_runtime["themeColor"], "blue")
            self.assertEqual(builder_before_runtime["primary"], "rgb(6, 111, 209)")
            self.assertEqual(
                builder_before_runtime["surface"],
                "oklch(0.148 0.004 228.8)",
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_layout_fixtures_are_served_with_assets_and_runtime_setup(self) -> None:
        for case in LAYOUT_CASES:
            with self.subTest(case=case.name):
                context, page, evidence = self._open("layout-app", case)
                try:
                    expect(page.locator("body")).to_have_attribute(
                        "data-layout-ready", "true"
                    )
                    self.assertEqual(
                        page.locator('link[href="/dist/assets/css/moo-ui.css"]').count(),
                        1,
                    )
                    self.assertEqual(
                        page.locator('[data-layout="app"]').count(), 1
                    )
                    self.assertEqual(
                        page.locator('[data-slot="sidebar-wrapper"]').count(), 1
                    )
                    self.assertEqual(
                        page.locator('[data-slot="sidebar-wrapper"]').get_attribute(
                            "data-sidebar-key"
                        ),
                        "layout-certification-shell",
                    )
                    self.assertEqual(
                        page.locator('[data-slot="sidebar-wrapper"]').get_attribute(
                            "data-sidebar-state"
                        ),
                        "expanded",
                    )
                    self.assertEqual(
                        page.locator(
                            '[data-slot="sidebar-wrapper"][data-sidebar-key="layout-certification-shell"]'
                        ).count(),
                        1,
                    )
                    self.assertTrue(
                        page.evaluate("() => Boolean(window.layoutCertificationSidebar)")
                    )
                    self.assertEqual(evidence.failed_responses, [])
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_public_sidebar_previews_initialize_dropdown_stacking_contract(self) -> None:
        for preview in (
            "layouts/previews/app-sidebar/index.html",
            "blocks/previews/sidebar-floating/index.html",
        ):
            context = new_case_context(self.browser, LAYOUT_CASES[0])
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
            evidence.failed_responses = failed_responses
            try:
                response = page.goto(
                    f"{self.base_url}/site-dist/{preview}",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, LAYOUT_CASES[0])

                root = page.locator(
                    '[data-slot="sidebar-wrapper"][data-sidebar-key]'
                )
                expect(root).to_have_attribute("data-sidebar-ready", "")
                trigger = page.locator(
                    '[data-slot="sidebar-header"] [data-bs-toggle="dropdown"]'
                ).first
                trigger.click()
                menu = trigger.locator("xpath=ancestor::li[1]").locator(
                    ".dropdown-menu"
                )
                expect(menu).to_have_class(re.compile(r"\bshow\b"))
                overlay = menu.evaluate(
                    """
                    menu => {
                      const rect = menu.getBoundingClientRect();
                      const hit = document.elementFromPoint(
                        rect.left + rect.width / 2,
                        rect.top + rect.height / 2
                      );
                      const sidebar = menu.closest('[data-slot="sidebar"]');
                      const owner = menu.closest('.sidebar-menu-item');
                      return {
                        position: getComputedStyle(menu).position,
                        topmost: Boolean(hit?.closest('.dropdown-menu.show')),
                        positioned: owner?.hasAttribute(
                          'data-sidebar-dropdown-positioned'
                        ),
                        sidebarZ: getComputedStyle(sidebar).zIndex,
                        innerZ: getComputedStyle(
                          sidebar?.querySelector('[data-slot="sidebar-inner"]')
                        ).zIndex,
                      };
                    }
                    """
                )
                with self.subTest(preview=preview, assertion="position"):
                    self.assertEqual(overlay["position"], "fixed")
                with self.subTest(preview=preview, assertion="positioned"):
                    self.assertTrue(overlay["positioned"])
                with self.subTest(preview=preview, assertion="topmost"):
                    self.assertTrue(overlay["topmost"])
                with self.subTest(preview=preview, assertion="stacking"):
                    self.assertEqual(overlay["sidebarZ"], "1031")
                    self.assertEqual(overlay["innerZ"], "1031")
                evidence.assert_clean()
            finally:
                context.close()

    def test_sidebar_variant_dividers_follow_the_public_shell_variant(self) -> None:
        for case in LAYOUT_CASES[:2]:
            context = new_case_context(self.browser, case)
            page = context.new_page()
            evidence = BrowserEvidence(page)
            try:
                response = page.goto(
                    f"{self.base_url}/site-dist/blocks/previews/sidebar-inset/index.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)
                self.assertEqual(page.locator(".moo-catalog").count(), 0)

                sidebar = page.locator('[data-slot="sidebar"]')
                inner = sidebar.locator('[data-slot="sidebar-inner"]')
                for side in ("left", "right"):
                    sidebar.evaluate("(element, side) => element.dataset.side = side", side)
                    for variant in ("sidebar", "inset", "floating"):
                        sidebar.evaluate(
                            "(element, variant) => element.dataset.variant = variant",
                            variant,
                        )
                        borders = inner.evaluate(
                            """element => {
                              const style = getComputedStyle(element);
                              return {
                                left: parseFloat(style.borderLeftWidth),
                                right: parseFloat(style.borderRightWidth),
                              };
                            }"""
                        )
                        with self.subTest(case=case.name, side=side, variant=variant):
                            if variant == "inset":
                                self.assertEqual(borders, {"left": 0, "right": 0})
                            elif variant == "floating":
                                self.assertGreater(borders["left"], 0)
                                self.assertGreater(borders["right"], 0)
                            else:
                                divider = "right" if side == "left" else "left"
                                self.assertGreater(borders[divider], 0)
                evidence.assert_clean()
            finally:
                context.close()

    def test_inset_page_header_follows_the_surface_top_corners(self) -> None:
        for route in ("blocks/previews/sidebar-inset/index.html", "index.html"):
            for case in LAYOUT_CASES[:2]:
                context = new_case_context(self.browser, case)
                if route == "index.html":
                    context.add_init_script(
                        "localStorage.setItem('moo:sidebar-variant', 'inset');"
                    )
                page = context.new_page()
                evidence = BrowserEvidence(page)
                try:
                    response = page.goto(
                        f"{self.base_url}/site-dist/{route}",
                        wait_until="networkidle",
                    )
                    self.assertIsNotNone(response)
                    self.assertTrue(response.ok)
                    prepare_page(page, case)
                    sidebar = page.locator('[data-slot="sidebar"]')
                    self.assertEqual(sidebar.get_attribute("data-variant"), "inset")

                    for side in ("left", "right"):
                        sidebar.evaluate(
                            "(element, value) => element.dataset.side = value", side
                        )
                        corners = page.evaluate(
                            """() => {
                              const surface = document.querySelector(
                                '.wrapper[data-layout="app"] > [data-slot="page"]'
                              );
                              const header = surface.querySelector(':scope > header');
                              const pageStyle = getComputedStyle(surface);
                              const headerStyle = getComputedStyle(header);
                              return {
                                pageLeft: pageStyle.borderTopLeftRadius,
                                pageRight: pageStyle.borderTopRightRadius,
                                headerLeft: headerStyle.borderTopLeftRadius,
                                headerRight: headerStyle.borderTopRightRadius,
                              };
                            }"""
                        )
                        with self.subTest(route=route, case=case.name, side=side):
                            self.assertGreater(
                                float(corners["pageLeft"].removesuffix("px")), 0
                            )
                            self.assertGreater(
                                float(corners["pageRight"].removesuffix("px")), 0
                            )
                            self.assertEqual(corners["headerLeft"], corners["pageLeft"])
                            self.assertEqual(corners["headerRight"], corners["pageRight"])
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_app_page_topology_and_region_rails(self) -> None:
        context, page, evidence = self._open("layout-app", LAYOUT_CASES[0])
        try:
            root = page.locator('[data-layout="app"]')
            self.assertEqual(root.locator(':scope > [data-slot="sidebar"]').count(), 1)
            page_host = root.locator(':scope > [data-slot="page"]')
            self.assertEqual(page_host.count(), 1)
            self.assertEqual(page_host.locator("main#main-content").count(), 1)
            self.assertEqual(page.locator("main#main-content").count(), 1)
            self.assertEqual(page.locator('[data-slot="sidebar-inset"], .sidebar-inset').count(), 0)

            bounds = page.evaluate(
                """
                () => {
                  const host = document.querySelector('[data-slot="page"]');
                  const regions = ['header', 'main', 'footer'].map(tag => {
                    const region = host.querySelector(tag);
                    const rail = region?.querySelector(':scope > .container-xl');
                    return {
                      tag,
                      regionLeft: region?.getBoundingClientRect().left,
                      regionRight: region?.getBoundingClientRect().right,
                      railLeft: rail?.getBoundingClientRect().left,
                      railRight: rail?.getBoundingClientRect().right,
                    };
                  });
                  return {regions, scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth};
                }
                """
            )
            self.assertLessEqual(bounds["scrollWidth"], bounds["clientWidth"])
            rails = [region for region in bounds["regions"] if region["railLeft"] is not None]
            self.assertEqual(len(rails), 3)
            self.assertEqual({region["railLeft"] for region in rails}, {rails[0]["railLeft"]})
            self.assertEqual({region["railRight"] for region in rails}, {rails[0]["railRight"]})
            evidence.assert_clean()
        finally:
            context.close()

    def test_navigation_none_emits_page_only_shell(self) -> None:
        context, page, evidence = self._open("layout-app-none", LAYOUT_CASES[0])
        try:
            root = page.locator('[data-layout="app"]')
            self.assertEqual(root.locator(':scope > [data-slot="sidebar"]').count(), 0)
            self.assertEqual(root.locator(':scope > [data-slot="page"]').count(), 1)
            self.assertEqual(root.locator('[data-slot="sidebar-wrapper"]').count(), 0)
            self.assertEqual(page.locator("[data-sidebar-trigger]").count(), 0)
            self.assertEqual(page.locator("main#main-content").count(), 1)
            evidence.assert_clean()
        finally:
            context.close()

    def test_page_main_focus_and_skip_link(self) -> None:
        for fixture, query in (
            ("layout-app", ""),
            ("layout-app-contained", ""),
            ("layout-page", ""),
        ):
            with self.subTest(fixture=fixture):
                context, page, evidence = self._open(fixture, LAYOUT_CASES[0])
                try:
                    skip_link = page.locator('a[href="#main-content"]')
                    skip_link.focus()
                    skip_link.press("Enter")
                    self.assertEqual(
                        page.evaluate("() => document.activeElement?.id"),
                        "main-content",
                    )
                    self.assertEqual(
                        page.locator('main#main-content[tabindex="-1"]').count(), 1
                    )
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_page_width_matrix_and_fluid_gutters(self) -> None:
        expected = {
            "base": "container",
            "sm": "container-sm",
            "md": "container-md",
            "lg": "container-lg",
            "xl": "container-xl",
            "xxl": "container-xxl",
            "fluid": "container-fluid",
        }
        all_container_classes = tuple(expected.values())
        for width, container_class in expected.items():
            fixture = "layout-page" if width == "xl" else f"layout-page-{width}"
            context, page, evidence = self._open(fixture, LAYOUT_CASES[0])
            try:
                regions = page.locator(
                    '[data-slot="page"] > header, [data-slot="page"] > main, '
                    '[data-slot="page"] > footer'
                )
                self.assertEqual(regions.count(), 3)
                with self.subTest(width=width):
                    for index in range(regions.count()):
                        rails = regions.nth(index).locator(
                            ":scope > ." + container_class
                        )
                        self.assertEqual(rails.count(), 1)
                        for other_class in all_container_classes:
                            if other_class != container_class:
                                self.assertEqual(
                                    regions.nth(index).locator(
                                        ":scope > ." + other_class
                                    ).count(),
                                    0,
                                )
                    metrics = page.evaluate(
                    """
                    () => {
                      const host = document.querySelector('[data-slot="page"]');
                      return ['header', 'main', 'footer'].map(tag => {
                        const region = host.querySelector(`:scope > ${tag}`);
                        const rail = region?.firstElementChild;
                        const regionRect = region.getBoundingClientRect();
                        const railRect = rail.getBoundingClientRect();
                        const style = getComputedStyle(rail);
                        return {
                          regionLeft: regionRect.left, regionRight: regionRect.right,
                          railLeft: railRect.left, railRight: railRect.right,
                          paddingLeft: parseFloat(style.paddingLeft),
                          paddingRight: parseFloat(style.paddingRight),
                        };
                      });
                    }
                    """
                )
                    if width == "fluid":
                        for metric in metrics:
                            self.assertLessEqual(
                                abs(metric["railLeft"] - metric["regionLeft"]), 1
                            )
                            self.assertLessEqual(
                                abs(metric["railRight"] - metric["regionRight"]), 1
                            )
                            self.assertGreater(metric["paddingLeft"], 0)
                            self.assertGreater(metric["paddingRight"], 0)
                    evidence.assert_clean()
            finally:
                context.close()

    def test_page_regions_are_static_full_width_and_ordered(self) -> None:
        for fixture in ("layout-page", "layout-app"):
            with self.subTest(fixture=fixture):
                context, page, evidence = self._open(fixture, LAYOUT_CASES[0])
                try:
                    details = page.locator('[data-slot="page"]').evaluate(
                    """
                    host => {
                      const regions = [...host.children].filter(node =>
                        ['HEADER', 'MAIN', 'FOOTER'].includes(node.tagName));
                      return regions.map(region => {
                        const style = getComputedStyle(region);
                        const rect = region.getBoundingClientRect();
                        return {tag: region.tagName, position: style.position,
                          left: rect.left, right: rect.right};
                      });
                    }
                    """
                )
                    self.assertEqual([item["tag"] for item in details], ["HEADER", "MAIN", "FOOTER"])
                    self.assertTrue(all(item["position"] == "static" for item in details))
                    host = page.locator('[data-slot="page"]').bounding_box()
                    self.assertIsNotNone(host)
                    self.assertTrue(all(abs(item["left"] - host["x"]) < 1 for item in details))
                    self.assertTrue(
                        all(abs(item["right"] - (host["x"] + host["width"])) < 1 for item in details)
                    )
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_standalone_page_owns_document_scroll_without_forced_shell_height(self) -> None:
        context, page, evidence = self._open("layout-page", LAYOUT_CASES[2])
        try:
            scroll = page.evaluate(
                """
                () => ({scrollHeight: document.documentElement.scrollHeight,
                  clientHeight: document.documentElement.clientHeight,
                  bodyOverflow: getComputedStyle(document.body).overflow,
                  mainOverflow: getComputedStyle(document.querySelector('main')).overflowY})
                """
            )
            self.assertGreater(scroll["scrollHeight"], scroll["clientHeight"])
            self.assertEqual(scroll["bodyOverflow"], "visible")
            self.assertEqual(scroll["mainOverflow"], "visible")
            before = page.evaluate("() => window.scrollY")
            page.evaluate("() => window.scrollTo(0, 320)")
            after = page.evaluate("() => window.scrollY")
            self.assertGreater(after, before)
            self.assertEqual(page.evaluate("() => document.querySelector('main').scrollTop"), 0)
            evidence.assert_clean()
        finally:
            context.close()

    def test_sidebar_persistence_and_keyed_keyboard_toggle(self) -> None:
        init_script = """
          const storageKey = 'moo-sidebar:layout-certification-shell';
          if (localStorage.getItem(storageKey) === null) {
            localStorage.setItem(storageKey, 'collapsed');
          }
          window.__layoutCertificationFirstFrame = null;
          requestAnimationFrame(() => {
            const root = document.querySelector('[data-sidebar-key="layout-certification-shell"]');
            window.__layoutCertificationFirstFrame = {
              key: root?.dataset.sidebarKey || null,
              state: root?.dataset.sidebarState || null
            };
          });
        """
        context, page, evidence = self._open(
            "layout-app", LAYOUT_CASES[0], init_script=init_script
        )
        try:
            root = page.locator('[data-slot="sidebar-wrapper"]')
            trigger = page.locator("[data-sidebar-trigger]")
            keyed_roots = page.locator(
                '[data-slot="sidebar-wrapper"][data-sidebar-key="layout-certification-shell"]'
            )
            self.assertEqual(keyed_roots.count(), 1)
            self.assertEqual(
                keyed_roots.locator(':scope > aside#layout-certification-sidebar').count(),
                1,
            )
            self.assertEqual(
                page.evaluate("() => window.__layoutCertificationFirstFrame"),
                {
                    "key": "layout-certification-shell",
                    "state": "collapsed",
                },
            )
            expect(root).to_have_attribute("data-sidebar-state", "collapsed")
            self.assertEqual(
                page.evaluate("() => localStorage.getItem('moo-sidebar:layout-certification-shell')"),
                "collapsed",
            )
            page.keyboard.press("Control+b")
            expect(root).to_have_attribute("data-sidebar-state", "expanded")
            self.assertEqual(keyed_roots.count(), 1)
            self.assertEqual(
                page.evaluate(
                    "() => [...document.querySelectorAll('[data-sidebar-key]')].map(root => ({key: root.dataset.sidebarKey, state: root.dataset.sidebarState}))"
                ),
                [{"key": "layout-certification-shell", "state": "expanded"}],
            )
            self.assertEqual(
                page.locator('[data-slot="sidebar-wrapper"] > aside#layout-certification-sidebar').count(),
                1,
            )
            self.assertEqual(
                page.evaluate("() => localStorage.getItem('moo-sidebar:layout-certification-shell')"),
                "expanded",
            )
            page.reload(wait_until="networkidle")
            prepare_page(page, LAYOUT_CASES[0])
            reloaded_root = page.locator('[data-slot="sidebar-wrapper"]')
            expect(reloaded_root).to_have_attribute("data-sidebar-state", "expanded")
            self.assertEqual(
                page.evaluate("() => window.__layoutCertificationFirstFrame"),
                {
                    "key": "layout-certification-shell",
                    "state": "expanded",
                },
            )
            self.assertEqual(
                page.locator('[data-slot="sidebar-wrapper"][data-sidebar-key="layout-certification-shell"]').count(),
                1,
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_collapsed_submenu_flyout_and_tooltip_are_topmost(self) -> None:
        for fixture, side in (("layout-app", "left"), ("layout-app-right", "right")):
            for case in (LAYOUT_CASES[0], LAYOUT_CASES[1]):
                with self.subTest(fixture=fixture, direction=case.direction):
                    context, page, evidence = self._open(
                        fixture, case, "?state=collapsed"
                    )
                    try:
                        root = page.locator('[data-slot="sidebar-wrapper"]')
                        expect(root).to_have_attribute("data-sidebar-state", "collapsed")
                        submenu_trigger = page.locator(".sidebar-menu-sub-trigger")
                        submenu_trigger.click()
                        flyout = page.locator(".sidebar-menu-flyout")
                        expect(flyout).to_be_visible()
                        flyout_style = flyout.evaluate(
                            """
                            element => {
                              const rect = element.getBoundingClientRect();
                              const hit = document.elementFromPoint(
                                rect.left + rect.width / 2, rect.top + rect.height / 2
                              );
                              return {
                                top: rect.top,
                                left: rect.left,
                                right: rect.right,
                                leftStyle: getComputedStyle(element).getPropertyValue(
                                  '--moo-sidebar-flyout-left'
                                ),
                                topmost: Boolean(hit?.closest('.sidebar-menu-flyout')),
                              };
                            }
                            """
                        )
                        with self.subTest(overlay="submenu-flyout"):
                            sidebar_rect = page.locator("#layout-certification-sidebar").bounding_box()
                            self.assertIsNotNone(sidebar_rect)
                            self.assertTrue(flyout_style["leftStyle"])
                            self.assertGreaterEqual(flyout_style["top"], 0)
                            if side == "left":
                                self.assertGreaterEqual(
                                    flyout_style["left"], sidebar_rect["x"] + sidebar_rect["width"] - 1
                                )
                            else:
                                self.assertLessEqual(
                                    flyout_style["right"], sidebar_rect["x"] + 1
                                )
                            self.assertTrue(flyout_style["topmost"])
                        overview = page.locator(
                            '[data-slot="sidebar-content"] a[data-sidebar-tooltip]'
                        ).first
                        overview.hover()
                        tooltip = page.locator(".tooltip")
                        expect(tooltip).to_be_visible()
                        tooltip_style = tooltip.evaluate(
                            """
                            element => {
                              const rect = element.getBoundingClientRect();
                              const hit = document.elementFromPoint(
                                rect.left + rect.width / 2, rect.top + rect.height / 2
                              );
                              return {left: rect.left, right: rect.right,
                                top: rect.top, topmost: Boolean(hit?.closest('.tooltip'))};
                            }
                            """
                        )
                        with self.subTest(overlay="tooltip"):
                            sidebar_rect = page.locator("#layout-certification-sidebar").bounding_box()
                            self.assertIsNotNone(sidebar_rect)
                            self.assertGreaterEqual(tooltip_style["top"], 0)
                            if side == "left":
                                self.assertGreaterEqual(
                                    tooltip_style["left"], sidebar_rect["x"] + sidebar_rect["width"] - 1
                                )
                            else:
                                self.assertLessEqual(
                                    tooltip_style["right"], sidebar_rect["x"] + 1
                                )
                            self.assertTrue(tooltip_style["topmost"])
                        evidence.assert_clean()
                    finally:
                        context.close()

    def test_theme_text_and_focus_ring_are_readable(self) -> None:
        for case in (LAYOUT_CASES[0], LAYOUT_CASES[1]):
            context, page, evidence = self._open("layout-page", case)
            try:
                with self.subTest(case=case.name):
                    values = page.locator("h1").evaluate(
                    """element => {
                      const parse = value => {
                        const match = value.match(/rgba?\\(([^)]+)\\)/);
                        if (!match) return null;
                        const parts = match[1].split(',').map(part => Number(part.trim()));
                        return {rgb: parts.slice(0, 3), alpha: parts[3] ?? 1};
                      };
                      const composite = (foreground, background) => {
                        const alpha = foreground.alpha + background.alpha * (1 - foreground.alpha);
                        if (!alpha) return {rgb: [0, 0, 0], alpha: 0};
                        return {
                          rgb: foreground.rgb.map((channel, index) =>
                            (channel * foreground.alpha + background.rgb[index] * background.alpha * (1 - foreground.alpha)) / alpha
                          ),
                          alpha,
                        };
                      };
                      const backgroundBehind = node => {
                        const chain = [];
                        for (let current = node; current; current = current.parentElement) chain.push(current);
                        let background = {rgb: [0, 0, 0], alpha: 1};
                        for (const current of chain.reverse()) {
                          const color = parse(getComputedStyle(current).backgroundColor);
                          if (color) background = composite(color, background);
                        }
                        return background.rgb;
                      };
                      const relativeLuminance = rgb => rgb.map(value => value / 255).map(value =>
                        value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
                      ).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
                      const style = getComputedStyle(element);
                      const foreground = parse(style.color);
                      const background = backgroundBehind(element);
                      const foregroundLum = relativeLuminance(foreground.rgb);
                      const backgroundLum = relativeLuminance(background);
                      const contrast = (Math.max(foregroundLum, backgroundLum) + 0.05) /
                        (Math.min(foregroundLum, backgroundLum) + 0.05);
                      return {color: style.color, background, contrast};
                    }"""
                )
                    self.assertNotIn(values["color"], ("transparent", "rgba(0, 0, 0, 0)"))
                    self.assertGreaterEqual(values["contrast"], 4.5)
                    button = page.locator("a[href='#main-content']")
                    button.focus()
                    ring = button.evaluate(
                    """
                    element => {
                      const s = getComputedStyle(element);
                      return {outlineStyle: s.outlineStyle,
                        outlineWidth: parseFloat(s.outlineWidth),
                        shadow: s.boxShadow};
                    }
                    """
                )
                    self.assertTrue(
                        (ring["outlineStyle"] != "none" and ring["outlineWidth"] > 0)
                        or ring["shadow"] != "none"
                    )
                    evidence.assert_clean()
            finally:
                context.close()

    def test_fixture_has_unique_ids_and_no_external_shell_helpers(self) -> None:
        fixtures = (
            "layout-app", "layout-app-contained", "layout-app-right", "layout-app-none",
            "layout-page", "layout-page-base", "layout-page-sm", "layout-page-md",
            "layout-page-lg", "layout-page-xxl", "layout-page-fluid",
        )
        for fixture in fixtures:
            context, page, evidence = self._open(fixture, LAYOUT_CASES[0])
            try:
                with self.subTest(fixture=fixture):
                    ids = page.locator("[id]").evaluate_all(
                    "elements => elements.map(element => element.id)"
                )
                    self.assertEqual(len(ids), len(set(ids)))
                    source = page.locator("html").evaluate("element => element.outerHTML")
                    self.assertNotRegex(source, r"class=[\"'][^\"']*(?:sticky|fixed)")
                    self.assertNotIn("data-certification-region", source)
                    self.assertEqual(page.locator('[data-slot="sidebar-inset"]').count(), 0)
                    self.assertEqual(page.locator(".sidebar-inset").count(), 0)
                    self.assertEqual(evidence.failed_responses, [])
                    evidence.assert_clean()
            finally:
                context.close()

    def test_responsive_scroll_and_sidebar_width_ownership_matrix(self) -> None:
        context, page, evidence = self._open("layout-app", LAYOUT_CASES[0])
        try:
            styles = page.evaluate(
                """
                () => {
                  const root = document.querySelector('[data-layout="app"]');
                  const sidebar = root.querySelector('[data-slot="sidebar"]');
                  const pageHost = root.querySelector('[data-slot="page"]');
                  const rootStyle = getComputedStyle(root);
                  const sidebarStyle = getComputedStyle(sidebar);
                  const pageStyle = getComputedStyle(pageHost);
                  const rootRect = root.getBoundingClientRect();
                  return {
                    rootStyleHeight: rootStyle.height,
                    rootStyleMinHeight: rootStyle.minHeight,
                    rootMinHeightPixels: parseFloat(rootStyle.minHeight),
                    rootRectHeight: rootRect.height,
                    viewportHeight: window.innerHeight,
                    rootOverflow: rootStyle.overflow,
                    rootOverflowY: rootStyle.overflowY,
                    bodyOverflowY: getComputedStyle(document.body).overflowY,
                    pageOverflow: pageStyle.overflow,
                    pageOverflowY: pageStyle.overflowY,
                    mainOverflowY: getComputedStyle(pageHost.querySelector('main')).overflowY,
                    sidebarWidth: sidebarStyle.getPropertyValue('--moo-sidebar-width').trim(),
                    sidebarIconWidth: sidebarStyle.getPropertyValue('--moo-sidebar-width-icon').trim(),
                    rootSidebarWidth: rootStyle.getPropertyValue('--moo-sidebar-width').trim(),
                    offcanvasWidth: sidebarStyle.getPropertyValue('--bs-offcanvas-width').trim(),
                  };
                }
                """
            )
            self.assertEqual(styles["rootMinHeightPixels"], 0)
            self.assertTrue(styles["rootStyleHeight"])
            self.assertAlmostEqual(
                float(styles["rootStyleHeight"].removesuffix("px")),
                styles["viewportHeight"],
                delta=1,
            )
            self.assertAlmostEqual(
                styles["rootRectHeight"], styles["viewportHeight"], delta=1
            )
            self.assertIn(styles["rootOverflow"], ("hidden", "clip"))
            self.assertNotIn(styles["rootOverflowY"], ("auto", "scroll"))
            self.assertNotIn(styles["bodyOverflowY"], ("auto", "scroll"))
            self.assertEqual(styles["mainOverflowY"], "auto")
            self.assertEqual(styles["pageOverflowY"], "visible")
            page.evaluate("() => window.scrollTo(0, 0)")
            page.evaluate("() => document.querySelector('[data-slot=page] > main').scrollTo(0, 320)")
            self.assertGreater(
                page.evaluate("() => document.querySelector('[data-slot=page] > main').scrollTop"),
                0,
            )
            self.assertEqual(
                page.evaluate("() => document.querySelector('[data-slot=page]').scrollTop"),
                0,
            )
            self.assertEqual(page.evaluate("() => window.scrollY"), 0)
            evidence.assert_clean()
        finally:
            context.close()

    def test_sidebar_width_tokens_are_owned_by_sidebar_not_app_root(self) -> None:
        context, page, evidence = self._open("layout-app", LAYOUT_CASES[0])
        try:
            styles = page.evaluate(
                """
                () => {
                  const root = document.querySelector('[data-layout="app"]');
                  const sidebar = root.querySelector('[data-slot="sidebar"]');
                  const rootStyle = getComputedStyle(root);
                  const sidebarStyle = getComputedStyle(sidebar);
                  const resolve = name => {
                    const probe = document.createElement('div');
                    probe.style.cssText = `position:absolute; visibility:hidden; width:var(${name}); height:0;`;
                    sidebar.append(probe);
                    const value = probe.getBoundingClientRect().width;
                    probe.remove();
                    return value;
                  };
                  const expandedWidth = sidebar.getBoundingClientRect().width;
                  const expandedTokenWidth = resolve('--moo-sidebar-width');
                  const expandedOffcanvasWidth = resolve('--bs-offcanvas-width');
                  return {
                    sidebarWidth: sidebarStyle.getPropertyValue('--moo-sidebar-width').trim(),
                    sidebarIconWidth: sidebarStyle.getPropertyValue('--moo-sidebar-width-icon').trim(),
                    rootSidebarWidth: rootStyle.getPropertyValue('--moo-sidebar-width').trim(),
                    offcanvasWidth: sidebarStyle.getPropertyValue('--bs-offcanvas-width').trim(),
                    expandedWidth, expandedTokenWidth, expandedOffcanvasWidth,
                  };
                }
                """
            )
            self.assertTrue(styles["sidebarWidth"])
            self.assertTrue(styles["sidebarIconWidth"])
            self.assertTrue(styles["offcanvasWidth"])
            self.assertEqual(styles["rootSidebarWidth"], "")
            self.assertAlmostEqual(styles["expandedWidth"], styles["expandedTokenWidth"], delta=1)
            self.assertAlmostEqual(styles["expandedWidth"], styles["expandedOffcanvasWidth"], delta=1)
            page.evaluate(
                "() => { document.querySelector('[data-layout=app]').dataset.sidebarState = 'collapsed'; }"
            )
            page.wait_for_function(
                """
                () => {
                  const sidebar = document.querySelector('[data-slot=sidebar]');
                  const probe = document.createElement('div');
                  probe.style.cssText = 'position:absolute; visibility:hidden; width:var(--moo-sidebar-width-icon); height:0';
                  sidebar.append(probe);
                  const expected = probe.getBoundingClientRect().width;
                  probe.remove();
                  return Math.abs(sidebar.getBoundingClientRect().width - expected) < 1;
                }
                """
            )
            collapsed = page.evaluate(
                """
                () => {
                  const sidebar = document.querySelector('[data-slot=sidebar]');
                  const probe = document.createElement('div');
                  probe.style.cssText = 'position:absolute; visibility:hidden; width:var(--moo-sidebar-width-icon); height:0';
                  sidebar.append(probe);
                  const expected = probe.getBoundingClientRect().width;
                  probe.remove();
                  return {width: sidebar.getBoundingClientRect().width, expected};
                }
                """
            )
            self.assertAlmostEqual(collapsed["width"], collapsed["expected"], delta=1)
            evidence.assert_clean()
        finally:
            context.close()

    def test_contained_mode_and_mobile_document_scroll_matrix(self) -> None:
        for case in (LAYOUT_CASES[0], LAYOUT_CASES[2]):
            with self.subTest(case=case.name):
                context, page, evidence = self._open("layout-app-contained", case)
                try:
                    styles = page.evaluate(
                    """
                    () => {
                      const root = document.querySelector('[data-layout="app"]');
                      const outer = document.querySelector('#layout-certification-host');
                      const pageHost = root.querySelector('[data-slot="page"]');
                      const rootStyle = getComputedStyle(root);
                      const outerStyle = getComputedStyle(outer);
                      const pageStyle = getComputedStyle(pageHost);
                      const rootRect = root.getBoundingClientRect();
                      const outerRect = outer.getBoundingClientRect();
                      return {
                        mode: root.dataset.shellMode,
                        rootHeight: rootStyle.height,
                        rootRectHeight: rootRect.height,
                        rootOverflow: rootStyle.overflow,
                        outerHeight: outerStyle.height,
                        outerRectHeight: outerRect.height,
                        outerOverflow: outerStyle.overflow,
                        innerHeight: window.innerHeight,
                        pageOverflowY: pageStyle.overflowY,
                        mainOverflowY: getComputedStyle(pageHost.querySelector('main')).overflowY,
                        documentOverflowY: getComputedStyle(document.documentElement).overflowY,
                        documentScrollHeight: document.documentElement.scrollHeight,
                        documentClientHeight: document.documentElement.clientHeight,
                      };
                    }
                    """
                    )
                    self.assertEqual(styles["mode"], "contained")
                    if case.is_mobile:
                        self.assertGreater(styles["rootRectHeight"], styles["innerHeight"])
                        self.assertGreater(styles["outerRectHeight"], styles["innerHeight"])
                        self.assertEqual(styles["rootOverflow"], "visible")
                        self.assertEqual(styles["outerOverflow"], "visible")
                        self.assertEqual(styles["pageOverflowY"], "visible")
                        self.assertEqual(styles["mainOverflowY"], "visible")
                        self.assertGreater(
                            styles["documentScrollHeight"], styles["documentClientHeight"]
                        )
                        page.evaluate("() => window.scrollTo(0, 320)")
                        self.assertEqual(
                            page.evaluate("() => document.querySelector('[data-slot=page]').scrollTop"),
                            0,
                        )
                        self.assertGreater(page.evaluate("() => window.scrollY"), 0)
                    else:
                        self.assertAlmostEqual(styles["rootRectHeight"], 544, delta=1)
                        self.assertIn(styles["rootOverflow"], ("hidden", "clip"))
                        self.assertAlmostEqual(styles["outerRectHeight"], 544, delta=1)
                        self.assertEqual(styles["innerHeight"], 844)
                        self.assertEqual(styles["pageOverflowY"], "visible")
                        self.assertEqual(styles["mainOverflowY"], "auto")
                        page.evaluate("() => window.scrollTo(0, 0)")
                        page.evaluate("() => document.querySelector('[data-slot=page] > main').scrollTo(0, 320)")
                        self.assertGreater(
                            page.evaluate("() => document.querySelector('[data-slot=page] > main').scrollTop"),
                            0,
                        )
                        self.assertEqual(page.evaluate("() => window.scrollY"), 0)
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_sidebar_overlay_is_keyboard_reachable_and_topmost(self) -> None:
        context, page, evidence = self._open("layout-app", LAYOUT_CASES[0])
        try:
            for trigger_id in (
                "[aria-label='Open workspaces']",
                "[aria-label='Open account menu']",
            ):
                with self.subTest(trigger=trigger_id):
                    trigger = page.locator(trigger_id)
                    trigger.focus()
                    trigger.press("Enter")
                    menu = trigger.locator("xpath=..").locator(".dropdown-menu")
                    expect(menu).to_be_visible()
                    topmost = menu.evaluate(
                    """
                    menu => {
                      const rect = menu.getBoundingClientRect();
                      const hit = document.elementFromPoint(rect.left + rect.width / 2,
                        rect.top + rect.height / 2);
                      return Boolean(hit?.closest('#layout-certification-sidebar .dropdown-menu'));
                    }
                    """
                )
                    sidebar_rect = page.locator("#layout-certification-sidebar").bounding_box()
                    menu_rect = menu.bounding_box()
                    self.assertIsNotNone(sidebar_rect)
                    self.assertIsNotNone(menu_rect)
                    self.assertGreaterEqual(menu_rect["x"], sidebar_rect["x"] - 1)
                    self.assertLessEqual(
                        menu_rect["x"], sidebar_rect["x"] + sidebar_rect["width"] + 1
                    )
                    self.assertTrue(topmost)
                    trigger.press("Escape")
            evidence.assert_clean()
        finally:
            context.close()

    def test_right_sidebar_and_rtl_keep_physical_page_placement(self) -> None:
        for side in ("left", "right"):
            for direction in ("ltr", "rtl"):
                case = BrowserCase(
                    name=f"{side}-{direction}",
                    viewport={"width": 1040, "height": 844},
                    color_scheme="light",
                    direction=direction,
                )
                fixture = "layout-app-right" if side == "right" else "layout-app"
                with self.subTest(side=side, direction=direction):
                    context, page, evidence = self._open(fixture, case)
                    try:
                        placement = page.evaluate(
                            """
                            () => {
                              const root = document.querySelector('[data-layout="app"]');
                              const sidebar = root.querySelector('[data-slot="sidebar"]');
                              const pageHost = root.querySelector('[data-slot="page"]');
                              const main = pageHost.querySelector('main');
                              const sidebarRect = sidebar.getBoundingClientRect();
                              const pageRect = pageHost.getBoundingClientRect();
                              const rootRect = root.getBoundingClientRect();
                              const mainRect = main.getBoundingClientRect();
                              const inner = sidebar.querySelector('.sidebar-inner');
                              const innerStyle = getComputedStyle(inner);
                              const breadcrumb = pageHost.querySelector('.layout-certification-breadcrumb');
                              return {dir: document.documentElement.dir, sidebarSide: sidebar.dataset.side,
                                sidebarLeft: sidebarRect.left, sidebarRight: sidebarRect.right,
                                pageLeft: pageRect.left, pageRight: pageRect.right,
                                rootLeft: rootRect.left, rootRight: rootRect.right,
                                mainLeft: mainRect.left, mainRight: mainRect.right,
                                borderLeft: innerStyle.borderLeftWidth,
                                borderRight: innerStyle.borderRightWidth,
                                accountItemCount: sidebar.querySelectorAll('.sidebar-menu-item--account').length,
                                accountTriggerCount: sidebar.querySelectorAll('.sidebar-menu-button--account').length,
                                viewportWidth: window.innerWidth,
                                breadcrumbDirection: breadcrumb ? getComputedStyle(breadcrumb).direction : null,
                                breadcrumbOrder: breadcrumb ? [...breadcrumb.querySelectorAll('.breadcrumb-item')].map(item => item.textContent.trim()) : [],
                              };
                            }
                            """
                        )
                        self.assertEqual(placement["sidebarSide"], side)
                        self.assertEqual(placement["dir"], direction)
                        self.assertEqual(placement["accountItemCount"], 1)
                        self.assertEqual(placement["accountTriggerCount"], 1)
                        if side == "left":
                            self.assertEqual(placement["borderLeft"], "0px")
                            self.assertEqual(placement["borderRight"], "1px")
                        else:
                            self.assertEqual(placement["borderLeft"], "1px")
                            self.assertEqual(placement["borderRight"], "0px")
                        tolerance = 1
                        self.assertGreaterEqual(placement["sidebarLeft"], -tolerance)
                        self.assertLessEqual(
                            placement["sidebarRight"], placement["viewportWidth"] + tolerance
                        )
                        self.assertGreaterEqual(
                            placement["mainLeft"], placement["pageLeft"] - tolerance
                        )
                        self.assertLessEqual(
                            placement["mainRight"], placement["pageRight"] + tolerance
                        )
                        self.assertAlmostEqual(placement["rootLeft"], 0, delta=tolerance)
                        self.assertAlmostEqual(
                            placement["rootRight"], placement["viewportWidth"], delta=tolerance
                        )
                        if side == "right":
                            self.assertAlmostEqual(
                                placement["pageLeft"], placement["rootLeft"], delta=tolerance
                            )
                            self.assertAlmostEqual(
                                placement["pageRight"], placement["sidebarLeft"], delta=tolerance
                            )
                            self.assertAlmostEqual(
                                placement["sidebarRight"], placement["rootRight"], delta=tolerance
                            )
                        else:
                            self.assertAlmostEqual(
                                placement["sidebarLeft"], placement["rootLeft"], delta=tolerance
                            )
                            self.assertAlmostEqual(
                                placement["sidebarRight"], placement["pageLeft"], delta=tolerance
                            )
                            self.assertAlmostEqual(
                                placement["pageRight"], placement["rootRight"], delta=tolerance
                            )
                        self.assertEqual(
                            placement["breadcrumbOrder"], ["Workspace", "Overview"]
                        )
                        self.assertEqual(placement["breadcrumbDirection"], direction)
                        evidence.assert_clean()
                    finally:
                        context.close()

    def test_light_dark_focus_and_zoom_gate_are_explicit(self) -> None:
        evidence_path = self._root_path("src/certification/layout-evidence.json")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["layouts"]["app"]["status"], "preview")
        self.assertEqual(evidence["layouts"]["page"]["status"], "preview")
        self.assertIn("manual-browser-zoom-200-required", evidence["manualReleaseGates"])
        self.skipTest(
            "Playwright harness does not control real browser zoom; manual 200% release gate remains open"
        )

    @staticmethod
    def _root_path(relative: str):
        from pathlib import Path

        return Path(__file__).resolve().parents[1] / relative
