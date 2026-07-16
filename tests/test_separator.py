from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/separator.html.jinja"
PAGE = ROOT / "src/pages/components/separator.html.jinja"


class SeparatorTests(CatalogTestCase):
    def render_separator(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Separator macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/separator.html.jinja" import separator %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_separator_renders_native_horizontal_and_vertical_rules(self) -> None:
        self.assertEqual(self.render_separator("separator()"), '<hr aria-hidden="true">')
        self.assertEqual(
            self.render_separator('separator("vertical")'),
            '<div class="vr" aria-hidden="true"></div>',
        )
        self.assertEqual(
            self.render_separator('separator("vertical", decorative=false)'),
            '<div class="vr" role="separator" aria-orientation="vertical"></div>',
        )
        self.assertEqual(
            self.render_separator('separator(extra_class="my-4")'),
            '<hr class="my-4" aria-hidden="true">',
        )

    def test_separator_rejects_unknown_orientation(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown separator orientation: diagonal"):
            self.render_separator('separator("diagonal")')
