from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/pagination.html.jinja"
PAGE = ROOT / "src/pages/components/pagination.html.jinja"


class PaginationTests(CatalogTestCase):
    def render_pagination(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Pagination macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/pagination.html.jinja" import pagination,'
            " pagination_ellipsis, pagination_item, pagination_next,"
            ' pagination_prev %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_pagination_wraps_items_in_nav_and_list(self) -> None:
        # pagination() is call-based; render it through a literal template.
        template = create_environment().from_string(
            '{% from "components/pagination.html.jinja" import pagination, pagination_item %}'
            '{% call pagination() %}{{ pagination_item("1") }}{% endcall %}'
        )
        output = " ".join(template.render().split())
        self.assertIn('<nav aria-label="Pagination">', output)
        self.assertIn('<ul class="pagination">', output)
        self.assertIn('<li class="page-item"> <a class="page-link" href="#">1</a> </li>', output)

    def test_pagination_rejects_unknown_size(self) -> None:
        template = create_environment().from_string(
            '{% from "components/pagination.html.jinja" import pagination %}'
            '{% call pagination(size="xl") %}x{% endcall %}'
        )
        with self.assertRaisesRegex(ValueError, "Unknown pagination size: xl"):
            " ".join(template.render().split())

    def test_pagination_item_marks_active_page_current(self) -> None:
        self.assertEqual(
            self.render_pagination('pagination_item("2", active=true)'),
            '<li class="page-item active" aria-current="page">'
            ' <a class="page-link" href="#">2</a> </li>',
        )

    def test_pagination_item_disabled_renders_span_not_link(self) -> None:
        self.assertEqual(
            self.render_pagination('pagination_item("3", disabled=true)'),
            '<li class="page-item disabled"> <span class="page-link">3</span> </li>',
        )

    def test_pagination_item_requires_visible_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Pagination item label is required"):
            self.render_pagination('pagination_item("   ")')

    def test_pagination_prev_places_icon_before_label(self) -> None:
        output = self.render_pagination("pagination_prev()")
        self.assertIn('aria-label="Previous"', output)
        icon_index = output.index('data-icon="inline-start"')
        label_index = output.index(">Previous<")
        self.assertLess(icon_index, label_index)

    def test_pagination_next_places_icon_after_label(self) -> None:
        output = self.render_pagination("pagination_next()")
        self.assertIn('aria-label="Next"', output)
        label_index = output.index(">Next<")
        icon_index = output.index('data-icon="inline-end"')
        self.assertLess(label_index, icon_index)

    def test_pagination_nav_item_disabled_renders_span_not_link(self) -> None:
        output = self.render_pagination("pagination_prev(disabled=true)")
        self.assertIn('<li class="page-item disabled">', output)
        self.assertIn('<span class="page-link" aria-label="Previous">', output)

    def test_pagination_ellipsis_is_non_interactive(self) -> None:
        output = self.render_pagination("pagination_ellipsis()")
        self.assertIn('<li class="page-item disabled">', output)
        self.assertIn('<span class="visually-hidden">More pages</span>', output)

    def test_page_uses_shared_rtl_example_tabs(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn("render_rtl_example", source)
        self.assertNotIn('title="RTL"', source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertGreaterEqual(source.count('dir="rtl"'), 3)

        # The RTL rule requires exact translations of the same example:
        # same page range (1/2/3, page 2 active) and ellipsis in all three.
        for block_start in ("rtl_arabic %}", "rtl_hebrew %}", "rtl_english %}"):
            block = source.split(block_start, 1)[1].split("{% endset %}", 1)[0]
            with self.subTest(locale=block_start):
                self.assertIn('pagination_item("1")', block)
                self.assertIn('pagination_item("2", active=true)', block)
                self.assertIn('pagination_item("3")', block)
                self.assertIn("pagination_ellipsis(", block)
                self.assertIn("pagination_prev(", block)
                self.assertIn("pagination_next(", block)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/pagination.html")
        self.assertIn("pagination-direction-tabs", output)
        self.assertIn(">Arabic</button>", output)
        self.assertIn(">Hebrew</button>", output)
        self.assertIn(">English</button>", output)
