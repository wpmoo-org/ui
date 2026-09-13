from __future__ import annotations

import re
import unittest
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


if __name__ == "__main__":
    unittest.main()
