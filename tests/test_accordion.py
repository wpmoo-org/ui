from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/accordion.html.jinja"
PAGE = ROOT / "src/pages/components/accordion.html.jinja"


class AccordionTests(CatalogTestCase):
    def render_accordion(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Accordion macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/accordion.html.jinja" import accordion %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_accordion_renders_flush_container_and_native_bootstrap_button(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1"}])'
        )

        self.assertIn('<div class="accordion w-100 accordion-flush" id="faq">', output)
        self.assertIn('class="accordion-button collapsed"', output)
        self.assertIn('data-icon="inline-end"', output)

    def test_accordion_can_render_contained_bootstrap_variant(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1"}], flush=false)'
        )

        self.assertIn('<div class="accordion w-100" id="faq">', output)
        self.assertNotIn("accordion-flush", output)

    def test_accordion_width_is_stable_inside_flex_catalog_previews(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1"}])'
        )

        self.assertIn("w-100", output)

    def test_accordion_page_includes_reference_parity_examples(self) -> None:
        page = PAGE.read_text()

        self.assertIn('"bordered"', page)
        self.assertIn('"disabled"', page)
        self.assertIn('"in-card"', page)
        self.assertGreaterEqual(
            page.count('preview_class="moo-example__preview--medium"'), 6
        )
        self.assertIn("render_rtl_example", page)
        self.assertIn('"accordion"', page)
        self.assertIn('"accordion-rtl-arabic"', page)
        self.assertIn('"accordion-rtl-hebrew"', page)
        self.assertIn('"accordion-rtl-english"', page)
        self.assertGreaterEqual(page.count('<div class="w-100" dir="rtl">'), 3)
        self.assertIn('"من يعتمد النتيجة؟"', page)
        self.assertIn('"מי מאשר סופית?"', page)
        self.assertNotIn("قبل סגירה", page)
        self.assertGreaterEqual(page.count('dir="rtl"'), 3)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/accordion.html")
        self.assertIn("accordion-direction-tabs", output)
        self.assertIn("rtl-arabic-code", output)
        self.assertIn(">Arabic</button>", output)
        self.assertIn(">Hebrew</button>", output)
        self.assertIn(">English</button>", output)

    def test_accordion_item_defaults_to_collapsed(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1"}])'
        )

        self.assertIn('class="accordion-button collapsed"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertIn('class="accordion-collapse collapse"', output)
        self.assertIn('data-bs-parent="#faq"', output)

    def test_accordion_item_open_drops_collapsed_state(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1", "open": true}])'
        )

        self.assertIn('class="accordion-button"', output)
        self.assertNotIn("collapsed", output)
        self.assertIn('aria-expanded="true"', output)
        self.assertIn('class="accordion-collapse collapse show"', output)

    def test_accordion_always_open_omits_data_bs_parent(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1"}], always_open=true)'
        )

        self.assertNotIn("data-bs-parent", output)

    def test_accordion_item_disabled_adds_attribute(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "A1", "disabled": true}])'
        )

        self.assertIn("disabled>", output)
        self.assertIn('class="accordion-button collapsed text-muted"', output)

    def test_accordion_content_is_not_escaped(self) -> None:
        output = self.render_accordion(
            'accordion("faq", [{"id": "a", "title": "Q1", "content": "See <code>docs</code>."}])'
        )

        self.assertIn("See <code>docs</code>.", output)

    def test_accordion_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Accordion id is required"):
            self.render_accordion(
                'accordion("   ", [{"id": "a", "title": "Q1", "content": "A1"}])'
            )

    def test_accordion_requires_items(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Accordion requires at least one item"
        ):
            self.render_accordion('accordion("faq", [])')

    def test_accordion_requires_item_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Accordion item id is required"):
            self.render_accordion(
                'accordion("faq", [{"id": "   ", "title": "Q1", "content": "A1"}])'
            )

    def test_accordion_requires_item_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Accordion item title is required"):
            self.render_accordion(
                'accordion("faq", [{"id": "a", "title": "   ", "content": "A1"}])'
            )
