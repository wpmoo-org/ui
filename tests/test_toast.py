from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase, read_primary_variables


COMPONENT = ROOT / "src/components/toast.html.jinja"
PAGE = ROOT / "site/src/pages/components/toast.html.jinja"
BOOTSTRAP_PREVIEW_JS = ROOT / "site/src/js/catalog/bootstrap-preview.js"
TOAST_SCSS = ROOT / "scss/components/_toast.scss"
COMPONENT_SETTINGS = ROOT / "scss/settings/_components.scss"
PRIMARY_VARIABLES = ROOT / "scss/_primary_variables.scss"


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
        self.assertIn('role="status"', output)
        self.assertIn('aria-live="polite"', output)
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

    def test_toast_supports_assertive_priority_for_urgent_messages(self) -> None:
        output = self.render(
            '{{ toast("toast-error", "Sync failed", "Try again.", priority="assertive") }}'
        )

        self.assertIn('role="alert"', output)
        self.assertIn('aria-live="assertive"', output)

    def test_toast_requires_id_title_body_and_known_priority(self) -> None:
        with self.assertRaisesRegex(ValueError, "Toast id is required"):
            self.render('{{ toast("   ", "Title", "Body") }}')
        with self.assertRaisesRegex(ValueError, "Toast title is required"):
            self.render('{{ toast("id", "   ", "Body") }}')
        with self.assertRaisesRegex(ValueError, "Toast body is required"):
            self.render('{{ toast("id", "Title", "   ") }}')
        with self.assertRaisesRegex(ValueError, "Unknown toast priority: loud"):
            self.render('{{ toast("id", "Title", "Body", priority="loud") }}')

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

    def test_toast_supports_native_action_markup(self) -> None:
        source = COMPONENT.read_text(encoding="utf-8")
        self.assertIn("action_label", source)

        output = self.render(
            '{{ toast("toast-action", "Event created", "Saved.", action_label="Undo") }}'
        )

        self.assertIn("Undo", output)
        self.assertIn('data-bs-dismiss="toast"', output)

    def test_toast_template_renders_one_toast_root(self) -> None:
        source = COMPONENT.read_text(encoding="utf-8")
        self.assertIn("macro toast_template(", source)

        output = self.render(
            '{% from "components/toast.html.jinja" import toast_template %}'
            '{{ toast_template("toast-template", "Event created", "Saved.") }}'
        )

        self.assertIn('<template id="toast-template" data-toast-template="toast">', output)
        self.assertEqual(output.count('class="toast"'), 1)

    def test_stacked_container_supports_a_bottom_end_deck(self) -> None:
        source = COMPONENT.read_text(encoding="utf-8")
        self.assertIn("stacked=false", source)

        output = self.render(
            '{% call toast_container(placement="bottom-end", stacked=true) %}x{% endcall %}'
        )

        self.assertIn("toast-container--stacked", output)
        self.assertIn('data-toast-stack="deck"', output)
        self.assertIn("bottom-0 end-0", output)

        with self.assertRaisesRegex(ValueError, "stacked Toast containers require placement=bottom-end"):
            self.render(
                '{% call toast_container(placement="top-end", stacked=true) %}x{% endcall %}'
            )
        with self.assertRaisesRegex(ValueError, "stacked Toast containers require placement=bottom-end"):
            self.render(
                '{% call toast_container(placement="bottom-center", stacked=true) %}x{% endcall %}'
            )

    def test_page_composes_one_repeated_trigger_and_template_deck(self) -> None:
        self.assertTrue(PAGE.is_file(), "Toast page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn(
            '{% from "components/toast.html.jinja" import toast_container, toast_template %}',
            source,
        )
        self.assertIn('toast_target="toast-demo-template"', source)
        self.assertIn('placement="bottom-end"', source)
        self.assertIn('stacked=true', source)
        self.assertIn('action_label="Undo"', source)
        self.assertEqual(source.count("toast_target="), 1)
        self.assertNotIn("toast-basic", source)
        self.assertNotIn("toast-stack-", source)

    def test_catalog_bootstrap_module_creates_repeated_toast_instances(self) -> None:
        script = BOOTSTRAP_PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn(
            'event.target.closest("[data-toast-target]")',
            script,
        )
        self.assertIn("dataset.toastTarget", script)
        self.assertIn("root.getElementById", script)
        self.assertIn("template.content.cloneNode", script)
        self.assertIn("data-toast-generated", script)
        self.assertIn("data-toast-stack-sequence", script)
        self.assertIn("toastStackVisibleLimit", script)
        self.assertIn("data-toast-stack-limited", script)
        self.assertIn("Toast.getOrCreateInstance", script)
        self.assertIn("show.bs.toast", script)
        self.assertIn("shown.bs.toast", script)
        self.assertIn("hidden.bs.toast", script)
        self.assertIn("listen(root", script)
        self.assertNotIn("document.addEventListener", script)
        self.assertNotIn(
            'document.querySelectorAll("[data-toast-target]").forEach',
            script,
        )

    def test_toast_stack_styles_and_settings_define_runtime_contract(self) -> None:
        styles = TOAST_SCSS.read_text(encoding="utf-8")
        settings = COMPONENT_SETTINGS.read_text(encoding="utf-8")
        primary = read_primary_variables()

        self.assertIn("toast-container--stacked[data-toast-stack=\"deck\"]", styles)
        self.assertIn(":has(> .toast[data-toast-stack-index])", styles)
        self.assertIn('width: unquote("min(24rem, calc(100vw - 2rem))");', styles)
        self.assertIn("height: 0;", styles)
        self.assertIn("padding: 0 !important;", styles)
        self.assertIn("position: absolute;", styles)
        self.assertIn("inset-inline-end: 0;", styles)
        self.assertIn("inset-block-end: 0;", styles)
        self.assertIn("max-width: none;", styles)
        self.assertIn("width: 100%;", styles)
        self.assertIn("margin-bottom: 0", styles)
        self.assertIn("--moo-toast-stack-collapsed-y", styles)
        self.assertIn("--moo-toast-stack-expanded-y", styles)
        self.assertIn("data-toast-stack-limited", styles)
        self.assertIn("opacity: 0", styles)
        self.assertIn("pointer-events: none", styles)
        self.assertIn("transform-origin: bottom center", styles)
        self.assertIn("focus-within", styles)
        self.assertIn("prefers-reduced-motion", styles)
        self.assertIn("$moo-toast-stack-gap", settings)
        self.assertIn("$moo-toast-stack-peek", settings)
        self.assertIn("$moo-toast-stack-scale-step", settings)
        self.assertIn("$moo-toast-stack-min-scale", settings)
        self.assertIn("$moo-toast-stack-transition-duration", settings)
        self.assertIn("$moo-toast-stack-gap", primary)
        self.assertIn("$moo-toast-stack-peek", primary)
        self.assertIn("$moo-toast-stack-scale-step", primary)
        self.assertIn("$moo-toast-stack-min-scale", primary)
        self.assertIn("$moo-toast-stack-transition-duration", primary)

    def test_catalog_stack_uses_live_reference_geometry_and_newest_dom_order(self) -> None:
        script = BOOTSTRAP_PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn('computed.getPropertyValue("--moo-toast-stack-gap")', script)
        self.assertIn('computed.getPropertyValue("--moo-toast-stack-peek")', script)
        self.assertIn('computed.getPropertyValue("--moo-toast-stack-min-scale")', script)
        self.assertIn("container.prepend(toast)", script)
        self.assertIn("toast.setAttribute(\"inert\", \"\")", script)
        self.assertIn("toast.removeAttribute(\"inert\")", script)
        self.assertIn("(1 - scale) * stackHeight", script)
