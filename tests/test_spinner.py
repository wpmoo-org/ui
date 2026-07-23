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

    def test_page_uses_shared_rtl_example_tabs(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn("render_rtl_example", source)
        self.assertNotIn('title="RTL"', source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertGreaterEqual(source.count('dir="rtl"'), 3)

        # RTL rule: exact translations of the same example, same structure.
        for block_start in ("rtl_arabic %}", "rtl_hebrew %}", "rtl_english %}"):
            block = source.split(block_start, 1)[1].split("{% endset %}", 1)[0]
            with self.subTest(locale=block_start):
                self.assertIn('class="d-flex align-items-center gap-2"', block)
                self.assertIn("spinner(aria_label=", block)
                self.assertEqual(block.count("<span>"), 1)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/spinner.html")
        self.assertIn("spinner-direction-tabs", output)
        self.assertIn(">Arabic</button>", output)
        self.assertIn(">Hebrew</button>", output)
        self.assertIn(">English</button>", output)
