from __future__ import annotations

import json
import re
from html import unescape

from build import dedent_html, format_html
from tests.helpers import ROOT, CatalogTestCase


class CodeExampleTests(CatalogTestCase):
    def test_render_example_owns_one_preview_and_source_surface(self) -> None:
        template = (
            ROOT / "site/src/includes/example.html.jinja"
        ).read_text(encoding="utf-8")
        render_example_block = template[
            template.index("{% macro render_example("):
            template.index("{% macro render_component_intro(")
        ]

        self.assertEqual(render_example_block.count('class="moo-example__surface'), 1)
        self.assertEqual(render_example_block.count('class="moo-example__preview'), 1)
        self.assertEqual(render_example_block.count('class="moo-example__source'), 1)
        self.assertIn("data-moo-code-panel", render_example_block)
        self.assertIn("data-moo-code-toggle", render_example_block)
        self.assertIn('aria-expanded="false"', render_example_block)
        self.assertIn("data-moo-code-copy", render_example_block)
        self.assertNotIn('data-bs-theme="dark"', render_example_block)
        self.assertEqual(render_example_block.count("{{ rendered | safe }}"), 1)
        self.assertIn("portal_content=\"\"", render_example_block)
        self.assertIn("source_content=\"\"", render_example_block)
        self.assertIn(
            "{% set rendered_portal = portal_content | dedent_html %}",
            render_example_block,
        )
        self.assertIn("{% if source_content %}", render_example_block)
        self.assertIn("{{ rendered_portal | safe }}", render_example_block)
        self.assertIn("portal_content=arabic_portal", template)
        self.assertIn("portal_content=hebrew_portal", template)
        self.assertIn("portal_content=english_portal", template)
        self.assertEqual(render_example_block.count("{{ source | highlight_html }}"), 1)
        self.assertNotIn("line_numbers", render_example_block)

    def test_component_examples_render_catalog_toolbar_actions(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        example_start = page.index('data-example="primary"')
        example_end = page.index('data-example="outline"', example_start)
        example = page[example_start:example_end]
        self.assertIn('class="moo-example__toolbar"', example)
        header_start = example.index('class="moo-example__header"')
        toolbar_start = example.index('class="moo-example__toolbar"')
        toolbar_end = example.index('class="moo-example__surface"', toolbar_start)
        toolbar = example[toolbar_start:toolbar_end]
        surface_start = example.index('class="moo-example__surface"')

        self.assertLess(header_start, toolbar_start)
        self.assertLess(toolbar_start, surface_start)

        self.assertIn("Button", toolbar)
        self.assertIn('data-lucide="mouse-pointer-click"', toolbar)
        self.assertIn('data-moo-code-copy-target="#primary-code"', toolbar)
        self.assertIn('data-moo-copy-icon="copy"', toolbar)
        self.assertIn('data-moo-copy-icon="check" hidden', toolbar)
        self.assertIn("Try in CodePen", toolbar)
        self.assertIn("data-moo-codepen-form", toolbar)
        self.assertNotIn("View Code", toolbar)

        match = re.search(
            r'<input type="hidden" name="data" value="([^"]+)"',
            toolbar,
        )
        self.assertIsNotNone(match)
        payload = json.loads(unescape(match.group(1)))

        self.assertEqual(payload["title"], "Moo UI Button - Primary")
        self.assertEqual(payload["tags"], ["moo-ui", "button", "components"])
        self.assertIn('class="moo-codepen-signature"', payload["html"])
        self.assertIn("Bootstrap markup. shadcn feel.", payload["html"])
        self.assertIn('class="moo-codepen-signature__note"', payload["html"])
        self.assertIn('<span class="moo-codepen-signature__note-line">Moo UI is not another shadcn clone.</span>', payload["html"])
        self.assertIn(
            '<span class="moo-codepen-signature__note-line">It brings the shadcn/ui feel to</span>',
            payload["html"],
        )
        self.assertIn(
            '<span class="moo-codepen-signature__note-line">Bootstrap-native HTML.</span>',
            payload["html"],
        )
        self.assertIn(
            '<a class="moo-codepen-signature__learn-more" href="https://ui.wpmoo.org/" target="_blank" rel="noopener noreferrer">',
            payload["html"],
        )
        self.assertIn("Learn more", payload["html"])
        self.assertIn('data-lucide="external-link"', payload["html"])
        self.assertIn('<footer class="moo-codepen-footer text-body-secondary small">', payload["html"])
        self.assertNotIn("Demo only", payload["html"])
        self.assertIn("This demo is composed from the", payload["html"])
        self.assertIn('class="btn btn-outline-secondary moo-examples-footer__component-trigger"', payload["html"])
        self.assertIn('data-bs-toggle="popover"', payload["html"])
        self.assertIn('data-bs-content="', payload["html"])
        self.assertIn("moo-examples-footer__preview", payload["html"])
        self.assertIn("assets/images/components/button.webp", payload["html"])
        self.assertIn("https://ui.wpmoo.org/components/button/", payload["html"])
        self.assertIn(">Button</a> component.", payload["html"])
        self.assertIn('class="moo-codepen-example-shell"', payload["html"])
        self.assertIn('<button class="btn btn-primary" type="button">', payload["html"])
        self.assertIn("min-height: 100vh;", payload["css"])
        self.assertIn(".moo-codepen-signature", payload["css"])
        signature_css = payload["css"].split(".moo-codepen-signature {", 1)[1].split("}", 1)[0]
        self.assertIn("position: fixed;", signature_css)
        self.assertIn(
            "bottom: calc(var(--moo-codepen-footer-height, var(--moo-examples-footer-height, 0rem)) + 1rem);",
            signature_css,
        )
        self.assertIn("left: 1rem;", signature_css)
        self.assertNotIn("top:", signature_css)
        self.assertNotIn("right:", signature_css)
        lockup_css = payload["css"].split(".moo-codepen-signature__lockup {", 1)[1].split("}", 1)[0]
        self.assertIn("border: 0;", lockup_css)
        self.assertIn("background: transparent;", lockup_css)
        self.assertIn("box-shadow: none;", lockup_css)
        note_css = payload["css"].split(
            ".moo-codepen-signature__note {",
            1,
        )[1].split("}", 1)[0]
        self.assertIn(
            "margin-left: calc(var(--moo-codepen-signature-lockup-padding) + var(--moo-codepen-signature-mark-size) + var(--moo-codepen-signature-gap));",
            note_css,
        )
        self.assertIn("color: var(--bs-tertiary-color);", note_css)
        self.assertIn("font-size: 0.8125rem;", note_css)
        note_line_css = payload["css"].split(
            ".moo-codepen-signature__note-line {",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("display: block;", note_line_css)
        self.assertIn("white-space: nowrap;", note_line_css)
        learn_more_css = payload["css"].split(
            ".moo-codepen-signature__learn-more {",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("display: inline-flex;", learn_more_css)
        self.assertIn("margin-top: 0.125rem;", learn_more_css)
        self.assertIn(".moo-codepen-footer", payload["css"])
        self.assertIn(".moo-examples-footer__component-trigger", payload["css"])
        footer_css = payload["css"].split(".moo-codepen-footer {", 1)[1].split("}", 1)[0]
        self.assertIn("position: fixed;", footer_css)
        self.assertIn("bottom: 0;", footer_css)
        self.assertIn("background: var(--bs-secondary-bg);", footer_css)
        self.assertIn("--moo-codepen-footer-height: 3rem;", payload["css"])
        self.assertIn(".moo-codepen-example-shell", payload["css"])
        shell_css = payload["css"].split(".moo-codepen-example-shell {", 1)[1].split("}", 1)[0]
        self.assertIn("display: grid;", shell_css)
        self.assertIn("place-items: center;", shell_css)
        full_width_css = payload["css"].split(".moo-codepen-example-shell > :where(", 1)[1].split("}", 1)[0]
        self.assertIn(".w-100", full_width_css)
        self.assertIn(".accordion", full_width_css)
        self.assertIn(".slider", full_width_css)
        self.assertIn("width: 100%;", full_width_css)
        self.assertIn("@wpmoo/ui@", payload["css_external"])
        self.assertEqual(
            payload["js_external"],
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js",
        )
        self.assertIn("initializeMooCodePenPopovers", payload["js"])
        self.assertFalse(payload["js_module"])

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
            ROOT / "site/src/includes/example.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertIn("{% macro render_rtl_example(", template)
        self.assertIn('id ~ "-direction-tabs"', template)
        self.assertIn('title="RTL"', template)
        self.assertIn('title_id="rtl"', template)
        self.assertIn('example_prefix="rtl"', template)
        self.assertEqual(template.count("show_header=false"), 3)

    def test_render_component_intro_centralizes_hero_and_usage_layout(self) -> None:
        template = (
            ROOT / "site/src/includes/example.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertIn("{% macro render_component_intro(", template)
        self.assertIn('class="moo-example__surface mb-5"', template)
        self.assertIn('aria-labelledby="usage"', template)
        self.assertIn('<h2 class="h4" id="usage">Usage</h2>', template)

        excluded_component_intro_pages = {"datatable", "sidebar"}
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        intro_slugs = [
            item["slug"]
            for item in catalog
            if item["slug"] not in excluded_component_intro_pages
        ]

        self.assertGreaterEqual(len(intro_slugs), 40)
        for slug in intro_slugs:
            with self.subTest(slug=slug):
                source = (
                    ROOT / f"site/src/pages/components/{slug}.html.jinja"
                ).read_text(encoding="utf-8")
                self.assertIn("render_component_intro(", source)
                self.assertNotIn('<div class="moo-example__surface mb-5">', source)
                self.assertNotIn(
                    '<section class="moo-example" aria-labelledby="usage">',
                    source,
                )

    def test_catalog_example_surface_integrates_preview_and_code(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-example__surface {", css)
        surface = css.split(".moo-example__surface {", 1)[1].split("}", 1)[0]
        self.assertIn("min-width: 0;", surface)
        self.assertIn("overflow: hidden;", surface)
        self.assertIn(
            "border: var(--bs-border-width) solid var(--bs-card-border-color, var(--bs-border-color));",
            surface,
        )
        self.assertIn(
            "background: var(--bs-card-bg, var(--bs-body-bg));",
            surface,
        )
        active_example = css.split(".moo-example:has(.dropdown-menu.show) {", 1)[1].split("}", 1)[0]
        active_surface = css.split(".moo-example__surface:has(.dropdown-menu.show) {", 1)[1].split("}", 1)[0]
        self.assertIn("position: relative;", active_example)
        self.assertIn("z-index: 5;", active_example)
        self.assertIn("overflow: visible;", active_surface)
        preview = css.split(".moo-example__preview {", 1)[1].split("}", 1)[0]
        self.assertIn("position: relative;", preview)
        self.assertIn("z-index: 4;", preview)
        self.assertIn("overflow: visible;", preview)
        self.assertIn(".moo-example__source {", css)
        source = css.split(".moo-example__source {", 1)[1].split("}", 1)[0]
        self.assertIn("min-width: 0;", source)
        self.assertIn("z-index: 1;", source)
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
        reveal = css.split(".moo-code__reveal {", 1)[1].split("}", 1)[0]
        self.assertNotIn("padding-bottom:", reveal)
        reveal_button = css.split(".moo-code__reveal .btn {", 1)[1].split(
            "}", 1
        )[0]
        self.assertIn("background: var(--bs-body-bg);", reveal_button)
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
        self.assertIn(
            '<span class="moo-code__lines" aria-hidden="true"></span>',
            page,
        )
        self.assertNotRegex(page, r'class="moo-code__lines"[^>]*>\s*1\s*<')
        self.assertIn('<span class="token tag">', page)
        self.assertIn('<span class="token attr-name">class</span>', page)
        self.assertIn('<span class="token attr-value">', page)

        catalog_css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-code__lines {", catalog_css)
        self.assertIn(".token.tag {", catalog_css)
        self.assertIn(".token.attr-name", catalog_css)
        self.assertIn(".token.attr-value", catalog_css)

    def test_inline_code_chips_apply_across_catalog_prose_contexts(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("installation.html")
        self.assertIn("<dd>Use either the full <code>moo-ui.css</code>", page)
        self.assertIn("<td><code>moo-ui.css</code> instead of Bootstrap CSS.</td>", page)

        catalog_css = self.read_output("assets/css/catalog.css")
        selector = catalog_css.split(
            ".moo-catalog__content :where(p, li, dd, dt, td, th) code {", 1
        )[1].split("}", 1)[0]
        self.assertIn("color: var(--bs-secondary-text-emphasis);", selector)
        self.assertIn("background: var(--moo-muted-surface);", selector)
        self.assertIn("border-radius:", selector)

    def test_code_panel_expands_and_copies_only_code_text(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        self.assertIn('data-expanded="false"', page)
        self.assertIn('data-moo-code-copy hidden', page)
        self.assertIn('data-moo-copy-status role="status"', page)
        self.assertIn('data-moo-copy-icon="copy"', page)
        self.assertIn('data-moo-copy-icon="check" hidden', page)
        self.assertRegex(page, r'aria-controls="[a-z0-9-]+-code"')

        script = self.read_output("assets/js/catalog/code-preview.js")
        self.assertIn('panel.dataset.expanded = "true";', script)
        self.assertIn("scroller.classList.toggle(", script)
        self.assertIn('"moo-code--scrolling",', script)
        self.assertIn("scroller.scrollHeight > scroller.clientHeight", script)
        self.assertIn('toggle.setAttribute("aria-expanded", "true")', script)
        self.assertIn("copyButton.hidden = false;", script)
        self.assertIn("navigator.clipboard.writeText(code.textContent)", script)
        self.assertIn('copyStatus.textContent = "Copied";', script)
        self.assertIn('copyStatus.textContent = "Copy failed";', script)
        self.assertIn("setCopyButtonState(copyButton, true);", script)
        self.assertIn("setCopyButtonState(copyButton, false);", script)
        self.assertIn('copyButton.dataset.mooCopied = copied ? "true" : "false";', script)
        self.assertIn("renderCodeLineNumbers", script)
        self.assertIn('panel.querySelector(".moo-code__lines")', script)

        catalog_css = self.read_output("assets/css/catalog.css")
        copy_button = catalog_css.split(".moo-code__copy {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--bs-body-bg);", copy_button)
        copy_icon = catalog_css.split(
            ".moo-code__copy [data-moo-copy-icon]:not([hidden]) {", 1
        )[1].split("}", 1)[0]
        self.assertIn("display: inline-flex;", copy_icon)
        nested_icon = catalog_css.split(
            ".moo-code__copy [data-icon] {", 1
        )[1].split("}", 1)[0]
        self.assertIn("width: 0.875rem;", nested_icon)
        self.assertIn("height: 0.875rem;", nested_icon)
        self.assertIn(".moo-code__lines {", catalog_css)
        self.assertIn("pointer-events: none;", catalog_css)
        self.assertIn("user-select: none;", catalog_css)
        self.assertNotIn(".moo-code__status {", catalog_css)
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
        self.assertNotIn('data-bs-theme="dark"', page)
        self.assertIn('data-moo-code-copy aria-label="Copy code"', page)
        self.assertIn('data-moo-copy-icon="copy"', page)
        self.assertIn('data-moo-copy-icon="check" hidden', page)
        self.assertIn('class="visually-hidden" data-moo-copy-status role="status"', page)
        self.assertNotIn("data-moo-code-copy hidden", page)
        self.assertIn('class="moo-code scroll-fade-x no-scrollbar"', page)
        self.assertIn('tabindex="0"', page)

        catalog_css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-doc-code-panel {", catalog_css)
        self.assertIn(
            ".moo-doc-code-panel .moo-code {",
            catalog_css,
        )
