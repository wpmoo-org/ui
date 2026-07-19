from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase, lucide_body


COMPONENT = ROOT / "src/components/spinner.html.jinja"
PAGE = ROOT / "src/pages/components/spinner.html.jinja"


class SpinnerTests(CatalogTestCase):
    def render_spinner(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Spinner macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/spinner.html.jinja" import spinner %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_spinner_renders_loader_circle_icon_with_status_role(self) -> None:
        output = self.render_spinner("spinner()")

        self.assertIn('<div class="spinner" role="status">', output)
        self.assertIn(lucide_body("loader-circle"), output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn('<span class="visually-hidden">Loading</span>', output)

    def test_spinner_supports_custom_aria_label(self) -> None:
        self.assertIn(
            '<span class="visually-hidden">Fetching results</span>',
            self.render_spinner('spinner(aria_label="Fetching results")'),
        )

    def test_spinner_small_size_adds_modifier_class(self) -> None:
        self.assertIn(
            'class="spinner spinner-sm"',
            self.render_spinner('spinner(size="sm")'),
        )

    def test_spinner_rejects_unknown_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "Spinner size must be '' or 'sm'"):
            self.render_spinner('spinner(size="lg")')

    def test_spinner_requires_aria_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Spinner aria_label is required"):
            self.render_spinner('spinner(aria_label="   ")')

    def test_spinner_supports_extra_class(self) -> None:
        self.assertIn(
            'class="spinner m-5"',
            self.render_spinner('spinner(extra_class="m-5")'),
        )
