from __future__ import annotations

from tests.helpers import DIST, CatalogTestCase, lucide_body


class ButtonGroupTests(CatalogTestCase):
    def test_button_group_page_uses_bootstrap_native_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = DIST / "components/button-group.html"
        self.assertTrue(output.is_file())

        page = output.read_text(encoding="utf-8")
        self.assertGreater(page.count("moo-example__preview"), 0)
        self.assertEqual(
            page.count("moo-example__preview"),
            page.count("moo-example__source"),
        )
        for marker in (
            'data-example="basic-actions"',
            'data-example="icon-only-group"',
            'data-example="size-groups"',
            'data-example="vertical-group"',
            'data-example="toolbar-groups"',
            'data-example="rtl-preview"',
        ):
            self.assertIn(marker, page)

        for native_class in (
            "btn-group",
            "btn-group-vertical",
            "btn-toolbar",
            "btn-group-sm",
            "btn-group-lg",
        ):
            self.assertIn(native_class, page)

        self.assertIn('role="group"', page)
        self.assertIn('role="toolbar"', page)
        self.assertIn('aria-label="Ticket actions"', page)
        self.assertIn('aria-label="Media controls"', page)
        self.assertNotIn("dropdown-menu", page)
        self.assertNotIn("btn-check", page)
        self.assertNotIn("form-control", page)
        self.assertNotIn('<a class="btn', page)
        self.assertNotIn("example.com", page)
        self.assertNotIn("React", page)
        self.assertNotIn("Tailwind", page)

    def test_button_group_rtl_keeps_bootstrap_ltr_geometry(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn('[dir="rtl"] .btn-group,', css)
        self.assertIn('[dir="rtl"] .btn-toolbar {', css)
        self.assertIn("direction: ltr;", css)
        self.assertIn('[dir="rtl"] .btn-group > .btn,', css)
        self.assertIn('[dir="rtl"] .btn-toolbar > .btn {', css)
        self.assertIn("unicode-bidi: plaintext;", css)

    def test_button_group_composition_uses_ready_group_macros(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        composition = page.split('data-example="basic-actions"', 1)[1].split(
            "</section>", 1
        )[0]
        self.assertIn('aria-label="Go back"', composition)
        self.assertIn(lucide_body("arrow-left"), composition)
        self.assertIn('aria-label="Ticket review"', composition)
        self.assertIn("Archive", composition)
        self.assertIn("Report", composition)
        self.assertIn("Snooze", composition)
        self.assertNotIn("dropdown", composition)
        self.assertNotIn("‹", composition)
        self.assertNotIn('href="#"', composition)

    def test_button_group_examples_cover_orientation_and_size(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button-group.html")
        self.assertIn('aria-label="Increase value"', page)
        self.assertIn('aria-label="Decrease value"', page)
        self.assertIn(lucide_body("plus"), page)
        self.assertIn(lucide_body("minus"), page)
        self.assertIn(
            'class="d-flex flex-column align-items-center gap-3"',
            page,
        )
