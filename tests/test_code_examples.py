from __future__ import annotations

import json
import re
from html import unescape

import build
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
            r'<textarea name="data" hidden>(.*?)</textarea>',
            toolbar,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        payload = json.loads(unescape(match.group(1)).strip())

        self.assertEqual(payload["title"], "Moo UI Button - Primary")
        self.assertEqual(payload["tags"], ["moo-ui", "button", "components"])
        self.assertNotIn("moo-codepen-signature", payload["html"])
        self.assertNotIn("moo-codepen-footer", payload["html"])
        self.assertNotIn("moo-examples-footer__component-trigger", payload["html"])
        self.assertNotIn('data-bs-toggle="popover"', payload["html"])
        self.assertNotIn("This demo is composed from the", payload["html"])
        self.assertNotIn(
            'class="container min-vh-100 d-flex align-items-center justify-content-center py-5"',
            payload["html"],
        )
        self.assertNotIn('class="row w-100 justify-content-center"', payload["html"])
        self.assertNotIn('class="col-12 col-lg-8 d-flex justify-content-center"', payload["html"])
        self.assertNotIn("moo-codepen-example-shell", payload["html"])
        self.assertEqual(
            payload["html"].strip(),
            '<button class="btn btn-primary" type="button">Primary</button>',
        )
        self.assertEqual(payload["css"], "")
        self.assertNotIn(".moo-codepen-signature", payload["css"])
        self.assertNotIn(".moo-codepen-footer", payload["css"])
        self.assertNotIn(".moo-examples-footer__component-trigger", payload["css"])
        self.assertNotIn("--moo-codepen-footer-height", payload["css"])
        self.assertNotIn(".moo-codepen-example-shell", payload["css"])
        self.assertEqual(
            payload["css_external"],
            (
                f"https://unpkg.com/@wpmoo/ui@{build.CODEPEN_CDN_VERSION}/dist/assets/css/moo-ui.css;"
                "https://ui.wpmoo.org/assets/css/codepen-demo.css"
            ),
        )
        self.assertEqual(
            payload["js_external"],
            (
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js;"
                "https://ui.wpmoo.org/assets/js/codepen-demo.js"
            ),
        )
        self.assertEqual(payload["js"], "")
        self.assertNotIn("window.MooCodePen", payload["js"])
        self.assertNotIn("initializeMooCodePenPopovers", payload["js"])
        self.assertNotIn("getOrCreateInstance", payload["js"])
        self.assertFalse(payload["js_module"])
        self.assertTrue((ROOT / "site-dist/assets/js/codepen-demo.js").is_file())
        self.assertTrue((ROOT / "site-dist/assets/css/codepen-demo.css").is_file())
        demo_css = (ROOT / "site-dist/assets/css/codepen-demo.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("body.moo-codepen-demo", demo_css)
        self.assertIn("body.moo-codepen-component-demo", demo_css)
        component_body_css = demo_css.split(
            "body.moo-codepen-component-demo {", 1
        )[1].split("}", 1)[0]
        self.assertIn("display: grid;", component_body_css)
        self.assertIn("place-items: center;", component_body_css)
        self.assertIn("padding: 2rem;", component_body_css)
        self.assertIn("body.moo-codepen-component-demo > :where(", demo_css)
        self.assertNotIn('.container > .row > [class*="col"]', demo_css)
        self.assertIn(".moo-codepen-signature", demo_css)
        self.assertIn(".moo-codepen-footer", demo_css)
        self.assertIn(".moo-examples-footer__component-trigger", demo_css)
        self.assertIn(".slider", demo_css)
        demo_js = (ROOT / "site-dist/assets/js/codepen-demo.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('document.body.classList.add("moo-codepen-demo")', demo_js)
        self.assertIn('function inferCodePenConfig(root)', demo_js)
        self.assertIn('function observeCodePenConfig()', demo_js)
        self.assertIn('"button"', demo_js)
        self.assertNotIn("ensureStyles", demo_js)
        self.assertNotIn('document.createElement("style")', demo_js)

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
            '  <i class="lucide lucide-copy" data-icon="inline-start" aria-hidden="true"></i>\n'
            "</button>",
        )

    def test_source_formatter_closes_lucide_placeholders_before_visible_text(self) -> None:
        source = """
          <button class="btn btn-outline-secondary moo-datepicker__trigger" type="button">
            <svg
              data-icon="inline-start"
              data-lucide="calendar"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M8 2v4m8-4v4"/>
              <rect width="18" height="18" x="3" y="4" rx="2"/>
              <path d="M3 10h18"/>
            </svg>
            <span data-datepicker-label>Pick a date</span>
          </button>
        """

        self.assertEqual(
            format_html(source),
            '<button class="btn btn-outline-secondary moo-datepicker__trigger" type="button">\n'
            '  <i class="lucide lucide-calendar" data-icon="inline-start" aria-hidden="true"></i>\n'
            "  <span data-datepicker-label>Pick a date</span>\n"
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

        excluded_component_intro_pages = {"chart", "datatable", "sidebar"}
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
            "border: var(--bs-border-width) solid var(--bs-border-color-translucent);",
            surface,
        )
        self.assertIn("background: var(--bs-body-bg);", surface)
        self.assertNotIn("--bs-card-bg", surface)
        self.assertNotIn("--bs-card-border-color", surface)
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
        self.assertIn("background: var(--moo-code-surface);", source)
        self.assertNotIn("--bs-tertiary-bg", source)
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
        self.assertIn("var(--moo-code-surface)", reveal)
        self.assertNotIn("--bs-tertiary-bg", reveal)
        lines = css.split(".moo-code__lines {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--moo-code-surface);", lines)
        self.assertNotIn("--bs-tertiary-bg", lines)
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

    def test_theme_builder_preview_tokens_are_schema_owned(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")

        for selector in (
            '[data-moo-catalog-theme-builder-style="soft"] .moo-catalog',
            '[data-moo-catalog-theme-builder-style="solid"] .moo-catalog',
            '[data-moo-catalog-theme-builder-style="tinted"] .moo-catalog',
            "[data-moo-catalog-theme-builder-theme-color] .moo-catalog",
            '[data-bs-theme="dark"][data-moo-catalog-theme-builder-style="tinted"] .moo-catalog',
            '[data-bs-theme="dark"][data-moo-catalog-theme-builder-theme-color] .moo-catalog',
        ):
            self.assertNotIn(selector, css)

        self.assertIn("[data-moo-catalog-theme-builder-updating] .moo-catalog", css)
        updating = css.split(
            "[data-moo-catalog-theme-builder-updating] .moo-catalog,",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("transition: none !important;", updating)

        self.assertNotIn(".moo-settings-panel__surface-preview", css)
        self.assertNotIn(".moo-settings-panel__option-preview", css)

    def test_syntax_highlight_colors_use_catalog_code_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")

        catalog_tokens = css.split(".moo-catalog {", 1)[1].split("}", 1)[0]
        for token in (
            "--moo-code-muted:",
            "--moo-code-keyword:",
            "--moo-code-selector:",
            "--moo-code-tag:",
            "--moo-code-property:",
            "--moo-code-function:",
            "--moo-code-string:",
            "--moo-code-constant:",
        ):
            with self.subTest(token=token):
                self.assertIn(token, catalog_tokens)

        dark_selector = '[data-bs-theme=dark] .moo-catalog {'
        self.assertIn(dark_selector, css)
        dark_catalog = css.split(dark_selector, 1)[1].split("}", 1)[0]
        self.assertIn("--moo-code-keyword:", dark_catalog)
        self.assertIn("--moo-code-string:", dark_catalog)

        selector_contracts = {
            ".token.comment": "--moo-code-muted",
            ".token.keyword": "--moo-code-keyword",
            ".token.selector": "--moo-code-selector",
            ".token.tag": "--moo-code-tag",
            ".token.attr-name": "--moo-code-property",
            ".token.function": "--moo-code-function",
            ".token.property": "--moo-code-property",
            ".token.string": "--moo-code-string",
            ".token.constant": "--moo-code-constant",
        }
        for selector, token in selector_contracts.items():
            with self.subTest(selector=selector):
                rule = css.split(f"{selector} {{", 1)[1].split("}", 1)[0]
                self.assertIn(f"color: var({token});", rule)

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

    def test_doc_code_snippets_highlight_language_specific_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("installation.html")
        snippet_start = page.index('id="installation-esm-code"')
        snippet_end = page.index("</pre>", snippet_start)
        snippet = page[snippet_start:snippet_end]

        self.assertIn('<code class="language-js">', snippet)
        self.assertIn('<span class="token keyword">import</span>', snippet)
        self.assertIn('<span class="token keyword">const</span>', snippet)
        self.assertIn(
            '<span class="token string">&quot;@wpmoo/ui/chart.js&quot;</span>',
            snippet,
        )

        cdn_snippet_start = page.index('id="installation-esm-cdn-code"')
        cdn_snippet_end = page.index("</pre>", cdn_snippet_start)
        cdn_snippet = page[cdn_snippet_start:cdn_snippet_end]
        self.assertIn('<code class="language-html">', cdn_snippet)
        self.assertIn('<span class="token keyword">import</span>', cdn_snippet)
        self.assertIn(
            '<span class="token string">'
            '&quot;https://cdn.jsdelivr.net/npm/@wpmoo/ui@1.0.0-rc.3/dist/js/chart.js&quot;'
            "</span>",
            cdn_snippet,
        )

        contributing = self.read_output("contributing.html")
        setup_start = contributing.index('id="contributing-local-setup-code"')
        setup_end = contributing.index("</pre>", setup_start)
        setup_snippet = contributing[setup_start:setup_end]
        self.assertIn('<code class="language-shell">', setup_snippet)
        self.assertIn('<span class="token function">python3</span>', setup_snippet)
        self.assertIn('<span class="token operator">-m</span>', setup_snippet)
        self.assertIn(
            '<span class="token property">npm_config_cache</span>',
            setup_snippet,
        )

        css = str(
            build.highlight_code(
                ".sample {\n  color: var(--bs-body-color);\n}", "css"
            )
        )
        self.assertIn('<span class="token selector">.sample</span>', css)
        self.assertIn('<span class="token property">color</span>', css)
        self.assertIn('<span class="token function">var</span>', css)

        python = str(
            build.highlight_code(
                "from pathlib import Path\n"
                "\n"
                "if Path('.').exists():\n"
                "    print('ok')\n",
                "python",
            )
        )
        self.assertIn('<span class="token keyword">from</span>', python)
        self.assertIn('<span class="token keyword">if</span>', python)
        self.assertIn('<span class="token function">Path</span>', python)
        self.assertIn('<span class="token function">print</span>', python)
        self.assertIn('<span class="token string">&#x27;.&#x27;</span>', python)

        catalog_css = self.read_output("assets/css/catalog.css")
        self.assertIn(".token.keyword", catalog_css)
        self.assertIn(".token.string", catalog_css)
        self.assertIn(".token.selector", catalog_css)
        self.assertIn(".token.property", catalog_css)

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
