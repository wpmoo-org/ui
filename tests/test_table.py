from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/table.html.jinja"
PAGE = ROOT / "src/pages/components/table.html.jinja"


class TableTests(CatalogTestCase):
    def render_table(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Table macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/table.html.jinja" import table %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_table_wraps_headers_and_rows_in_a_responsive_container(self) -> None:
        self.assertEqual(
            self.render_table('table(["A", "B"], [["1", "2"]])'),
            '<div class="table-responsive"> <table class="table">'
            ' <thead> <tr> <th scope="col">A</th> <th scope="col">B</th>'
            " </tr> </thead> <tbody> <tr> <td>1</td> <td>2</td> </tr>"
            " </tbody> </table> </div>",
        )

    def test_table_requires_headers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Table headers are required"):
            self.render_table("table([], [])")

    def test_table_align_applies_to_header_and_cell_in_that_column(self) -> None:
        output = self.render_table('table(["A", "B"], [["1", "2"]], align=["", "end"])')
        self.assertIn('<th scope="col" class="text-end">B</th>', output)
        self.assertIn('<td class="text-end">2</td>', output)

    def test_table_row_header_renders_first_cell_as_th_scope_row(self) -> None:
        output = self.render_table(
            'table(["A"], [["x"]], row_ids=["row-x"], row_header=true)'
        )
        self.assertIn('<tr id="row-x">', output)
        self.assertIn('<th scope="row">x</th>', output)

    def test_table_caption_renders_when_provided(self) -> None:
        self.assertIn(
            "<caption>Cap</caption>",
            self.render_table('table(["A"], [["x"]], caption="Cap")'),
        )

    def test_table_modifier_flags_map_to_bootstrap_classes(self) -> None:
        output = self.render_table(
            'table(["A"], [["x"]], striped=true, hover=true, small=true, borderless=true)'
        )
        self.assertIn(
            'class="table table-striped table-hover table-sm table-borderless"',
            output,
        )
