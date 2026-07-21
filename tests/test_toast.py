from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/toast.html.jinja"
PAGE = ROOT / "src/pages/components/toast.html.jinja"
PREVIEW_JS = ROOT / "static/js/preview.js"


class ToastTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Toast macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/toast.html.jinja" import toast, toast_container %}'
            + source
        )
        return " ".join(template.render().split())

    def test_toast_renders_header_body_and_close_button(self) -> None:
        output = self.render(
            '{{ toast("toast-basic", "Moo UI", "Changes saved.", timestamp="just now") }}'
        )

        self.assertIn('id="toast-basic"', output)
        self.assertIn('class="toast"', output)
        self.assertIn('role="alert"', output)
        self.assertIn('aria-live="assertive"', output)
        self.assertIn('aria-atomic="true"', output)
        self.assertIn('class="toast-header"', output)
        self.assertIn("Moo UI", output)
        self.assertIn("just now", output)
        self.assertIn('class="toast-body"', output)
        self.assertIn("Changes saved.", output)
        self.assertIn('class="btn-close"', output)
        self.assertIn('data-bs-dismiss="toast"', output)
        self.assertNotIn("data-bs-autohide", output)
        self.assertNotIn("data-bs-delay", output)

    def test_toast_requires_id_title_and_body(self) -> None:
        with self.assertRaisesRegex(ValueError, "Toast id is required"):
            self.render('{{ toast("   ", "Title", "Body") }}')
        with self.assertRaisesRegex(ValueError, "Toast title is required"):
            self.render('{{ toast("id", "   ", "Body") }}')
        with self.assertRaisesRegex(ValueError, "Toast body is required"):
            self.render('{{ toast("id", "Title", "   ") }}')

    def test_toast_timestamp_is_optional(self) -> None:
        output = self.render('{{ toast("id", "Title", "Body") }}')

        self.assertNotIn("<small>", output)

    def test_toast_autohide_false_sets_data_attribute(self) -> None:
        output = self.render('{{ toast("id", "Title", "Body", autohide=false) }}')

        self.assertIn('data-bs-autohide="false"', output)

    def test_toast_custom_delay_sets_data_attribute(self) -> None:
        output = self.render('{{ toast("id", "Title", "Body", delay=10000) }}')

        self.assertIn('data-bs-delay="10000"', output)

    def test_toast_default_delay_omits_data_attribute(self) -> None:
        output = self.render('{{ toast("id", "Title", "Body", delay=5000) }}')

        self.assertNotIn("data-bs-delay", output)

    def test_toast_container_renders_fixed_position_utilities(self) -> None:
        output = self.render(
            '{% call toast_container(placement="bottom-end") %}Content{% endcall %}'
        )

        self.assertIn('class="toast-container position-fixed bottom-0 end-0 p-3"', output)
        self.assertIn("Content", output)

    def test_toast_container_supports_all_documented_placements(self) -> None:
        expectations = {
            "top-start": "top-0 start-0",
            "top-center": "top-0 start-50 translate-middle-x",
            "top-end": "top-0 end-0",
            "bottom-start": "bottom-0 start-0",
            "bottom-center": "bottom-0 start-50 translate-middle-x",
            "bottom-end": "bottom-0 end-0",
        }
        for placement, utility_classes in expectations.items():
            with self.subTest(placement=placement):
                output = self.render(
                    f'{{% call toast_container(placement="{placement}") %}}x{{% endcall %}}'
                )
                self.assertIn(utility_classes, output)

    def test_toast_container_rejects_unknown_placement(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown toast placement: huge"):
            self.render(
                '{% call toast_container(placement="huge") %}Content{% endcall %}'
            )

    def test_page_composes_toast_with_button_data_hook_trigger(self) -> None:
        self.assertTrue(PAGE.is_file(), "Toast page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn(
            '{% from "components/toast.html.jinja" import toast, toast_container %}',
            source,
        )
        self.assertIn('toast_target="toast-basic"', source)
        self.assertIn("autohide=false", source)
        self.assertIn('dir="rtl"', source)

    def test_preview_uses_one_delegated_toast_listener(self) -> None:
        script = PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn(
            'event.target.closest("[data-moo-toast-target]")',
            script,
        )
        self.assertIn("document.getElementById", script)
        self.assertNotIn(
            'document.querySelectorAll("[data-moo-toast-target]").forEach',
            script,
        )
