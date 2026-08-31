from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase, read_settings


COMPONENT = ROOT / "src/components/badge.html.jinja"
PAGE = ROOT / "site/src/pages/components/badge.html.jinja"


class BadgeTests(CatalogTestCase):
    def render_badge(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Badge macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/badge.html.jinja" import badge %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_badge_maps_variants_to_bootstrap_utilities(self) -> None:
        self.assertIn('class="badge text-bg-primary"', self.render_badge('badge("Default")'))
        self.assertIn(
            'class="badge text-bg-secondary rounded-pill"',
            self.render_badge('badge("Secondary", variant="secondary", pill=true)'),
        )
        self.assertIn(
            'class="badge text-bg-danger"',
            self.render_badge('badge("Delete", variant="destructive")'),
        )
        self.assertIn(
            'class="badge border text-body-secondary"',
            self.render_badge('badge("Outline", variant="outline")'),
        )

    def test_badge_requires_known_variant_and_visible_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown badge variant: ghost"):
            self.render_badge('badge("Ghost", variant="ghost")')
        with self.assertRaisesRegex(ValueError, "Badge label is required"):
            self.render_badge('badge("   ")')

    def test_badge_can_add_visually_hidden_context(self) -> None:
        output = self.render_badge(
            'badge("12", variant="secondary", visually_hidden="unread messages")'
        )

        self.assertIn("12", output)
        self.assertIn(
            '<span class="visually-hidden">unread messages</span>',
            output,
        )

    def test_badge_supports_attrs(self) -> None:
        output = self.render_badge('badge("3", attrs="data-count")')

        self.assertIn('data-count', output)

    def test_badge_uses_medium_bootstrap_font_weight_token(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"--bs-badge-font-weight:\s*500;")

    def test_badge_uses_centered_reference_chip_geometry(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        badge_rule = re.search(
            r"\.badge\s*\{(?P<body>[^}]*display:\s*inline-flex;[^}]*)\}",
            css,
        )
        self.assertIsNotNone(badge_rule)
        badge_css = badge_rule.group("body")

        self.assertRegex(css, r"--bs-badge-padding-x:\s*0\.5rem;")
        self.assertRegex(css, r"--bs-badge-padding-y:\s*0\.125rem;")
        self.assertRegex(css, r"--bs-badge-font-size:\s*0\.75rem;")
        self.assertRegex(css, r"--bs-badge-border-radius:\s*var\(--bs-border-radius-pill\);")
        self.assertIn("display: inline-flex;", badge_css)
        self.assertIn("align-items: center;", badge_css)
        self.assertIn("justify-content: center;", badge_css)
        self.assertRegex(badge_css, r"(?m)^\s*height:\s*1\.25rem;")
        self.assertIn("border: var(--bs-border-width) solid var(--bs-border-color);", badge_css)
        self.assertIn("border-color: transparent;", badge_css)
        self.assertIn("$badge-border-color: transparent !default;", read_settings())
        self.assertIn("gap: 0.25rem;", badge_css)
        self.assertIn("line-height: 1rem;", badge_css)

    def test_badge_variants_use_reference_theme_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        source = (ROOT / "scss/settings/_palette.scss").read_text(encoding="utf-8")
        tokens_root = (ROOT / "scss/themes/_standalone_root.scss").read_text(
            encoding="utf-8"
        )
        core_theme = (ROOT / "scss/themes/_scoped_core.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "$moo-destructive-surface: color-mix(in srgb, $moo-destructive 3%, transparent) !default;",
            source,
        )
        self.assertIn(
            "$moo-destructive-surface-dark: color-mix(in srgb, $moo-destructive-dark 20%, transparent) !default;",
            source,
        )
        self.assertIn("--moo-destructive-surface: #{$moo-destructive-surface};", tokens_root)
        self.assertIn("--moo-destructive-surface: #{$moo-destructive-surface-dark};", tokens_root)
        self.assertIn("--moo-destructive-surface: #{$moo-destructive-surface};", core_theme)
        self.assertIn("--moo-destructive-surface: #{$moo-destructive-surface-dark};", core_theme)

        expected_rules = {
            '.badge[class~="border"]': (
                "border-color: var(--moo-border) !important;",
            ),
            '.badge[class~="text-bg-primary"]': (
                "color: var(--moo-primary-foreground) !important;",
                "background-color: var(--moo-primary) !important;",
            ),
            '.badge[class~="text-bg-secondary"]': (
                "color: var(--moo-foreground) !important;",
                "background-color: var(--moo-muted-surface) !important;",
            ),
            '.badge[class~="text-bg-danger"]': (
                "color: var(--moo-destructive) !important;",
                "background-color: var(--moo-destructive-surface) !important;",
            ),
            '.badge[class~="text-body-secondary"]': (
                "color: var(--moo-foreground) !important;",
            ),
        }
        for selector, declarations in expected_rules.items():
            with self.subTest(selector=selector):
                escaped_selector = re.escape(selector).replace("\\[", "\\[").replace("\\]", "\\]")
                rule = re.search(rf"{escaped_selector}\s*\{{(?P<body>[^}}]*)\}}", css)
                self.assertIsNotNone(rule)
                body = rule.group("body")
                for declaration in declarations:
                    self.assertIn(declaration, body)

    def test_page_uses_shared_rtl_example_tabs(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn("render_rtl_example", source)
        self.assertIn("arabic_badge", source)
        self.assertIn("hebrew_badge", source)
        self.assertIn("english_badge", source)
        self.assertGreaterEqual(source.count('dir="rtl"'), 2)
        self.assertIn('dir="ltr"', source)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/badge.html")
        self.assertIn(">Badge</span>", output)
        self.assertIn("badge-direction-tabs", output)
        self.assertIn("rtl-arabic-code", output)
        self.assertIn("rtl-hebrew-code", output)
        self.assertIn("rtl-english-code", output)
