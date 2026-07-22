from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/breadcrumb.html.jinja"
PAGE = ROOT / "src/pages/components/breadcrumb.html.jinja"


class BreadcrumbTests(CatalogTestCase):
    def render_breadcrumb(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Breadcrumb macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/breadcrumb.html.jinja" import breadcrumb %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_breadcrumb_renders_current_page_only(self) -> None:
        self.assertEqual(
            self.render_breadcrumb('breadcrumb([{"label": "Home"}])'),
            '<nav aria-label="breadcrumb"> <ol class="breadcrumb">'
            ' <li class="breadcrumb-item active" aria-current="page">Home</li>'
            " </ol> </nav>",
        )

    def test_breadcrumb_links_every_item_but_the_last(self) -> None:
        output = self.render_breadcrumb(
            'breadcrumb([{"label": "Home", "href": "/"}, {"label": "Library"}])'
        )
        self.assertIn('<li class="breadcrumb-item"><a href="/">Home</a></li>', output)
        self.assertIn(
            '<li class="breadcrumb-item active" aria-current="page">Library</li>',
            output,
        )

    def test_breadcrumb_item_without_href_falls_back_to_hash(self) -> None:
        output = self.render_breadcrumb(
            'breadcrumb([{"label": "Home"}, {"label": "Library"}])'
        )
        self.assertIn('<a href="#">Home</a>', output)

    def test_breadcrumb_supports_extra_class_and_aria_label(self) -> None:
        self.assertIn(
            'class="breadcrumb mb-0"',
            self.render_breadcrumb('breadcrumb([{"label": "Home"}], extra_class="mb-0")'),
        )
        self.assertIn(
            'aria-label="trail"',
            self.render_breadcrumb('breadcrumb([{"label": "Home"}], aria_label="trail")'),
        )

    def test_breadcrumb_links_are_muted_without_hover_underline(self) -> None:
        styles = (ROOT / "scss/components/_breadcrumb.scss").read_text(encoding="utf-8")

        self.assertIn("color: var(--moo-muted-foreground)", styles)
        self.assertIn("transition: color 0.15s ease", styles)
        self.assertIn(
            ".breadcrumb-item a:hover {\n  color: var(--moo-foreground);\n  text-decoration: none;\n}",
            styles,
        )

    def test_breadcrumb_supports_custom_divider(self) -> None:
        output = self.render_breadcrumb(
            'breadcrumb([{"label": "Home"}, {"label": "Library"}], divider="•")'
        )
        self.assertIn(
            'class="breadcrumb" style="--bs-breadcrumb-divider: \'•\';"',
            output,
        )

    def test_breadcrumb_ellipsis_item_renders_a_static_marker(self) -> None:
        output = self.render_breadcrumb(
            'breadcrumb([{"label": "Home", "href": "#"}, {"ellipsis": true}, {"label": "Library"}])'
        )
        self.assertIn('<span class="breadcrumb-ellipsis">', output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn('<span class="visually-hidden">More</span>', output)
        self.assertNotIn("<button", output)
        self.assertNotIn("<a ", output.split("visually-hidden")[1])

    def test_breadcrumb_dropdown_item_renders_via_ready_dropdown_macros(self) -> None:
        output = self.render_breadcrumb(
            'breadcrumb(['
            '{"label": "Home", "href": "#"}, '
            '{"label": "Projects", "dropdown_items": ['
            '{"label": "Projects", "href": "/projects"}, '
            '{"label": "Reports", "href": "/reports"}'
            ']}, '
            '{"label": "Library"}'
            '])'
        )
        self.assertIn('<span class="breadcrumb-dropdown-item">', output)
        self.assertIn('class="dropdown-item" href="/projects"', output)
        self.assertIn('class="dropdown-item" href="/reports"', output)

    def test_breadcrumb_dropdown_item_requires_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Breadcrumb item label is required"):
            self.render_breadcrumb(
                'breadcrumb([{"label": "   ", "dropdown_items": [{"label": "Projects"}]}])'
            )

    def test_breadcrumb_requires_items(self) -> None:
        with self.assertRaisesRegex(ValueError, "Breadcrumb items are required"):
            self.render_breadcrumb("breadcrumb([])")

    def test_breadcrumb_requires_visible_item_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Breadcrumb item label is required"):
            self.render_breadcrumb('breadcrumb([{"label": "   "}])')
