from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


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

    def test_spinner_renders_default_border_ring_with_status_role(self) -> None:
        self.assertEqual(
            self.render_spinner("spinner()"),
            '<div class="spinner-border" role="status">'
            ' <span class="visually-hidden">Loading</span> </div>',
        )

    def test_spinner_supports_custom_aria_label(self) -> None:
        self.assertIn(
            '<span class="visually-hidden">Fetching results</span>',
            self.render_spinner('spinner(aria_label="Fetching results")'),
        )

    def test_spinner_small_size_adds_modifier_class(self) -> None:
        self.assertIn(
            'class="spinner-border spinner-border-sm"',
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
            'class="spinner-border m-5"',
            self.render_spinner('spinner(extra_class="m-5")'),
        )
