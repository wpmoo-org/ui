from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/badge.html.jinja"
PAGE = ROOT / "src/pages/components/badge.html.jinja"


class BadgeTests(CatalogTestCase):
    def render_badge(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Badge macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/badge.html.jinja" import badge %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_badge_maps_variants_to_bootstrap_utilities(self) -> None:
        self.assertIn('class="badge text-bg-primary"', self.render_badge('badge("Default")'))
        self.assertIn(
            'class="badge text-bg-secondary rounded-pill"',
            self.render_badge('badge("Secondary", variant="secondary", pill=true)'),
        )
        self.assertIn(
            'class="badge text-bg-danger"',
            self.render_badge('badge("Delete", variant="destructive")'),
        )
        self.assertIn(
            'class="badge border text-body-secondary"',
            self.render_badge('badge("Outline", variant="outline")'),
        )

    def test_badge_requires_known_variant_and_visible_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown badge variant: ghost"):
            self.render_badge('badge("Ghost", variant="ghost")')
        with self.assertRaisesRegex(ValueError, "Badge label is required"):
            self.render_badge('badge("   ")')

    def test_badge_can_add_visually_hidden_context(self) -> None:
        output = self.render_badge(
            'badge("12", variant="secondary", visually_hidden="unread messages")'
        )

        self.assertIn("12", output)
        self.assertIn(
            '<span class="visually-hidden">unread messages</span>',
            output,
        )
