from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/sheet.html.jinja"
PAGE = ROOT / "src/pages/components/sheet.html.jinja"
STYLES = ROOT / "scss/components/_sheet.scss"


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

        self.assertIn('class="offcanvas offcanvas-end sheet"', output)
        self.assertIn('id="example"', output)
        self.assertIn('aria-labelledby="example-title"', output)
        self.assertIn("Content", output)
        self.assertNotIn("data-bs-backdrop", output)
        self.assertNotIn("data-bs-scroll", output)

    def test_sheet_supports_explicit_aria_label_fallback(self) -> None:
        output = self.render(
            '{% call sheet("example", aria_label="Filter results") %}'
            "Content{% endcall %}"
        )

        self.assertIn('aria-label="Filter results"', output)
        self.assertNotIn("aria-labelledby", output)

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
                self.assertIn(f'class="offcanvas offcanvas-{placement} sheet"', output)

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
        self.assertIn("portal_content=basic_sheet", source)
        self.assertIn("portal_content=placement_sheets", source)
        self.assertIn("portal_content=scroll_sheet", source)
        self.assertIn("portal_content=no_close_sheet", source)
        self.assertIn("portal_content=workflow_sheet", source)
        self.assertIn("arabic_portal=rtl_arabic_sheet", source)

    def test_sheet_page_keeps_offcanvas_outside_example_preview(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/sheet.html")
        basic_section = page.split('data-example="basic"', 1)[1].split(
            'data-example="placements"', 1
        )[0]
        preview = basic_section.split('class="moo-example__preview"', 1)[1].split(
            'class="moo-example__source"', 1
        )[0]
        section_markup = basic_section.split("</section>", 1)[0]
        after_section = basic_section.split("</section>", 1)[1]

        self.assertIn('data-bs-toggle="offcanvas"', preview)
        self.assertNotIn('class="offcanvas offcanvas-end sheet"', preview)
        self.assertNotIn('class="offcanvas offcanvas-end sheet"', section_markup)
        self.assertIn('class="offcanvas offcanvas-end sheet"', after_section)

    def test_sheet_styles_are_isolated_from_other_offcanvas_components(self) -> None:
        styles = STYLES.read_text(encoding="utf-8")

        self.assertIn(".offcanvas.sheet .offcanvas-title", styles)
        self.assertNotIn(".offcanvas-backdrop", styles)
        self.assertNotIn("backdrop-filter", styles)
        self.assertNotRegex(styles, r"(?m)^\.offcanvas-title\s*\{")

    def test_sheet_preserves_shadow_when_bootstrap_focuses_the_panel(self) -> None:
        styles = STYLES.read_text(encoding="utf-8")

        self.assertIn(".offcanvas.sheet[tabindex]:focus-visible", styles)
        self.assertIn("outline: none", styles)
        self.assertGreaterEqual(
            styles.count("box-shadow: var(--bs-box-shadow-lg)"),
            2,
        )

    def test_sheet_does_not_own_global_backdrop_tokens(self) -> None:
        styles = STYLES.read_text(encoding="utf-8")

        self.assertNotIn(".offcanvas-backdrop", styles)
        self.assertNotIn(".modal-backdrop", styles)
        self.assertNotIn("--moo-overlay-backdrop", styles)
        self.assertNotIn("backdrop-filter", styles)
        self.assertNotIn(".moo-example__surface:has(.offcanvas.sheet", styles)
        self.assertNotIn("body:has(.offcanvas.sheet.show)", styles)

    def test_sheet_panels_are_portaled_before_bootstrap_creates_backdrop(self) -> None:
        script = (ROOT / "static/js/preview.js").read_text(encoding="utf-8")

        self.assertIn(
            'document.querySelectorAll(".moo-catalog .offcanvas.sheet").forEach(portalCatalogSheet)',
            script,
        )
        self.assertIn("document.body.appendChild(sheet)", script)
        self.assertNotIn("moo-sheet-placeholder", script)
        self.assertNotIn("catalogSheetPlaceholders", script)
