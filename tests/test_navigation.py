from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/navigation.html.jinja"
PAGE = ROOT / "site/src/pages/components/navigation.html.jinja"


class NavigationTests(CatalogTestCase):
    def render_navigation(self, template_source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Navigation macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/navigation.html.jinja" import nav_item, nav_menu %}'
            + template_source
        )
        return " ".join(template.render().split())

    def test_navigation_macro_outputs_native_bootstrap_nav(self) -> None:
        output = self.render_navigation(
            """
            {% call nav_menu("Primary sections", vertical=true) %}
              {{ nav_item("Dashboard", active=true, icon="layout-dashboard") }}
              {{ nav_item("Tasks") }}
              {{ nav_item("Inbox", badge_label="3") }}
              {{ nav_item("Settings", end_icon="chevron-right") }}
              {{ nav_item("Settings", disabled=true) }}
            {% endcall %}
            """
        )

        self.assertIn('<nav aria-label="Primary sections">', output)
        self.assertIn('class="nav nav-pills flex-column gap-1"', output)
        self.assertIn('class="nav-link active"', output)
        self.assertIn('aria-current="page"', output)
        self.assertIn('class="badge text-bg-secondary rounded-pill ms-auto"', output)
        self.assertIn('data-icon="inline-end"', output)
        self.assertIn('aria-disabled="true" tabindex="-1"', output)
        self.assertNotIn("--moo-navigation", output)

    def test_navigation_macro_rejects_unknown_options(self) -> None:
        with self.assertRaisesRegex(ValueError, "Navigation aria_label is required"):
            self.render_navigation('{% call nav_menu("") %}{{ nav_item("A") }}{% endcall %}')

        with self.assertRaisesRegex(ValueError, "Unknown navigation style: tabs"):
            self.render_navigation(
                '{% call nav_menu("Tabs", style="tabs") %}{{ nav_item("A") }}{% endcall %}'
            )

        with self.assertRaisesRegex(ValueError, "Unknown navigation direction: sideways"):
            self.render_navigation(
                '{% call nav_menu("RTL", dir="sideways") %}{{ nav_item("A") }}{% endcall %}'
            )

        with self.assertRaisesRegex(ValueError, "Navigation item label is required"):
            self.render_navigation('{% call nav_menu("Nav") %}{{ nav_item("") }}{% endcall %}')

    def test_heading_and_item_utilities_preserve_native_navigation(self) -> None:
        output = self.render_navigation(
            '{% call nav_menu("Sections", heading="On this page", heading_class="ps-3") %}'
            '{{ nav_item("One", href="#one", extra_class="ps-3") }}{% endcall %}'
        )
        self.assertIn('<span class="small fw-semibold ps-3">On this page</span>', output)
        self.assertIn('<a class="nav-link ps-3" href="#one">', output)
        template = create_environment().from_string(
            '{% from "components/navigation.html.jinja" import nav_item %}'
            '{{ nav_item("One", extra_class=utilities) }}'
        )
        self.assertIn(
            'ps-3&#34; onmouseover=&#34;bad',
            template.render(utilities='ps-3" onmouseover="bad'),
        )
        with self.assertRaisesRegex(ValueError, "Navigation item extra_class must be a string"):
            template.render(utilities=[])
        with self.assertRaisesRegex(ValueError, "Navigation heading_class must be a string"):
            self.render_navigation('{% call nav_menu("Sections", heading_class=[]) %}{% endcall %}')

    def test_steps_navigation_keeps_current_completion_and_disabled_states_distinct(self) -> None:
        output = self.render_navigation(
            """
            {% call nav_menu("Application steps", style="steps") %}
              {{ nav_item("Details", href="/details", icon="folder-open", description="Details saved", completed=true) }}
              {{ nav_item("Members", href="/members", icon="user", description="Choose members", active=true) }}
              {{ nav_item("Submission", icon="pencil", description="Available later", disabled=true) }}
            {% endcall %}
            """
        )

        self.assertIn('class="nav nav-pills nav-steps flex-column"', output)
        self.assertEqual(output.count('data-nav-completed="true"'), 1)
        first_item = re.search(r'<li\b[^>]*>.*?</li>', output)
        self.assertIsNotNone(first_item)
        self.assertIn('<span class="visually-hidden">Completed</span>', first_item.group())
        self.assertIn('class="nav-link-icon" aria-hidden="true"', output)
        self.assertIn('href="/members" aria-current="page"', output)
        self.assertIn('aria-disabled="true" tabindex="-1"', output)
        self.assertIn('<span class="nav-link-description d-block small">Details saved</span>', first_item.group())
        self.assertIn('<span class="nav-link-description d-block small">Choose members</span>', output)
