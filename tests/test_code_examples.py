from __future__ import annotations

from build import dedent_html, format_html
from tests.helpers import ROOT, CatalogTestCase


class CodeExampleTests(CatalogTestCase):
    def test_render_example_owns_one_preview_and_source_surface(self) -> None:
        template = (
            ROOT / "src/components/example.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertEqual(template.count('class="moo-example__surface"'), 1)
        self.assertEqual(template.count('class="moo-example__preview"'), 1)
        self.assertEqual(template.count('class="moo-example__source"'), 1)
        self.assertIn("<summary>View Code</summary>", template)
        self.assertEqual(template.count("{{ rendered | safe }}"), 1)
        self.assertEqual(template.count("{% set source = rendered | format_html %}"), 1)
        self.assertEqual(template.count("{{ source | highlight_html }}"), 1)
        self.assertEqual(template.count("{{ source | line_numbers }}"), 1)

    def test_source_formatter_indents_nested_macro_markup(self) -> None:
        source = """
          <button class="btn">
        <svg viewBox="0 0 24 24">
          <path d="M5 12h14"/>
        </svg>      Create space
            </button>
        """

        self.assertEqual(
            format_html(source),
            '<button class="btn">\n'
            '  <svg viewBox="0 0 24 24">\n'
            '    <path d="M5 12h14"/>\n'
            '  </svg>\n'
            '  Create space\n'
            '</button>',
        )

    def test_catalog_example_surface_integrates_preview_and_code(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-example__surface {", css)
        surface = css.split(".moo-example__surface {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow: hidden;", surface)
        self.assertIn(
            "border: var(--bs-border-width) solid var(--bs-border-color);",
            surface,
        )
        self.assertIn(".moo-example__source {", css)
        source = css.split(".moo-example__source {", 1)[1].split("}", 1)[0]
        self.assertIn(
            "border-top: var(--bs-border-width) solid var(--bs-border-color);",
            source,
        )
        source_code = css.split(".moo-example__source pre {", 1)[1].split(
            "}", 1
        )[0]
        self.assertIn("white-space: pre;", source_code)
        self.assertIn("overflow-x: auto;", source_code)
        self.assertNotIn("overflow-wrap: anywhere;", source_code)
        self.assertNotIn("max-height:", source_code)
        self.assertNotIn(".moo-example__preview:has(.dropdown-menu)", css)

        for relative_path in (
            "components/button.html",
            "components/button-group.html",
            "components/card.html",
        ):
            page = self.read_output(relative_path)
            self.assertEqual(
                page.count("moo-example__surface"),
                page.count("moo-example__preview"),
            )

    def test_rendered_code_has_syntax_tokens_lines_and_clean_indent(self) -> None:
        source = """
                <div class="sample">
                  <span>First</span>



                  <span>Second</span>
                </div>
        """
        self.assertEqual(
            dedent_html(source),
            '<div class="sample">\n'
            "  <span>First</span>\n\n"
            "  <span>Second</span>\n"
            "</div>",
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        self.assertIn('<code class="language-html">', page)
        self.assertIn('class="moo-code__lines" aria-hidden="true"', page)
        self.assertIn('<span class="token tag">', page)
        self.assertIn('<span class="token attr-name">class</span>', page)
        self.assertIn('<span class="token attr-value">', page)

        catalog_css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-code__lines {", catalog_css)
        self.assertIn(".token.tag {", catalog_css)
        self.assertIn(".token.attr-name", catalog_css)
        self.assertIn(".token.attr-value", catalog_css)
