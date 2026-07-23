from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/skeleton.html.jinja"
PAGE = ROOT / "src/pages/components/skeleton.html.jinja"


class SkeletonTests(CatalogTestCase):
    def render_skeleton(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Skeleton macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/skeleton.html.jinja" import skeleton %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_skeleton_macro_emits_placeholder_surface_contract(self) -> None:
        output = self.render_skeleton("skeleton()")
        class_tokens = [
            set(class_value.split()) for class_value in re.findall(r'<[^>]+class="([^"]+)"', output)
        ]

        self.assertTrue(
            any("placeholder-glow" in classes for classes in class_tokens),
            f"expected placeholder-glow in macro output, got: {output}",
        )
        self.assertTrue(
            any("skeleton" in classes for classes in class_tokens),
            f"expected skeleton in macro output, got: {output}",
        )
        self.assertTrue(
            any("placeholder" in classes for classes in class_tokens),
            f"expected placeholder in macro output, got: {output}",
        )
        self.assertFalse(
            any(
                "placeholder-glow" in classes and "placeholder" in classes
                for classes in class_tokens
            ),
            f"expected placeholder-glow wrapper with nested placeholder child, got: {output}",
        )
        self.assertIn('aria-hidden="true"', output)
        self.assertIn('style="width: 100%;', output)

    def test_skeleton_width_height_are_escaped_and_deterministic(self) -> None:
        width = "42%"
        height = "2rem"
        first = self.render_skeleton(
            f'skeleton(width="{width}", height="{height}")'
        )
        second = self.render_skeleton(
            f'skeleton(width="{width}", height="{height}")'
        )

        self.assertEqual(first, second)
        self.assertIn("width: 42%;", first)
        self.assertIn("height: 2rem;", first)

        dangerous = "<script>bad()</script>"
        dangerous_output = self.render_skeleton(f'skeleton(width="{dangerous}")')
        self.assertNotIn("<script>", dangerous_output)
        self.assertIn("&lt;script&gt;bad()&lt;/script&gt;", dangerous_output)

    def test_skeleton_fails_fast_on_empty_width(self) -> None:
        for call in ('skeleton(width="")', 'skeleton(width="   ")'):
            with self.subTest(call=call):
                with self.assertRaisesRegex(ValueError, "Skeleton width is required"):
                    self.render_skeleton(call)

    def test_skeleton_component_partial_is_imported_into_main_bundle(self) -> None:
        styles = (ROOT / "scss/moo-ui.scss").read_text(encoding="utf-8")
        component_layer = (ROOT / "scss/_component_layer.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn('@import "component_layer";', styles)
        self.assertIn('@import "components/skeleton";', component_layer)

    def test_skeleton_is_ready_in_catalog_and_pages_build(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "skeleton", "label": "Skeleton", "status": "ready"},
            catalog,
        )

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "components/skeleton.html").is_file())

    def test_skeleton_catalog_page_uses_macro_not_raw_placeholder_markup(self) -> None:
        self.assertTrue(PAGE.is_file(), "Skeleton catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("skeleton(", source)
        self.assertNotIn("class=\"placeholder", source)
        self.assertNotIn("placeholder-glow", source)

    def test_skeleton_page_covers_the_reference_example_shapes(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        for example_id in ("basic", "profile-row", "card", "form", "list-rows", "rtl"):
            self.assertIn(
                f'"{example_id}"',
                source,
                f"Expected a render_example id of {example_id!r}",
            )

    def test_skeleton_page_does_not_stretch_examples_full_width_by_accident(
        self,
    ) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("w-100", source)
        self.assertNotIn("moo-example__preview--narrow", source)
