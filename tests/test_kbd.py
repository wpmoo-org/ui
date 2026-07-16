from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/kbd.html.jinja"
PAGE = ROOT / "src/pages/components/kbd.html.jinja"


class KbdTests(CatalogTestCase):
    def render_kbd(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Kbd macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/kbd.html.jinja" import kbd %}'
            f"{{{{ {call} }}}}"
        )
        return template.render().strip()

    def read_kbd_output(self) -> str:
        output = DIST / "components/kbd.html"
        self.assertTrue(output.is_file(), "Kbd catalog output is not implemented")
        return output.read_text(encoding="utf-8")

    def test_kbd_uses_native_markup_and_autoescapes_text(self) -> None:
        self.assertEqual(self.render_kbd('kbd("K")'), "<kbd>K</kbd>")
        self.assertEqual(
            self.render_kbd('kbd("<script>")'),
            "<kbd>&lt;script&gt;</kbd>",
        )

    def test_kbd_rejects_blank_text(self) -> None:
        self.assertTrue(COMPONENT.is_file(), "Kbd macro is not implemented")
        for call in ('kbd("")', 'kbd("   ")'):
            with self.subTest(call=call):
                with self.assertRaisesRegex(ValueError, "Kbd text is required"):
                    self.render_kbd(call)
