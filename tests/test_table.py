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

    def test_table_caption_can_move_to_top_with_bootstrap_class(self) -> None:
        output = self.render_table(
            'table(["A"], [["x"]], caption="Cap", caption_top=true)'
        )

        self.assertIn('class="table caption-top"', output)
        self.assertIn("<caption>Cap</caption>", output)

    def test_table_footer_renders_summary_row(self) -> None:
        output = self.render_table(
            'table(["Item", "Amount"], [["Hosting", "$90"]], footer=["Total", "$90"], align=["", "end"])'
        )

        self.assertIn("<tfoot>", output)
        self.assertIn('<th scope="row">Total</th>', output)
        self.assertIn('<td class="text-end">$90</td>', output)

    def test_table_body_cells_render_caller_supplied_markup_intentionally(self) -> None:
        # Cells intentionally allow rich markup (e.g. a composed Badge) for
        # component-rich table content; headers/caption stay plain text and
        # are still escaped, so this is a scoped, caller-controlled contract,
        # not a general HTML passthrough.
        output = self.render_table(
            'table(["Status"], [["<span class=\\"badge\\">Done</span>"]])'
        )
        self.assertIn('<td><span class="badge">Done</span></td>', output)

    def test_table_footer_cells_render_markup_like_body_cells_do(self) -> None:
        output = self.render_table(
            'table(["Item"], [["Hosting"]], footer=["<strong>Total</strong>"])'
        )
        self.assertIn("<tfoot>", output)
        self.assertIn('<th scope="row"><strong>Total</strong></th>', output)

    def test_table_header_and_caption_text_stay_escaped(self) -> None:
        output = self.render_table(
            'table(["<script>"], [["x"]], caption="<script>")'
        )
        self.assertIn("&lt;script&gt;", output)
        self.assertNotIn("<script>", output)

    def test_table_modifier_flags_map_to_bootstrap_classes(self) -> None:
        output = self.render_table(
            'table(["A"], [["x"]], striped=true, hover=true, small=true, borderless=true)'
        )
        self.assertIn(
            'class="table table-striped table-hover table-sm table-borderless"',
            output,
        )

    def test_table_row_actions_renders_an_icon_only_dropdown_trigger(self) -> None:
        template = create_environment().from_string(
            '{% from "components/table.html.jinja" import table_row_actions %}'
            '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
            '{% call table_row_actions(aria_label="Open actions for Web frontend") %}'
            '{{ dropdown_item("Redeploy") }}'
            "{% endcall %}"
        )
        output = " ".join(template.render().split())

        self.assertIn('aria-label="Open actions for Web frontend"', output)
        self.assertIn('data-bs-toggle="dropdown"', output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn("Redeploy", output)
        self.assertNotIn(">Open menu<", output)

    def test_table_row_actions_requires_aria_label(self) -> None:
        template = create_environment().from_string(
            '{% from "components/table.html.jinja" import table_row_actions %}'
            '{% call table_row_actions(aria_label="") %}x{% endcall %}'
        )
        with self.assertRaisesRegex(
            ValueError, "Table row actions aria_label is required"
        ):
            " ".join(template.render().split())

    def test_page_uses_realistic_original_scenarios(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        for distinctive_reference_scenario in (
            "INV00",
            "Credit Card",
            "PayPal",
            "Bank Transfer",
            "recent invoices",
            "Wireless Mouse",
            "Mechanical Keyboard",
        ):
            self.assertNotIn(
                distinctive_reference_scenario,
                source,
                f"Page reuses the reference's own scenario shape: {distinctive_reference_scenario}",
            )
        for original_scenario in (
            "Partner agreement",
            "Web frontend",
            "Batch worker",
        ):
            self.assertIn(original_scenario, source)

    def test_page_composes_actions_from_ready_row_actions_and_dropdown_macros(
        self,
    ) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn(
            '{% from "components/table.html.jinja" import table, table_row_actions %}',
            source,
        )
        self.assertIn(
            '{% from "components/dropdown_menu.html.jinja" import dropdown_item, dropdown_divider %}',
            source,
        )
