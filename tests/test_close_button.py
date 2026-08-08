from __future__ import annotations

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/close_button.html.jinja"
PAGE = ROOT / "site/src/pages/components/close-button.html.jinja"


class CloseButtonTests(CatalogTestCase):
    def render_close_button(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Close Button macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/close_button.html.jinja" import close_button %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_close_button_renders_native_btn_close(self) -> None:
        output = self.render_close_button("close_button()")

        self.assertEqual(
            output,
            '<button type="button" class="btn-close" aria-label="Close"></button>',
        )

    def test_close_button_supports_disabled_and_extra_class(self) -> None:
        self.assertIn(
            '<button type="button" class="btn-close" aria-label="Close" disabled></button>',
            self.render_close_button("close_button(disabled=true)"),
        )
        self.assertIn(
            '<button type="button" class="btn-close ms-auto" aria-label="Close"></button>',
            self.render_close_button('close_button(extra_class="ms-auto")'),
        )

    def test_close_button_supports_custom_aria_label(self) -> None:
        self.assertIn(
            '<button type="button" class="btn-close" aria-label="Dismiss"></button>',
            self.render_close_button('close_button(aria_label="Dismiss")'),
        )

    def test_close_button_dismiss_adds_bootstrap_dismiss_attribute(self) -> None:
        self.assertIn(
            '<button type="button" class="btn-close" aria-label="Close"'
            ' data-bs-dismiss="alert"></button>',
            self.render_close_button('close_button(dismiss="alert")'),
        )

    def test_close_button_requires_visible_aria_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Close button aria_label is required"):
            self.render_close_button('close_button(aria_label="   ")')

    def test_close_button_uses_reference_icon_button_geometry(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        source = (ROOT / "scss/components/_close_button.scss").read_text(
            encoding="utf-8"
        )
        settings = (ROOT / "scss/settings/_components.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn('@import "components/close_button";', (ROOT / "scss/_component_layer.scss").read_text(encoding="utf-8"))
        self.assertIn("$btn-close-width: 0.75rem !default;", settings)
        self.assertIn("$btn-close-padding-x: 0.34375rem !default;", settings)
        self.assertIn("$btn-close-opacity: 1 !default;", settings)
        self.assertIn("$btn-close-disabled-opacity: $moo-disabled-control-opacity !default;", settings)
        self.assertIn("border-radius: var(--bs-border-radius-xl);", source)
        self.assertIn("--bs-btn-hover-bg: var(--moo-muted-surface);", source)
        self.assertIn("Lucide", source)
        self.assertNotIn("[data-icon]", source)
        self.assertIn("--bs-btn-close-opacity: 1;", css)
        self.assertIn("--bs-btn-close-disabled-opacity: 0.5;", css)
        self.assertIn("opacity: var(--moo-disabled-control-opacity);", css)
        self.assertIn("width: 0.75rem;", css)
        self.assertIn("padding: 0.34375rem 0.34375rem;", css)
        self.assertIn(".btn-close {", css)

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
        self.assertIn('id="rtl">RTL</h2>', output)
