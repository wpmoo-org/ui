from __future__ import annotations

import unittest
from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT
from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class TableOfContentsBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def open_example(self, viewport: dict[str, int] | None = None, fragment: str = "", **options: object):
        context = self.browser.new_context(viewport=viewport or {"width": 390, "height": 844}, reduced_motion="reduce")
        self.addCleanup(context.close)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        self.addCleanup(evidence.assert_clean)
        source = (ROOT / "conformance/table-of-contents/index.html.jinja").read_text(encoding="utf-8")
        html = create_environment().from_string(source).render(**options)
        page.route("**/conformance/table-of-contents/index.html*", lambda route: route.fulfill(content_type="text/html", body=html))
        page.goto(f"{self.base_url}/conformance/table-of-contents/index.html{fragment}")
        expected = 3 if options.get("second_owner") else 2
        page.wait_for_function("expected => import('/conformance/table-of-contents/init.js').then(m => m.instances.length === expected)", arg=expected)
        return page

    def test_compact_navigation_uses_native_hash_and_keyboard_disclosure(self) -> None:
        page = self.open_example(theme="dark", direction="rtl")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")
        trigger = page.locator("#toc-compact button")
        trigger.focus()
        trigger.press("ArrowDown")
        expect(trigger).to_have_attribute("aria-expanded", "true")
        page.locator("#toc-compact .dropdown-item").first.press("Escape")
        expect(trigger).to_have_attribute("aria-expanded", "false")
        trigger.click()
        page.locator('#toc-compact a[href="#intro"]').click()
        expect(page).to_have_url(f"{self.base_url}/conformance/table-of-contents/index.html#intro")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Introduction")
        expect(page.locator('#toc-list a[href="#intro"]')).to_have_attribute("aria-current", "location")

    def test_short_document_does_not_select_last_section_on_initialization(self) -> None:
        page = self.open_example(short=True, viewport={"width": 1440, "height": 1600})
        self.assertTrue(page.evaluate("document.scrollingElement.scrollHeight <= document.scrollingElement.clientHeight"))
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")
        self.assertEqual(page.locator("[data-toc] [aria-current]").count(), 0)

    def test_short_document_tracks_explicit_fragments_on_load_and_navigation(self) -> None:
        page = self.open_example(short=True, viewport={"width": 1440, "height": 1600}, fragment="#intro")
        self.assertTrue(page.evaluate("document.scrollingElement.scrollHeight <= document.scrollingElement.clientHeight"))
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Introduction")
        expect(page.locator('#toc-list a[href="#intro"]')).to_have_attribute("aria-current", "location")
        page.locator('#toc-list a[href="#languages"]').click()
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Languages")
        expect(page.locator('#toc-list a[href="#languages"]')).to_have_attribute("aria-current", "location")
        page.evaluate("window.location.hash = ''")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")

    def test_scroll_end_updates_both_views_and_dispose_restores_initial_state(self) -> None:
        page = self.open_example()
        page.evaluate("window.scrollTo(0, document.scrollingElement.scrollHeight)")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Languages")
        page.evaluate("async () => { const m = await import('/conformance/table-of-contents/init.js'); m.instances.forEach(i => i.dispose()); }")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")
        self.assertEqual(page.locator("[data-toc] [aria-current]").count(), 0)

    def test_encoded_targets_missing_content_and_refresh(self) -> None:
        page = self.open_example()
        page.evaluate("async () => { const {default:Toc} = await import('/src/js/components/table-of-contents.js'); const root = document.getElementById('toc-compact'); const instance = Toc.getOrCreateInstance(root); window.tocSameInstance = instance === Toc.getInstance(root); document.getElementById('languages').id = 'über/x#y'; root.querySelector('a[href=\"#languages\"]').setAttribute('href', '#%C3%BCber%2Fx%23y'); instance.refresh(); }")
        self.assertTrue(page.evaluate("window.tocSameInstance"))
        page.locator("#toc-compact button").click()
        page.locator('#toc-compact a[href="#%C3%BCber%2Fx%23y"]').click()
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Languages")
        page.evaluate("async () => { const {default:Toc} = await import('/src/js/components/table-of-contents.js'); const root = document.getElementById('toc-compact'); root.dataset.tocContent = 'missing'; Toc.getInstance(root).refresh(); }")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")
        self.assertEqual(page.locator("#toc-compact a").count(), 3)

    def test_nested_scroll_root_and_owner_scope_are_explicit(self) -> None:
        page = self.open_example(nested=True)
        page.evaluate("document.getElementById('reader').scrollTop = document.getElementById('reader').scrollHeight")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Languages")
        page.evaluate("async () => { const {default:Toc} = await import('/src/js/components/table-of-contents.js'); const root = document.getElementById('toc-compact'); root.dataset.tocContent = 'outside-content'; Toc.getInstance(root).refresh(); }")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")

    def test_nested_scroll_root_tracks_native_fragment_on_initial_load(self) -> None:
        page = self.open_example(nested=True, fragment="#content")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Content and configuration")
        expect(page.locator('#toc-list a[href="#content"]')).to_have_attribute("aria-current", "location")
        self.assertGreater(page.locator("#reader").evaluate("element => element.scrollTop"), 0)

    def test_pending_update_is_cancelled_and_invalid_offsets_fail(self) -> None:
        page = self.open_example()
        result = page.evaluate("async () => { const {default:Toc} = await import('/src/js/components/table-of-contents.js'); const root = document.getElementById('toc-compact'); const instance = Toc.getInstance(root); let rejected = 0; for (const activationOffset of [-1, Infinity, '0']) { try { instance.refresh({activationOffset}); } catch { rejected++; } } window.dispatchEvent(new Event('resize')); instance.dispose(); await new Promise(requestAnimationFrame); return {rejected, disposed: Toc.getInstance(root) === null}; }")
        self.assertEqual(result, {"rejected": 3, "disposed": True})

    def test_independent_owner_cannot_be_selected_as_another_toc_scope(self) -> None:
        page = self.open_example(short=True, second_owner=True)
        page.evaluate("async () => { const {default:Toc} = await import('/src/js/components/table-of-contents.js'); const root = document.getElementById('toc-compact'); root.dataset.tocContent = 'other-article'; Toc.getInstance(root).refresh(); }")
        page.locator("#other-toc button").click()
        page.locator('#other-toc a[href="#other-section"]').click()
        expect(page.locator("#other-toc [data-toc-current]")).to_have_text("Independent section")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Overview")

    def test_accepted_compact_panel_width_and_stationary_header(self) -> None:
        for theme, direction in (("light", "ltr"), ("dark", "rtl")):
            with self.subTest(theme=theme, direction=direction):
                page = self.open_example(nested=True, theme=theme, direction=direction, long_labels=True)
                header_before = page.locator("header").bounding_box()
                bar_before = page.locator("#toc-compact").bounding_box()
                trigger = page.locator("#toc-compact button")
                trigger.click()
                menu = page.locator("#toc-compact .dropdown-menu")
                expect(menu).to_be_visible()
                panel = menu.bounding_box()
                self.assertAlmostEqual(panel["x"], bar_before["x"], delta=1)
                self.assertAlmostEqual(panel["width"], bar_before["width"], delta=1)
                self.assertLessEqual(menu.evaluate("el => el.scrollWidth - el.clientWidth"), 1)
                page.locator('#toc-compact a[href="#content"]').click()
                expect(menu).not_to_be_visible()
                expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Content and configuration")
                self.assertGreater(page.locator("#reader").evaluate("el => el.scrollTop"), 0)
                header_after = page.locator("header").bounding_box()
                bar_after = page.locator("#toc-compact").bounding_box()
                self.assertAlmostEqual(header_after["y"], header_before["y"], delta=1)
                self.assertAlmostEqual(bar_after["y"], bar_before["y"], delta=1)
                self.assertGreaterEqual(page.locator("#content").bounding_box()["y"], header_after["y"] + header_after["height"] - 1)
                expect(page.locator('#toc-compact a[href="#content"]')).to_have_attribute("aria-current", "location")

    def test_accepted_mobile_aside_follows_article_and_remains_open(self) -> None:
        page = self.open_example(nested=True)
        page.locator("#reader").evaluate("el => { el.scrollTop = el.scrollHeight; }")
        expect(page.locator("#toc-compact [data-toc-current]")).to_have_text("Languages")
        article = page.locator("#toc-article").bounding_box()
        aside = page.get_by_role("complementary", name="Page information").bounding_box()
        reader = page.locator("#reader").bounding_box()
        self.assertGreaterEqual(aside["y"], article["y"] + article["height"] - 1)
        self.assertGreaterEqual(aside["y"], reader["y"] - 1)
        self.assertLessEqual(aside["y"] + aside["height"], reader["y"] + reader["height"] + 1)
        expect(page.get_by_role("heading", name="Useful information")).to_be_visible()
        self.assertEqual(page.get_by_role("heading", name="Useful information").count(), 1)

    def test_accepted_breakpoint_exposes_one_presentation_at_a_time(self) -> None:
        page = self.open_example(nested=True, viewport={"width": 1199, "height": 900})
        expect(page.locator("#toc-compact")).to_be_visible()
        expect(page.locator("#toc-list")).not_to_be_visible()
        page.set_viewport_size({"width": 1200, "height": 900})
        expect(page.locator("#toc-compact")).not_to_be_visible()
        expect(page.locator("#toc-list")).to_be_visible()
        article = page.locator("#toc-article").bounding_box()
        aside = page.get_by_role("complementary", name="Page information").bounding_box()
        self.assertGreaterEqual(aside["x"], article["x"] + article["width"] - 1)
