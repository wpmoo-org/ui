from __future__ import annotations

from tests.helpers import DIST, ROOT, CatalogTestCase


class ButtonTests(CatalogTestCase):
    def test_button_examples_share_one_rendered_source(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        button_output = DIST / "components/button.html"
        self.assertTrue(button_output.is_file())

        page = button_output.read_text(encoding="utf-8")
        example_template = (
            ROOT / "src/components/example.html.jinja"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            example_template.count(
                "{% set rendered = content | dedent_html %}"
            ),
            1,
        )
        self.assertEqual(example_template.count("{{ rendered | safe }}"), 1)
        self.assertEqual(
            example_template.count("{% set source = rendered | format_html %}"),
            1,
        )
        self.assertEqual(
            example_template.count("{{ source | highlight_html }}"), 1
        )
        self.assertGreater(page.count("moo-example__preview"), 0)
        self.assertEqual(
            page.count("moo-example__preview"),
            page.count("moo-example__source"),
        )
        self.assertIn('class="btn btn-primary"', page)
        self.assertIn('<button class="btn', page)
        self.assertIn('<input class="btn', page)
        self.assertIn("disabled", page)
        self.assertIn('aria-label="Pin dashboard"', page)

    def test_button_examples_do_not_emit_demo_links(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        examples = page.split(
            '<section class="moo-component-reference"', 1
        )[0]
        self.assertNotIn('<a class="btn', examples)
        self.assertNotIn("example.com", examples)

    def test_button_page_covers_approved_variants_and_states(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        for class_name in (
            "btn-primary",
            "btn-secondary",
            "btn-outline-secondary",
            "btn-ghost",
            "btn-danger",
            "btn-link",
            "btn-success",
            "btn-warning",
            "btn-info",
            "btn-light",
            "btn-dark",
            "btn-outline-primary",
            "btn-outline-success",
            "btn-outline-danger",
            "btn-sm",
            "btn-lg",
            "btn-icon",
            "w-100",
        ):
            self.assertIn(class_name, page)

        self.assertIn('data-bs-toggle="button"', page)
        self.assertIn('aria-pressed="false"', page)
        self.assertEqual(page.count('data-example="rtl-preview"'), 1)
        self.assertIn('dir="rtl"', page)

        for runtime_name in ("React", "Tailwind", "Vue", "customElements"):
            self.assertNotIn(runtime_name, page)
        for reference_label in (
            "Primary button",
            "Secondary button",
            "Large button",
            "Small button",
            "Toggle button",
            "Active toggle button",
            "New Branch",
            "Continue",
            "Login",
            "Docs",
            "Review",
        ):
            self.assertNotIn(reference_label, page)

    def test_button_supports_compact_text_and_icon_sizes(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        size_example = page.split(
            'data-example="button-sizes"', 1
        )[1].split("</section>", 1)[0]
        self.assertEqual(size_example.count("<button"), 8)
        for class_name in (
            "btn-xs",
            "btn-sm",
            "btn-lg",
            "btn-icon",
            "btn-icon-xs",
            "btn-icon-sm",
            "btn-icon-lg",
        ):
            self.assertIn(class_name, size_example)

        css = self.read_output("assets/css/moo-ui.css")
        for height in ("1.5rem", "1.75rem", "2rem", "2.25rem"):
            self.assertIn(f"--moo-button-height: {height};", css)
        self.assertIn(
            ".btn:not(.btn-icon, .btn-icon-xs, .btn-icon-sm, .btn-icon-lg):has(> [data-icon=\"inline-start\"])",
            css,
        )
        self.assertIn(
            ".btn:not(.btn-icon, .btn-icon-xs, .btn-icon-sm, .btn-icon-lg):has(> [data-icon=\"inline-end\"])",
            css,
        )

    def test_button_focus_indicator_uses_high_contrast_outline(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn("outline: 2px solid var(--moo-ring);", css)
        self.assertIn("outline-offset: 2px;", css)
        self.assertNotIn("var(--moo-ring) 30%, transparent", css)

    def test_button_active_press_uses_subtle_half_pixel_shift(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(
            '.btn:not(:disabled):not(.disabled):not([aria-disabled="true"]):active',
            css,
        )
        self.assertIn("transform: translateY(0.5px);", css)

    def test_native_button_cursor_stays_default(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn("button.btn:not(:disabled),", css)
        self.assertIn("input.btn:not(:disabled),", css)
        self.assertIn("label.btn {", css)
        self.assertIn("cursor: default;", css)
        self.assertNotIn("\n.btn:not(:disabled) {\n  cursor: default;", css)

    def test_primary_outline_button_uses_theme_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(".btn-outline-primary {", css)
        outline_primary = css.split(".btn-outline-primary {")[-1].split("}", 1)[0]
        self.assertIn("--bs-btn-color: var(--moo-foreground);", outline_primary)
        self.assertIn(
            "--bs-btn-border-color: var(--moo-foreground);",
            outline_primary,
        )
        self.assertIn("--bs-btn-hover-color: var(--moo-surface);", outline_primary)

    def test_owned_disabled_buttons_use_runtime_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        owned_variants = css.split(
            ":is(.btn-primary, .btn-secondary, .btn-outline-secondary, .btn-outline-primary, .btn-ghost, .btn-danger) {",
            1,
        )[1].split("}", 1)[0]
        disabled_rule = css.split(
            ".btn:disabled,\n.btn.disabled,\n.btn[aria-disabled=\"true\"] {",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("--bs-btn-disabled-color: var(--bs-btn-color);", owned_variants)
        self.assertIn(
            "--bs-btn-disabled-border-color: var(--bs-btn-border-color);",
            owned_variants,
        )
        self.assertIn(
            ":is(.btn-primary, .btn-secondary, .btn-danger) {",
            css,
        )
        self.assertIn(
            ":is(.btn-outline-secondary, .btn-outline-primary, .btn-ghost) {",
            css,
        )
        self.assertIn("opacity: var(--bs-btn-disabled-opacity);", disabled_rule)
        self.assertNotIn("opacity: 0.5;", disabled_rule)
