from __future__ import annotations

import json
import re

from tests.helpers import DIST, ICONS, ROOT, CatalogTestCase


class CatalogContractTests(CatalogTestCase):
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
        self.assertIn("render_icon(name, position)", button_template)
        self.assertNotIn("lucide_icon(", button_template)
        self.assertNotIn("{% if name ==", button_template)

    def test_icons_need_no_cdn_or_runtime_script(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for path in DIST.rglob("*.html"):
            page = path.read_text(encoding="utf-8")
            for script_source in re.findall(
                r'<script\b[^>]*\bsrc="([^"]+)"', page
            ):
                self.assertNotRegex(script_source, r"^(?:https?:)?//")
                self.assertNotRegex(script_source, r"(?i)(?:iconify|lucide)")

    def test_component_scss_stays_inside_bootstrap_selector_ownership(self) -> None:
        allowed_prefixes = {
            "button": ("btn", "disabled"),
            "button_group": ("btn",),
            "card": ("card",),
            "input": ("form-control",),
            # Bootstrap's own forms/_input-group.scss styles `.input-group >
            # .form-control` / `> .form-select`, so the group legitimately owns
            # those controls within its scope.
            "input_group": ("input-group", "form-control", "form-select"),
            "navigation": ("active", "disabled", "nav"),
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
        infrastructure = {"example"}
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
                    r"<(?:button|form|input|kbd|select|textarea)\b",
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
                            r"^box-shadow: (?:none|\$input-focus-box-shadow|var\(--bs-[a-z0-9-]*box-shadow[a-z0-9-]*\));$",
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
                                r"^(?:0|var\(--bs-border-radius(?:-[a-z0-9-]+)?\)|calc\(var\(--bs-[a-z0-9-]*border-radius\) - var\(--bs-[a-z0-9-]*border-width\)\))$",
                            )

    def test_example_preview_container_centers_component_demos(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/catalog.css")
        preview_block = css.split(".moo-example__preview {", 1)[1].split("}", 1)[0]
        self.assertIn("justify-content: center;", preview_block)
        self.assertIn(".moo-example__preview--narrow > * {", css)
        self.assertNotIn(".moo-example__preview .card", css)
        for component_page in (
            "components/button.html",
            "components/button-group.html",
            "components/card.html",
        ):
            page = self.read_output(component_page)
            self.assertNotIn("mx-auto", page)
