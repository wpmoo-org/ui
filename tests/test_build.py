from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ICONS = ROOT / "src/icons/lucide-icons.json"


def lucide_body(name: str) -> str:
    return json.loads(ICONS.read_text(encoding="utf-8"))["icons"][name]["body"]


class CatalogBuildTests(unittest.TestCase):
    def run_build(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def read_output(self, relative_path: str) -> str:
        return (DIST / relative_path).read_text(encoding="utf-8")

    def test_build_creates_static_entrypoints(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "index.html").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.css").is_file())
        self.assertTrue((DIST / "assets/css/catalog.css").is_file())
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js").is_file()
        )

    def test_build_uses_one_shared_catalog_shell(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        self.assertEqual(index.count('data-moo-shell="catalog"'), 1)
        self.assertEqual(index.count("<header"), 1)
        self.assertEqual(index.count("<footer"), 1)
        self.assertIn('href="components/button.html"', index)
        self.assertIn('id="main-content"', index)
        self.assertIn('href="#main-content"', index)
        self.assertIn('id="main-content" tabindex="-1"', index)

        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            catalog,
            [
                {"slug": "button", "label": "Button", "status": "ready"},
                {
                    "slug": "button-group",
                    "label": "Button Group",
                    "status": "ready",
                },
            ],
        )

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
        self.assertEqual(example_template.count("{{ rendered | e }}"), 1)
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

    def test_icons_render_from_local_lucide_json_source(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(ICONS.is_file())
        self.assertFalse((DIST / "assets/icons/lucide-icons.json").exists())

        icon_data = json.loads(ICONS.read_text(encoding="utf-8"))
        self.assertEqual(icon_data["prefix"], "lucide")
        self.assertIn("arrow-left", icon_data["icons"])
        self.assertIn("audio-lines", icon_data["icons"])

        button_template = (
            ROOT / "src/components/button.html.jinja"
        ).read_text(encoding="utf-8")
        self.assertIn("lucide_icon(name, position)", button_template)
        self.assertNotIn("{% if name ==", button_template)

    def test_component_pages_render_public_api_reference_sections(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for relative_path in (
            "components/button.html",
            "components/button-group.html",
        ):
            page = self.read_output(relative_path)
            self.assertIn('class="moo-component-reference"', page)
            reference = page.split('class="moo-component-reference"', 1)[1]
            self.assertIn(">API Reference</h2>", reference)
            self.assertNotIn("<pre", reference)
            self.assertNotIn("button(", reference)
            self.assertNotIn("Use the Jinja", page)
            self.assertNotIn("button_group(", page)
            self.assertNotIn("Internal note:", page)

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

    def test_button_group_page_uses_bootstrap_native_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = DIST / "components/button-group.html"
        self.assertTrue(output.is_file())

        page = output.read_text(encoding="utf-8")
        self.assertGreater(page.count("moo-example__preview"), 0)
        self.assertEqual(
            page.count("moo-example__preview"),
            page.count("moo-example__source"),
        )
        for marker in (
            'data-example="basic-actions"',
            'data-example="icon-only-group"',
            'data-example="size-groups"',
            'data-example="vertical-group"',
            'data-example="toolbar-groups"',
            'data-example="radio-toggle-group"',
            'data-example="nested-groups"',
            'data-example="rtl-preview"',
        ):
            self.assertIn(marker, page)

        for native_class in (
            "btn-group",
            "btn-group-vertical",
            "btn-toolbar",
            "btn-group-sm",
            "btn-group-lg",
            "btn-check",
        ):
            self.assertIn(native_class, page)

        self.assertIn('role="group"', page)
        self.assertIn('role="toolbar"', page)
        self.assertIn('aria-label="Ticket actions"', page)
        self.assertIn('aria-label="Media controls"', page)
        self.assertIn('name="button-group-view"', page)
        self.assertIn('autocomplete="off"', page)
        self.assertNotIn('<a class="btn', page)
        self.assertNotIn("example.com", page)
        self.assertNotIn("React", page)
        self.assertNotIn("Tailwind", page)

    def test_button_group_api_reference_documents_public_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        self.assertIn('class="moo-component-reference"', page)
        reference = page.split('class="moo-component-reference"', 1)[1]
        for contract_text in (
            "btn-group",
            "btn-group-vertical",
            "btn-toolbar",
            "btn-group-sm",
            "role",
            "aria-label",
            "View markup",
        ):
            self.assertIn(contract_text, reference)
        self.assertNotIn("button_group(", reference)
        self.assertNotIn("Internal note", reference)

    def test_button_group_rtl_keeps_bootstrap_ltr_geometry(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn("[dir=\"rtl\"] .btn-group,", css)
        self.assertIn("[dir=\"rtl\"] .btn-toolbar {", css)
        self.assertIn("direction: ltr;", css)
        self.assertIn("[dir=\"rtl\"] .btn-group > .btn,", css)
        self.assertIn("[dir=\"rtl\"] .btn-toolbar > .btn {", css)
        self.assertIn("unicode-bidi: plaintext;", css)

    def test_button_group_more_buttons_use_svg_ellipsis_icon(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        self.assertIn('aria-label="More options"', page)
        self.assertNotIn("…", page)
        self.assertIn('data-icon="inline-start"', page)
        self.assertIn(lucide_body("ellipsis"), page)
        self.assertNotIn("‹", page)
        self.assertNotIn("›", page)

    def test_button_group_composition_uses_native_dropdown(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        composition = page.split('data-example="basic-actions"', 1)[1].split(
            "</section>", 1
        )[0]
        self.assertIn('aria-label="Go back"', composition)
        self.assertIn(lucide_body("arrow-left"), composition)
        self.assertIn('data-bs-toggle="dropdown"', composition)
        self.assertIn('aria-expanded="false"', composition)
        self.assertIn('btn-icon dropdown-toggle', composition)
        self.assertIn('class="dropdown-menu dropdown-menu-end"', composition)
        self.assertIn('class="dropdown-item"', composition)
        self.assertIn("dropdown-divider", composition)
        self.assertNotIn("‹", composition)
        self.assertNotIn('href="#"', composition)

    def test_button_group_examples_cover_orientation_size_and_input(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        self.assertIn('aria-label="Increase value"', page)
        self.assertIn('aria-label="Decrease value"', page)
        self.assertIn(lucide_body("plus"), page)
        self.assertIn(lucide_body("minus"), page)
        self.assertIn('placeholder="Send a message..."', page)
        self.assertIn('aria-label="Add attachment"', page)
        self.assertIn('aria-label="Record voice note"', page)
        self.assertIn(
            'class="d-flex flex-column align-items-center gap-3 mx-auto"',
            page,
        )
        self.assertIn(
            'class="d-flex align-items-center gap-2 mx-auto moo-button-group-message"',
            page,
        )
        self.assertIn('class="input-group moo-button-group-input"', page)
        self.assertIn(lucide_body("audio-lines"), page)

    def test_button_group_dropdown_uses_runtime_theme_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(".dropdown-menu {", css)
        self.assertIn("--bs-dropdown-bg: var(--moo-surface);", css)
        self.assertIn("--bs-dropdown-border-color: var(--moo-border);", css)
        self.assertIn(
            "--bs-dropdown-link-hover-bg: var(--moo-muted-surface);",
            css,
        )
        self.assertIn(".dropdown-item > [data-icon=\"inline-start\"]", css)

    def test_dropdown_examples_are_not_clipped_by_preview_card(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-example__preview:has(.dropdown-menu) {", css)
        dropdown_preview = css.split(
            ".moo-example__preview:has(.dropdown-menu) {", 1
        )[1].split("}", 1)[0]
        self.assertIn("overflow: visible;", dropdown_preview)
        self.assertIn("align-items: flex-start;", dropdown_preview)
        self.assertIn("min-height: 22rem;", dropdown_preview)

    def test_button_group_dropdown_items_match_shadcn_spacing(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        dropdown_menu = css.rsplit(".dropdown-menu {", 1)[1].split("}", 1)[0]
        self.assertIn("--bs-dropdown-padding-x: 0.25rem;", dropdown_menu)
        self.assertIn("--bs-dropdown-item-border-radius: var(--bs-border-radius);", dropdown_menu)
        self.assertIn("--bs-dropdown-item-padding-x: 0.5rem;", dropdown_menu)
        self.assertIn("--bs-dropdown-item-padding-y: 0.375rem;", dropdown_menu)
        self.assertIn(".dropdown-item:hover,", css)
        self.assertIn(".dropdown-item:focus {", css)
        hover_block = css.rsplit(".dropdown-item:hover,", 1)[1].split("}", 1)[0]
        self.assertIn("border-radius: var(--bs-dropdown-item-border-radius);", hover_block)
        self.assertIn(".btn-icon.dropdown-toggle::after {", css)
        self.assertIn("display: none;", css.rsplit(".btn-icon.dropdown-toggle::after {", 1)[1].split("}", 1)[0])


if __name__ == "__main__":
    unittest.main()
