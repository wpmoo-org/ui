from __future__ import annotations

import json
import re

from tests.helpers import DIST, ICONS, ROOT, CatalogTestCase


class CatalogContractTests(CatalogTestCase):
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

    def test_elevation_and_radius_scales_are_shared_ui_wide(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
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
