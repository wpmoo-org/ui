from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/input_group.html.jinja"
PAGE = ROOT / "site/src/pages/components/input-group.html.jinja"
FIXTURE = ROOT / "tests/fixtures/certification/input-group.html"


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

    def test_validation_groups_are_not_forced_to_single_row_height(self) -> None:
        source = (ROOT / "scss/components/_input_group.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            ".input-group:not(:has(> :is(.valid-feedback, .invalid-feedback, .valid-tooltip, .invalid-tooltip))):not(:has(textarea)):not(:has(> .form-control[type=\"file\"])):not(:has(> [data-align])) {",
            source,
        )
        self.assertIn(
            ".input-group:not(:has(> :is(.valid-feedback, .invalid-feedback, .valid-tooltip, .invalid-tooltip))):not(:has(textarea)):not(:has(> .form-control[type=\"file\"])):not(:has(> [data-align])) > .form-control {",
            source,
        )

    def test_invalid_validation_group_draws_compound_invalid_ring(self) -> None:
        source = (ROOT / "scss/foundations/_focus.scss").read_text(
            encoding="utf-8"
        )
        feedback_exclusion = (
            ":not(:has(> :is(.valid-feedback, .invalid-feedback, "
            ".valid-tooltip, .invalid-tooltip)))"
        )

        self.assertIn(
            ".input-group.has-validation"
            f"{feedback_exclusion}:has(> :is(.form-control, .form-select).is-invalid),",
            source,
        )
        self.assertIn(
            ".was-validated .input-group.has-validation"
            f"{feedback_exclusion}:has(> :is(.form-control, .form-select):invalid) {{",
            source,
        )
        self.assertIn(
            "border-color: var(--bs-form-invalid-border-color);",
            source,
        )
        self.assertIn(
            "box-shadow: 0 0 0 #{$moo-form-focus-ring-width} var(--moo-form-invalid-ring-color);",
            source,
        )
        self.assertIn(
            ".input-group.has-validation"
            f"{feedback_exclusion} > :is(.form-control, .form-select).is-invalid,",
            source,
        )
        self.assertIn(
            ".was-validated .input-group.has-validation"
            f"{feedback_exclusion} > :is(.form-control, .form-select):invalid {{",
            source,
        )
        child_block = re.search(
            r"\.input-group\.has-validation:not\(:has\(> :is\(\.valid-feedback, \.invalid-feedback, \.valid-tooltip, \.invalid-tooltip\)\)\) > :is\(\.form-control, \.form-select\)\.is-invalid,"
            r".*?\.was-validated \.input-group\.has-validation:not\(:has\(> :is\(\.valid-feedback, \.invalid-feedback, \.valid-tooltip, \.invalid-tooltip\)\)\) > :is\(\.form-control, \.form-select\):invalid \{"
            r"(?P<body>.*?)\n\}",
            source,
            re.DOTALL,
        )

        self.assertIsNotNone(child_block)
        self.assertIn("box-shadow: none;", child_block.group("body"))

    def test_validation_feedback_stays_outside_the_compound_control(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")

        validation_group = re.search(
            r'<div class="input-group has-validation" '
            r'id="certification-input-group-invalid">(?P<body>.*?)\n          </div>',
            source,
            re.DOTALL,
        )

        self.assertIsNotNone(validation_group)
        self.assertNotIn("invalid-feedback", validation_group.group("body"))
        self.assertRegex(
            source,
            r'</div>\n          <div id="certification-input-group-token-feedback" '
            r'class="field-error invalid-feedback d-block">',
        )
        self.assertIn('class="field" data-invalid="true" data-certification-field', source)
        self.assertIn(
            'id="certification-input-group-url-help" class="field-description form-text"',
            source,
        )

    def test_textarea_fixture_uses_block_end_addon_contract(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")

        textarea_group = re.search(
            r'<div class="input-group" '
            r'id="certification-input-group-textarea">(?P<body>.*?)\n        </div>',
            source,
            re.DOTALL,
        )

        self.assertIsNotNone(textarea_group)
        body = textarea_group.group("body")
        self.assertIn(
            '<textarea\n            class="form-control"\n            '
            'id="certification-input-group-notes"',
            body,
        )
        self.assertIn('data-align="block-end"', body)
        self.assertIn("0/280", body)
        self.assertIn('id="certification-input-group-post"', body)
        self.assertNotIn("With textarea", body)

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
