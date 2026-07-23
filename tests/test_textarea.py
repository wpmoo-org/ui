from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/textarea.html.jinja"
PAGE = ROOT / "src/pages/components/textarea.html.jinja"


class TextareaTests(CatalogTestCase):
    def render_textarea(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Textarea macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/textarea.html.jinja" import textarea %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_visible_label_is_linked_to_native_textarea(self) -> None:
        output = self.render_textarea(
            'textarea(label="<Message>", id="message", '
            'placeholder="<draft>", value="<hello>", rows=4)'
        )

        self.assertEqual(
            output,
            '<label class="form-label" for="message">&lt;Message&gt;</label> '
            '<textarea class="form-control" id="message" rows="4" '
            'placeholder="&lt;draft&gt;">&lt;hello&gt;</textarea>',
        )

    def test_textarea_requires_exactly_one_accessible_name_source(self) -> None:
        for call in (
            "textarea()",
            'textarea(label="   ", aria_label="")',
            'textarea(label="Message", aria_label="Message", id="message")',
            'textarea(placeholder="Message")',
        ):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    ValueError,
                    "Textarea requires exactly one of label or aria_label",
                ):
                    self.render_textarea(call)

    def test_textarea_validates_label_size_and_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "Visible textarea labels require id"):
            self.render_textarea('textarea(label="Message")')
        with self.assertRaisesRegex(ValueError, "Unknown textarea size: xl"):
            self.render_textarea('textarea(aria_label="Message", size="xl")')
        with self.assertRaisesRegex(ValueError, "Textarea rows must be positive"):
            self.render_textarea('textarea(aria_label="Message", rows=0)')

    def test_textarea_emits_native_states(self) -> None:
        output = self.render_textarea(
            'textarea(aria_label="Message", size="lg", aria_invalid=true, '
            'disabled=true, readonly=true)'
        )

        self.assertIn(" form-control-lg", output)
        self.assertIn(" is-invalid", output)
        self.assertIn(' aria-invalid="true"', output)
        self.assertIn(" disabled", output)
        self.assertIn(" readonly", output)

    def test_textarea_describedby_links_helper_text(self) -> None:
        output = self.render_textarea(
            'textarea(label="Message", id="message", describedby="message-help")'
        )

        self.assertIn('aria-describedby="message-help"', output)

    def test_button_example_uses_render_example_argument_order(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/textarea.html")
        self.assertIn('id="button-title">Button</', output)
        self.assertIn(
            "Connect a compact textarea to a form action when composition needs a quick send step.",
            output,
        )
        self.assertNotIn(">moo-example__preview--narrow<", output)
