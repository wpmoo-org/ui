from __future__ import annotations

import json
import re
from markupsafe import escape

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/avatar.html.jinja"
PAGE = ROOT / "src/pages/components/avatar.html.jinja"
STYLE = ROOT / "scss/components/_avatar.scss"


class AvatarTests(CatalogTestCase):
    def render_avatar(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Avatar macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/avatar.html.jinja" import avatar %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_fallback_avatar_requires_initials_and_accessible_name(self) -> None:
        output = self.render_avatar('avatar(name="Moo UI", initials="MU")')

        self.assertIn('class="avatar"', output)
        self.assertIn('role="img" aria-label="Moo UI"', output)
        self.assertIn('<span class="avatar-fallback">MU</span>', output)

        with self.assertRaisesRegex(
            ValueError,
            "Avatar fallback initials are required when src is empty",
        ):
            self.render_avatar('avatar(name="Moo UI")')

    def test_image_avatar_renders_hidden_fallback_markup(self) -> None:
        output = self.render_avatar(
            'avatar(name="Maya Quinn", src="/avatars/maya.png", alt="Maya Quinn", fallback="MQ")'
        )

        self.assertIn("avatar--has-image", output)
        self.assertIn('<span class="avatar-fallback">MQ</span>', output)
        self.assertNotIn("aria-label", output)

    def test_fallback_text_is_escaped(self) -> None:
        marker = "<script/>"
        output = self.render_avatar(
            f'avatar(name="Ops Desk", fallback="{marker}")'
        )

        self.assertIn(escape(marker), output)

    def test_image_avatar_requires_alt_text(self) -> None:
        output = self.render_avatar(
            'avatar(src="/avatar.svg", alt="Moo mascot", size="lg")'
        )

        self.assertIn("avatar-lg", output)
        self.assertIn('<img src="/avatar.svg" alt="Moo mascot">', output)
        self.assertNotIn("aria-label", output)

        with self.assertRaisesRegex(ValueError, "Avatar images require alt text"):
            self.render_avatar('avatar(src="/avatar.svg")')

    def test_badge_dot_renders_without_text_or_icon(self) -> None:
        output = self.render_avatar(
            'avatar(name="Moo User", initials="MU", badge_dot=true, '
            'badge_class="bg-success", badge_aria_label="Online")'
        )

        self.assertIn('class="avatar-badge avatar-badge--dot bg-success"', output)
        self.assertIn('role="status" aria-label="Online"', output)

    def test_badge_with_text_still_renders_without_dot_modifier(self) -> None:
        output = self.render_avatar(
            'avatar(name="Ops analyst", initials="OA", badge="!", '
            'badge_aria_label="Escalation pending")'
        )

        self.assertIn('class="avatar-badge"', output)
        self.assertNotIn("avatar-badge--dot", output)
        self.assertIn("! </span>", output)

    def test_badge_icon_renders_via_render_icon(self) -> None:
        output = self.render_avatar(
            'avatar(name="Compliance owner", initials="CO", badge_icon="plus")'
        )

        self.assertIn("avatar-badge--icon", output)
        self.assertIn('data-icon="inline-start"', output)

    def test_avatar_accepts_only_documented_sizes(self) -> None:
        self.assertIn(
            'class="avatar avatar-sm"',
            self.render_avatar('avatar(name="Small", initials="SM", size="sm")'),
        )

        with self.assertRaisesRegex(ValueError, "Unknown avatar size: xl"):
            self.render_avatar('avatar(name="Large", initials="LG", size="xl")')

    def test_avatar_page_examples_stay_product_shaped(self) -> None:
        page = PAGE.read_text()

        self.assertIn("Moo Admin", page)
        self.assertIn("admin@example.com", page)
        self.assertIn("render_rtl_example", page)
        self.assertNotIn('title="Direction aware"', page)
        self.assertNotIn("badge_dot for", page)
        self.assertNotIn('style="width: 0.5rem; height: 0.5rem;"', page)

    def test_avatar_badge_paints_above_avatar_outline(self) -> None:
        style = STYLE.read_text()

        self.assertRegex(style, r"\.avatar::after\s*\{[^}]*z-index:\s*1;")
        self.assertRegex(style, r"\.avatar-badge\s*\{[^}]*z-index:\s*2;")
        self.assertRegex(style, r"\.avatar-badge--icon\s*\{[^}]*padding-inline:\s*0;")
        self.assertRegex(style, r"\.avatar-badge--icon \[data-icon\]\s*\{[^}]*width:\s*0\.375rem;")
        self.assertRegex(style, r"\.avatar-group > \.avatar\s*\{[^}]*z-index:\s*0;")
