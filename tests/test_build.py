from __future__ import annotations

import json
import re
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
        self.assertIn('href="components/card.html"', index)
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
                {"slug": "card", "label": "Card", "status": "ready"},
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

    def test_render_example_owns_one_preview_and_source_surface(self) -> None:
        template = (
            ROOT / "src/components/example.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertEqual(template.count('class="moo-example__surface"'), 1)
        self.assertEqual(template.count('class="moo-example__preview"'), 1)
        self.assertEqual(template.count('class="moo-example__source"'), 1)
        self.assertIn("<summary>View Code</summary>", template)
        self.assertEqual(template.count("{{ rendered | safe }}"), 1)
        self.assertEqual(template.count("{{ rendered | e }}"), 1)

    def test_component_pages_use_shared_api_reference_macro(self) -> None:
        macro_path = ROOT / "src/components/api_reference.html.jinja"
        self.assertTrue(macro_path.is_file())
        macro = macro_path.read_text(encoding="utf-8")
        self.assertIn("{% macro render_api_reference(", macro)
        self.assertEqual(macro.count('class="moo-component-reference"'), 1)

        for path in sorted((ROOT / "src/pages/components").glob("*.jinja")):
            source = path.read_text(encoding="utf-8")
            with self.subTest(page=path.name):
                self.assertIn(
                    '{% from "components/api_reference.html.jinja" import render_api_reference %}',
                    source,
                )
                self.assertIn("{{ render_api_reference(", source)
                self.assertNotIn(
                    '<section class="moo-component-reference"',
                    source,
                )
                self.assertNotIn('<table class="table', source)

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
            "components/card.html",
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

    def test_card_examples_are_generated_from_component_macro(self) -> None:
        card_component_path = ROOT / "src/components/card.html.jinja"
        self.assertTrue(card_component_path.is_file())
        card_component = card_component_path.read_text(encoding="utf-8")
        card_page = (
            ROOT / "src/pages/components/card.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertIn("{% macro card(", card_component)
        self.assertIn(
            '{% from "components/card.html.jinja" import card %}',
            card_page,
        )
        self.assertNotIn('<div class="card"', card_page)

    def test_component_scss_stays_inside_bootstrap_selector_ownership(self) -> None:
        allowed_prefixes = {
            "button": ("btn", "disabled"),
            "button_group": ("btn",),
            "card": ("card",),
        }

        for path in sorted((ROOT / "scss/components").glob("*.scss")):
            source = path.read_text(encoding="utf-8")
            component = path.stem.removeprefix("_")
            prefixes = allowed_prefixes.get(
                component,
                (component.replace("_", "-"),),
            )

            for class_name in set(re.findall(r"\.([a-z][a-z0-9_-]*)", source)):
                with self.subTest(component=component, selector=class_name):
                    self.assertTrue(
                        any(
                            class_name == prefix
                            or class_name.startswith(f"{prefix}-")
                            for prefix in prefixes
                        ),
                        f".{class_name} belongs to another component or catalog chrome",
                    )

    def test_component_pages_compose_ready_macros_only(self) -> None:
        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        ready = {
            item["slug"] for item in catalog if item["status"] == "ready"
        }
        infrastructure = {"api_reference", "example"}
        component_class = re.compile(
            r"^(?:accordion|alert|badge|btn|card|dropdown|form-control|"
            r"form-label|input-group|list-group|modal|nav|navbar|offcanvas|"
            r"placeholder|popover|progress|spinner|toast)(?:-|$)"
        )

        for path in sorted((ROOT / "src/pages/components").glob("*.jinja")):
            source = path.read_text(encoding="utf-8")

            with self.subTest(page=path.name, contract="interactive markup"):
                self.assertNotRegex(
                    source,
                    r"<(?:button|form|input|select|textarea)\b",
                )

            imports = re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
            for imported in imports:
                with self.subTest(page=path.name, imported=imported):
                    self.assertTrue(
                        imported in infrastructure
                        or imported.replace("_", "-") in ready,
                        f"{imported} is not a ready component macro",
                    )

            for class_value in re.findall(r'class="([^"]*)"', source):
                for class_name in class_value.split():
                    with self.subTest(page=path.name, class_name=class_name):
                        self.assertIsNone(
                            component_class.match(class_name),
                            f".{class_name} must come from a ready component macro",
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
            'data-example="rtl-preview"',
        ):
            self.assertIn(marker, page)

        for native_class in (
            "btn-group",
            "btn-group-vertical",
            "btn-toolbar",
            "btn-group-sm",
            "btn-group-lg",
        ):
            self.assertIn(native_class, page)

        self.assertIn('role="group"', page)
        self.assertIn('role="toolbar"', page)
        self.assertIn('aria-label="Ticket actions"', page)
        self.assertIn('aria-label="Media controls"', page)
        self.assertNotIn("dropdown-menu", page)
        self.assertNotIn("btn-check", page)
        self.assertNotIn("form-control", page)
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
            "View Code",
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

    def test_button_group_composition_uses_ready_group_macros(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        composition = page.split('data-example="basic-actions"', 1)[1].split(
            "</section>", 1
        )[0]
        self.assertIn('aria-label="Go back"', composition)
        self.assertIn(lucide_body("arrow-left"), composition)
        self.assertIn('aria-label="Ticket review"', composition)
        self.assertIn("Archive", composition)
        self.assertIn("Report", composition)
        self.assertIn("Snooze", composition)
        self.assertNotIn("dropdown", composition)
        self.assertNotIn("‹", composition)
        self.assertNotIn('href="#"', composition)

    def test_button_group_examples_cover_orientation_and_size(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        self.assertIn('aria-label="Increase value"', page)
        self.assertIn('aria-label="Decrease value"', page)
        self.assertIn(lucide_body("plus"), page)
        self.assertIn(lucide_body("minus"), page)
        self.assertIn(
            'class="d-flex flex-column align-items-center gap-3"',
            page,
        )

    def test_card_page_uses_bootstrap_native_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = DIST / "components/card.html"
        self.assertTrue(output.is_file())

        page = output.read_text(encoding="utf-8")
        self.assertGreater(page.count("moo-example__preview"), 0)
        self.assertEqual(
            page.count("moo-example__preview"),
            page.count("moo-example__source"),
        )
        for marker in (
            'data-example="card-content"',
            'data-example="card-basic"',
            'data-example="card-actions"',
            'data-example="card-rtl"',
        ):
            self.assertIn(marker, page)

        for native_class in (
            "card",
            "card-header",
            "card-body",
            "card-title",
            "card-subtitle",
            "card-text",
            "card-footer",
        ):
            self.assertIn(native_class, page)

        # Examples reuse finished controls only; no unbuilt elements.
        self.assertIn('class="btn btn-primary"', page)
        self.assertIn('class="btn btn-outline-secondary"', page)
        self.assertIn('dir="rtl"', page)
        self.assertNotIn('<a class="btn', page)
        self.assertNotIn("<input", page)
        self.assertNotIn("form-control", page)
        self.assertNotIn("form-label", page)
        self.assertNotIn("list-group", page)
        self.assertNotIn("card-img", page)
        self.assertNotIn("example.com", page)
        for runtime_name in ("React", "Tailwind", "className", "shadcn"):
            self.assertNotIn(runtime_name, page)

    def test_card_api_reference_documents_public_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/card.html")
        self.assertIn('class="moo-component-reference"', page)
        reference = page.split('class="moo-component-reference"', 1)[1]
        for contract_text in (
            "card",
            "card-header",
            "card-body",
            "card-title",
            "card-subtitle",
            "card-text",
            "card-footer",
            "View Code",
        ):
            self.assertIn(contract_text, reference)
        self.assertNotIn("<pre", reference)
        self.assertNotIn("card(", reference)
        self.assertNotIn("Internal note", reference)

    def test_card_uses_runtime_theme_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn('@import "components/card";', (ROOT / "scss/moo-ui.scss").read_text(encoding="utf-8"))
        self.assertIn(".card {", css)
        card_block = css.rsplit(".card {", 1)[1].split("}", 1)[0]
        for declaration in (
            "--bs-card-bg: var(--moo-surface);",
            "--bs-card-color: var(--moo-foreground);",
            "--bs-card-border-color: var(--moo-border);",
            "--bs-card-border-radius: var(--bs-border-radius-xl);",
            "--bs-card-box-shadow: var(--bs-box-shadow-sm);",
            "--bs-card-cap-bg: transparent;",
            "--bs-card-title-color: var(--moo-foreground);",
            "--bs-card-subtitle-color: var(--moo-muted-foreground);",
        ):
            self.assertIn(declaration, card_block)

    def test_card_bridges_shared_primitives_without_hardcoded_values(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        card_scss = (
            ROOT / "scss/components/_card.scss"
        ).read_text(encoding="utf-8")
        # Colours are only ever referenced through tokens, never hardcoded.
        self.assertNotIn("#", card_scss)
        self.assertNotIn("rgb", card_scss)
        # Elevation and radius consume the UI-wide shared primitives.
        self.assertIn(
            "--bs-card-box-shadow: var(--bs-box-shadow-sm);", card_scss
        )
        self.assertIn(
            "--bs-card-border-radius: var(--bs-border-radius-xl);", card_scss
        )
        # Themed colours come from runtime theme tokens.
        self.assertIn("var(--moo-surface)", card_scss)
        self.assertIn("var(--moo-border)", card_scss)
        # No dependency on elements that are not built yet.
        self.assertNotIn("form-control", card_scss)
        self.assertNotIn("list-group", card_scss)

    def test_elevation_and_radius_scales_are_shared_ui_wide(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        # shadcn elevation lives on Bootstrap's own UI-wide shadow scale.
        self.assertIn(
            "--bs-box-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);", css
        )
        self.assertIn("--bs-border-radius-xl: 0.75rem;", css)
        variables = (
            ROOT / "scss/_primary_variables.scss"
        ).read_text(encoding="utf-8")
        self.assertIn("$box-shadow-sm:", variables)
        self.assertIn("$border-radius-xl:", variables)

    def test_component_styles_use_bootstrap_visual_primitives(self) -> None:
        for path in sorted((ROOT / "scss/components").glob("*.scss")):
            source = path.read_text(encoding="utf-8")

            with self.subTest(component=path.name):
                self.assertNotRegex(
                    source,
                    r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(",
                    "Component colors must use runtime theme tokens",
                )

                for line in source.splitlines():
                    declaration = line.strip()
                    if declaration.startswith("box-shadow:"):
                        self.assertRegex(
                            declaration,
                            r"^box-shadow: (?:none|var\(--bs-[a-z0-9-]*box-shadow[a-z0-9-]*\));$",
                        )
                    elif declaration.startswith("border-radius:"):
                        self.assertRegex(
                            declaration,
                            r"^border-radius: (?:0|var\(--bs-[a-z0-9-]*border-radius[a-z0-9-]*\));$",
                        )
                    elif declaration.startswith("--bs-"):
                        name, value = declaration.rstrip(";").split(":", 1)
                        value = value.strip()
                        if "box-shadow" in name:
                            self.assertRegex(
                                value,
                                r"^(?:none|var\(--bs-box-shadow(?:-[a-z0-9-]+)?\))$",
                            )
                        elif "border-radius" in name:
                            self.assertRegex(
                                value,
                                r"^(?:0|var\(--bs-border-radius(?:-[a-z0-9-]+)?\))$",
                            )

    def test_example_preview_container_centers_component_demos(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        preview_block = css.split(".moo-example__preview {", 1)[1].split("}", 1)[0]
        self.assertIn("justify-content: center;", preview_block)
        for component_page in (
            "components/button.html",
            "components/button-group.html",
            "components/card.html",
        ):
            page = self.read_output(component_page)
            examples = page.split(
                '<section class="moo-component-reference"',
                1,
            )[0]
            self.assertNotIn("mx-auto", examples)

    def test_catalog_example_surface_integrates_preview_and_code(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-example__surface {", css)
        surface = css.split(".moo-example__surface {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow: hidden;", surface)
        self.assertIn("border: var(--bs-border-width) solid var(--bs-border-color);", surface)
        self.assertIn(".moo-example__source {", css)
        source = css.split(".moo-example__source {", 1)[1].split("}", 1)[0]
        self.assertIn("border-top: var(--bs-border-width) solid var(--bs-border-color);", source)
        source_code = css.split(".moo-example__source pre {", 1)[1].split("}", 1)[0]
        self.assertIn("white-space: pre-wrap;", source_code)
        self.assertIn("overflow-wrap: anywhere;", source_code)
        self.assertNotIn("max-height:", source_code)
        self.assertNotIn("overflow:", source_code)
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


if __name__ == "__main__":
    unittest.main()
