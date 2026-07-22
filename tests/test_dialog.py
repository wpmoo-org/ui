from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/dialog.html.jinja"
PAGE = ROOT / "src/pages/components/dialog.html.jinja"
STYLES = ROOT / "scss/components/_dialog.scss"


class DialogTests(CatalogTestCase):
    def render_dialog(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Dialog macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/dialog.html.jinja" import dialog, dialog_body, '
            'dialog_footer, dialog_header %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def render_dialog_block(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Dialog macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/dialog.html.jinja" import dialog, dialog_body, '
            'dialog_footer, dialog_header %}'
            + source
        )
        return " ".join(template.render().split())

    def test_dialog_renders_modal_shell_with_aria_wiring(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example") %}Content{% endcall %}'
        )

        self.assertIn('class="modal fade"', output)
        self.assertIn('id="example"', output)
        self.assertIn('aria-labelledby="example-title"', output)
        self.assertIn('aria-hidden="true"', output)
        self.assertIn('class="modal-dialog"', output)
        self.assertIn('class="modal-content"', output)
        self.assertIn("Content", output)

    def test_dialog_supports_explicit_aria_label_fallback(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example", aria_label="Workspace settings") %}'
            "Content{% endcall %}"
        )

        self.assertIn('aria-label="Workspace settings"', output)
        self.assertNotIn("aria-labelledby", output)

    def test_dialog_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Dialog id is required"):
            self.render_dialog_block('{% call dialog("   ") %}Content{% endcall %}')

    def test_dialog_rejects_unknown_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown dialog size: huge"):
            self.render_dialog_block(
                '{% call dialog("example", size="huge") %}Content{% endcall %}'
            )

    def test_dialog_supports_explicit_direction_for_portaled_rtl_modals(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example", direction="rtl") %}Content{% endcall %}'
        )

        self.assertIn('dir="rtl"', output)

    def test_dialog_rejects_unknown_direction(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown dialog direction: sideways"):
            self.render_dialog_block(
                '{% call dialog("example", direction="sideways") %}Content{% endcall %}'
            )

    def test_dialog_size_classes(self) -> None:
        for size, expected_class in (
            ("sm", "modal-sm"),
            ("lg", "modal-lg"),
            ("xl", "modal-xl"),
            ("fullscreen", "modal-fullscreen"),
        ):
            with self.subTest(size=size):
                output = self.render_dialog_block(
                    f'{{% call dialog("example", size="{size}") %}}Content{{% endcall %}}'
                )
                self.assertIn(f'class="modal-dialog {expected_class}"', output)

    def test_dialog_centered_and_scrollable_classes(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example", centered=true, scrollable=true) %}Content{% endcall %}'
        )

        self.assertIn("modal-dialog-centered", output)
        self.assertIn("modal-dialog-scrollable", output)

    def test_dialog_static_sets_backdrop_and_keyboard_attrs(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example", static=true) %}Content{% endcall %}'
        )

        self.assertIn('data-bs-backdrop="static"', output)
        self.assertIn('data-bs-keyboard="false"', output)

    def test_dialog_supports_extra_modal_class(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example", extra_class="modal--alert") %}Content{% endcall %}'
        )

        self.assertIn('class="modal fade modal--alert"', output)

    def test_dialog_default_allows_backdrop_and_keyboard_dismiss(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog("example") %}Content{% endcall %}'
        )

        self.assertNotIn("data-bs-backdrop", output)
        self.assertNotIn("data-bs-keyboard", output)

    def test_dialog_header_renders_title_and_close_button(self) -> None:
        output = self.render_dialog('dialog_header("example", "Edit workspace name")')

        self.assertIn('class="modal-header"', output)
        self.assertIn('id="example-title"', output)
        self.assertIn("Edit workspace name", output)
        self.assertIn('class="btn-close"', output)
        self.assertIn('data-bs-dismiss="modal"', output)
        self.assertIn('aria-label="Close"', output)

    def test_dialog_header_requires_id_and_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Dialog header id is required"):
            self.render_dialog('dialog_header("   ", "Title")')
        with self.assertRaisesRegex(ValueError, "Dialog title is required"):
            self.render_dialog('dialog_header("example", "   ")')

    def test_dialog_body_and_footer_wrap_caller_content(self) -> None:
        output = self.render_dialog_block(
            '{% call dialog_body() %}Body text{% endcall %}'
            '{% call dialog_footer() %}Footer actions{% endcall %}'
        )

        self.assertIn('class="modal-body"', output)
        self.assertIn("Body text", output)
        self.assertIn('class="modal-footer"', output)
        self.assertIn("Footer actions", output)

    def test_page_composes_dialog_with_button_data_api_trigger(self) -> None:
        self.assertTrue(PAGE.is_file(), "Dialog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn(
            '{% from "components/dialog.html.jinja" import dialog, dialog_body, '
            "dialog_footer, dialog_header %}",
            source,
        )
        self.assertIn('dialog_target="dialog-basic"', source)
        self.assertIn('dismiss="modal"', source)
        self.assertIn('size="sm"', source)
        self.assertIn('size="lg"', source)
        self.assertIn('size="xl"', source)
        self.assertIn("scrollable=true", source)
        self.assertIn("static=true", source)
        self.assertIn('dir="rtl"', source)

    def test_dialog_styles_keep_one_surface_and_preserve_elevation_on_focus(self) -> None:
        styles = STYLES.read_text(encoding="utf-8")

        self.assertNotIn("--bs-modal-footer-bg", styles)
        self.assertIn(".modal-content", styles)
        self.assertIn("box-shadow: var(--bs-box-shadow-lg)", styles)
        self.assertIn(".modal[tabindex]:focus-visible", styles)
        self.assertIn("outline: none", styles)

    def test_dialog_does_not_own_global_backdrop_blur(self) -> None:
        styles = STYLES.read_text(encoding="utf-8")

        self.assertNotIn(".modal-backdrop", styles)
        self.assertNotIn("body:has(.modal.show)", styles)
        self.assertNotIn("backdrop-filter", styles)
        self.assertNotIn("-webkit-backdrop-filter", styles)

    def test_catalog_portals_nested_preview_modals_above_body_backdrops(self) -> None:
        script = ROOT.joinpath("static/js/preview.js").read_text(encoding="utf-8")

        self.assertIn('document.addEventListener("show.bs.modal"', script)
        self.assertIn('document.addEventListener("hidden.bs.modal"', script)
        self.assertIn('modal.closest(".moo-catalog")', script)
        self.assertIn("document.body.appendChild(modal)", script)
        self.assertIn("catalogModalPlaceholders", script)
        self.assertIn("placeholder.parentNode.insertBefore(modal, placeholder)", script)
