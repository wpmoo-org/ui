from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase, lucide_body


COMPONENT = ROOT / "src/components/collapsible.html.jinja"
PAGE = ROOT / "src/pages/components/collapsible.html.jinja"


class CollapsibleTests(CatalogTestCase):
    def render_collapsible(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Collapsible macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/collapsible.html.jinja" import collapsible %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_collapsible_renders_header_trigger_and_collapsed_panel(self) -> None:
        output = self.render_collapsible(
            'collapsible("panel", "Order #4189", "Placed on March 14.")'
        )

        self.assertIn('<div class="collapsible-header">', output)
        self.assertIn('<h4 class="collapsible-title">Order #4189</h4>', output)
        self.assertIn(lucide_body("chevrons-up-down"), output)
        self.assertIn('data-bs-toggle="collapse"', output)
        self.assertIn('data-bs-target="#panel"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertIn('aria-controls="panel"', output)
        self.assertIn('id="panel" class="collapse"', output)
        self.assertIn(
            '<div class="collapsible-content">Placed on March 14.</div>', output
        )

    def test_collapsible_open_shows_panel_and_sets_aria_expanded(self) -> None:
        output = self.render_collapsible(
            'collapsible("panel", "Order #4189", "Placed on March 14.", open=true)'
        )

        self.assertIn('aria-expanded="true"', output)
        self.assertIn('id="panel" class="collapse show"', output)

    def test_collapsible_trigger_uses_aria_label_not_visible_text(self) -> None:
        output = self.render_collapsible(
            'collapsible("panel", "Order #4189", "Details.", '
            'trigger_aria_label="Toggle order details")'
        )

        self.assertIn('aria-label="Toggle order details"', output)

    def test_collapsible_content_is_not_escaped(self) -> None:
        output = self.render_collapsible(
            'collapsible("panel", "Title", "See <code>docs</code>.")'
        )

        self.assertIn("See <code>docs</code>.", output)

    def test_collapsible_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Collapsible id is required"):
            self.render_collapsible('collapsible("   ", "Title", "Content")')

    def test_collapsible_requires_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Collapsible title is required"):
            self.render_collapsible('collapsible("panel", "   ", "Content")')

    def test_collapsible_requires_content(self) -> None:
        with self.assertRaisesRegex(ValueError, "Collapsible content is required"):
            self.render_collapsible('collapsible("panel", "Title", "   ")')

    def test_page_uses_render_rtl_example(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "includes/example.html.jinja" import render_example, render_rtl_example %}',
            source,
        )
        self.assertIn("render_rtl_example(", source)
        self.assertIn("collapsible-ribbon", source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertIn('dir="rtl"', source)
        self.assertIn(
            "Compare RTL behavior for task and workflow examples across Arabic, Hebrew, and English content.",
            source,
        )
        self.assertNotIn("Right-to-left layout", source)
        self.assertNotIn("title_id=", source)
        self.assertNotIn(
            '{% from "components/tabs.html.jinja" import tabs %}',
            source,
        )

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/collapsible.html")
        self.assertIn("collapsible-ribbon-direction-tabs", output)
        self.assertIn("rtl-arabic-code", output)
        self.assertIn("rtl-hebrew-code", output)
        self.assertIn("rtl-english-code", output)
        self.assertIn(">Arabic</button>", output)
        self.assertIn(">Hebrew</button>", output)
        self.assertIn(">English</button>", output)
        self.assertIn('id="rtl">RTL</h2>', output)
