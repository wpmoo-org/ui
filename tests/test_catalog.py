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
    def test_visible_component_lists_are_sorted_by_label(self) -> None:
        sorted_loop = (
            '{% for component in catalog | sort(attribute="label") %}'
        )

        for path in (
            ROOT / "src/shell/sidebar.html.jinja",
            ROOT / "src/pages/components/index.html.jinja",
        ):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertTrue(
                    sorted_loop in path.read_text(encoding="utf-8"),
                    f"{path.relative_to(ROOT)} must sort components by label",
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
            "tabs": ("tabs", "nav-link", "active", "tab-content", "tab-pane"),
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
            "field": ("field", "form-label", "form-text", "invalid-feedback"),
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

        catalog_scss = (ROOT / "scss/catalog.scss").read_text(encoding="utf-8")
        self.assertIn(".moo-catalog__search-trigger:focus-visible", catalog_scss)
        self.assertIn("background: $input-disabled-bg;", catalog_scss)

    def test_header_navigation_links_docs_between_home_and_components(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        header_start = index.index('<header class="moo-catalog__header">')
        header_end = index.index("</header>", header_start)
        header = index[header_start:header_end]

        home_index = header.index('href="index.html"')
        docs_index = header.index('href="introduction.html"')
        components_index = header.index('href="components/index.html"')
        blocks_index = header.index('href="blocks/index.html"')

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
        self.assertIn('href="installation.html"', home)
        self.assertIn('href="components/index.html"', home)
        self.assertIn('href="components/button.html"', home)
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
            ("Introduction", "../introduction.html"),
            ("Installation", "../installation.html"),
            ("Components", "../components/index.html"),
            ("Blocks", "../blocks/index.html"),
            ("Skills", "../skills.html"),
            ("Changelog", "../changelog.html"),
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
            "Mission",
            "Vision",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, introduction)
        self.assertIn('href="installation.html"', introduction)
        self.assertIn('href="components/index.html"', introduction)

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
                header_start = page.index('<header class="moo-component-header"')
                header_end = page.index("</header>", header_start)
                header = page[header_start:header_end]

                self.assertIn("<h1", header)
                self.assertNotIn("moo-doc-hero", page)
                self.assertNotIn("moo-catalog__intro", page)

        home = self.read_output("index.html")
        self.assertIn('<section class="moo-home-hero"', home)
        self.assertIn('<h1 class="moo-home-hero__title" id="home-title">Moo UI</h1>', home)
        self.assertNotIn("moo-doc-hero", home)
        self.assertNotIn("moo-catalog__intro", home)

        introduction = self.read_output("introduction.html")
        self.assertIn("moo-component-header__actions", introduction)

    def test_primary_docs_render_a_right_side_table_of_contents(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        expected_links = {
            "introduction.html": (
                ("why-title", "Why Moo UI Exists"),
                ("principles-title", "Principles"),
                ("mission-title", "Mission"),
            ),
            "installation.html": (
                ("cdn-title", "CDN"),
                ("npm-title", "npm"),
                ("javascript-title", "JavaScript"),
            ),
            "skills.html": (
                ("skills-roadmap-title", "What Skills Are For"),
                ("skills-context-title", "What Agents Should Know"),
                ("skills-workflow-title", "Expected Workflow"),
            ),
            "changelog.html": (
                ("release-0-1-1", "Catalog Polish"),
                ("release-0-1-0", "Initial Release"),
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
                self.assertNotIn("moo-doc-toc", page)

        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-doc-layout", css)
        self.assertIn("@media (min-width: 1200px)", css)
        self.assertIn("--moo-doc-toc-offset: calc(var(--moo-catalog-header-height) + 1rem)", css)
        self.assertIn("scroll-behavior: smooth", css)
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
        self.assertIn('id="basic-title"', component)

        components_index = self.read_output("components/index.html")
        self.assertNotIn('data-moo-component-toc', components_index)
        self.assertNotIn('data-moo-component-doc-layout', components_index)

        preview = self.read_output("assets/js/preview.js")
        self.assertIn("[data-moo-component-toc]", preview)
        self.assertIn(".moo-component-examples > .moo-example[aria-labelledby]", preview)
        self.assertIn("componentTocNav.appendChild(link)", preview)
        self.assertIn('link.setAttribute("aria-current", "true")', preview)
        self.assertIn('link.classList.toggle("active", isActive)', preview)

    def test_installation_page_uses_published_cdn_path(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        installation = self.read_output("installation.html")

        self.assertIn(
            "https://unpkg.com/@wpmoo/ui@0.2.0/dist/assets/css/moo-ui.css",
            installation,
        )
        self.assertNotIn(
            "https://unpkg.com/@wpmoo/ui/dist/assets/css/moo-ui.min.css",
            installation,
        )
        self.assertIn("Create workspace", installation)
        self.assertIn("Bootstrap's JavaScript bundle", installation)

    def test_skills_page_documents_agent_component_guidance(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        skills = self.read_output("skills.html")

        for copy in (
            "Project-aware instructions for coding agents",
            "What Skills Are For",
            "What Agents Should Know",
            "Bootstrap first",
            "Taste, not source",
            "Verify before ready",
            "Expected Workflow",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, skills)

    def test_changelog_page_documents_initial_release_without_timeline_chrome(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        changelog = self.read_output("changelog.html")

        for copy in (
            "Product-facing notes for the public Moo UI package and catalog.",
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
            "introduction.html",
            "installation.html",
            "components/index.html",
            "blocks/index.html",
            "skills.html",
            "changelog.html",
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
