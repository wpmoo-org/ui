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

    def test_close_button_dismiss_adds_bootstrap_dismiss_attribute(self) -> None:
        self.assertEqual(
            self.render_close_button('close_button(dismiss="alert")'),
            '<button type="button" class="btn-close" aria-label="Close"'
            ' data-bs-dismiss="alert"></button>',
        )

    def test_close_button_requires_visible_aria_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Close button aria_label is required"):
            self.render_close_button('close_button(aria_label="   ")')

    def test_page_uses_render_rtl_example(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "includes/example.html.jinja" import render_example, render_rtl_example %}',
            source,
        )
        self.assertIn("render_rtl_example(", source)
        self.assertIn("close-button-ribbon", source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertIn('dir="rtl"', source)
        self.assertIn(
            "Compare Arabic, Hebrew, and English close actions in an RTL layout for operations workflows.",
            source,
        )
        self.assertIn("تم تجاهل الحادث", source)
        self.assertIn("האירוע נסגר", source)
        self.assertIn("Incident dismissed", source)
        self.assertIn('close_button(aria_label="إغلاق")', source)
        self.assertIn('close_button(aria_label="סגירה")', source)
        self.assertIn('close_button(aria_label="Close")', source)
        self.assertNotIn("title_id=", source)
        self.assertNotIn("Right-to-left layout", source)
        self.assertNotIn('{% from "components/tabs.html.jinja" import tabs %}', source)

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/close-button.html")
        self.assertIn("close-button-ribbon-direction-tabs", output)
        self.assertIn("rtl-arabic-code", output)
        self.assertIn("rtl-hebrew-code", output)
        self.assertIn("rtl-english-code", output)
        self.assertIn(">Arabic</button>", output)
        self.assertIn(">Hebrew</button>", output)
        self.assertIn(">English</button>", output)
        self.assertIn('id="rtl-title">RTL</h2>', output)
