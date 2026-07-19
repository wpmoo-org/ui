from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/close_button.html.jinja"
PAGE = ROOT / "src/pages/components/close-button.html.jinja"


class CloseButtonTests(CatalogTestCase):
    def render_close_button(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Close Button macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/close_button.html.jinja" import close_button %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_close_button_renders_native_btn_close(self) -> None:
        self.assertEqual(
            self.render_close_button("close_button()"),
            '<button type="button" class="btn-close" aria-label="Close"></button>',
        )

    def test_close_button_supports_disabled_and_extra_class(self) -> None:
        self.assertEqual(
            self.render_close_button("close_button(disabled=true)"),
            '<button type="button" class="btn-close" aria-label="Close" disabled></button>',
        )
        self.assertEqual(
            self.render_close_button('close_button(extra_class="ms-auto")'),
            '<button type="button" class="btn-close ms-auto" aria-label="Close"></button>',
        )

    def test_close_button_supports_custom_aria_label(self) -> None:
        self.assertEqual(
            self.render_close_button('close_button(aria_label="Dismiss")'),
            '<button type="button" class="btn-close" aria-label="Dismiss"></button>',
        )

    def test_close_button_requires_visible_aria_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Close button aria_label is required"):
            self.render_close_button('close_button(aria_label="   ")')
