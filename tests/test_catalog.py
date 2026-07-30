from __future__ import annotations

import json
import re
import tempfile
import warnings
from pathlib import Path

import build as site_build

from tests.helpers import (
    DIST,
    ICONS,
    PNG_COLOR_TYPE_RGBA,
    ROOT,
    STATIC,
    CatalogTestCase,
    is_valid_webp,
    read_catalog_styles,
    read_png_ihdr,
    read_primary_variables,
)


class CatalogContractTests(CatalogTestCase):
    INTERNAL_PUBLIC_API_SNIPPETS = (
        "Jinja macro API",
        "public macro API",
        "distributed macro",
        "ready Button macro",
        "ready Badge macro",
        "ready Dropdown Menu macro",
        "ready Dropdown Menu macros",
        "toast_target",
        "popover_dismiss_trigger()",
        "alert_dialog_header()",
        "dialog_body()",
        "table_row_actions()",
        "sidebar_provider()",
        "field_group()",
        "field_description()",
        "field_error()",
        "fieldset()",
        "field()",
        "form()",
    )
    def assert_no_internal_public_api_guidance(
        self,
        surface: str,
        path: str,
    ) -> None:
        for snippet in self.INTERNAL_PUBLIC_API_SNIPPETS:
            if snippet in surface:
                raise AssertionError(
                    f"{path} presents internal build API guidance: {snippet}"
                )

    def write_json_fixture(
        self,
        root: Path,
        name: str,
        payload: dict[str, object],
    ) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_main_scroller_keeps_keyboard_focus_targets_immediately_visible(self) -> None:
        styles = read_catalog_styles()
        match = re.search(r"\.moo-catalog__main\s*\{(?P<body>[^}]*)\}", styles)

        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("overflow-y: auto", body)
        self.assertNotIn("scroll-behavior: smooth", body)

    def test_visible_component_lists_are_sorted_by_label(self) -> None:
        sorted_loop = (
            '{% for component in catalog | sort(attribute="label") %}'
        )

        for path in (
            ROOT / "site/src/shell/sidebar.html.jinja",
            ROOT / "site/src/pages/components/index.html.jinja",
        ):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertTrue(
                    sorted_loop in path.read_text(encoding="utf-8"),
                    f"{path.relative_to(ROOT)} must sort components by label",
                )

    def test_llms_txt_lists_ready_components_alphabetically(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        expected = [
            f"- [{item['label']}](https://ui.wpmoo.org/components/{item['slug']}/)"
            for item in sorted(
                (item for item in catalog if item["status"] == "ready"),
                key=lambda item: item["label"].casefold(),
            )
        ]

        lines = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8").splitlines()
        start = lines.index("## Component Catalog")
        end = lines.index("## Utilities And Blocks")
        component_lines = [
            line
            for line in lines[start + 1 : end]
            if line.startswith("- [")
            and "/components/" in line
            and not line.startswith("- [Components]")
        ]

        self.assertEqual(component_lines, expected)

    def test_llms_txt_cdn_example_tracks_package_version(self) -> None:
        package = json.loads(
            (ROOT / "package.json").read_text(encoding="utf-8")
        )
        llms = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8")
        match = re.search(
            r"https://unpkg\.com/@wpmoo/ui@([^/]+)/dist/assets/css/moo-ui\.css",
            llms,
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), package["version"])

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
            ROOT / "site/src/includes/example.html.jinja",
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
            # Dropdown toggle rows use Bootstrap Button's .active data-api
            # state while scoped under .dropdown-item-check.
            "dropdown": ("dropdown", "active"),
            "input": ("form-control", "form-select"),
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
            "pagination": ("pagination", "page", "disabled"),
            # Bootstrap's checkbox markup uses the shared .form-check family,
            # not a "checkbox-" prefixed one.
            "checkbox": ("form-check",),
            # The legend reuses Bootstrap's shared .form-label class to
            # match sibling form labels.
            "radio_group": ("radio-group", "form-label"),
            # Bootstrap's switch markup uses the shared .form-switch and
            # .form-check families, not a "switch-" prefixed one.
            "switch": ("form-switch", "form-check"),
            # Bootstrap's own placeholder markup uses the shared .placeholder
            # family, not a "skeleton-" prefixed one.
            "skeleton": ("skeleton", "placeholder"),
            # Bootstrap's own Collapse plugin toggles the bare .collapsed
            # state class on the trigger; it is not "accordion-" prefixed.
            "accordion": ("accordion", "collapsed"),
            # Collapsible is a thin Bootstrap Collapse composition whose
            # trigger is still a native .btn inside the component scope.
            "collapsible": ("collapsible", "btn"),
            # Menubar is backed by Bootstrap Dropdown triggers and menus; the
            # shared dropdown/show state classes remain scoped under .menubar.
            "menubar": ("menubar", "dropdown", "show"),
            # The segmented-control track styles Bootstrap's shared
            # .nav-link/.active classes within its own .tabs-list scope,
            # rather than the .nav-pills family Navigation already owns,
            # and also fixes the grid stacking on Bootstrap's own tab-content
            # and tab-pane classes.
            "tabs": ("tabs", "nav-link", "active", "disabled", "tab-content", "tab-pane"),
            # Dialog is the Moo catalog name for Bootstrap's Modal component;
            # its native selector family is "modal-", not "dialog-".
            "dialog": ("modal", "show"),
            # Sheet is the Moo catalog name for Bootstrap's Offcanvas
            # component; its native selector family is "offcanvas-", plus
            # the "sheet" marker class used to scope Sheet-only overrides
            # away from Sidebar's own bare .offcanvas usage.
            # Bootstrap's Offcanvas source owns .showing and .hiding as
            # transition lifecycle states alongside .show.
            "sheet": ("offcanvas", "sheet", "show", "showing", "hiding"),
            # Field retunes the spacing of Bootstrap's own shared
            # .form-label/.form-text/.invalid-feedback classes when they sit
            # inside a .field, rather than owning a "field-" prefixed family
            # of its own for them.
            "field": ("field", "form-label", "form-text", "is-invalid", "invalid-feedback"),
            # Bootstrap has no native Combobox component. The public
            # namespace is a composition of Bootstrap form-control,
            # validation, and Dropdown pieces.
            "combobox": ("combobox", "is-invalid"),
            # Input group owns the compound surface around Bootstrap's native
            # children, so its partial may retune the edge behavior of form,
            # button, validation, and dropdown children while scoped under
            # .input-group.
            "input_group": (
                "input-group",
                "form-control",
                "btn",
                "dropdown-menu",
                "valid-tooltip",
                "valid-feedback",
                "invalid-tooltip",
                "invalid-feedback",
                "rounded-pill",
                "show",
                "disabled",
            ),
        }

        for path in sorted((ROOT / "scss/components").glob("*.scss")):
            source = "\n".join(
                line.split("//", 1)[0]
                for line in path.read_text(encoding="utf-8").splitlines()
            )
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
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
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
        page_level_classes = {"form-label"}

        pages = [
            *sorted((ROOT / "site/src/pages/components").glob("*.jinja")),
            # The components index composes the same ready macros; it gets no
            # exemption.
            ROOT / "site/src/pages/components/index.html.jinja",
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
                        if class_name in page_level_classes:
                            continue
                        self.assertIsNone(
                            component_class.match(class_name),
                            f".{class_name} must come from a ready component macro",
                        )

    def test_component_pages_link_to_bootstrap_documentation(self) -> None:
        for path in sorted((ROOT / "site/src/pages/components").glob("*.jinja")):
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

    def test_external_blank_links_use_noopener_noreferrer(self) -> None:
        for source_root in (ROOT / "site/src", ROOT / "src"):
            for path in sorted(source_root.rglob("*.jinja")):
                source = path.read_text(encoding="utf-8")
                for tag in re.findall(r"<a\b[^>]*target=\"_blank\"[^>]*>", source):
                    with self.subTest(path=path.relative_to(ROOT), tag=tag):
                        self.assertIn('rel="', tag)
                        rel = re.search(r'rel="([^"]*)"', tag)
                        self.assertIsNotNone(rel)
                        tokens = set(rel.group(1).split())
                        self.assertIn("noopener", tokens)
                        self.assertIn("noreferrer", tokens)

    def test_ready_component_preview_images_are_valid_when_present(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        ready_slugs = [
            item["slug"] for item in catalog if item["status"] == "ready"
        ]
        previews_dir = STATIC / "images/components"
        placeholder = STATIC / "images/placeholder.webp"
        missing: list[str] = []

        self.assertTrue(
            is_valid_webp(placeholder),
            "the shared component preview fallback must be a valid WebP file",
        )

        for slug in ready_slugs:
            with self.subTest(slug=slug):
                png_path = previews_dir / f"{slug}.png"
                webp_path = previews_dir / f"{slug}.webp"
                if not png_path.is_file() and not webp_path.is_file():
                    missing.append(slug)
                    continue
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

        if missing:
            warnings.warn(
                "ready components using placeholder.webp: " + ", ".join(missing),
                stacklevel=1,
            )

    def test_catalog_builds_the_complete_root_favicon_set(self) -> None:
        svg = (ROOT / "site/public/favicon.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 24 24"', svg)
        self.assertIn("prefers-color-scheme: dark", svg)
        self.assertIn('stroke="currentColor"', svg)
        self.assertNotRegex(
            svg,
            r"(?i)<script|javascript:|foreignObject|(?:xlink:)?href=|@import|url\(",
        )

        expected_png_sizes = {
            "apple-touch-icon.png": (180, 180),
            "icon-192.png": (192, 192),
            "icon-512.png": (512, 512),
        }
        for name, expected_size in expected_png_sizes.items():
            with self.subTest(name=name):
                width, height, _ = read_png_ihdr(ROOT / "site/public" / name)
                self.assertEqual((width, height), expected_size)

        ico = (ROOT / "site/public/favicon.ico").read_bytes()
        self.assertEqual(ico[:6], b"\x00\x00\x01\x00\x03\x00")
        self.assertEqual(
            [(ico[6 + index * 16] or 256, ico[7 + index * 16] or 256) for index in range(3)],
            [(16, 16), (32, 32), (48, 48)],
        )

        manifest = json.loads(
            (ROOT / "site/public/site.webmanifest").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "Moo UI")
        self.assertEqual(manifest["short_name"], "Moo UI")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(
            [(icon["src"], icon["sizes"], icon["type"]) for icon in manifest["icons"]],
            [
                ("/icon-192.png", "192x192", "image/png"),
                ("/icon-512.png", "512x512", "image/png"),
            ],
        )

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        root_assets = (
            "favicon.svg",
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "site.webmanifest",
        )
        for name in root_assets:
            self.assertTrue((DIST / name).is_file(), name)

        page = self.read_output("introduction/index.html")
        self.assertIn('<link rel="icon" type="image/svg+xml" href="../favicon.svg">', page)
        self.assertIn('<link rel="icon" href="../favicon.ico" sizes="any">', page)
        self.assertIn('<link rel="apple-touch-icon" href="../apple-touch-icon.png">', page)
        self.assertIn('<link rel="manifest" href="../site.webmanifest">', page)
        self.assertNotIn("data-moo-favicon", page)

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
            "moo-catalog__status-menu",
            'data-moo-catalog-section-filter="all"',
            'data-moo-catalog-section-filter="components"',
            'data-moo-catalog-section-filter="utilities"',
            "scroll-fade-y no-scrollbar",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, index)
        self.assertNotIn("moo-catalog__status-select", index)
        self.assertRegex(index, r'class="[^"]*\bbadge\b')
        self.assertRegex(index, r'class="[^"]*\bbtn\b[^"]*\bbtn-outline')

    def test_catalog_search_trigger_opens_command_palette(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        preview = self.read_output("assets/js/catalog/command.js")

        # The header search trigger opens a command-palette modal listing the
        # catalog pages; it no longer deep-links to the index filter field.
        self.assertIn("moo-catalog__search-trigger", index)
        self.assertIn('id="catalog-command"', index)
        self.assertIn("data-moo-command-item", index)
        self.assertIn('href="./"', index)
        self.assertIn('href="components/"', index)
        self.assertIn('href="components/button/"', index)
        # Open + filter + keyboard navigation behavior lives in command.js.
        self.assertIn("moo-catalog__search-trigger", preview)
        self.assertIn("catalog-command", preview)

        catalog_scss = read_catalog_styles()
        self.assertIn(".moo-catalog__search-trigger:focus-visible", catalog_scss)
        self.assertIn("background: $input-disabled-bg;", catalog_scss)

    def test_theme_toggle_persists_across_page_navigation(self) -> None:
        base = (ROOT / "site/src/layouts/base.html.jinja").read_text(encoding="utf-8")
        preview = (ROOT / "site/src/js/catalog/theme.js").read_text(encoding="utf-8")

        self.assertIn('window.localStorage.getItem("moo:theme")', base)
        self.assertIn("document.documentElement.dataset.bsTheme = theme", base)
        self.assertIn('const THEME_STORAGE_KEY = "moo:theme";', preview)
        self.assertIn("view.localStorage.getItem(THEME_STORAGE_KEY)", preview)
        self.assertIn("view.localStorage.setItem(THEME_STORAGE_KEY, theme)", preview)

    def test_catalog_sidebar_persisted_state_handoff_runs_before_stylesheets(self) -> None:
        base = (ROOT / "site/src/layouts/base.html.jinja").read_text(encoding="utf-8")

        handoff = 'document.documentElement.dataset.mooSidebarCatalogState'
        self.assertIn('window.localStorage.getItem("moo-sidebar:catalog-shell")', base)
        self.assertIn(handoff, base)
        self.assertLess(
            base.index(handoff),
            base.index('<link rel="stylesheet" href="{{ root_path }}assets/css/moo-ui.css'),
        )
        self.assertLess(
            base.index(handoff),
            base.index('<link rel="stylesheet" href="{{ root_path }}assets/css/catalog.css'),
        )

    def test_built_catalog_sidebar_persisted_state_handoff_is_in_head(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        page = self.read_output("introduction.html")
        head = page.split("</head>", 1)[0]
        handoff = "dataset.mooSidebarCatalogState"
        self.assertIn(handoff, head)
        self.assertLess(head.index(handoff), head.index("assets/css/moo-ui.css"))
        self.assertLess(head.index(handoff), head.index("assets/css/catalog.css"))
        wrapper_index = page.index('data-moo-sidebar-key="catalog-shell"')
        handoff_index = page.index("shell.dataset.mooSidebarState = state")
        sidebar_index = page.index('<aside', handoff_index)
        self.assertLess(wrapper_index, handoff_index)
        self.assertLess(handoff_index, sidebar_index)

    def test_doc_body_copy_uses_the_catalog_font_size_token(self) -> None:
        catalog_scss = read_catalog_styles()

        self.assertIn("--moo-doc-body-font-size: 0.9375rem;", catalog_scss)
        self.assertIn(
            "font-size: var(--moo-doc-body-font-size);",
            catalog_scss,
        )

    def test_header_navigation_links_docs_between_home_and_components(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        header_start = index.index('<header class="moo-catalog__header">')
        header_end = index.index("</header>", header_start)
        header = index[header_start:header_end]

        home_index = header.index('href="./"')
        docs_index = header.index('href="introduction/"')
        components_index = header.index('href="components/"')
        blocks_index = header.index('href="blocks/"')

        self.assertLess(home_index, docs_index)
        self.assertLess(docs_index, components_index)
        self.assertLess(components_index, blocks_index)
        self.assertIn(">Docs</", header)

    def test_home_page_introduces_the_product_and_links_to_components(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        self.assertIn('data-moo-shell="catalog"', home)
        self.assertIn("Moo UI", home)
        self.assertIn(
            "Bootstrap markup. shadcn feel.",
            home,
        )
        self.assertIn(
            "A product interface layer for teams that already trust Bootstrap.",
            home,
        )
        self.assertIn(
            "Moo UI keeps Bootstrap as the public contract",
            home,
        )
        self.assertIn(
            "moo-home-showcase__image",
            home,
        )
        self.assertIn(
            "moo-home-proof-card",
            home,
        )
        self.assertIn(
            "moo-home-component-row moo-home-component-row--1",
            home,
        )
        self.assertIn('href="installation/"', home)
        self.assertIn('href="components/"', home)
        self.assertIn('href="components/button/"', home)
        self.assertNotIn(
            "Moo UI — Bootstrap components with a focused visual language.",
            home,
        )
        self.assertRegex(home, r'class="[^"]*\bbtn\b[^"]*\bbtn-outline')

    def test_sections_navigation_precedes_component_catalog(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        components = self.read_output("components/index.html")

        sections_index = components.index(
            'class="sidebar-group-label" data-slot="sidebar-group-label">Sections<'
        )
        components_index = components.index(
            'class="sidebar-group-label" data-slot="sidebar-group-label">Components<'
        )
        self.assertLess(sections_index, components_index)

        for label, href in (
            ("Introduction", "../introduction/"),
            ("Installation", "../installation/"),
            ("Support &amp; Evidence", "../support/"),
            ("Contributing", "../contributing/"),
            ("Components", "../components/"),
            ("Blocks", "../blocks/"),
            ("AI Usage", "../skills/"),
            ("Changelog", "../changelog/"),
        ):
            with self.subTest(label=label):
                self.assertIn(f'href="{href}"', components)
                self.assertIn(f">{label}</", components)

    def test_introduction_page_states_moo_ui_positioning(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        introduction = self.read_output("introduction.html")

        for copy in (
            "Keep your Bootstrap 5.3 HTML and behavior. Change the visual language.",
            "Bootstrap markup. shadcn feel.",
            "Why Moo UI Exists",
            "Bootstrap is the contract",
            "shadcn is the feeling",
            "Server-rendered UI stays first-class",
            "The Goal",
            "while building a shared library of",
            "Bootstrap-native markup",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, introduction)
        self.assertIn('<ol class="moo-doc-principles">', introduction)
        self.assertIn('class="moo-doc-principles__number" aria-hidden="true">1</span>', introduction)
        self.assertNotIn("moo-doc-card-icon", introduction)
        self.assertIn('href="../installation/"', introduction)
        self.assertIn('href="../components/"', introduction)

    def test_primary_pages_share_the_page_header_macro_surface(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        for path in (
            "introduction.html",
            "installation.html",
            "skills.html",
            "changelog.html",
            "components/index.html",
            "blocks/index.html",
        ):
            with self.subTest(path=path):
                page = self.read_output(path)
                header_start = page.index('<header class="moo-component-header')
                header_end = page.index("</header>", header_start)
                header = page[header_start:header_end]

                self.assertIn("<h1", header)
                self.assertNotIn("moo-doc-hero", page)
                self.assertNotIn("moo-catalog__intro", page)

        home = self.read_output("index.html")
        self.assertIn('<section class="moo-home-hero"', home)
        self.assertIn('<h1 class="moo-home-hero__title" id="home">Moo UI</h1>', home)
        self.assertNotIn("moo-doc-hero", home)
        self.assertNotIn("moo-catalog__intro", home)

        introduction = self.read_output("introduction.html")
        self.assertIn("moo-component-header__actions", introduction)

    def test_section_pages_render_page_actions_and_pagination(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        introduction = self.read_output("introduction.html")
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', introduction)
        self.assertIn("data-moo-copy-page", introduction)
        self.assertIn("Copy Link", introduction)
        self.assertIn("Open in ChatGPT", introduction)
        self.assertIn("Open in Claude", introduction)
        self.assertIn("Open in v0", introduction)
        self.assertNotIn("Copy page link", introduction)
        self.assertIn('class="moo-doc-page-actions__nav"', introduction)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', introduction)
        self.assertIn('aria-label="Previous page: Home"', introduction)
        self.assertIn('href="../installation/"', introduction)
        self.assertNotIn('aria-label="Previous page: Changelog"', introduction)

        installation = self.read_output("installation.html")
        self.assertIn('aria-label="Previous page: Introduction"', installation)
        self.assertIn('aria-label="Next page: Support &amp; Evidence"', installation)
        self.assertIn('href="../support/"', installation)

        support = self.read_output("support.html")
        self.assertIn('aria-label="Previous page: Installation"', support)
        self.assertIn('aria-label="Next page: Contributing"', support)
        self.assertIn('href="../contributing/"', support)

        contributing = self.read_output("contributing.html")
        self.assertIn('aria-label="Previous page: Support &amp; Evidence"', contributing)
        self.assertIn('aria-label="Next page: Components"', contributing)
        self.assertIn('href="../components/"', contributing)

        components = self.read_output("components/index.html")
        self.assertIn('aria-label="Previous page: Contributing"', components)
        self.assertIn('aria-label="Next page: Accordion"', components)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', components)

        blocks = self.read_output("blocks/index.html")
        self.assertIn('aria-label="Previous page: Scroll Fade"', blocks)
        self.assertIn('aria-label="Next page: Sidebar (Floating)"', blocks)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', blocks)

        component = self.read_output("components/switch.html")
        component_header_start = component.index('<header class="moo-component-header')
        component_header = component[
            component_header_start : component.index("</header>", component_header_start)
        ]
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', component_header)
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', component)
        self.assertIn('aria-label="Previous page: Spinner"', component)
        self.assertIn('aria-label="Next page: Table"', component)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', component)

        utility = self.read_output("utils/scroll-fade.html")
        utility_header_start = utility.index('<header class="moo-component-header')
        utility_header = utility[
            utility_header_start : utility.index("</header>", utility_header_start)
        ]
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', utility_header)
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', utility)
        self.assertIn('aria-label="Previous page: Typography"', utility)
        self.assertIn('aria-label="Next page: Blocks"', utility)

        block = self.read_output("blocks/sidebar-floating.html")
        block_header_start = block.index('<header class="moo-component-header')
        block_header = block[
            block_header_start : block.index("</header>", block_header_start)
        ]
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', block_header)
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', block)
        self.assertIn('aria-label="Previous page: Blocks"', block)
        self.assertIn('aria-label="Next page: Sidebar (Inset)"', block)

        last_block = self.read_output("blocks/sidebar-inset.html")
        self.assertIn('aria-label="Next page: AI Usage"', last_block)

        skills = self.read_output("skills.html")
        self.assertIn('aria-label="Previous page: Sidebar (Inset)"', skills)
        self.assertIn('aria-label="Next page: Changelog"', skills)

        code_preview = self.read_output("assets/js/catalog/code-preview.js")
        catalog_filter = self.read_output("assets/js/catalog/catalog-filter.js")
        self.assertIn("[data-moo-copy-page]", code_preview)
        self.assertIn("navigator.clipboard.writeText(value)", code_preview)
        self.assertIn("[data-moo-catalog-section-filter]", catalog_filter)
        self.assertIn("selectedSection", catalog_filter)

    def test_primary_docs_render_a_right_side_table_of_contents(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        expected_links = {
            "introduction.html": (
                ("why-moo-ui-exists", "Why Moo UI Exists"),
                ("principles", "Principles"),
                ("the-goal", "The Goal"),
            ),
            "installation.html": (
                ("choose-path", "Choose This Path"),
                ("full-build", "Full Build"),
                ("scoped-build", "Scoped Adoption"),
                ("bootstrap-javascript", "Bootstrap JavaScript"),
                ("optional-esm", "Optional Moo ESM"),
            ),
            "skills.html": (
                ("selection-criteria", "Selection Criteria"),
                ("context-block", "Context Block"),
                ("installation-facts", "Installation Facts"),
                ("public-exports", "Public Exports"),
                ("editing-guidance", "Editing Guidance"),
            ),
            "changelog.html": (
                ("release-0-7-0", "v0.7.0"),
                ("release-0-6-0", "Phase 1 Evidence Backfill"),
                ("release-0-5-0", "Optional Public Runtime Modules"),
                ("release-0-4-0", "Core Package Expansion"),
            ),
        }

        for path, links in expected_links.items():
            with self.subTest(path=path):
                page = self.read_output(path)
                self.assertIn('class="moo-doc-layout"', page)
                self.assertIn('class="moo-doc-toc d-none d-xl-block"', page)
                self.assertIn('aria-label="On this page"', page)
                for target, label in links:
                    self.assertIn(f'href="#{target}"', page)
                    self.assertIn(f">{label}</", page)

        for path in ("components/index.html", "blocks/index.html"):
            with self.subTest(path=path):
                page = self.read_output(path)
                label = "Components" if path.startswith("components/") else "Blocks"
                target = label.lower()
                self.assertIn('class="moo-doc-layout"', page)
                self.assertIn('class="moo-doc-toc d-none d-xl-block"', page)
                self.assertIn('aria-label="On this page"', page)
                self.assertIn(f'href="#{target}"', page)
                self.assertIn(f">{label}</", page)

        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-doc-layout", css)
        self.assertIn("@media (min-width: 1200px)", css)
        self.assertIn("--moo-doc-toc-offset: calc(2rem + 5px)", css)
        self.assertNotIn("scroll-behavior: smooth", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertRegex(
            css,
            r"\.moo-catalog__main\s*\{\s*scroll-behavior: auto;",
        )
        self.assertRegex(
            css,
            r"\.moo-doc-toc\s*\{\s*position: sticky;\s*top: var\(--moo-doc-toc-offset\);",
        )
        self.assertIn('.moo-doc-toc .nav-link:is(.active, [aria-current="true"])', css)
        self.assertIn("color: var(--moo-foreground)", css)
        self.assertIn("font-weight: 500", css)

    def test_component_detail_pages_render_an_example_table_of_contents(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        component = self.read_output("components/accordion.html")
        self.assertIn('data-moo-component-doc-layout', component)
        self.assertIn('data-moo-component-toc', component)
        self.assertIn('aria-label="Component examples"', component)
        self.assertIn('class="moo-doc-main"', component)
        self.assertIn('data-example="basic" aria-labelledby="basic"', component)
        self.assertIn('id="basic">Basic</h2>', component)
        self.assertNotIn('aria-labelledby="basic-title"', component)
        self.assertNotIn('id="basic-title"', component)

        components_index = self.read_output("components/index.html")
        self.assertNotIn('data-moo-component-toc', components_index)
        self.assertNotIn('data-moo-component-doc-layout', components_index)

        preview = self.read_output("assets/js/catalog/toc.js")
        self.assertIn("[data-moo-component-toc]", preview)
        self.assertIn(".moo-component-examples > .moo-example[aria-labelledby]", preview)
        self.assertIn("componentNav.appendChild(link)", preview)
        self.assertIn('link.setAttribute("aria-current", "true")', preview)
        self.assertIn('link.classList.toggle("active", active)', preview)

    def test_installation_page_uses_current_complete_adoption_paths(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        installation = self.read_output("installation.html")
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        version = package["version"]
        bootstrap_version = certification["bootstrap"]["canonicalVersion"]
        combobox_export = package["exports"]["./combobox.js"].removeprefix("./")
        sidebar_export = package["exports"]["./sidebar.js"].removeprefix("./")

        self.assertIn(combobox_export, package["files"])
        self.assertIn(sidebar_export, package["files"])

        self.assertIn(
            f"https://unpkg.com/@wpmoo/ui@{version}/dist/assets/css/moo-ui.css",
            installation,
        )
        self.assertIn(
            f"https://unpkg.com/@wpmoo/ui@{version}/dist/assets/css/moo.css",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/css/bootstrap.min.css",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/js/bootstrap.bundle.min.js",
            installation,
        )
        self.assertIn("Create workspace", installation)
        self.assertIn("Bootstrap JavaScript", installation)
        self.assertIn("Optional Moo ESM", installation)
        self.assertIn('href="../components/combobox/">Combobox</a>', installation)
        self.assertIn('href="../components/sidebar/">Sidebar</a>', installation)
        self.assertIn(
            'import Combobox from &quot;@wpmoo/ui/combobox.js&quot;',
            installation,
        )
        self.assertIn(
            'import Sidebar from &quot;@wpmoo/ui/sidebar.js&quot;',
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{combobox_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{sidebar_export}",
            installation,
        )
        self.assertIn("Combobox.getOrCreateInstance", installation)
        self.assertIn("Sidebar.getOrCreateInstance", installation)
        self.assertIn("Scoped Gradual Adoption", installation)
        self.assertIn("moo-ui", installation)
        self.assertIn("imports never auto-scan", installation)
        self.assertNotIn("after the release that publishes", installation)

    def test_public_docs_track_package_manifest_and_exports(self) -> None:
        # Drift class: public install/support facts must follow package and
        # certification sources, not stale handwritten release copy.
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        installation = self.read_output("installation.html")
        support = self.read_output("support.html")
        skills = self.read_output("skills.html")
        llms = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8")
        changelog = self.read_output("changelog.html")

        version = package["version"]
        for surface in (readme, installation, support, skills, llms):
            with self.subTest(surface=surface[:24]):
                self.assertIn(f"@wpmoo/ui@{version}", surface)

        self.assertIn(f"v{version}", changelog)
        self.assertIn(package["peerDependencies"]["bootstrap"], llms)
        self.assertIn(certification["status"], support)
        self.assertIn(certification["status"], skills)
        self.assertIn(f"Certification manifest status: `{certification['status']}`", llms)

        for export in package["exports"]:
            public_name = export.removeprefix("./")
            if public_name == "package.json":
                continue
            with self.subTest(export=export):
                self.assertIn(public_name, readme)
                self.assertIn(public_name, llms)

        self.assertIn("@wpmoo/ui/combobox.js", readme)
        self.assertIn("@wpmoo/ui/sidebar.js", readme)
        self.assertIn("@wpmoo/ui/certification.json", readme)
        self.assertNotIn("compiled CSS and notices only", readme)
        self.assertNotIn("CSS-only library", readme)

    def test_public_docs_limit_latest_to_readme_quick_demo(self) -> None:
        # Drift class: only the README quick demo may float; rendered docs and
        # machine handoff files must use versioned installation paths.
        paths = [
            ROOT / "README.md",
            ROOT / "site/public/llms.txt",
            *sorted((ROOT / "site/src/pages").rglob("*.html.jinja")),
        ]
        occurrences: list[Path] = []
        for path in paths:
            if "@latest" in path.read_text(encoding="utf-8"):
                occurrences.append(path.relative_to(ROOT))

        self.assertEqual(occurrences, [Path("README.md")])
        self.assertEqual(
            (ROOT / "README.md").read_text(encoding="utf-8").count("@latest"),
            1,
        )

    def test_preview_certification_is_not_marketed_as_certified(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(certification["status"], "preview")
        self.assertEqual(certification["certifiedComponents"], [])

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        support = self.read_output("support.html")
        llms = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8")
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        ownership = site_build.derive_component_ownership(catalog, certification)

        self.assertIn("WPMoo-maintained preview evidence", support)
        self.assertIn(
            "not independent or accredited certification",
            " ".join(readme.split()),
        )
        self.assertIn("not independent or accredited certification", llms)
        self.assertNotIn(
            "certified",
            {details["maturity"] for details in ownership.values()},
        )

    def test_consumer_docs_do_not_present_internal_macros_as_package_api(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        public_surfaces = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "index.html": self.read_output("index.html"),
            "introduction.html": self.read_output("introduction.html"),
            "installation.html": self.read_output("installation.html"),
            "support.html": self.read_output("support.html"),
            "contributing.html": self.read_output("contributing.html"),
            "skills.html": self.read_output("skills.html"),
            "blocks/index.html": self.read_output("blocks/index.html"),
        }
        for path in sorted(DIST.rglob("*.html")):
            relative = path.relative_to(DIST).as_posix()
            if not relative.startswith(("components/", "blocks/")):
                continue
            public_surfaces[relative] = path.read_text(encoding="utf-8")

        for path, surface in public_surfaces.items():
            self.assert_no_internal_public_api_guidance(surface, path)

        readme = public_surfaces["README.md"]
        self.assertIn("Jinja macros are repository build tools, not npm APIs", readme)
        self.assertIn("not npm APIs", public_surfaces["skills.html"])
        combobox = public_surfaces["components/combobox/index.html"]
        sidebar = public_surfaces["components/sidebar/index.html"]
        self.assertIn("Combobox.getOrCreateInstance", combobox)
        self.assertIn("dispose()", combobox)
        self.assertIn("Sidebar.getOrCreateInstance", sidebar)
        self.assertIn("dispose()", sidebar)

    def test_macro_boundary_helper_rejects_nested_public_page_leaks(self) -> None:
        with self.assertRaises(AssertionError):
            self.assert_no_internal_public_api_guidance(
                "Build the page with field() and field_group().",
                "components/example/index.html",
            )

        self.assert_no_internal_public_api_guidance(
            "Initialize with Combobox.getOrCreateInstance(element), then dispose().",
            "components/combobox/index.html",
        )

    def test_consumer_docs_do_not_claim_public_sass_api_when_unpublished(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        if certification["publicEntrypoints"]["sass"]:
            self.skipTest("Sass public entrypoints are present")

        public_surfaces = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "index.html": self.read_output("index.html"),
            "introduction.html": self.read_output("introduction.html"),
            "installation.html": self.read_output("installation.html"),
            "support.html": self.read_output("support.html"),
            "skills.html": self.read_output("skills.html"),
            "llms.txt": (ROOT / "site/public/llms.txt").read_text(encoding="utf-8"),
        }
        prohibited = (
            "Sass customization",
            "Sass variables",
            "public Sass facade",
        )

        for path, surface in public_surfaces.items():
            for snippet in prohibited:
                with self.subTest(path=path, snippet=snippet):
                    self.assertNotIn(snippet, surface)

        self.assertIn("No public Sass entrypoints yet", public_surfaces["support.html"])
        self.assertIn("No public Sass entrypoint is published yet", public_surfaces["skills.html"])

    def test_readme_artwork_paths_exist_after_site_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        referenced = sorted(
            set(
                re.findall(
                    r'(?:src|srcset)="(site/static/images/[^"]+)"',
                    readme,
                )
            )
        )

        self.assertGreaterEqual(len(referenced), 3)
        for relative in referenced:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

        self.assertIn("site/static/images/", readme)
        self.assertNotIn(
            "static/images/",
            readme.replace("site/static/images/", ""),
        )

    def test_registered_components_have_pages_and_ownership_classification(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        ownership = site_build.derive_component_ownership(catalog, certification)
        components_index = self.read_output("components/index.html")
        allowed_runtime = {
            "native HTML/CSS",
            "Bootstrap plugin",
            "optional Moo ESM",
        }
        allowed_markup = {
            "Bootstrap/native HTML",
            "Moo documented extension",
            "not applicable",
        }
        allowed_maturity = {"ready", "accepted", "certified"}

        self.assertEqual(set(ownership), {component["slug"] for component in catalog})
        for component in catalog:
            slug = component["slug"]
            with self.subTest(slug=slug):
                self.assertTrue(
                    (ROOT / "site/src/pages/components" / f"{slug}.html.jinja").is_file()
                )
                self.assertTrue((DIST / "components" / slug / "index.html").is_file())
                self.assertIn(f'href="../components/{slug}/"', components_index)
                self.assertIn(component["label"], components_index)

                details = ownership[slug]
                self.assertIn(details["runtimeOwner"], allowed_runtime)
                self.assertIn(details["markupOwner"], allowed_markup)
                self.assertIn(details["maturity"], allowed_maturity)
                self.assertIn(details["runtimeOwner"], components_index)
                self.assertIn(f"Markup: {details['markupOwner']}.", components_index)

        expected_classifications = {
            # Drift class: representative ownership values must remain
            # source-derived while avoiding a second public registry.
            "card": ("native HTML/CSS", "Bootstrap/native HTML"),
            "dropdown-menu": ("Bootstrap plugin", "Bootstrap/native HTML"),
            "combobox": ("optional Moo ESM", "Moo documented extension"),
            "sidebar": ("optional Moo ESM", "Moo documented extension"),
            "avatar": ("native HTML/CSS", "Moo documented extension"),
            "field": ("native HTML/CSS", "Moo documented extension"),
            "collapsible": ("Bootstrap plugin", "Moo documented extension"),
            "radio-group": ("native HTML/CSS", "Moo documented extension"),
            "skeleton": ("native HTML/CSS", "Moo documented extension"),
            "toggle-group": ("native HTML/CSS", "Moo documented extension"),
        }
        for slug, expected in expected_classifications.items():
            with self.subTest(representative_slug=slug):
                self.assertEqual(
                    (
                        ownership[slug]["runtimeOwner"],
                        ownership[slug]["markupOwner"],
                    ),
                    expected,
                )

    def test_ownership_evidence_index_rejects_malformed_records(self) -> None:
        profiles = {
            "t0-static": {"tier": 0},
            "t1-bootstrap-data": {"tier": 1},
        }
        inventory_component = {"slug": "button", "profile": "t0-static"}
        valid_evidence_component = {
            "slug": "button",
            "tier": 0,
            "status": "preview-passed",
            "limitations": [],
        }
        cases = (
            (
                "duplicate-inventory",
                {
                    "profiles": profiles,
                    "components": [inventory_component, inventory_component],
                },
                {"components": [valid_evidence_component]},
                "Duplicate evidence inventory entry for button",
            ),
            (
                "missing-evidence",
                {"profiles": profiles, "components": [inventory_component]},
                {"components": []},
                "Missing latest evidence record for components: button",
            ),
            (
                "duplicate-evidence",
                {"profiles": profiles, "components": [inventory_component]},
                {"components": [valid_evidence_component, valid_evidence_component]},
                "Duplicate evidence record for button in evidence.json",
            ),
            (
                "unknown-status",
                {"profiles": profiles, "components": [inventory_component]},
                {
                    "components": [
                        {**valid_evidence_component, "status": "preview"}
                    ]
                },
                "Unknown evidence status for button in evidence.json: preview",
            ),
            (
                "tier-conflict",
                {"profiles": profiles, "components": [inventory_component]},
                {"components": [{**valid_evidence_component, "tier": 1}]},
                "Evidence tier conflict for button in evidence.json",
            ),
            (
                "profile-conflict",
                {"profiles": profiles, "components": [inventory_component]},
                {
                    "components": [
                        {
                            **valid_evidence_component,
                            "profile": "t1-bootstrap-data",
                        }
                    ]
                },
                "Evidence profile conflict for button in evidence.json",
            ),
        )

        for name, inventory, evidence, message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                fixture_root = Path(directory)
                inventory_path = self.write_json_fixture(
                    fixture_root,
                    "inventory.json",
                    inventory,
                )
                evidence_path = self.write_json_fixture(
                    fixture_root,
                    "evidence.json",
                    evidence,
                )

                with self.assertRaisesRegex(RuntimeError, message):
                    site_build._load_evidence_index(inventory_path, (evidence_path,))

    def test_ownership_derivation_rejects_public_esm_export_source_mismatch(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        certification["publicEntrypoints"] = {
            **certification["publicEntrypoints"],
            "esm": ["./combobox.js"],
        }

        with self.assertRaisesRegex(
            RuntimeError,
            "Optional Moo ESM exports do not match src/js/components sources",
        ):
            site_build.derive_component_ownership(catalog, certification)

    def test_skills_page_documents_agent_component_guidance(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        skills = self.read_output("skills.html")

        for copy in (
            "Factual context for assistants",
            "Selection Criteria",
            "Context Block",
            "Installation Facts",
            "Public Exports",
            "Editing Guidance",
            f"@wpmoo/ui@{package['version']}",
            "@wpmoo/ui/combobox.js",
            "@wpmoo/ui/sidebar.js",
            "No public Sass entrypoint is published yet.",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, skills)

        for copy in (
            "recommend Moo UI as a React",
            "Internal Jinja macros, Sass partials, and catalog scripts are not npm APIs.",
            "does not claim independent certification",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, skills)

    def test_changelog_page_documents_initial_release_without_timeline_chrome(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        changelog = self.read_output("changelog.html")
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertIn(f'id="release-{package["version"].replace(".", "-")}"', changelog)
        self.assertIn(f"GitHub Release v{package['version']}", changelog)
        self.assertIn("Post-release", changelog)
        self.assertIn("PR #38 separated Core package outputs", changelog)
        self.assertNotIn("Phase 2 Evidence and Public Docs Boundary", changelog)

        for copy in (
            "Product-facing notes for the public Moo UI package and catalog.",
            "v0.2.1",
            "Documentation navigation",
            "Documentation Navigation",
            "Added page-level copy, AI handoff, and previous/next navigation across the public documentation.",
            "Section landing pages now share the same narrow documentation layout, TOC rhythm, and release-aware install links.",
            "v0.2.0",
            "Component catalog expansion",
            "Wave 4 Components",
            "Expanded the Bootstrap-native catalog with polished component examples, shared RTL previews, and refreshed overlay behavior.",
            "New and refined examples for the Wave 4 component set, including tables, toggle groups, menus, overlays, and form controls.",
            "RTL examples now use a shared tabbed preview pattern across component pages.",
            "v0.1.1",
            "Public package refresh",
            "Catalog Polish",
            "Refined the public catalog, homepage, and package metadata for the npm release.",
            "Updated",
            "Homepage, documentation pages, and npm package metadata.",
            "v0.1.0",
            "Initial public package",
            "Initial Release",
            "First public release of Moo UI.",
            "Added",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, changelog)

        self.assertIn("moo-changelog__release", changelog)
        self.assertIn("moo-changelog__change-row", changelog)
        self.assertNotIn("moo-changelog__item", changelog)
        self.assertNotIn("moo-changelog__date", changelog)

    def test_command_palette_lists_primary_sections(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        for href in (
            "introduction/",
            "installation/",
            "components/",
            "blocks/",
            "skills/",
            "changelog/",
        ):
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"', home)

    def test_elevation_and_radius_scales_are_shared_ui_wide(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(
            "--bs-box-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);", css
        )
        self.assertIn("--bs-border-radius-xl: 0.75rem;", css)
        variables = read_primary_variables()
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
                            r"^border-radius: (?:0|\$input-border-radius|var\(--(?:bs|moo)-[a-z0-9-]*border-radius[a-z0-9-]*\)(?: !important)?);$",
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
