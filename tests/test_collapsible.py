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
