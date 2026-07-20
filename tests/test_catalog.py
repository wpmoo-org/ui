from __future__ import annotations

import json
import re

from tests.helpers import (
    DIST,
    ICONS,
    PNG_COLOR_TYPE_RGBA,
    ROOT,
    STATIC,
    CatalogTestCase,
    is_valid_webp,
    read_png_ihdr,
)


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

        for path in (
            ROOT / "src/components/dropdown_menu.html.jinja",
            ROOT / "src/includes/example.html.jinja",
        ):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("render_icon(", source)
                self.assertNotIn("lucide_icon(", source)

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
            # Bootstrap renders both single-line inputs and textareas through
            # the shared `.form-control` family.
            "textarea": ("form-control",),
            # Bootstrap's own forms/_input-group.scss styles `.input-group >
            # .form-control` / `> .form-select`, so the group legitimately owns
            # those controls within its scope.
            "input_group": ("input-group", "form-control", "form-select"),
            # Bootstrap documents vertical navs as `.nav.flex-column`, so the
            # Navigation partial may scope width fixes to that native utility.
            "navigation": ("active", "disabled", "flex-column", "nav"),
            # Bootstrap has no native sidebar component; its public namespace
            # is owned explicitly by the Sidebar partial and styles.
            "sidebar": ("sidebar",),
            # Bootstrap's pagination markup uses .page-item/.page-link, not a
            # "pagination-" prefixed family.
            "pagination": ("pagination", "page"),
            # Bootstrap's checkbox markup uses the shared .form-check family,
            # not a "checkbox-" prefixed one.
            "checkbox": ("form-check",),
            # The legend reuses Bootstrap's shared .form-label class to
            # match sibling form labels.
            "radio_group": ("radio-group", "form-label"),
            # Bootstrap's switch markup uses the shared .form-switch and
            # .form-check families, not a "switch-" prefixed one.
            "switch": ("form-switch", "form-check"),
            # Bootstrap's own Collapse plugin toggles the bare .collapsed
            # state class on the trigger; it is not "accordion-" prefixed.
            "accordion": ("accordion", "collapsed"),
            # The segmented-control track styles Bootstrap's shared
            # .nav-link/.active classes within its own .tabs-list scope,
            # rather than the .nav-pills family Navigation already owns,
            # and also fixes the grid stacking on Bootstrap's own tab-content
            # and tab-pane classes.
            "tabs": ("tabs", "nav-link", "active", "tab-content", "tab-pane"),
            # Dialog is the Moo catalog name for Bootstrap's Modal component;
            # its native selector family is "modal-", not "dialog-".
            "dialog": ("modal",),
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
            r"^(?:accordion|alert|badge|breadcrumb|btn|card|dropdown|"
            r"form-check|form-control|form-label|input-group|list-group|"
            r"modal|nav|navbar|offcanvas|page|pagination|placeholder|"
            r"popover|progress|spinner|table|toast)(?:-|$)"
        )

        pages = [
            *sorted((ROOT / "src/pages/components").glob("*.jinja")),
            # The components index composes the same ready macros; it gets no
            # exemption.
            ROOT / "src/pages/components/index.html.jinja",
        ]
        for path in pages:
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

    def test_component_pages_link_to_bootstrap_documentation(self) -> None:
        for path in sorted((ROOT / "src/pages/components").glob("*.jinja")):
            # The components index lists every component; it documents no
            # single Bootstrap component itself, so it carries no reference.
            if path.name == "index.html.jinja":
                continue
            source = path.read_text(encoding="utf-8")

            with self.subTest(page=path.name, contract="reference import"):
                self.assertIn(
                    '{% from "includes/documentation-reference.html.jinja" '
                    "import render_reference %}",
                    source,
                )
            with self.subTest(page=path.name, contract="reference call"):
                self.assertIn("render_reference(", source)

    def test_ready_components_ship_a_real_preview_image(self) -> None:
        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        ready_slugs = [
            item["slug"] for item in catalog if item["status"] == "ready"
        ]
        previews_dir = STATIC / "images/components"

        for slug in ready_slugs:
            with self.subTest(slug=slug):
                png_path = previews_dir / f"{slug}.png"
                webp_path = previews_dir / f"{slug}.webp"
                self.assertTrue(
                    png_path.is_file() or webp_path.is_file(),
                    f"{slug} has no preview PNG/WEBP and silently falls back "
                    "to placeholder.webp",
                )
                if webp_path.is_file():
                    self.assertTrue(
                        is_valid_webp(webp_path),
                        f"{slug}.webp is not a well-formed WebP file",
                    )
                    continue
                width, height, color_type = read_png_ihdr(png_path)
                self.assertEqual((width, height), (1536, 1024), slug)
                self.assertEqual(
                    color_type,
                    PNG_COLOR_TYPE_RGBA,
                    f"{slug}.png is not RGBA (color type {color_type})",
                )

    def test_components_index_uses_admin_shell_primitives(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("components/index.html")

        for contract in (
            'data-moo-shell="catalog"',
            'class="sidebar-wrapper"',
            'id="catalog-sidebar"',
            'data-moo-sidebar-trigger',
            "moo-catalog__search-trigger",
            "wpmoo-org/ui",
            'aria-label="Catalog navigation"',
            "input-group",
            "dropdown-menu",
            "scroll-fade-y no-scrollbar",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, index)
        self.assertRegex(index, r'class="[^"]*\bbadge\b')
        self.assertRegex(index, r'class="[^"]*\bbtn\b[^"]*\bbtn-outline')

    def test_catalog_search_trigger_opens_command_palette(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        preview = self.read_output("assets/js/preview.js")

        # The header search trigger opens a command-palette modal listing the
        # catalog pages; it no longer deep-links to the index filter field.
        self.assertIn("moo-catalog__search-trigger", index)
        self.assertIn('id="catalog-command"', index)
        self.assertIn("data-moo-command-item", index)
        self.assertIn('href="index.html"', index)
        self.assertIn('href="components/index.html"', index)
        self.assertIn('href="components/button.html"', index)
        # Open + filter + keyboard navigation behavior lives in preview.js.
        self.assertIn("moo-catalog__search-trigger", preview)
        self.assertIn("catalog-command", preview)

    def test_home_page_introduces_the_product_and_links_to_components(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        self.assertIn('data-moo-shell="catalog"', home)
        self.assertIn("Moo UI", home)
        self.assertIn(
            "Bootstrap-native component system", home
        )
        self.assertIn('href="components/index.html"', home)
        self.assertRegex(home, r'class="[^"]*\bbtn\b[^"]*\bbtn-outline')

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
                            r"^border-radius: (?:0|\$input-border-radius|var\(--bs-[a-z0-9-]*border-radius[a-z0-9-]*\));$",
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
