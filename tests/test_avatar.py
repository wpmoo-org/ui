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

    def test_avatar_page_uses_avatar_contract_only(self) -> None:
        self.assertTrue(PAGE.is_file(), "Avatar catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"avatar"})
        self.assertIn(
            '{% from "includes/page-header.html.jinja" import render_page_header %}',
            source,
        )
        self.assertIn(
            '{% from "includes/example.html.jinja" import render_example %}',
            source,
        )
        self.assertIn(
            '{% from "includes/documentation-reference.html.jinja" import render_reference %}',
            source,
        )
        self.assertNotRegex(source, r"<(?:button|form|input|kbd|label|select|textarea)\b")
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-avatar", source)

    def test_avatar_styles_stay_in_the_public_avatar_namespace(self) -> None:
        self.assertTrue(STYLE.is_file(), "Avatar style partial is not implemented")
        source = STYLE.read_text(encoding="utf-8")

        self.assertIn(".avatar {", source)
        self.assertIn("border-radius: var(--bs-border-radius-pill);", source)
        self.assertIn("object-fit: cover;", source)
        self.assertIn(".avatar-sm", source)
        self.assertIn(".avatar-lg", source)
        self.assertNotIn("--moo-avatar", source)

    def test_avatar_catalog_builds_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "avatar", "label": "Avatar", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/avatar.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 4)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="avatar"', page)
        self.assertIn('class="avatar avatar-sm"', page)
        self.assertIn('class="avatar avatar-lg"', page)
        self.assertIn('role="img" aria-label="Moo UI"', page)
        self.assertIn('alt="Moo mascot"', page)
        self.assertIn("Bootstrap Image documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-avatar", page)
