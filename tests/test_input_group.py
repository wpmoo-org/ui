from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/input_group.html.jinja"
PAGE = ROOT / "src/pages/components/input-group.html.jinja"


class InputGroupTests(CatalogTestCase):
    def render_template(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Input Group macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def test_input_group_wraps_native_bootstrap_markup(self) -> None:
        output = self.render_template(
            '{% from "components/input_group.html.jinja" import '
            "input_group, input_group_text %}"
            '{% call input_group(dir="rtl") %}'
            '{{ input_group_text("@", id="addon") }}'
            '<input class="form-control" aria-label="Username">'
            "{% endcall %}"
        )

        self.assertEqual(
            output,
            '<div class="input-group" dir="rtl"> <span class="input-group-text" '
            'id="addon">@</span><input class="form-control" '
            'aria-label="Username"> </div>',
        )

    def test_block_addon_maps_logical_alignment_and_classes(self) -> None:
        for align, expected in (
            ("start", '<div data-align="block-start"> Header </div>'),
            (
                "end",
                '<div class="d-flex gap-2" data-align="block-end"> Footer </div>',
            ),
        ):
            with self.subTest(align=align):
                extra_class = ', extra_class="d-flex gap-2"' if align == "end" else ""
                output = self.render_template(
                    '{% from "components/input_group.html.jinja" import '
                    "input_group_block_addon %}"
                    f'{{% call input_group_block_addon("{align}"{extra_class}) %}}'
                    f"{'Header' if align == 'start' else 'Footer'}"
                    "{% endcall %}"
                )

                self.assertEqual(output, expected)

    def test_input_group_fails_fast_for_unknown_contracts(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "macro 'input_group' takes no keyword argument 'size'",
        ):
            self.render_template(
                '{% from "components/input_group.html.jinja" import input_group %}'
                '{% call input_group(size="lg") %}x{% endcall %}'
            )

        invalid_templates = (
            (
                '{% from "components/input_group.html.jinja" import input_group %}'
                '{% call input_group(dir="sideways") %}x{% endcall %}',
                "Unknown input group direction: sideways",
            ),
            (
                '{% from "components/input_group.html.jinja" import '
                "input_group_text %}"
                '{{ input_group_text("   ") }}',
                "Input group text content is required",
            ),
            (
                '{% from "components/input_group.html.jinja" import '
                "input_group_block_addon %}"
                '{% call input_group_block_addon("middle") %}x{% endcall %}',
                "Unknown input group block addon alignment: middle",
            ),
        )

        for source, message in invalid_templates:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_template(source)
