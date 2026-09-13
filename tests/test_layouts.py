from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from build import create_environment


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


class LayoutMacroTests(unittest.TestCase):
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
        page_id: str = "",
        header: str = "Header",
        main: str = "Main",
        footer: str = "Footer",
    ) -> str:
        return self.render_page(
            """
            {% call(region) page(width=width, id=page_id) %}
              {% if region == "header" %}{{ header }}
              {% elif region == "main" %}{{ main }}
              {% elif region == "footer" %}{{ footer }}
              {% endif %}
            {% endcall %}
            """,
            width=width,
            page_id=page_id,
            header=header,
            main=main,
            footer=footer,
        )

    def test_page_container_contract(self) -> None:
        output = self.render_regions(page_id="workspace-page")

        self.assertIn('data-slot="page"', output)
        self.assertIn('id="workspace-page"', output)
        self.assertEqual(output.count('<header>'), 1)
        self.assertEqual(output.count('<main id="main-content" tabindex="-1">'), 1)
        self.assertEqual(output.count('<footer>'), 1)
        self.assertEqual(output.count('class="container-xl"'), 3)
        self.assertLess(output.index("Header"), output.index("Main"))
        self.assertLess(output.index("Main"), output.index("Footer"))
        self.assertNotIn("sidebar_provider", output)
        self.assertNotIn("sidebar_inset", output)
        self.assertNotIn("sidebar-inset__", output)

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
        self.assertEqual(output.count('<main id="main-content" tabindex="-1">'), 1)
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
        for argument in ("extra_class", "header_width", "footer_width", "bleed"):
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


class AppLayoutTests(LayoutMacroTests):
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
                [("aside", "sidebar"), ("div", "page")],
            )
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
        self.assertIn('class="sidebar-wrapper"', output)
        self.assertIn('id="workspace-app"', output)
        self.assertIn('data-layout="app"', output)
        self.assertIn('data-shell-mode="viewport"', output)
        self.assertEqual(output.count('data-slot="sidebar-wrapper"'), 1)
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
        self.assertIn('class="sidebar-wrapper"', output)
        self.assertIn('data-layout="app"', output)
        self.assertIn('data-shell-mode="contained"', output)
        self.assertEqual(output.count('data-slot="page"'), 1)
        self.assertNotIn('data-slot="sidebar-wrapper"', output)
        self.assertNotIn('data-slot="sidebar"', output)
        self.assertNotIn("data-sidebar-state", output)
        self.assertNotIn("data-sidebar-key", output)
        self.assertNotIn("data-sidebar-trigger", output)

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


if __name__ == "__main__":
    unittest.main()
