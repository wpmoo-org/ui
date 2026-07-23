from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/tabs.html.jinja"
PAGE = ROOT / "src/pages/components/tabs.html.jinja"


class TabsTests(CatalogTestCase):
    def render_tabs(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Tabs macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/tabs.html.jinja" import tabs %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_tabs_renders_pills_list_and_tab_content(self) -> None:
        output = self.render_tabs(
            'tabs("t", [{"id": "a", "title": "A", "content": "Content A"}])'
        )

        self.assertIn('<div class="tabs-list nav nav-pills" id="t-list" role="tablist">', output)
        self.assertIn('<div class="tab-content" id="t-content">', output)
        self.assertIn("Content A", output)

    def test_tabs_first_item_is_active_by_default(self) -> None:
        output = self.render_tabs(
            'tabs("t", [{"id": "a", "title": "A", "content": "Content A"}, '
            '{"id": "b", "title": "B", "content": "Content B"}])'
        )

        self.assertIn('id="t-a-tab"', output)
        self.assertIn('class="nav-link active"', output)
        self.assertIn('aria-selected="true"', output)
        self.assertIn('class="tab-pane fade show active"', output)

    def test_tabs_explicit_active_overrides_first_item(self) -> None:
        output = self.render_tabs(
            'tabs("t", [{"id": "a", "title": "A", "content": "Content A"}, '
            '{"id": "b", "title": "B", "content": "Content B", "active": true}])'
        )

        self.assertIn('id="t-b-tab" data-bs-toggle="tab" data-bs-target="#t-b-pane"'
                       ' type="button" role="tab" aria-controls="t-b-pane"'
                       ' aria-selected="true"', output)
        self.assertNotIn('id="t-a-tab" data-bs-toggle="tab" data-bs-target="#t-a-pane"'
                          ' type="button" role="tab" aria-controls="t-a-pane"'
                          ' aria-selected="true"', output)

    def test_tabs_item_disabled_adds_attribute(self) -> None:
        output = self.render_tabs(
            'tabs("t", [{"id": "a", "title": "A", "content": "Content A", "disabled": true}])'
        )

        self.assertIn("disabled>", output)

    def test_tabs_content_is_not_escaped(self) -> None:
        output = self.render_tabs(
            'tabs("t", [{"id": "a", "title": "A", "content": "See <code>docs</code>."}])'
        )

        self.assertIn("See <code>docs</code>.", output)

    def test_tabs_css_keeps_panes_stable_and_animates_switches(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        tab_content = css.rsplit(".tab-content {", 1)[1].split("}", 1)[0]
        self.assertIn("width: 100%;", tab_content)
        self.assertIn("max-width: 100%;", tab_content)
        self.assertIn("min-width: 0;", tab_content)
        tab_pane = css.rsplit(".tab-content > .tab-pane {", 1)[1].split("}", 1)[0]
        self.assertIn("display: block;", tab_pane)
        self.assertIn("width: 100%;", tab_pane)
        self.assertIn("max-width: 100%;", tab_pane)
        self.assertIn("min-width: 0;", tab_pane)
        self.assertIn("opacity: 0;", tab_pane)
        self.assertIn("transform: translateY(0.25rem);", tab_pane)
        self.assertIn("pointer-events: none;", tab_pane)
        self.assertIn("transition: opacity 0.16s ease", tab_pane)
        active_tab_pane = css.rsplit(".tab-content > .active {", 1)[1].split("}", 1)[0]
        self.assertIn("opacity: 1;", active_tab_pane)
        self.assertIn("transform: none;", active_tab_pane)
        self.assertIn("pointer-events: auto;", active_tab_pane)

    def test_catalog_tabs_freeze_smooth_scroll_during_handoff(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        script = self.read_output("assets/js/preview.js")
        self.assertIn("freezeCatalogScrollForTab", script)
        self.assertIn("captureCatalogScrollForTab", script)
        self.assertIn("pendingCatalogTabScrollTop", script)
        self.assertIn('document.addEventListener("pointerdown"', script)
        self.assertIn('document.addEventListener("show.bs.tab"', script)
        self.assertIn('trigger.closest(".tabs-list")', script)
        self.assertIn('catalogMain.style.scrollBehavior = "auto";', script)
        self.assertIn("catalogMain.scrollTop = currentScrollTop;", script)

    def test_tabs_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tabs id is required"):
            self.render_tabs(
                'tabs("   ", [{"id": "a", "title": "A", "content": "Content A"}])'
            )

    def test_tabs_requires_items(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tabs requires at least one item"):
            self.render_tabs('tabs("t", [])')

    def test_tabs_requires_item_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tabs item id is required"):
            self.render_tabs(
                'tabs("t", [{"id": "   ", "title": "A", "content": "Content A"}])'
            )

    def test_tabs_requires_item_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tabs item title is required"):
            self.render_tabs(
                'tabs("t", [{"id": "a", "title": "   ", "content": "Content A"}])'
            )
