from __future__ import annotations

import json
import re

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
        self.assertIn("> MU </span>", output)

        with self.assertRaisesRegex(
            ValueError,
            "Avatar fallback initials are required when src is empty",
        ):
            self.render_avatar('avatar(name="Moo UI")')

    def test_image_avatar_requires_alt_text(self) -> None:
        output = self.render_avatar(
            'avatar(src="/avatar.svg", alt="Moo mascot", size="lg")'
        )

        self.assertIn('class="avatar avatar-lg"', output)
        self.assertIn('<img src="/avatar.svg" alt="Moo mascot">', output)
        self.assertNotIn("aria-label", output)

        with self.assertRaisesRegex(ValueError, "Avatar images require alt text"):
            self.render_avatar('avatar(src="/avatar.svg")')

    def test_avatar_accepts_only_documented_sizes(self) -> None:
        self.assertIn(
            'class="avatar avatar-sm"',
            self.render_avatar('avatar(name="Small", initials="SM", size="sm")'),
        )

        with self.assertRaisesRegex(ValueError, "Unknown avatar size: xl"):
            self.render_avatar('avatar(name="Large", initials="LG", size="xl")')
