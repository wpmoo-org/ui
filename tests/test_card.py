from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase

COMPONENT = ROOT / "src/components/card.html.jinja"
PAGE = ROOT / "src/pages/components/card.html.jinja"


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

    def test_card_page_renders_rtl_tabbed_examples(self) -> None:
        self.assertTrue(PAGE.is_file(), "Card catalog page is not implemented")
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/card.html")
        self.assertIn('id="card-direction-tabs-list"', page)
        self.assertIn('id="rtl-title"', page)
        self.assertIn('id="card-direction-tabs-arabic-tab"', page)
        self.assertIn('id="card-direction-tabs-hebrew-tab"', page)
        self.assertIn('id="card-direction-tabs-english-tab"', page)

    def test_card_rtl_examples_are_exact_translations_of_one_scenario(self) -> None:
        # The RTL rule requires Arabic/Hebrew/English to be exact
        # translations of the same example with identical structure, not
        # three unrelated scenarios -- lock the shared two-row layout here.
        source = PAGE.read_text(encoding="utf-8")

        for block_start in ("arabic_card %}", "hebrew_card %}", "english_card %}"):
            block = source.split(block_start, 1)[1].split("{% endset %}", 1)[0]
            with self.subTest(locale=block_start):
                self.assertEqual(block.count("d-flex justify-content-between"), 2)
                self.assertIn('class="text-body-secondary"', block)
                self.assertIn('class="fw-medium"', block)
                self.assertIn('dir="rtl"', block)
