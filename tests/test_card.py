from __future__ import annotations

import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase

COMPONENT = ROOT / "src/components/card.html.jinja"
PAGE = ROOT / "site/src/pages/components/card.html.jinja"


class CardTests(CatalogTestCase):
    def render_card(self, template_source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Card macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/card.html.jinja" import card %}'
            f"{template_source}"
        )
        return " ".join(template.render().split())

    def test_card_renders_header_body_and_footer_sections(self) -> None:
        output = self.render_card(
            '{% call card("Incident status", "Validation summary is shown per environment.", '
            'footer="View ticket", footer_class="justify-content-end") %}'
            'Body preview'
            '{% endcall %}'
        )

        self.assertIn('class="card"', output)
        self.assertIn('<h3 class="card-title">Incident status</h3>', output)
        self.assertIn('<p class="card-subtitle">Validation summary is shown per environment.</p>', output)
        self.assertIn('<div class="card-body">', output)
        self.assertIn('<div class="card-footer justify-content-end">', output)
        self.assertIn('View ticket', output)

    def test_card_renders_direction_attribute_for_rtl_content(self) -> None:
        output = self.render_card(
            '{% call card("مراجعة", "النسخة التجريبية", dir="rtl", footer="حفظ") %}'
            'الحالة'
            '{% endcall %}'
        )

        self.assertIn('dir="rtl"', output)

    def test_card_page_renders_rtl_login_example(self) -> None:
        self.assertTrue(PAGE.is_file(), "Card catalog page is not implemented")
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/card.html")
        # The three-language render_rtl_example macro generates
        # data-example="rtl-arabic", "rtl-hebrew", "rtl-english".
        self.assertIn('data-example="rtl-arabic"', page)
        self.assertIn('data-example="rtl-hebrew"', page)
        self.assertIn('data-example="rtl-english"', page)
        self.assertIn('dir="rtl"', page)
        self.assertIn("تسجيل الدخول", page)

    def test_card_rtl_example_is_a_single_translated_login_scenario(self) -> None:
        # The RTL example uses render_rtl_example with three language
        # variants (Arabic, Hebrew, English), each wrapping the same
        # login card structure in dir="rtl".
        source = PAGE.read_text(encoding="utf-8")

        arabic_block = source.split("rtl_arabic %}", 1)[1].split("{% endset %}", 1)[0]
        self.assertIn('dir="rtl"', arabic_block)
        self.assertIn("تسجيل الدخول إلى حسابك", arabic_block)
        self.assertIn('action=button("إنشاء حساب"', arabic_block)
        self.assertIn("card-rtl-ar-email", arabic_block)
        self.assertIn("card-rtl-ar-password", arabic_block)

        hebrew_block = source.split("rtl_hebrew %}", 1)[1].split("{% endset %}", 1)[0]
        self.assertIn('dir="rtl"', hebrew_block)
        self.assertIn("card-rtl-he-email", hebrew_block)

        english_block = source.split("rtl_english %}", 1)[1].split("{% endset %}", 1)[0]
        self.assertIn('dir="ltr"', english_block)
        self.assertIn("Login to your account", english_block)
        self.assertIn("card-rtl-en-email", english_block)

    def test_card_light_surface_keeps_footer_separately_tinted(self) -> None:
        source = (ROOT / "scss/components/_card.scss").read_text(encoding="utf-8")
        settings = (ROOT / "scss/settings/_component_variables.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "--bs-card-bg: color-mix(in srgb, var(--bs-secondary-bg) #{$moo-card-bg-mix}, var(--bs-body-bg));",
            source,
        )
        self.assertIn(
            "--bs-card-border-color: color-mix(in srgb, var(--bs-body-color) #{$moo-card-border-mix}, #{$moo-card-border-mix-base});",
            source,
        )
        self.assertIn(
            "--moo-card-footer-bg: #{$moo-card-footer-bg};",
            source,
        )
        self.assertIn(
            "--bs-card-bg: color-mix(in srgb, var(--bs-secondary-bg) #{$moo-card-bg-mix-dark}, var(--bs-body-bg));",
            source,
        )
        for variable in (
            "$moo-card-spacing",
            "$moo-card-spacing-sm",
            "$moo-card-bg-mix",
            "$moo-card-border-mix",
            "$moo-card-bg-mix-dark",
            "$moo-card-footer-bg",
            "$moo-card-footer-bg-dark",
        ):
            with self.subTest(variable=variable):
                self.assertRegex(
                    settings,
                    rf"(?m)^{re.escape(variable)}:\s*[^;]+!default;",
                    f"{variable} must remain an overridable Sass knob",
                )
        self.assertIn("$moo-card-border-mix-base: transparent !default;", settings)
        self.assertIn(
            ':where([data-bs-theme="dark"]) &:not([data-bs-theme="light"]):not([data-bs-theme="light"] *)',
            source,
        )
        self.assertNotIn(
            "--moo-card-footer-bg: color-mix(in srgb, var(--moo-muted-surface) 5%, transparent);",
            source,
        )

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        self.assertIn('.card[data-bs-theme="dark"]', css)
