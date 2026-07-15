from __future__ import annotations

from tests.helpers import DIST, ROOT, CatalogTestCase


class CardTests(CatalogTestCase):
    def test_card_examples_are_generated_from_component_macro(self) -> None:
        card_component_path = ROOT / "src/components/card.html.jinja"
        self.assertTrue(card_component_path.is_file())
        card_component = card_component_path.read_text(encoding="utf-8")
        card_page = (
            ROOT / "src/pages/components/card.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertIn("{% macro card(", card_component)
        self.assertIn(
            '{% from "components/card.html.jinja" import card %}',
            card_page,
        )
        self.assertNotIn('<div class="card"', card_page)
        self.assertNotIn('style=""', card_component)
        self.assertNotIn("style=", card_page)
        self.assertEqual(
            card_page.count(
                'preview_class="moo-example__preview--narrow"'
            ),
            5,
        )

    def test_card_page_uses_bootstrap_native_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = DIST / "components/card.html"
        self.assertTrue(output.is_file())

        page = output.read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertGreater(preview_count, 0)
        self.assertEqual(
            preview_count,
            page.count("moo-example__source"),
        )
        for marker in (
            'data-example="card-content"',
            'data-example="card-basic"',
            'data-example="card-actions"',
            'data-example="card-rtl"',
        ):
            self.assertIn(marker, page)

        for native_class in (
            "card",
            "card-header",
            "card-body",
            "card-title",
            "card-subtitle",
            "card-footer",
        ):
            self.assertIn(native_class, page)

        self.assertIn('class="btn btn-primary"', page)
        self.assertIn('class="btn btn-outline-secondary"', page)
        self.assertIn('dir="rtl"', page)
        self.assertNotIn('<a class="btn', page)
        self.assertNotIn("<input", page)
        self.assertNotIn("form-control", page)
        self.assertNotIn("form-label", page)
        self.assertNotIn("list-group", page)
        self.assertNotIn("card-img", page)
        self.assertNotIn("example.com", page)
        self.assertNotIn('style="width: 22rem;"', page)
        for runtime_name in ("React", "Tailwind", "className", "shadcn"):
            self.assertNotIn(runtime_name, page)

    def test_card_uses_runtime_theme_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(
            '@import "components/card";',
            (ROOT / "scss/moo-ui.scss").read_text(encoding="utf-8"),
        )
        self.assertIn(".card {", css)
        card_block = css.rsplit(".card {", 1)[1].split("}", 1)[0]
        for declaration in (
            "--bs-card-bg: var(--moo-surface);",
            "--bs-card-color: var(--moo-foreground);",
            "--bs-card-border-color: var(--moo-border);",
            "--bs-card-border-radius: var(--bs-border-radius-xl);",
            "--bs-card-inner-border-radius: calc(var(--bs-card-border-radius) - var(--bs-card-border-width));",
            "--bs-card-box-shadow: var(--bs-box-shadow-sm);",
            "--bs-card-cap-bg: transparent;",
            "--bs-card-title-color: var(--moo-foreground);",
            "--bs-card-subtitle-color: var(--moo-muted-foreground);",
        ):
            self.assertIn(declaration, card_block)

    def test_card_bridges_shared_primitives_without_hardcoded_values(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        card_scss = (
            ROOT / "scss/components/_card.scss"
        ).read_text(encoding="utf-8")
        self.assertNotIn("#", card_scss)
        self.assertNotIn("rgb", card_scss)
        self.assertIn(
            "--bs-card-box-shadow: var(--bs-box-shadow-sm);", card_scss
        )
        self.assertIn(
            "--bs-card-border-radius: var(--bs-border-radius-xl);", card_scss
        )
        self.assertIn("var(--moo-surface)", card_scss)
        self.assertIn("var(--moo-border)", card_scss)
        self.assertNotIn("form-control", card_scss)
        self.assertNotIn("list-group", card_scss)
