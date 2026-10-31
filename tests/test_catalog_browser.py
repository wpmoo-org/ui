from __future__ import annotations

from dataclasses import replace
import itertools
import json
import re
import time
import unittest

from playwright.sync_api import expect, sync_playwright

from build import create_environment, theme_builder_first_paint_payload
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

CHEVRON_DIRECTION = """button => {
  const shape = button.querySelector('.sidebar-menu-button__end svg path, .sidebar-menu-button__end svg polyline');
  const matrix = shape?.getScreenCTM();
  if (!matrix) return null;
  const length = shape.getTotalLength();
  const project = point => new DOMPoint(point.x, point.y).matrixTransform(matrix);
  const start = project(shape.getPointAtLength(0));
  const end = project(shape.getPointAtLength(length));
  const tip = project(shape.getPointAtLength(length / 2));
  const dx = tip.x - (start.x + end.x) / 2;
  const dy = tip.y - (start.y + end.y) / 2;
  const tolerance = Math.hypot(dx, dy) * 0.02;
  if (Math.abs(dx) > tolerance && Math.abs(dy) > tolerance) return 'turning';
  return Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
}"""


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

    def test_card_floating_checklist_keeps_its_composed_public_contract(self) -> None:
        for theme, direction, width in itertools.product(
            ("light", "dark"), ("ltr", "rtl"), (390, 1061, 1440),
        ):
            with self.subTest(theme=theme, direction=direction, width=width):
                context = self.browser.new_context(viewport={"width": width, "height": 1195})
                try:
                    page = context.new_page()
                    evidence = BrowserEvidence(page)
                    page.goto(f"{self.base_url}/site-dist/components/card/index.html")
                    panel = page.locator("#card-preparation-panel")
                    expect(panel).to_have_attribute("data-floating-panel-ready", "true")
                    panel.evaluate("""(element, state) => {
                        const owner = element.closest('.moo-ui');
                        owner.setAttribute('data-bs-theme', state.theme);
                        owner.setAttribute('dir', state.direction);
                    }""", {"theme": theme, "direction": direction})
                    expect(panel).to_be_visible()
                    progress = panel.get_by_role("progressbar")
                    expect(progress).to_have_attribute("aria-valuenow", "2")
                    expect(progress).to_have_attribute("aria-valuemax", "5")
                    expect(panel.locator(".nav-item")).to_have_count(5)
                    expect(panel.locator("a[href]")).to_have_count(0)
                    expect(panel.locator('.nav-link[aria-disabled="true"][tabindex="-1"]')).to_have_count(5)
                    expect(panel.locator(".badge")).to_have_text("Demo")
                    original_url = page.url
                    panel.locator(".nav-item").nth(2).click()
                    self.assertEqual(page.url, original_url)
                    completed = panel.locator('[data-nav-completed="true"] a')
                    expect(completed).to_have_count(2)
                    self.assertTrue(completed.evaluate_all("elements => elements.every(e => getComputedStyle(e).textDecorationLine.includes('line-through'))"))
                    box = panel.bounding_box()
                    self.assertGreaterEqual(box["x"], -1)
                    self.assertLessEqual(box["x"] + box["width"], width + 1)
                    self.assert_floating_panel_above_content(page, width, direction)
                    toggle = panel.get_by_role("button", name="Toggle preparation steps")
                    content = panel.locator("#card-preparation-steps")
                    toggle.focus()
                    toggle.press("Enter")
                    expect(content).to_be_hidden()
                    expect(content).not_to_have_class(re.compile(r"\bcollapsing\b"))
                    self.assert_floating_panel_above_content(page, width, direction)
                    toggle.press("Enter")
                    expect(content).to_be_visible()
                    expect(content).not_to_have_class(re.compile(r"\bcollapsing\b"))
                    dismiss = panel.get_by_role("button", name="Dismiss forever")
                    dismiss.focus()
                    dismiss.press("Enter")
                    expect(panel).to_be_hidden()
                    launcher = page.locator('[data-floating-panel-open="card-preparation-panel"]')
                    expect(launcher).to_be_focused()
                    launcher.press("Enter")
                    expect(panel).to_be_visible()
                    expect(toggle).to_be_focused()
                    evidence.assert_clean()
                finally:
                    context.close()

    def assert_floating_panel_above_content(self, page, width: int, direction: str) -> None:
        action = create_environment().from_string(
            '{% from "components/button.html.jinja" import button %}'
            '{{ button("Background action", extra_class="position-absolute bottom-0 start-50 translate-middle-x") }}'
        ).render()
        page.evaluate("""markup => {
            if (document.querySelector('[data-floating-layer-probe]')) return;
            // Keep a real preview's ancestors; only the probe geometry is controlled.
            const background = [...document.querySelectorAll('.moo-example__preview')]
                .filter(element => element.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) &&
                    element.querySelector('button, input, select, textarea')).at(-1);
            if (!background) throw new Error('An interactive catalog preview is required');
            background.dataset.floatingLayerProbe = '';
            background.dataset.floatingLayerClicks = '0';
            background.classList.add('position-fixed', 'top-0', 'start-0', 'w-100', 'h-100', 'bg-body');
            const template = document.createElement('template');
            template.innerHTML = markup;
            const action = template.content.firstElementChild;
            action.dataset.floatingLayerAction = '';
            action.addEventListener('click', () => {
                background.dataset.floatingLayerClicks = String(Number(background.dataset.floatingLayerClicks) + 1);
            });
            background.append(action);
        }""", action)
        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        result = page.evaluate("""() => {
            const panel = document.querySelector('#card-preparation-panel');
            const card = panel.querySelector('.card').getBoundingClientRect();
            const preview = document.querySelector('[data-floating-layer-probe]');
            const background = preview.getBoundingClientRect();
            const left = Math.max(card.left, background.left);
            const right = Math.min(card.right, background.right);
            const top = Math.max(card.top, background.top);
            const bottom = Math.min(card.bottom, background.bottom, innerHeight);
            const overlap = right > left && bottom > top;
            const hits = [.2, .5, .8].flatMap(tx => [.2, .5, .8].map(ty => {
                const x = overlap ? left + (right - left) * tx : card.left + card.width * tx;
                const y = overlap ? top + (bottom - top) * ty : card.top + card.height * ty;
                const hit = document.elementFromPoint(x, y);
                return Boolean(hit && panel.contains(hit));
            }));
            const outside = document.elementFromPoint(innerWidth / 2, card.top + card.height / 2);
            return {overlap, hits, left: card.left, right: card.right,
                outsidePassesThrough: Boolean(outside && preview.contains(outside))};
        }""")
        self.assertTrue(all(result["hits"]), result)
        self.assertTrue(result["overlap"], result)
        if result["right"] - result["left"] < width / 2:
            self.assertTrue(result["outsidePassesThrough"], result)
            preview = page.locator('[data-floating-layer-probe]')
            previous = int(preview.get_attribute('data-floating-layer-clicks'))
            page.locator('[data-floating-layer-action]').click()
            expect(preview).to_have_attribute('data-floating-layer-clicks', str(previous + 1))
        self.assertGreaterEqual(result["left"], 0)
        self.assertLessEqual(result["right"], width)
        center = (result["left"] + result["right"]) / 2
        if direction == "ltr":
            self.assertGreaterEqual(center, width / 2)
        else:
            self.assertLessEqual(center, width / 2)

    def test_toc_document_preview_keeps_fragment_navigation_inside_its_frame(self) -> None:
        context = self.browser.new_context(viewport={"width": 1540, "height": 1314})
        self.addCleanup(context.close)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        page.goto(f"{self.base_url}/site-dist/components/toc/index.html")
        frame = page.frame_locator('iframe[data-moo-block-frame]')
        expect(frame.locator('#demo-toc-list')).to_be_visible()
        expect(frame.locator('#demo-toc-compact')).to_be_hidden()
        expect(page.locator('iframe[data-moo-block-frame]')).to_have_count(1)
        before = page.evaluate("() => ({url:location.href, y:scrollY, main:document.getElementById('main-content').scrollTop})")
        for label, target in [('Languages', 'languages'), ('Navigation', 'navigation'), ('Introduction', 'introduction')]:
            frame.locator('#demo-toc-list').get_by_role('link', name=label, exact=True).click()
            expect(frame.locator(f'#demo-toc-list a[href="#{target}"]')).to_have_attribute('aria-current', 'location')
            after = page.evaluate("() => ({url:location.href, y:scrollY, main:document.getElementById('main-content').scrollTop})")
            self.assertEqual(after, before)
        for label, width in [('Tablet', 768), ('Mobile', 390), ('Desktop', 1280)]:
            page.get_by_role('button', name=f'{label} preview', exact=True).click()
            expect(page.locator('iframe[data-moo-block-frame]')).to_have_attribute('width', str(width))
            if width < 992:
                expect(frame.locator('#demo-toc-list')).to_be_hidden()
                expect(frame.locator('#demo-toc-compact')).to_be_visible()
                frame.locator('#demo-toc-compact').get_by_role('button', name='On this page').click()
                frame.locator('#demo-toc-compact').get_by_role('link', name='Languages', exact=True).click()
                expect(frame.locator('#demo-toc-compact [data-toc-current]')).to_have_text('Languages')
                expect(frame.locator('#demo-toc-compact .dropdown-menu')).to_be_hidden()
            else:
                expect(frame.locator('#demo-toc-list')).to_be_visible()
                expect(frame.locator('#demo-toc-compact')).to_be_hidden()
            after = page.evaluate("() => ({url:location.href, y:scrollY, main:document.getElementById('main-content').scrollTop})")
            self.assertEqual(after, before)
        evidence.assert_clean()

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

    def test_catalog_toc_presentation_follows_available_page_width(self) -> None:
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                case = replace(CERTIFICATION_CASES[0], color_scheme=theme)
                context = new_case_context(self.browser, case)
                context.add_init_script(
                    "localStorage.setItem('moo-sidebar:catalog-shell', 'expanded');"
                )
                try:
                    page = context.new_page()
                    page.set_viewport_size({"width": 1159, "height": 900})
                    evidence = BrowserEvidence(page)
                    page.goto(f"{self.base_url}/site-dist/components/breadcrumb/")
                    prepare_page(page, case)
                    compact = page.locator("#catalog-toc-compact")
                    outline = page.locator("#catalog-toc-list")
                    expect(compact).to_be_hidden()
                    page.locator("#main-content").evaluate("el => el.scrollTo({top:700,behavior:'instant'})")
                    expect(compact).to_be_visible()
                    expect(outline).to_be_hidden()
                    self.assertLess(page.locator("#main-content").evaluate("el => el.clientWidth"), 992)
                    trigger = compact.locator("button")
                    trigger.click()
                    link = compact.locator("a").nth(1)
                    href = link.get_attribute("href")
                    label = link.inner_text()
                    link.click()
                    expect(page).to_have_url(f"{self.base_url}/site-dist/components/breadcrumb/{href}")
                    expect(compact.locator("[data-toc-current]")).to_have_text(label)
                    expect(trigger).to_have_attribute("aria-expanded", "false")

                    page.get_by_role("button", name="Toggle sidebar").first.click()
                    expect(outline).to_be_visible()
                    expect(compact).to_be_hidden()
                    self.assertGreaterEqual(page.locator("#main-content").evaluate("el => el.clientWidth"), 992)
                    expect(outline.locator(f'a[href="{href}"]')).to_have_attribute("aria-current", "location")
                    page.get_by_role("button", name="Toggle sidebar").first.click()
                    expect(compact).to_be_visible()
                    expect(compact.locator(f'a[href="{href}"]')).to_have_attribute("aria-current", "location")
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth - innerWidth"), 1)
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_compact_toc_keyboard_selection_continues_from_the_selected_section(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 900, "height": 900})
            page.emulate_media(reduced_motion="no-preference")
            evidence = BrowserEvidence(page)
            page.goto(f"{self.base_url}/site-dist/components/breadcrumb/")
            prepare_page(page, CERTIFICATION_CASES[0])
            compact = page.locator("#catalog-toc-compact")
            expect(compact).to_be_hidden()
            page.locator("#main-content").evaluate("el => el.scrollTo({top:700,behavior:'instant'})")
            expect(compact).to_be_visible()
            trigger = compact.get_by_role("button", name="On this page")
            trigger.press("ArrowDown")
            compact.locator('a[href="#dropdown"]').press("Enter")
            expect(page).to_have_url(f"{self.base_url}/site-dist/components/breadcrumb/#dropdown")
            expect(trigger).to_have_attribute("aria-expanded", "false")
            expect(compact.locator("[data-toc-current]")).to_have_text("Dropdown")

            page.keyboard.press("Tab")
            reading_position = page.evaluate("""
                () => {
                  const active = document.activeElement;
                  const target = document.getElementById('dropdown');
                  return {
                    inContent: document.getElementById('main-content').contains(active),
                    afterSection: Boolean(target.compareDocumentPosition(active) & Node.DOCUMENT_POSITION_FOLLOWING),
                    windowScrollY: window.scrollY,
                  };
                }
            """)
            self.assertEqual(
                reading_position,
                {"inContent": True, "afterSection": True, "windowScrollY": 0},
            )
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


class CatalogDirectionBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        # Exercise current catalog source against built Core assets without
        # rebuilding the distribution or changing any certification fixture.
        cls.state_script = create_environment().get_template(
            "js/catalog-direction-state.js.jinja"
        ).render(theme_builder_state=theme_builder_first_paint_payload())
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.addClassCleanup(cls.playwright_manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def catalog_page(self, case, *, variant="sidebar", state="expanded"):
        context = new_case_context(self.browser, case)
        context.add_init_script(
            "const preferences = " + json.dumps({
                "moo:theme": case.color_scheme,
                "moo:direction": case.direction,
                "moo:sidebar-variant": variant,
                "moo-sidebar:catalog-shell": state,
            }) + """;
            for (const [key, value] of Object.entries(preferences)) {
              if (localStorage.getItem(key) === null) localStorage.setItem(key, value);
            }
            """
        )
        context.route(
            "**/assets/js/catalog-direction-state.js*",
            lambda route: route.fulfill(
                content_type="text/javascript", body=self.state_script,
            ),
        )
        page = context.new_page()
        return context, page, BrowserEvidence(page)

    def open_catalog(self, page):
        response = page.goto(f"{self.base_url}{HOME_PAGE_PATH}", wait_until="load")
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)

    def assert_edge(self, page, direction, configured="left"):
        sidebar = page.locator("#catalog-sidebar")
        side = ("right" if configured == "left" else "left") if direction == "rtl" else configured
        expect(sidebar).to_have_attribute("data-side", side)
        box = sidebar.bounding_box()
        self.assertIsNotNone(box)
        edge = box["x"] + box["width"] if side == "right" else box["x"]
        expected = page.evaluate("innerWidth") if side == "right" else 0
        self.assertAlmostEqual(edge, expected, delta=1)
        self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))

    def assert_chevron(self, page, button, direction):
        page.wait_for_function(
            "button => (" + CHEVRON_DIRECTION + ")(button) === " + json.dumps(direction),
            arg=button.element_handle(),
        )
        expect(button.locator(".sidebar-menu-button__end svg")).to_have_attribute(
            "aria-hidden", "true",
        )

    def toggle_group(self, page, button, *, opened):
        button.click()
        target = page.locator("#" + button.get_attribute("aria-controls"))
        if opened:
            expect(target).to_have_class(re.compile(r"\bcollapse\b.*\bshow\b"))
        else:
            expect(target).not_to_have_class(re.compile(r"\bshow\b|\bcollapsing\b"))

    def test_catalog_restores_edge_and_chevrons_before_the_deferred_module(self):
        for reference, direction in itertools.product(CERTIFICATION_CASES, ("ltr", "rtl")):
            case = replace(reference, direction=direction)
            with self.subTest(case=case.name, direction=direction):
                context, page, evidence = self.catalog_page(case)
                try:
                    context.add_init_script(
                        "const readChevron = " + CHEVRON_DIRECTION + ";" + """
                        const sample = () => {
                          const sidebar = document.getElementById('catalog-sidebar');
                          const heading = document.querySelector('main h1');
                          const buttons = sidebar?.querySelectorAll('button.sidebar-menu-button--disclosure');
                          if (!heading?.getBoundingClientRect().height || !buttons?.length) {
                            requestAnimationFrame(sample); return;
                          }
                          window.__catalogDirectionFirstFrame = {
                            side: sidebar.dataset.side,
                            visibility: getComputedStyle(sidebar).visibility,
                            chevrons: [...buttons].map(readChevron),
                            moduleExecuted: Boolean(window.__catalogDirectionModuleExecuted),
                          };
                        };
                        requestAnimationFrame(sample);
                        """
                    )

                    def delayed_state(route):
                        time.sleep(0.15)
                        route.fulfill(content_type="text/javascript", body=self.state_script)

                    page.route("**/assets/js/catalog-direction-state.js*", delayed_state)
                    def delayed_module(route):
                        page.wait_for_function("window.__catalogDirectionFirstFrame", timeout=5000)
                        route.fulfill(
                            content_type="text/javascript",
                            body="window.__catalogDirectionModuleExecuted = true;",
                        )

                    page.route("**/assets/js/catalog/index.js*", delayed_module)
                    self.open_catalog(page)
                    page.wait_for_function("window.__catalogDirectionFirstFrame")
                    frame = page.evaluate("window.__catalogDirectionFirstFrame")
                    self.assertEqual(frame["side"], "right" if direction == "rtl" else "left")
                    self.assertFalse(frame["moduleExecuted"])
                    self.assertTrue(page.evaluate("window.__catalogDirectionModuleExecuted"))
                    self.assertEqual(set(frame["chevrons"]), {"left" if direction == "rtl" else "right"})
                    if case.is_mobile:
                        self.assertEqual(frame["visibility"], "hidden")
                    else:
                        self.assert_edge(page, direction)
                    expect(page.locator('[data-sidebar-key="catalog-shell"]')).not_to_have_attribute(
                        "data-sidebar-ready", "",
                    )
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_repeated_direction_initialization_preserves_the_configured_edge(self):
        desktop = next(case for case in CERTIFICATION_CASES if not case.is_mobile)
        for direction, configured in itertools.product(("ltr", "rtl"), ("left", "right")):
            with self.subTest(direction=direction, configured=configured):
                case = replace(desktop, direction=direction)
                context, page, evidence = self.catalog_page(case)
                try:
                    # Exercise the first configured bind, then replay it. The
                    # separate first-frame test covers automatic early loading.
                    page.route(
                        "**/assets/js/catalog-direction-state.js*",
                        lambda route: route.fulfill(content_type="text/javascript", body=""),
                    )
                    self.open_catalog(page)
                    page.locator("#catalog-sidebar").evaluate("""(el, side) => {
                        delete el.dataset.catalogConfiguredSide;
                        el.dataset.side = side;
                    }""", configured)
                    for _ in range(2):
                        page.evaluate("""source => {
                            const script = document.createElement('script');
                            script.textContent = source;
                            document.querySelector('.moo-ui[data-bs-theme]').append(script);
                            script.remove();
                        }""", self.state_script)
                        expect(page.locator("#catalog-sidebar")).to_have_attribute("data-catalog-configured-side", configured)
                        expect(page.locator("#catalog-sidebar")).to_have_attribute("data-catalog-direction-bound", "")
                        expect(page.locator("#catalog-sidebar")).to_be_visible()
                        self.assert_edge(page, direction, configured)
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_late_disclosure_icon_follows_direction_without_a_state_change(self):
        desktop = next(case for case in CERTIFICATION_CASES if not case.is_mobile)
        for direction in ("ltr", "rtl"):
            with self.subTest(direction=direction):
                context, page, evidence = self.catalog_page(replace(desktop, direction=direction))
                try:
                    self.open_catalog(page)
                    button = page.locator("#catalog-sidebar button.sidebar-menu-button--disclosure").first
                    end = button.locator(".sidebar-menu-button__end")
                    end.locator("svg").evaluate("el => el.remove()")
                    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                    wrong_icon = "chevron-left" if direction == "ltr" else "chevron-right"
                    markup = create_environment().from_string(
                        '{{ render_icon(name, "inline-end") }}'
                    ).render(name=wrong_icon)
                    end.evaluate("""(el, markup) => {
                        const template = document.createElement('template');
                        template.innerHTML = markup;
                        el.append(template.content);
                    }""", markup)
                    self.assert_chevron(page, button, "right" if direction == "ltr" else "left")
                    expect(button).to_have_attribute("aria-expanded", "false")
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_catalog_mirrors_sidebar_variants_and_rail_without_changing_collapse_state(self):
        for reference, direction, variant, state in itertools.product(
            CERTIFICATION_CASES, ("ltr", "rtl"), ("sidebar", "floating", "inset"),
            ("expanded", "collapsed"),
        ):
            case = replace(reference, direction=direction)
            with self.subTest(case=case.name, direction=direction, variant=variant, state=state):
                context, page, evidence = self.catalog_page(case, variant=variant, state=state)
                try:
                    self.open_catalog(page)
                    shell = page.locator('[data-sidebar-key="catalog-shell"]')
                    expect(shell).to_have_attribute("data-sidebar-ready", "")
                    expect(shell).to_have_attribute("data-sidebar-state", state)
                    sidebar = page.locator("#catalog-sidebar")
                    expect(sidebar).to_have_attribute("data-variant", variant)
                    if case.is_mobile:
                        expect(sidebar).to_have_css("visibility", "hidden")
                        trigger = page.locator("[data-sidebar-trigger]")
                        page.evaluate("""() => {
                            window.__catalogSidebarShown = false;
                            document.getElementById('catalog-sidebar').addEventListener(
                                'shown.bs.offcanvas', () => { window.__catalogSidebarShown = true; },
                                {once: true},
                            );
                        }""")
                        trigger.click()
                        page.wait_for_function("window.__catalogSidebarShown === true")
                        expect(sidebar).to_have_css("transform", "none")
                        self.assert_edge(page, direction)
                        page.keyboard.press("Escape")
                        expect(sidebar).to_have_css("visibility", "hidden")
                        expect(trigger).to_be_focused()
                    else:
                        self.assert_edge(page, direction)
                        box = sidebar.bounding_box()
                        rail = sidebar.locator(".sidebar-rail").bounding_box()
                        boundary = box["x"] if direction == "rtl" else box["x"] + box["width"]
                        self.assertAlmostEqual(rail["x"] + rail["width"] / 2, boundary, delta=1)
                    expect(shell).to_have_attribute("data-sidebar-state", state)
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_catalog_chevrons_follow_open_state_and_live_direction(self):
        for reference, direction in itertools.product(CERTIFICATION_CASES, ("ltr", "rtl")):
            case = replace(reference, direction=direction)
            with self.subTest(case=case.name, direction=direction):
                context, page, evidence = self.catalog_page(case)
                try:
                    self.open_catalog(page)
                    if case.is_mobile:
                        page.locator("[data-sidebar-trigger]").click()
                        expect(page.locator("#catalog-sidebar")).to_have_css("transform", "none")
                    buttons = page.locator("#catalog-sidebar button.sidebar-menu-button--disclosure")
                    self.assertGreater(buttons.count(), 0)
                    for button in buttons.all():
                        button.scroll_into_view_if_needed()
                        self.assert_chevron(page, button, "left" if direction == "rtl" else "right")
                        self.toggle_group(page, button, opened=True)
                        self.assert_chevron(page, button, "down")
                        opposite = "ltr" if direction == "rtl" else "rtl"
                        page.evaluate("value => document.documentElement.dir = value", opposite)
                        self.assert_chevron(page, button, "down")
                        self.toggle_group(page, button, opened=False)
                        self.assert_chevron(page, button, "right" if direction == "rtl" else "left")
                        page.evaluate("value => document.documentElement.dir = value", direction)
                        self.assert_chevron(page, button, "left" if direction == "rtl" else "right")
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_catalog_direction_controls_persist_and_reset_placement_and_chevrons(self):
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context, page, evidence = self.catalog_page(case, variant="floating")
                try:
                    self.open_catalog(page)
                    sidebar = page.locator("#catalog-sidebar")
                    if case.is_mobile:
                        page.locator("[data-sidebar-trigger]").click()
                        expect(sidebar).to_have_css("transform", "none")
                    group = sidebar.locator("button.sidebar-menu-button--disclosure").first
                    self.toggle_group(page, group, opened=True)
                    if case.is_mobile:
                        page.keyboard.press("Escape")
                        expect(sidebar).to_have_css("visibility", "hidden")
                    page.locator('button[data-bs-target="#catalog-settings"]').click()
                    settings = page.locator("#catalog-settings")
                    for direction in ("rtl", "ltr", "rtl"):
                        settings.locator(
                            f'input[data-moo-settings-direction][value="{direction}"]'
                        ).locator("..").click()
                        expect(page.locator("html")).to_have_attribute("dir", direction)
                        expect(page.locator("#catalog-sidebar")).to_have_attribute(
                            "data-side", "right" if direction == "rtl" else "left",
                        )
                        self.assert_chevron(page, group, "down")
                    settings.locator('[data-bs-dismiss="offcanvas"]').click()
                    page.reload(wait_until="load")
                    expect(page.locator("html")).to_have_attribute("dir", "rtl")
                    expect(page.locator("#catalog-sidebar")).to_have_attribute("data-side", "right")
                    expect(page.locator("#catalog-sidebar")).to_have_attribute("data-variant", "floating")
                    page.locator('button[data-bs-target="#catalog-settings"]').click()
                    settings.locator("[data-moo-settings-reset]").click()
                    expect(page.locator("html")).to_have_attribute("dir", "ltr")
                    expect(page.locator("#catalog-sidebar")).to_have_attribute("data-side", "left")
                    expect(page.locator("#catalog-sidebar")).to_have_attribute("data-variant", "sidebar")
                    self.assertIsNone(page.evaluate("localStorage.getItem('moo:direction')"))
                    for button in page.locator("#catalog-sidebar button.sidebar-menu-button--disclosure").all():
                        self.assert_chevron(page, button, "right")
                    evidence.assert_clean()
                finally:
                    context.close()


if __name__ == "__main__":
    unittest.main()
