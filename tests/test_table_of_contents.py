from __future__ import annotations

import unittest

from markupsafe import Markup

from build import create_environment


class TableOfContentsTests(unittest.TestCase):
    def render_toc(self, **props: object) -> str:
        options = {
            "id": "page-toc",
            "items": [{"target_id": "intro", "label": "Introduction"}],
            **props,
        }
        template = create_environment().from_string(
            '{% from "components/toc.html.jinja" import table_of_contents %}'
            '{{ table_of_contents(**props) }}'
        )
        return " ".join(template.render(props=options).split())

    def test_list_has_one_navigation_landmark_and_native_fragment_links(self) -> None:
        output = self.render_toc(content_id="article")
        self.assertEqual(output.count("<nav "), 1)
        self.assertIn('id="page-toc"', output)
        self.assertIn('data-toc=""', output)
        self.assertIn('data-toc-content="article"', output)
        self.assertIn('href="#intro"', output)
        self.assertIn("Introduction", output)
        self.assertIn("On this page", output)

    def test_compact_uses_native_dropdown_and_overview_status(self) -> None:
        output = self.render_toc(presentation="compact", scroll_root_id="reader")
        self.assertIn('data-bs-toggle="dropdown"', output)
        self.assertRegex(output, r'class="dropdown-menu(?: [^"]*)?"')
        self.assertIn('data-toc-scroll-root="reader"', output)
        self.assertIn('data-toc-current', output)
        self.assertIn("Overview</span>", output)
        self.assertIn('href="#intro"', output)

    def test_empty_list_renders_nothing_and_single_section_remains_available(self) -> None:
        self.assertEqual(self.render_toc(items=[]), "")
        self.assertEqual(self.render_toc().count('href="#intro"'), 1)

    def test_labels_and_metadata_are_escaped_even_if_marked_trusted(self) -> None:
        for presentation in ("list", "compact"):
            with self.subTest(presentation=presentation):
                output = self.render_toc(
                    presentation=presentation,
                    label=Markup("<Deutsch>"),
                    overview_label=Markup("<Overview>"),
                    content_id=Markup('article"onmouseover="bad'),
                    items=[{"target_id": "intro", "label": Markup("<img src=x>")}],
                )
                self.assertIn("&lt;Deutsch&gt;", output)
                self.assertIn("&lt;img src=x&gt;", output)
                self.assertNotIn("<img", output)
                self.assertNotIn("&amp;lt;Deutsch", output)
                self.assertIn('article&#34;onmouseover=&#34;bad', output)

    def test_non_ascii_and_reserved_fragment_characters_are_encoded(self) -> None:
        output = self.render_toc(items=[{"target_id": "über/x#y", "label": "Überblick"}])
        self.assertIn('href="#%C3%BCber%2Fx%23y"', output)

    def test_duplicate_or_whitespace_targets_are_rejected(self) -> None:
        for items in (
            [{"target_id": "intro", "label": "One"}, {"target_id": "intro", "label": "Two"}],
            [{"target_id": "two words", "label": "One"}],
            [{"target_id": " intro", "label": "One"}],
            [{"target_id": "", "label": "One"}],
        ):
            with self.subTest(items=items), self.assertRaises(ValueError):
                self.render_toc(items=items)

    def test_invalid_inputs_are_rejected_before_rendering(self) -> None:
        for props in (
            {"id": "two words"}, {"id": 3}, {"items": "intro"},
            {"items": [{"target_id": "intro", "label": ""}]},
            {"items": [{"target_id": "intro", "label": 1}]},
            {"items": [{"label": "Missing target"}]},
            {"label": 3}, {"overview_label": ""}, {"presentation": "drawer"},
        ):
            with self.subTest(props=props), self.assertRaises(ValueError):
                self.render_toc(**props)

    def test_navigation_metadata_is_escaped_and_existing_calls_keep_their_anatomy(self) -> None:
        template = create_environment().from_string(
            '{% from "components/navigation.html.jinja" import nav_menu, nav_item %}'
            '{% call nav_menu("Sections", **props) %}{{ nav_item("One", href="#one") }}{% endcall %}'
        )
        original = " ".join(template.render(props={}).split())
        self.assertIn('<nav aria-label="Sections">', original)
        output = template.render(props={"id": 'nav"safe', "data": {"moo-scope": Markup('<safe>')}})
        self.assertIn('id="nav&#34;safe"', output)
        self.assertIn('data-moo-scope="&lt;safe&gt;"', output)
        for data in ({"onClick": "bad"}, {"x--y": "bad"}, {"x": []}, {1: "bad"}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                template.render(props={"data": data})
