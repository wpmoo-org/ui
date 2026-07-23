from __future__ import annotations

from build import dedent_html, format_html
from tests.helpers import ROOT, CatalogTestCase


class CodeExampleTests(CatalogTestCase):
    def test_render_example_owns_one_preview_and_source_surface(self) -> None:
        template = (
            ROOT / "src/includes/example.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertEqual(template.count('class="moo-example__surface"'), 1)
        self.assertEqual(template.count('class="moo-example__preview'), 1)
        self.assertEqual(template.count('class="moo-example__source"'), 1)
        self.assertIn("data-moo-code-panel", template)
        self.assertIn("data-moo-code-toggle", template)
        self.assertIn('aria-expanded="false"', template)
        self.assertIn("data-moo-code-copy", template)
        self.assertIn('data-bs-theme="dark"', template)
        self.assertEqual(template.count("{{ rendered | safe }}"), 1)
        self.assertIn("portal_content=\"\"", template)
        self.assertIn("{% set rendered_portal = portal_content | dedent_html %}", template)
        self.assertIn("{{ rendered_portal | safe }}", template)
        self.assertIn("portal_content=arabic_portal", template)
        self.assertIn("portal_content=hebrew_portal", template)
        self.assertIn("portal_content=english_portal", template)
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

    def test_source_formatter_compacts_build_time_lucide_icons(self) -> None:
        source = """
          <button class="btn btn-ghost" type="button" aria-label="Copy profile URL">
            <svg
              data-icon="inline-start"
              data-lucide="copy"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
            </svg>
          </button>
        """

        self.assertEqual(
            format_html(source),
            '<button class="btn btn-ghost" type="button" aria-label="Copy profile URL">\n'
            '  <i class="lucide lucide-copy" data-icon="inline-start" aria-hidden="true" />\n'
            "</button>",
        )

    def test_render_rtl_example_centralizes_tabbed_language_examples(self) -> None:
        template = (
            ROOT / "src/includes/example.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertIn("{% macro render_rtl_example(", template)
        self.assertIn('id ~ "-direction-tabs"', template)
        self.assertIn('title="RTL"', template)
        self.assertIn('title_id="rtl"', template)
        self.assertIn('example_prefix="rtl"', template)
        self.assertEqual(template.count("show_header=false"), 3)

    def test_catalog_example_surface_integrates_preview_and_code(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-example__surface {", css)
        surface = css.split(".moo-example__surface {", 1)[1].split("}", 1)[0]
        self.assertIn("min-width: 0;", surface)
        self.assertIn("overflow: hidden;", surface)
        self.assertIn(
            "border: var(--bs-border-width) solid var(--bs-border-color);",
            surface,
        )
        preview = css.split(".moo-example__preview {", 1)[1].split("}", 1)[0]
        self.assertIn("position: relative;", preview)
        self.assertIn("z-index: 4;", preview)
        self.assertIn("overflow: visible;", preview)
        self.assertIn(".moo-example__source {", css)
        source = css.split(".moo-example__source {", 1)[1].split("}", 1)[0]
        self.assertIn("min-width: 0;", source)
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
        self.assertIn("max-height: 6.75rem;", source_code)
        self.assertIn("padding: 0.875rem 0;", source_code)
        self.assertIn("font-size: 0.875rem;", source_code)
        self.assertIn("line-height: 1.75;", source_code)
        nested_tab_example = css.split(".tab-content .moo-example {", 1)[1].split("}", 1)[0]
        self.assertIn("max-width: 100%;", nested_tab_example)
        self.assertIn("min-width: 0;", nested_tab_example)
        self.assertIn(
            '[data-expanded="true"] .moo-code {',
            css,
        )
        expanded_code = css.split(
            '[data-expanded="true"] .moo-code {', 1
        )[1].split("}", 1)[0]
        self.assertIn("max-height: 18rem;", expanded_code)
        scrolling_code = css.split(
            '[data-expanded="true"] .moo-code--scrolling {', 1
        )[1].split("}", 1)[0]
        self.assertIn("margin-bottom: 0.625rem;", scrolling_code)
        self.assertNotIn(".moo-example__preview:has(.dropdown-menu)", css)

        for relative_path in (
            "components/button.html",
            "components/button-group.html",
            "components/card.html",
        ):
            page = self.read_output(relative_path)
            self.assertEqual(
                page.count("moo-example__surface"),
                page.count('<div class="moo-example__preview'),
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

    def test_code_panel_expands_and_copies_only_code_text(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        self.assertIn('data-expanded="false"', page)
        self.assertIn('data-moo-code-copy hidden', page)
        self.assertIn('data-moo-copy-status role="status"', page)
        self.assertIn('aria-controls="core-variants-code"', page)

        script = self.read_output("assets/js/preview.js")
        self.assertIn('panel.dataset.expanded = "true";', script)
        self.assertIn(
            'scroller.classList.toggle("moo-code--scrolling", scroller.scrollHeight > scroller.clientHeight);',
            script,
        )
        self.assertIn('toggle.setAttribute("aria-expanded", "true")', script)
        self.assertIn("copyButton.hidden = false;", script)
        self.assertIn("navigator.clipboard.writeText(code.textContent)", script)
        self.assertIn('let message = "Code copied";', script)
        self.assertIn('message = "Copy failed";', script)
        self.assertIn("copyStatus.textContent = message;", script)
        self.assertNotIn("moo-code__lines", script)

        catalog_css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-code__lines {", catalog_css)
        self.assertIn("pointer-events: none;", catalog_css)
        self.assertIn("user-select: none;", catalog_css)
        self.assertIn(
            '[data-expanded="true"] .moo-code__copy',
            catalog_css,
        )
        self.assertNotIn(
            '[data-expanded="true"]:hover .moo-code__copy',
            catalog_css,
        )

    def test_docs_code_snippets_use_copyable_code_panel(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("installation.html")

        self.assertIn("moo-doc-code-panel", page)
        self.assertIn('data-moo-code-panel data-expanded="true"', page)
        self.assertIn('data-moo-code-copy aria-label="Copy code"', page)
        self.assertIn('data-moo-copy-status role="status"', page)
        self.assertNotIn("data-moo-code-copy hidden", page)
        self.assertIn('class="moo-code scroll-fade-x no-scrollbar"', page)

        catalog_css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-doc-code-panel {", catalog_css)
        self.assertIn(
            ".moo-doc-code-panel .moo-code {",
            catalog_css,
        )
