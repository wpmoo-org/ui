from __future__ import annotations

import json
import re

from tests.helpers import DIST, ROOT, CatalogTestCase


class ScrollFadeTests(CatalogTestCase):
    def test_build_adds_scroll_fade_utility_navigation(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "utils/scroll-fade/index.html").is_file())

        utilities = json.loads(
            (ROOT / "src/registry/utilities.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            utilities,
            [
                {
                    "slug": "scroll-fade",
                    "label": "Scroll Fade",
                    "status": "ready",
                }
            ],
        )

        index = self.read_output("components/index.html")
        self.assertIn(">Components</h2>", index)
        self.assertIn(">Utilities</h2>", index)
        self.assertIn('href="../utils/scroll-fade/"', index)

        component = self.read_output("components/button.html")
        self.assertIn('href="../../utils/scroll-fade/"', component)

        utility = self.read_output("utils/scroll-fade.html")
        self.assertIn('aria-current="page"', utility)
        self.assertIn("Scroll Fade", utility)
        self.assertIn('data-moo-component-doc-layout', utility)
        self.assertIn('class="moo-doc-main"', utility)
        self.assertIn('data-moo-component-toc', utility)
        self.assertIn('aria-label="Utility examples"', utility)

    def test_scroll_fade_utility_contract_is_complete(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        for class_name in (
            "scroll-fade",
            "scroll-fade-y",
            "scroll-fade-x",
            "scroll-fade-t",
            "scroll-fade-b",
            "scroll-fade-l",
            "scroll-fade-r",
            "scroll-fade-s",
            "scroll-fade-e",
            "scroll-fade-none",
            "no-scrollbar",
        ):
            self.assertRegex(
                css,
                rf"\.{re.escape(class_name)}(?=[\s,:{{])",
            )
        self.assertIn(".no-scrollbar::-webkit-scrollbar", css)
        for variable in (
            "--scroll-fade-size",
            "--scroll-fade-reveal",
            "--moo-scroll-fade-t-size",
            "--moo-scroll-fade-b-size",
            "--moo-scroll-fade-s-size",
            "--moo-scroll-fade-e-size",
            "--moo-scroll-fade-mask",
        ):
            self.assertIn(variable, css)

        for animation in (
            "moo-scroll-fade-reveal-t",
            "moo-scroll-fade-reveal-b",
            "moo-scroll-fade-reveal-s",
            "moo-scroll-fade-reveal-e",
        ):
            self.assertIn(f"@keyframes {animation}", css)

        self.assertIn("animation-timeline: scroll(self y)", css)
        self.assertIn("animation-timeline: scroll(self x)", css)
        self.assertIn("animation-timeline: scroll(self inline)", css)
        self.assertIn('.scroll-fade-x:where([dir="rtl"], [dir="rtl"] *)', css)
        self.assertIn('.scroll-fade-s:where([dir="rtl"], [dir="rtl"] *)', css)
        self.assertIn('.scroll-fade-e:where([dir="rtl"], [dir="rtl"] *)', css)

        page = self.read_output("utils/scroll-fade.html")
        example_headings = {
            "vertical-scroll": "vertical-scrolling",
            "no-overflow": "no-overflow",
            "horizontal-scroll": "horizontal-scrolling",
            "edge-fades": "single-edges",
            "fade-size": "fade-size",
            "disabled-fade": "disable-the-fade",
        }
        for example, heading in example_headings.items():
            self.assertIn(f'data-example="{example}"', page)
            self.assertIn(f'aria-labelledby="{heading}"', page)
            self.assertIn(f'id="{heading}"', page)
        for contract in (
            "scroll-fade",
            "scroll-fade-y",
            "scroll-fade-x",
            "scroll-fade-t",
            "scroll-fade-b",
            "scroll-fade-l",
            "scroll-fade-r",
            "scroll-fade-s",
            "scroll-fade-e",
            "scroll-fade-none",
            "no-scrollbar",
        ):
            self.assertIn(contract, page)

    def test_shared_scroll_surfaces_use_scroll_fade_without_scrollbars(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        button = self.read_output("components/button.html")
        self.assertIn(
            'class="moo-code scroll-fade-x no-scrollbar"',
            button,
        )
        self.assertIn(
            'class="sidebar-content scroll-fade-y no-scrollbar"',
            button,
        )

        catalog_css = self.read_output("assets/css/catalog.css")
        code_block = catalog_css.split(".moo-example__source pre {", 1)[
            1
        ].split("}", 1)[0]
        self.assertIn("overflow-x: auto;", code_block)
        self.assertIn("white-space: pre;", code_block)
        self.assertNotIn("overflow-wrap: anywhere;", code_block)
