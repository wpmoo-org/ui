from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/sheet.html.jinja"
PAGE = ROOT / "src/pages/components/sheet.html.jinja"


class SheetTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Sheet macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/sheet.html.jinja" import sheet, sheet_body, '
            'sheet_header %}'
            + source
        )
        return " ".join(template.render().split())

    def test_sheet_renders_offcanvas_shell_with_aria_wiring(self) -> None:
        output = self.render('{% call sheet("example") %}Content{% endcall %}')

        self.assertIn('class="offcanvas offcanvas-end"', output)
        self.assertIn('id="example"', output)
        self.assertIn('aria-labelledby="example-title"', output)
        self.assertIn("Content", output)
        self.assertNotIn("data-bs-backdrop", output)
        self.assertNotIn("data-bs-scroll", output)

    def test_sheet_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Sheet id is required"):
            self.render('{% call sheet("   ") %}Content{% endcall %}')

    def test_sheet_rejects_unknown_placement(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown sheet placement: huge"):
            self.render(
                '{% call sheet("example", placement="huge") %}Content{% endcall %}'
            )

    def test_sheet_placement_classes(self) -> None:
        for placement in ("start", "end", "top", "bottom"):
            with self.subTest(placement=placement):
                output = self.render(
                    f'{{% call sheet("example", placement="{placement}") %}}x{{% endcall %}}'
                )
                self.assertIn(f'class="offcanvas offcanvas-{placement}"', output)

    def test_sheet_backdrop_false_and_scroll_true_set_data_attributes(self) -> None:
        output = self.render(
            '{% call sheet("example", backdrop=false, scroll=true) %}Content{% endcall %}'
        )

        self.assertIn('data-bs-backdrop="false"', output)
        self.assertIn('data-bs-scroll="true"', output)

    def test_sheet_header_renders_title_and_close_button_by_default(self) -> None:
        output = self.render('{{ sheet_header("example", "Edit profile") }}')

        self.assertIn('class="offcanvas-header"', output)
        self.assertIn('id="example-title"', output)
        self.assertIn("Edit profile", output)
        self.assertIn('class="btn-close"', output)
        self.assertIn('data-bs-dismiss="offcanvas"', output)

    def test_sheet_header_dismiss_false_omits_close_button(self) -> None:
        output = self.render(
            '{{ sheet_header("example", "Confirm export", dismiss=false) }}'
        )

        self.assertNotIn("btn-close", output)

    def test_sheet_header_requires_id_and_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Sheet header id is required"):
            self.render('{{ sheet_header("   ", "Title") }}')
        with self.assertRaisesRegex(ValueError, "Sheet title is required"):
            self.render('{{ sheet_header("example", "   ") }}')

    def test_sheet_body_wraps_caller_content(self) -> None:
        output = self.render('{% call sheet_body() %}Body text{% endcall %}')

        self.assertIn('class="offcanvas-body"', output)
        self.assertIn("Body text", output)

    def test_page_composes_sheet_with_button_data_api_trigger(self) -> None:
        self.assertTrue(PAGE.is_file(), "Sheet page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn(
            '{% from "components/sheet.html.jinja" import sheet, sheet_body, '
            "sheet_header %}",
            source,
        )
        self.assertIn('sheet_target="sheet-basic"', source)
        self.assertIn('placement="start"', source)
        self.assertIn('placement="top"', source)
        self.assertIn('placement="bottom"', source)
        self.assertIn("backdrop=false", source)
        self.assertIn("scroll=true", source)
        self.assertIn("dismiss=false", source)
        self.assertIn('dismiss="offcanvas"', source)
        self.assertIn('dir="rtl"', source)
