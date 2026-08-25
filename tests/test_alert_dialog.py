from __future__ import annotations

from html.parser import HTMLParser

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/alert_dialog.html.jinja"
PAGE = ROOT / "site/src/pages/components/alert-dialog.html.jinja"


class AlertDialogFooterButtonParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.alert_depth: int | None = None
        self.footer_depth: int | None = None
        self.footer_button_classes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get("class") or "").split()

        if tag == "div" and "modal--alert" in classes:
            self.alert_depth = self.depth

        if (
            self.alert_depth is not None
            and tag == "div"
            and "modal-footer" in classes
        ):
            self.footer_depth = self.depth

        if self.footer_depth is not None and tag in ("a", "button", "input"):
            self.footer_button_classes.append(attrs_dict.get("class") or "")

        self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        self.depth -= 1

        if self.footer_depth is not None and self.depth <= self.footer_depth:
            self.footer_depth = None

        if self.alert_depth is not None and self.depth <= self.alert_depth:
            self.alert_depth = None


class AlertDialogTests(CatalogTestCase):
    def render(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Alert Dialog macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/alert_dialog.html.jinja" import alert_dialog, alert_dialog_header %}'
            '{% from "components/dialog.html.jinja" import dialog_footer %}'
            '{% from "components/button.html.jinja" import button %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_header_renders_title_and_description_without_close_button_or_body_split(self) -> None:
        output = self.render(
            'alert_dialog_header("alert-x", "Discard this draft invoice?", '
            '"Any line items you have entered will be lost.")'
        )
        self.assertIn('<h1 class="modal-title" id="alert-x-title">Discard this draft invoice?</h1>', output)
        self.assertIn(
            '<p class="modal-description" id="alert-x-description">Any line items you have entered will be lost.</p>',
            output,
        )
        self.assertNotIn("modal-body", output)
        self.assertNotIn("btn-close", output)

    def test_header_can_render_media_icon(self) -> None:
        output = self.render(
            'alert_dialog_header("alert-x", "Pause nightly synchronization?", '
            '"Queued records will wait.", icon="cloud-off")'
        )
        self.assertIn('class="btn btn-icon-sm btn-outline-secondary flex-shrink-0"', output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn("Pause nightly synchronization?", output)

    def test_header_description_is_optional(self) -> None:
        output = self.render('alert_dialog_header("alert-x", "Leave without saving?")')
        self.assertIn("Leave without saving?", output)
        self.assertNotIn("alert-x-description", output)

    def test_header_uses_semantic_modal_classes_instead_of_spacing_utilities(self) -> None:
        source = COMPONENT.read_text(encoding="utf-8")

        self.assertIn("modal-header--alert", source)
        self.assertIn("modal-description", source)
        for utility_class in ("align-items-start", "gap-3", "pb-0", "mt-2", "mb-0"):
            with self.subTest(utility_class=utility_class):
                self.assertNotIn(utility_class, source)

    def test_header_whitespace_only_description_is_trimmed_away(self) -> None:
        output = self.render(
            'alert_dialog_header("alert-x", "Leave without saving?", "   ")'
        )
        self.assertNotIn("modal-body", output)

    def render_full_dialog(self) -> str:
        template = create_environment().from_string(
            '{% from "components/alert_dialog.html.jinja" import alert_dialog, alert_dialog_header %}'
            '{% from "components/dialog.html.jinja" import dialog_footer %}'
            '{% from "components/button.html.jinja" import button %}'
            '{% call alert_dialog("alert-x", describedby="alert-x-description") %}'
            '{{ alert_dialog_header("alert-x", "Discard this draft invoice?", "Any line items will be lost.") }}'
            '{% call dialog_footer() %}'
            '{{ button("Cancel", variant="outline", dismiss="modal") }}'
            '{{ button("Discard", dismiss="modal") }}'
            "{% endcall %}"
            "{% endcall %}"
        )
        return " ".join(template.render().split())

    def test_rendered_dialog_has_static_backdrop_and_disabled_keyboard(self) -> None:
        output = self.render_full_dialog()
        self.assertIn('data-bs-backdrop="static"', output)
        self.assertIn('data-bs-keyboard="false"', output)

    def test_rendered_dialog_uses_alert_modal_modifier(self) -> None:
        output = self.render_full_dialog()

        self.assertIn('class="modal fade modal--alert"', output)

    def test_rendered_dialog_can_carry_direction_on_modal_root(self) -> None:
        template = create_environment().from_string(
            '{% from "components/alert_dialog.html.jinja" import alert_dialog %}'
            '{% call alert_dialog("alert-x", direction="rtl") %}Body{% endcall %}'
        )
        output = " ".join(template.render().split())

        self.assertIn('dir="rtl"', output)

    def test_rendered_dialog_is_labelled_and_described(self) -> None:
        output = self.render_full_dialog()
        self.assertIn('aria-labelledby="alert-x-title"', output)
        self.assertIn('aria-describedby="alert-x-description"', output)

    def test_rendered_dialog_has_no_close_button(self) -> None:
        output = self.render_full_dialog()
        self.assertNotIn("btn-close", output)

    def test_requires_id(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Alert Dialog header id is required"
        ):
            self.render('alert_dialog_header("   ", "Title")')

    def test_requires_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Alert Dialog title is required"):
            self.render('alert_dialog_header("alert-x", "   ")')

    def test_page_uses_dialogs_static_backdrop_option(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("{% call alert_dialog(", source)
        self.assertNotIn("{% call dialog(", source)
        self.assertNotIn("static=true", source)

    def test_page_alert_dialog_actions_do_not_render_primary_buttons(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/alert-dialog.html")
        parser = AlertDialogFooterButtonParser()
        parser.feed(page)

        self.assertGreaterEqual(len(parser.footer_button_classes), 2)
        self.assertFalse(
            [
                classes
                for classes in parser.footer_button_classes
                if "btn-primary" in classes.split()
            ],
            "Alert Dialog examples should not inherit the base-color primary action style.",
        )

    def test_page_includes_small_media_and_tabbed_rtl_examples(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('icon="circle-alert"', source)
        self.assertIn("render_rtl_example", source)
        self.assertIn('"alert-dialog"', source)
        self.assertIn('preview_class="moo-example__preview--fit"', source)
        self.assertGreaterEqual(source.count('direction="rtl"'), 2)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/alert-dialog.html")
        self.assertIn('id="rtl"', page)
        self.assertIn("alert-dialog-direction-tabs", page)
        self.assertIn("rtl-arabic-code", page)

    def test_english_rtl_tab_keeps_modal_text_ltr(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        english_block = source.split("{% set rtl_english %}", 1)[1].split("{% endset %}", 1)[0]

        self.assertIn('<div dir="ltr">', english_block)
        self.assertIn('direction="ltr"', english_block)
        self.assertNotIn('direction="rtl"', english_block)

    def test_requires_dialog_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Alert Dialog id is required"):
            self.render('alert_dialog("   ")')
