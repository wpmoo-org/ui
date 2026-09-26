from __future__ import annotations

import json
import re
import tempfile
import unittest
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import build as site_build

from build import create_environment
from tests.helpers import CatalogTestCase


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src/layouts/page.html.jinja"
CONTAINER_CLASSES = {
    "base": "container",
    "sm": "container-sm",
    "md": "container-md",
    "lg": "container-lg",
    "xl": "container-xl",
    "xxl": "container-xxl",
    "fluid": "container-fluid",
}


class LayoutRenderMixin:
    def render_page(self, source: str, **context: object) -> str:
        self.assertTrue(PAGE.is_file(), "Page layout macro is not implemented")
        template = create_environment().from_string(
            '{% from "layouts/page.html.jinja" import page %}' + source
        )
        return " ".join(template.render(**context).split())

    def render_regions(
        self,
        *,
        width: str = "xl",
        header_width: str | None = None,
        page_id: str = "",
        header: str = "Header",
        main: str = "Main",
        footer: str = "Footer",
    ) -> str:
        return self.render_page(
            """
            {% if header_width is none %}
              {% call(region) page(width=width, id=page_id) %}
                {% if region == "header" %}{{ header }}
                {% elif region == "main" %}{{ main }}
                {% elif region == "footer" %}{{ footer }}
                {% endif %}
              {% endcall %}
            {% else %}
              {% call(region) page(width=width, id=page_id, header_width=header_width) %}
                {% if region == "header" %}{{ header }}
                {% elif region == "main" %}{{ main }}
                {% elif region == "footer" %}{{ footer }}
                {% endif %}
              {% endcall %}
            {% endif %}
            """,
            width=width,
            header_width=header_width,
            page_id=page_id,
            header=header,
            main=main,
            footer=footer,
        )


class LayoutMacroTests(LayoutRenderMixin, unittest.TestCase):
    def test_page_container_contract(self) -> None:
        output = self.render_regions(page_id="workspace-page")

        self.assertIn('data-slot="page"', output)
        self.assertIn('id="workspace-page"', output)
        self.assertEqual(output.count('<header>'), 1)
        self.assertEqual(
            output.count(
                '<main id="main-content" tabindex="-1" class="scroll-fade-y no-scrollbar">'
            ),
            1,
        )
        self.assertEqual(output.count('<footer>'), 1)
        self.assertEqual(output.count('class="container-xl"'), 3)
        self.assertEqual(output.count('data-page-container'), 1)
        main = output[output.index('<main '):output.index('</main>')]
        self.assertIn('class="container-xl" data-page-container', main)
        self.assertLess(output.index("Header"), output.index("Main"))
        self.assertLess(output.index("Main"), output.index("Footer"))
        self.assertNotIn("sidebar_provider", output)
        self.assertNotIn("sidebar_inset", output)
        self.assertNotIn("sidebar-inset__", output)

    def test_page_accepts_a_validated_header_width_without_changing_other_regions(
        self,
    ) -> None:
        output = self.render_regions(width="xl", header_width="fluid")

        header = output[output.index("<header>") : output.index("</header>")]
        main = output[output.index("<main") : output.index("</main>")]
        footer = output[output.index("<footer>") : output.index("</footer>")]

        self.assertIn('class="container-fluid"', header)
        self.assertNotIn('class="container-xl"', header)
        self.assertIn('class="container-xl"', main)
        self.assertIn('class="container-xl"', footer)

    def test_page_rejects_undocumented_main_class(self) -> None:
        with self.assertRaises(TypeError):
            self.render_page(
                """
                {% call(region) page(width="xl", main_class="px-md-5") %}
                  {% if region == "main" %}Main{% endif %}
                {% endcall %}
                """
            )

    def test_page_widths_map_to_one_native_container_per_region(self) -> None:
        for width, container_class in CONTAINER_CLASSES.items():
            with self.subTest(width=width):
                output = self.render_regions(width=width)
                self.assertEqual(output.count(f'class="{container_class}"'), 3)
                for other_class in CONTAINER_CLASSES.values():
                    if other_class != container_class:
                        self.assertNotIn(f'class="{other_class}"', output)

    def test_page_rejects_unknown_width(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown page width: narrow"):
            self.render_regions(width="narrow")

    def test_page_rejects_unknown_header_width(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown page header width: narrow"):
            self.render_regions(header_width="narrow")

    def test_page_validates_root_id_before_escaping(self) -> None:
        invalid_ids = (" ", "9-page", "page.name", "main-content", "page ")
        for page_id in invalid_ids:
            with self.subTest(page_id=page_id):
                with self.assertRaisesRegex(ValueError, "Invalid page id"):
                    self.render_regions(page_id=page_id)

        output = self.render_regions(page_id="page_1")
        self.assertIn('id="page_1"', output)

    def test_page_escapes_slot_values_while_preserving_named_markup(self) -> None:
        output = self.render_page(
            """
            {% set calls = namespace(main=0) %}
            {% call(region) page() %}
              {% if region == "main" %}
                {% set calls.main = calls.main + 1 %}<p>{{ unsafe }}</p>
              {% endif %}
            {% endcall %}
            <output data-calls="{{ calls.main }}"></output>
            """,
            unsafe="<script>alert('x')</script>",
        )

        self.assertIn("<p>&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;</p>", output)
        self.assertIn('data-calls="1"', output)
        self.assertNotIn("<script>alert", output)

    def test_page_evaluates_each_branch_once_and_omits_blank_optional_regions(self) -> None:
        output = self.render_page(
            """
            {% set calls = namespace(header=0, main=0, footer=0) %}
            {% call(region) page() %}
              {% if region == "header" %}{% set calls.header = calls.header + 1 %}
              {% elif region == "main" %}{% set calls.main = calls.main + 1 %}Main
              {% elif region == "footer" %}{% set calls.footer = calls.footer + 1 %}
              {% endif %}
            {% endcall %}
            <output data-calls="{{ calls.header }}-{{ calls.main }}-{{ calls.footer }}"></output>
            """
        )

        self.assertNotIn("<header>", output)
        self.assertEqual(
            output.count(
                '<main id="main-content" tabindex="-1" class="scroll-fade-y no-scrollbar">'
            ),
            1,
        )
        self.assertNotIn("<footer>", output)
        self.assertIn('data-calls="1-1-1"', output)

    def test_page_requires_a_non_empty_main_region(self) -> None:
        invalid_sources = (
            "{% call(region) page() %}{% if region == 'header' %}Header{% endif %}{% endcall %}",
            "{% call(region) page() %}{% if region == 'main' %}   {% endif %}{% endcall %}",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "Page main region is required"):
                    self.render_page(source)

    def test_page_signature_does_not_accept_visual_escape_hatches(self) -> None:
        for argument in (
            "extra_class",
            "footer_width",
            "bleed",
            "main_class",
        ):
            with self.subTest(argument=argument):
                with self.assertRaises(TypeError):
                    self.render_page(
                        "{% call(region) page(**kwargs) %}Main{% endcall %}",
                        kwargs={argument: "custom"},
                    )

        source = PAGE.read_text(encoding="utf-8")
        for forbidden in (".moo-", "style=", "<svg", "<button", "<input"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertNotRegex(source, re.compile(r"sidebar_(?:provider|inset)"))


class AppLayoutTests(LayoutRenderMixin, unittest.TestCase):
    APP = ROOT / "src/layouts/app.html.jinja"

    class _Element:
        def __init__(self, tag: str, attrs: dict[str, str]) -> None:
            self.tag = tag
            self.attrs = attrs
            self.children: list[AppLayoutTests._Element] = []

    class _TreeParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.root = AppLayoutTests._Element("#document", {})
            self.stack = [self.root]

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            element = AppLayoutTests._Element(
                tag,
                {name: value or "" for name, value in attrs},
            )
            self.stack[-1].children.append(element)
            if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
                self.stack.append(element)

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.handle_starttag(tag, attrs)
            if self.stack[-1].tag == tag:
                self.stack.pop()

        def handle_endtag(self, tag: str) -> None:
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index].tag == tag:
                    del self.stack[index:]
                    return

    @classmethod
    def _elements(cls, root: _Element) -> list[_Element]:
        result = [root]
        for child in root.children:
            result.extend(cls._elements(child))
        return result

    def assert_app_structure(
        self,
        output: str,
        *,
        navigation: str,
        sidebar_id: str,
    ) -> None:
        parser = self._TreeParser()
        parser.feed(output)
        app_roots = [
            element
            for element in self._elements(parser.root)
            if element.attrs.get("data-layout") == "app"
        ]
        self.assertEqual(len(app_roots), 1)
        app_root = app_roots[0]
        direct_children = [
            child
            for child in app_root.children
            if child.tag not in {"#text"}
        ]
        if navigation == "sidebar":
            self.assertEqual(
                [(child.tag, child.attrs.get("data-slot")) for child in direct_children],
                [("script", None), ("aside", "sidebar"), ("div", "page")],
            )
            self.assertNotIn("src", direct_children[0].attrs)
            self.assertNotIn("defer", direct_children[0].attrs)
        else:
            self.assertEqual(
                [(child.tag, child.attrs.get("data-slot")) for child in direct_children],
                [("div", "page")],
            )

        ids = [
            element.attrs["id"]
            for element in self._elements(parser.root)
            if "id" in element.attrs
        ]
        self.assertEqual(len(ids), len(set(ids)))
        for trigger in (
            element
            for element in self._elements(parser.root)
            if "data-sidebar-trigger" in element.attrs
        ):
            self.assertEqual(trigger.attrs.get("data-bs-target"), f"#{sidebar_id}")
            self.assertEqual(trigger.attrs.get("aria-controls"), sidebar_id)

    def render_app(self, source: str, **context: object) -> str:
        self.assertTrue(self.APP.is_file(), "App layout macro is not implemented")
        template = create_environment().from_string(
            """
            {% from "layouts/app.html.jinja" import app %}
            {% from "layouts/page.html.jinja" import page %}
            {% from "components/sidebar.html.jinja" import
              sidebar_header, sidebar_content, sidebar_footer, sidebar_trigger,
              sidebar_menu_button
            %}
            """
            + source
        )
        return " ".join(template.render(**context).split())

    def render_app_shell(
        self,
        *,
        navigation: str = "sidebar",
        sidebar_id: str = "app-sidebar",
        sidebar_key: str = "app-shell",
        default_open: bool = True,
        side: str = "left",
        variant: str = "sidebar",
        collapsible: str = "icon",
        rail: bool = True,
        aria_label: str = "Application navigation",
        aria_labelled_by: str = "app-navigation-label",
        shell_mode: str = "viewport",
        app_id: str = "",
        include_sidebar: bool = True,
        page_main: str = "Page main",
    ) -> str:
        return self.render_app(
            """
            {% call(slot) app(
              navigation=navigation,
              sidebar_id=sidebar_id,
              sidebar_key=sidebar_key,
              default_open=default_open,
              side=side,
              variant=variant,
              collapsible=collapsible,
              rail=rail,
              aria_label=aria_label,
              aria_labelled_by=aria_labelled_by,
              shell_mode=shell_mode,
              id=app_id
            ) %}
              {% if slot == "sidebar" and include_sidebar %}
                <span id="app-navigation-label">Navigation</span>
                {% call sidebar_header() %}
                  {{ sidebar_trigger(sidebar_id=sidebar_id) }}
                {% endcall %}
                {% call sidebar_content() %}
                  {{ sidebar_menu_button("Overview", href="/", active=true) }}
                {% endcall %}
                {% call sidebar_footer() %}Account{% endcall %}
              {% elif slot == "page" %}
                {% call(region) page(width="xl") %}
                  {% if region == "main" %}{{ page_main }}{% endif %}
                {% endcall %}
              {% endif %}
            {% endcall %}
            """,
            navigation=navigation,
            sidebar_id=sidebar_id,
            sidebar_key=sidebar_key,
            default_open=default_open,
            side=side,
            variant=variant,
            collapsible=collapsible,
            rail=rail,
            aria_label=aria_label,
            aria_labelled_by=aria_labelled_by,
            shell_mode=shell_mode,
            app_id=app_id,
            include_sidebar=include_sidebar,
            page_main=page_main,
        )

    def test_app_sidebar_navigation_emits_exact_shell_and_direct_siblings(self) -> None:
        output = self.render_app_shell(app_id="workspace-app")

        self.assert_app_structure(
            output,
            navigation="sidebar",
            sidebar_id="app-sidebar",
        )
        self.assertIn('class="wrapper"', output)
        self.assertNotIn('class="sidebar-wrapper"', output)
        self.assertIn('id="workspace-app"', output)
        self.assertIn('data-layout="app"', output)
        self.assertIn('data-shell-mode="viewport"', output)
        self.assertIn('data-sidebar-state="expanded"', output)
        self.assertEqual(output.count('data-sidebar-key="app-shell"'), 1)
        self.assertEqual(output.count('data-slot="sidebar"'), 1)
        self.assertEqual(output.count('data-slot="page"'), 1)
        self.assertLess(output.index('data-slot="sidebar"'), output.index('data-slot="page"'))
        self.assertIn('id="main-content" tabindex="-1"', output)
        self.assertNotIn("sidebar_provider", output)
        self.assertNotIn("sidebar_inset", output)
        self.assertNotIn("sidebar-inset__", output)

    def test_app_navigation_none_emits_only_the_page_and_no_sidebar_runtime(self) -> None:
        output = self.render_app_shell(
            navigation="none",
            include_sidebar=False,
            shell_mode="contained",
        )

        self.assert_app_structure(
            output,
            navigation="none",
            sidebar_id="app-sidebar",
        )
        self.assertIn('class="wrapper"', output)
        self.assertNotIn('class="sidebar-wrapper"', output)
        self.assertIn('data-layout="app"', output)
        self.assertIn('data-shell-mode="contained"', output)
        self.assertEqual(output.count('data-slot="page"'), 1)
        self.assertNotIn('data-slot="sidebar-wrapper"', output)
        self.assertNotIn('data-slot="sidebar"', output)
        self.assertNotIn("data-sidebar-state", output)
        self.assertNotIn("data-sidebar-key", output)
        self.assertNotIn("data-sidebar-trigger", output)
        self.assertNotIn("<script>", output)

    def test_app_forwards_sidebar_props_and_right_side_trigger_target(self) -> None:
        output = self.render_app_shell(
            sidebar_id="right-sidebar",
            side="right",
            variant="floating",
            collapsible="icon",
            rail=False,
            aria_label="Right navigation",
            aria_labelled_by="right-navigation-label",
        )

        self.assertIn('id="right-sidebar"', output)
        self.assertIn('data-side="right"', output)
        self.assertIn('data-variant="floating"', output)
        self.assertIn('data-collapsible="icon"', output)
        self.assertIn('aria-label="Right navigation"', output)
        self.assertIn('aria-labelledby="right-navigation-label"', output)
        self.assertIn('data-bs-target="#right-sidebar"', output)
        self.assertIn('aria-controls="right-sidebar"', output)
        self.assertNotIn('data-sidebar-rail', output)

    def test_app_layout_owns_the_sidebar_rail_markup(self) -> None:
        app_source = (ROOT / "src/layouts/app.html.jinja").read_text(
            encoding="utf-8"
        )
        sidebar_source = (ROOT / "src/components/sidebar.html.jinja").read_text(
            encoding="utf-8"
        )

        self.assertIn('class="sidebar-rail"', app_source)
        self.assertNotIn("{% macro sidebar_rail", sidebar_source)

    def test_app_offcanvas_mode_uses_the_native_drawer_shell_without_an_icon_rail(self) -> None:
        output = self.render_app_shell(collapsible="offcanvas")

        self.assertIn('class="sidebar offcanvas-lg offcanvas-start"', output)
        self.assertIn('data-collapsible="offcanvas"', output)
        self.assertNotIn('data-sidebar-rail', output)

    def test_app_validates_finite_props_and_shared_identifier_grammar(self) -> None:
        invalid_calls = (
            ({"navigation": "auto"}, "Unknown app navigation: auto"),
            ({"shell_mode": "document"}, "Unknown app shell mode: document"),
            ({"side": "top"}, "Unknown app sidebar side: top"),
            ({"variant": "card"}, "Unknown app sidebar variant: card"),
            ({"collapsible": "rail"}, "Unknown app sidebar collapsible mode: rail"),
            ({"default_open": "yes"}, "App default_open must be boolean"),
            ({"rail": "yes"}, "App rail must be boolean"),
        )
        for values, message in invalid_calls:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_app_shell(**values)

        for field in ("sidebar_id", "sidebar_key"):
            invalid_values = ("", " ", "9-invalid", "invalid.value")
            if field == "sidebar_id":
                invalid_values += ("main-content",)
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "Invalid app"):
                        self.render_app_shell(**{field: value})

        key_output = self.render_app_shell(sidebar_key="main-content")
        self.assertEqual(key_output.count('data-sidebar-key="main-content"'), 1)

        for app_id in (" ", "9-invalid", "invalid.value", "main-content"):
            with self.subTest(app_id=app_id):
                with self.assertRaisesRegex(ValueError, "Invalid app id"):
                    self.render_app_shell(app_id=app_id)

        with self.assertRaisesRegex(ValueError, "must differ"):
            self.render_app_shell(app_id="app-sidebar", sidebar_id="app-sidebar")

    def test_app_requires_page_and_enforces_sidebar_slot_by_navigation_mode(self) -> None:
        missing_page = """
          {% call(slot) app(navigation="sidebar", sidebar_id="app-sidebar", sidebar_key="app-shell") %}
            {% if slot == "sidebar" %}Sidebar{% endif %}
          {% endcall %}
        """
        with self.assertRaisesRegex(ValueError, "App page slot is required"):
            self.render_app(missing_page)

        missing_sidebar = """
          {% call(slot) app(navigation="sidebar", sidebar_id="app-sidebar", sidebar_key="app-shell") %}
            {% if slot == "page" %}
              {% call(region) page() %}{% if region == "main" %}Main{% endif %}{% endcall %}
            {% endif %}
          {% endcall %}
        """
        with self.assertRaisesRegex(ValueError, "App sidebar slot is required"):
            self.render_app(missing_sidebar)

        disabled_with_sidebar = """
          {% call(slot) app(navigation="none") %}
            {% if slot == "sidebar" %}Unexpected sidebar{% endif %}
            {% if slot == "page" %}
              {% call(region) page() %}{% if region == "main" %}Main{% endif %}{% endcall %}
            {% endif %}
          {% endcall %}
        """
        with self.assertRaisesRegex(ValueError, "must be empty when navigation is none"):
            self.render_app(disabled_with_sidebar)

    def test_app_evaluates_named_callers_once_and_preserves_page_contract(self) -> None:
        output = self.render_app(
            """
            {% set calls = namespace(sidebar=0, page=0) %}
            {% call(slot) app(navigation="none") %}
              {% if slot == "sidebar" %}{% set calls.sidebar = calls.sidebar + 1 %}
              {% elif slot == "page" %}
                {% set calls.page = calls.page + 1 %}
                {% call(region) page(width="fluid") %}
                  {% if region == "main" %}Page body{% endif %}
                {% endcall %}
              {% endif %}
            {% endcall %}
            <output data-calls="{{ calls.sidebar }}-{{ calls.page }}"></output>
            """
        )

        self.assertIn('data-calls="1-1"', output)
        self.assertIn('class="container-fluid"', output)
        self.assertIn('id="main-content" tabindex="-1"', output)

    def test_app_does_not_accept_raw_slots_or_copy_legacy_shell_behavior(self) -> None:
        with self.assertRaises(TypeError):
            self.render_app(
                "{% call(region) app(navigation='none', page='raw') %}Page{% endcall %}"
            )

        source = self.APP.read_text(encoding="utf-8")
        for forbidden in (
            "sidebar_provider",
            "sidebar_inset",
            "sidebar_inset_header",
            "sidebar_inset_content",
            "style=",
            "<svg",
            "route",
            "recordset",
            "odoo",
            "portal",
            "extra_class",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertNotIn("{% macro sidebar", source)

    def test_app_structure_gate_rejects_mutated_page_sibling(self) -> None:
        output = self.render_app_shell()
        mutated = output.replace(
            '<div data-slot="page">',
            '<section data-slot="page">',
            1,
        )

        with self.assertRaises(AssertionError):
            self.assert_app_structure(
                mutated,
                navigation="sidebar",
                sidebar_id="app-sidebar",
            )


class LayoutCatalogTests(CatalogTestCase):
    PAGES = ROOT / "site/src/pages/layouts"
    GUIDE = ROOT / "site/src/pages/layout.html.jinja"

    def read_page(self, name: str) -> str:
        return (self.PAGES / name).read_text(encoding="utf-8")

    def test_layout_guide_is_the_only_public_layout_document(self) -> None:
        guide = self.GUIDE.read_text(encoding="utf-8")
        self.assertIn('{% extends "layouts/catalog.html.jinja" %}', guide)
        self.assertIn('from "blocks/sidebar_shell.html.jinja" import render_sidebar_shell', guide)
        self.assertIn('from "components/table.html.jinja" import table', guide)
        self.assertIn("render_block_example(", guide)
        self.assertNotIn("render_code_snippet(", guide)
        self.assertNotIn('{% from "layouts/', guide)
        for name in ("index.html.jinja", "app.html.jinja", "page.html.jinja"):
            with self.subTest(removed_document=name):
                self.assertFalse((self.PAGES / name).exists())

    def test_layout_guide_is_canonical_without_legacy_routes(self) -> None:
        guide = self.GUIDE.read_text(encoding="utf-8")
        self.assertIn('{% extends "layouts/catalog.html.jinja" %}', guide)
        self.assertIn('id="layout"', guide)
        self.assertIn("A focused space for Moo UI layout examples.", guide)
        self.assertIn('id="app"', guide)
        self.assertIn('id="page"', guide)
        self.assertNotIn("data-example=", guide)
        self.assertNotIn("render_code_snippet(", guide)
        self.assertIn("render_block_example(", guide)
        self.assertFalse((ROOT / "site/public/_redirects").exists())

    def test_layout_guide_starts_with_the_app_example_for_collaborative_work(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("layout/index.html")
        self.assertIn('class="moo-doc-layout"', page)
        self.assertIn('<h1 class="fw-semibold" id="layout">Layout</h1>', page)
        self.assertIn("A focused space for Moo UI layout examples.", page)
        self.assertIn('aria-label="On this page"', page)
        self.assertEqual(page.count('data-example="layout-app-example"'), 1)
        self.assertIn('id="layout-app-example-code"', page)
        self.assertIn('href="#app"', page)
        self.assertIn('>App</a>', page)
        self.assertIn('<h2 class="h3" id="page">Page</h2>', page)
        self.assertIn('href="#page"', page)
        self.assertNotIn('<h2 class="h3" id="sidebar">Sidebar</h2>', page)
        self.assertNotIn('href="#sidebar"', page)
        app_start = page.index('id="app"')
        example_start = page.index('data-example="layout-app-example"', app_start)
        page_start = page.index('id="page"', example_start)
        app_section = page[app_start:page_start]
        self.assertLess(app_start, example_start)
        self.assertLess(example_start, page_start)
        self.assertNotIn('id="floating-variant"', app_section)
        self.assertNotIn("The floating Sidebar variant detaches", app_section)
        self.assertNotIn('class="moo-example__header"', app_section)
        for variant in ("sidebar", "floating", "inset"):
            with self.subTest(variant=variant):
                self.assertIn(f"<code>{variant}</code>", app_section)
        source_start = page.index('id="layout-app-example-code"')
        source_end = page.index("</pre>", source_start)
        source = page[source_start:source_end]
        visible_source = unescape(re.sub(r"<[^>]+>", "", source))
        for hook in (
            'data-slot="sidebar-wrapper"',
            'data-sidebar-key="app-shell"',
            'data-slot="sidebar"',
            'data-variant="floating"',
            'class="sidebar-inner"',
            'data-slot="page"',
            'id="main-content"',
        ):
            with self.subTest(hook=hook):
                self.assertIn(hook, visible_source)
        self.assertNotIn('data-sidebar="floating"', visible_source)
        self.assertNotIn('data-example="layout-page-example"', page)
        self.assertIn('href="#breakpoints"', page)
        self.assertIn('href="#containers"', page)
        self.assertIn('href="#grid"', page)
        self.assertIn('href="#columns"', page)
        self.assertIn('href="#gutters"', page)
        self.assertIn('href="#utilities"', page)
        self.assertIn('href="#z-index"', page)
        self.assertIn('href="#css-grid"', page)

    def test_layout_guide_documents_native_utility_sections_and_css_grid(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("layout/index.html")

        section_starts = {
            slug: page.index(f'id="{slug}"')
            for slug in ("gutters", "utilities", "z-index", "css-grid")
        }
        self.assertLess(section_starts["gutters"], section_starts["utilities"])
        self.assertLess(section_starts["utilities"], section_starts["z-index"])
        self.assertLess(section_starts["z-index"], section_starts["css-grid"])

        for slug, label in (
            ("gutters", "Gutters"),
            ("utilities", "Utilities"),
            ("z-index", "Z-index"),
            ("css-grid", "CSS Grid"),
        ):
            with self.subTest(slug=slug):
                self.assertIn(f'href="#{slug}"', page)
                self.assertIn(f'>{label}</a>', page)

        gutters_start = section_starts["gutters"]
        utilities_start = section_starts["utilities"]
        gutters_section = page[gutters_start:utilities_start]
        self.assertEqual(gutters_section.count('data-example="layout-gutters-example"'), 1)
        self.assertIn('class="row gx-5"', gutters_section)
        self.assertIn('href="https://getbootstrap.com/docs/5.3/layout/gutters/"', gutters_section)

        z_index_start = section_starts["z-index"]
        css_grid_start = section_starts["css-grid"]
        z_index_section = page[z_index_start:css_grid_start]
        for token, value in (
            ("$zindex-dropdown", "1000"),
            ("$zindex-modal", "1055"),
            ("$zindex-toast", "1090"),
        ):
            with self.subTest(token=token):
                self.assertIn(f'<code>{token}</code>', z_index_section)
                self.assertIn(f'>{value}</td>', z_index_section)
        self.assertIn('href="https://getbootstrap.com/docs/5.3/layout/z-index/"', z_index_section)

        css_grid_section = page[css_grid_start:]
        self.assertEqual(css_grid_section.count('data-example="layout-css-grid-example"'), 1)
        self.assertIn('class="grid gap-3"', css_grid_section)
        self.assertIn('class="g-col-6 g-col-md-4 p-3 border rounded bg-body-tertiary"', css_grid_section)
        self.assertIn('href="https://getbootstrap.com/docs/5.3/layout/css-grid/"', css_grid_section)
        source_start = page.index('id="layout-css-grid-example-code"', css_grid_start)
        source_end = page.index("</pre>", source_start)
        source = unescape(re.sub(r"<[^>]+>", "", page[source_start:source_end]))
        self.assertIn('class="grid gap-3"', source)
        self.assertIn('class="g-col-6 g-col-md-8"', source)
        self.assertNotIn("p-3 border rounded bg-body-tertiary", source)

    def test_layout_grid_and_columns_examples_keep_visual_preview_and_simple_source(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("layout/index.html")

        grid_start = page.index('id="grid"')
        grid_example_start = page.index('data-example="layout-grid-example"', grid_start)
        grid_options_start = page.index("Grid options", grid_example_start)
        columns_start = page.index('id="columns"', grid_options_start)
        columns_example_start = page.index('data-example="layout-columns-example"', columns_start)
        self.assertLess(grid_start, grid_example_start)
        self.assertLess(grid_example_start, grid_options_start)
        self.assertLess(grid_options_start, columns_start)
        self.assertLess(columns_start, columns_example_start)

        grid_section = page[grid_example_start:columns_start]
        columns_section = page[columns_example_start:]
        self.assertIn('class="row row-cols-1 row-cols-md-3 g-3"', grid_section)
        self.assertIn('class="p-3 border rounded bg-body-tertiary"', grid_section)
        self.assertIn('class="row mb-3"', columns_section)
        self.assertIn('class="p-3 border rounded bg-body-tertiary"', columns_section)
        self.assertNotIn('class="moo-example__header"', grid_section)
        self.assertNotIn('class="moo-example__header"', columns_section)

        for example_id, expected_source, forbidden_source in (
            (
                "layout-grid-example",
                'class="row row-cols-1 row-cols-md-3 g-3"',
                'p-3 border rounded bg-body-tertiary',
            ),
            (
                "layout-columns-example",
                'class="container text-center"',
                'row mb-3',
            ),
        ):
            with self.subTest(example=example_id):
                source_start = page.index(f'id="{example_id}-code"')
                source_end = page.index("</pre>", source_start)
                source = page[source_start:source_end]
                visible_source = unescape(re.sub(r"<[^>]+>", "", source))
                self.assertIn(expected_source, visible_source)
                self.assertNotIn(forbidden_source, visible_source)

    def test_rc7_removes_legacy_shell_macros_and_structural_hooks(self) -> None:
        active_sources = (
            ROOT / "src/components/sidebar.html.jinja",
            ROOT / "scss/layouts/_app.scss",
            ROOT / "scss/layouts/app/sidebar/_base.scss",
            ROOT / "scss/layouts/app/sidebar/_default.scss",
            ROOT / "scss/layouts/app/sidebar/_floating.scss",
            ROOT / "scss/layouts/app/sidebar/_inset.scss",
            ROOT / "scss/components/sidebar/_base.scss",
            ROOT / "scss/components/sidebar/_menus.scss",
            ROOT / "scss/components/sidebar/_identity.scss",
            ROOT / "scss/components/sidebar/_collapsed.scss",
            ROOT / "site/src/layouts/catalog.html.jinja",
            ROOT / "site/src/blocks/sidebar_shell.html.jinja",
            ROOT / "site/src/pages/components/sidebar.html.jinja",
            ROOT / "site/src/pages/blocks/sidebar-inset.html.jinja",
            ROOT / "site/src/pages/blocks/previews/sidebar-inset.html.jinja",
            ROOT / "tests/fixtures/certification/sidebar.html",
            ROOT / "conformance/fixtures/moo-esm.html",
        )
        forbidden = re.compile(
            r"sidebar_provider|sidebar_inset|sidebar-inset__|"
            r"data-slot=[\"']sidebar-inset|class=[\"'][^\"']*sidebar-inset"
        )
        for path in active_sources:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertFalse(forbidden.search(path.read_text(encoding="utf-8")))

    def test_layout_registry_is_canonical_and_stays_outside_components(self) -> None:
        layouts = json.loads(
            (ROOT / "src/registry/layouts.json").read_text(encoding="utf-8")
        )
        components = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        self.assertEqual([entry["slug"] for entry in layouts], ["app", "page"])
        self.assertEqual({entry["slug"] for entry in layouts}, {"app", "page"})
        self.assertEqual(
            {entry["source"] for entry in layouts},
            {"src/layouts/app.html.jinja", "src/layouts/page.html.jinja"},
        )
        self.assertNotIn("app", {entry["slug"] for entry in components})
        self.assertNotIn("page", {entry["slug"] for entry in components})

    def test_layout_docs_use_the_public_app_page_contract(self) -> None:
        guide = self.GUIDE.read_text(encoding="utf-8")
        self.assertNotIn("sidebar_provider", guide)
        self.assertNotIn("sidebar_inset", guide)
        self.assertNotIn("zero-gutter", guide)
        self.assertNotIn("region-specific", guide)
        self.assertNotIn("bleed support", guide)
        self.assertNotIn("data-example=", guide)
        self.assertNotIn("render_code_snippet(", guide)

        for name in (
            "previews/app-sidebar.html.jinja",
            "previews/app-none.html.jinja",
            "previews/page.html.jinja",
        ):
            with self.subTest(preview=name):
                preview = self.read_page(name)
                self.assertIn('{% extends "layouts/base.html.jinja" %}', preview)
                self.assertRegex(
                    preview,
                    r'class="(?=[^"]*\bmoo-layout-preview\b)(?=[^"]*\bmin-vh-100\b)[^"]*"',
                )
                self.assertNotIn("sidebar_provider", preview)
                self.assertNotIn("sidebar_inset", preview)
                self.assertNotIn("<main", preview)
        app_sidebar_preview = self.read_page("previews/app-sidebar.html.jinja")
        app_none_preview = self.read_page("previews/app-none.html.jinja")
        skeleton_import = '{% from "components/skeleton.html.jinja" import skeleton %}'
        self.assertIn(skeleton_import, app_none_preview)
        self.assertIn(
            '{% from "blocks/sidebar_shell.html.jinja" import render_sidebar_shell %}',
            app_sidebar_preview,
        )
        self.assertIn("render_sidebar_shell(", app_sidebar_preview)
        self.assertIn('demo_copy="portal"', app_sidebar_preview)
        card_import = '{% from "components/card.html.jinja" import card %}'
        self.assertIn(card_import, app_none_preview)
        self.assertGreaterEqual(app_none_preview.count('{% call card('), 2)
        self.assertIn('title="Page-only workspace"', app_none_preview)
        self.assertIn('New request', app_none_preview)
        self.assertIn('title="Footer actions"', app_none_preview)
        self.assertIn('flex-grow-1', app_none_preview)

    def test_layout_registry_requires_exact_runtime_source_parity(self) -> None:
        def make_fixture(
            root: Path,
            registry_slugs: tuple[str, ...],
            doc_slugs: tuple[str, ...],
        ) -> tuple[Path, Path]:
            layouts_dir = root / "src" / "layouts"
            registry = root / "registry"
            layouts_dir.mkdir(parents=True)
            registry.mkdir(parents=True)
            for slug in doc_slugs:
                source = layouts_dir / f"{slug}.html.jinja"
                source.write_text(
                    f'{{% macro {slug}() %}}{{% endmacro %}}\n',
                    encoding="utf-8",
                )
            (registry / "layouts.json").write_text(
                json.dumps(
                    [
                        {
                            "slug": slug,
                            "label": slug.title(),
                            "status": "preview",
                            "source": f"src/layouts/{slug}.html.jinja",
                        }
                        for slug in registry_slugs
                    ]
                ),
                encoding="utf-8",
            )
            return layouts_dir, registry

        with tempfile.TemporaryDirectory() as temporary:
            layouts_dir, registry = make_fixture(
                Path(temporary) / "missing", ("app", "page"), ("app",)
            )
            with self.assertRaisesRegex(ValueError, r"missing sources: page"):
                site_build.load_layouts(layouts_dir, registry)

        with tempfile.TemporaryDirectory() as temporary:
            layouts_dir, registry = make_fixture(
                Path(temporary) / "extra", ("app",), ("app", "page")
            )
            with self.assertRaisesRegex(ValueError, r"extra sources: page"):
                site_build.load_layouts(layouts_dir, registry)


if __name__ == "__main__":
    unittest.main()
