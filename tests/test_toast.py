from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase, read_primary_variables


COMPONENT = ROOT / "src/components/toast.html.jinja"
PAGE = ROOT / "site/src/pages/components/toast.html.jinja"
BOOTSTRAP_PREVIEW_JS = ROOT / "site/src/js/catalog/bootstrap-preview.js"
TOAST_SCSS = ROOT / "scss/components/_toast.scss"
COMPONENT_SETTINGS = ROOT / "scss/settings/_components.scss"
PRIMARY_VARIABLES = ROOT / "scss/_primary_variables.scss"
FIXTURE = ROOT / "tests/fixtures/certification/toast.html"


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

    def test_toast_supports_status_variants_with_icons(self) -> None:
        expected_icons = {
            "success": "circle-check",
            "info": "info",
            "warning": "triangle-alert",
            "destructive": "circle-alert",
            "loading": "loader-circle",
        }
        for variant, icon in expected_icons.items():
            with self.subTest(variant=variant):
                output = self.render(
                    f'{{{{ toast("toast-{variant}", "Title", "Body", variant="{variant}") }}}}'
                )

                self.assertIn(f'data-toast-variant="{variant}"', output)
                self.assertIn('<span class="toast-status-icon" aria-hidden="true">', output)
                self.assertIn(f'data-lucide="{icon}"', output)
                self.assertIn('data-icon="inline-start"', output)

    def test_toast_accepts_error_and_odoo_danger_as_destructive_variant_aliases(self) -> None:
        for alias in ("error", "danger"):
            with self.subTest(alias=alias):
                output = self.render(
                    f'{{{{ toast("toast-{alias}", "Sync failed", "Try again.", variant="{alias}") }}}}'
                )

                self.assertIn('data-toast-variant="destructive"', output)
                self.assertIn('data-lucide="circle-alert"', output)
                self.assertNotIn(f'data-toast-variant="{alias}"', output)

    def test_toast_requires_id_title_body_and_known_priority_and_variant(self) -> None:
        with self.assertRaisesRegex(ValueError, "Toast id is required"):
            self.render('{{ toast("   ", "Title", "Body") }}')
        with self.assertRaisesRegex(ValueError, "Toast title is required"):
            self.render('{{ toast("id", "   ", "Body") }}')
        with self.assertRaisesRegex(ValueError, "Toast body is required"):
            self.render('{{ toast("id", "Title", "   ") }}')
        with self.assertRaisesRegex(ValueError, "Unknown toast priority: loud"):
            self.render('{{ toast("id", "Title", "Body", priority="loud") }}')
        with self.assertRaisesRegex(ValueError, "Unknown toast variant: urgent"):
            self.render('{{ toast("id", "Title", "Body", variant="urgent") }}')

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

    def test_toast_template_forwards_status_variant(self) -> None:
        output = self.render(
            '{% from "components/toast.html.jinja" import toast_template %}'
            '{{ toast_template("toast-template", "Event created", "Saved.", variant="success") }}'
        )

        self.assertIn('data-toast-variant="success"', output)
        self.assertIn('data-lucide="circle-check"', output)

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

    def test_page_composes_repeated_trigger_template_decks(self) -> None:
        self.assertTrue(PAGE.is_file(), "Toast page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn(
            '{% from "components/toast.html.jinja" import toast, toast_container, toast_template %}',
            source,
        )
        self.assertIn('toast_target="toast-demo-template"', source)
        self.assertIn('stacked=true', source)
        self.assertIn('action_label="Undo"', source)
        self.assertEqual(source.count('toast_target="toast-demo-template"'), 1)
        self.assertEqual(source.count('stacked=true'), 3)
        self.assertNotIn("toast-stack-", source)

    def test_page_documents_basic_default_toast_and_standard_status_variants(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "includes/example.html.jinja" import render_component_intro, render_component_example with context %}',
            source,
        )
        self.assertIn('render_component_example("toast", "Toast",', source)
        self.assertIn('"basic"', source)
        self.assertIn('"Basic"', source)
        self.assertIn('toast_target="toast-basic-template"', source)
        self.assertIn('"toast-basic-template"', source)
        self.assertIn("Use <code>.toast</code>", source)
        self.assertIn("<code>.toast-header</code>", source)
        self.assertIn("<code>.toast-body</code>", source)
        self.assertNotIn("Use the default Toast without <code>data-toast-variant</code>", source)
        basic_start = source.index('{% set basic %}')
        basic_end = source.index('{% set basic_source %}')
        basic_example = source[basic_start:basic_end]
        self.assertIn(
            'toast_container(placement="bottom-end", stacked=true)',
            basic_example,
        )
        basic_source_start = source.index('{% set basic_source %}')
        basic_source_end = source.index(
            '{{ render_component_example("toast", "Toast",\n      "basic"',
            basic_source_start,
        )
        basic_source = source[basic_source_start:basic_source_end]
        self.assertIn('{{ toast(', basic_source)
        self.assertNotIn("<button", basic_source)
        self.assertNotIn('class="toast', basic_source)
        self.assertIn('"variants"', source)
        self.assertIn('"Variants"', source)
        variants_render_start = source.index(
            '{{ render_component_example("toast", "Toast",\n      "variants"'
        )
        variants_render_end = source.index("source_content=variants_source", variants_render_start)
        variants_render = source[variants_render_start:variants_render_end]
        self.assertIn('preview_class="moo-example__preview--medium"', variants_render)
        self.assertNotIn('preview_class="moo-example__preview--narrow"', variants_render)
        variants_start = source.index('{% set variants %}')
        variants_end = source.index('{% set variants_source %}')
        variants_example = source[variants_start:variants_end]
        self.assertIn(
            'toast_container(placement="bottom-end", stacked=true)',
            variants_example,
        )
        self.assertNotIn('"types"', source)
        self.assertNotIn('"Types"', source)
        for variant in ("success", "info", "warning", "destructive", "loading"):
            with self.subTest(variant=variant):
                self.assertIn(f'toast_target="toast-variant-{variant}-template"', source)
                self.assertIn(f'"toast-variant-{variant}-template"', source)
        self.assertIn('variant="success"', source)
        self.assertIn('variant="info"', source)
        self.assertIn('variant="warning"', source)
        self.assertIn('variant="destructive"', source)
        self.assertIn('variant="loading"', source)
        self.assertNotIn('toast-variant-error-template', source)
        variants_source_start = source.index('{% set variants_source %}')
        variants_source_end = source.index(
            '{{ render_component_example("toast", "Toast",\n      "variants"',
            variants_source_start,
        )
        variants_source = source[variants_source_start:variants_source_end]
        self.assertIn('{{ toast(', variants_source)
        self.assertNotIn("<button", variants_source)
        self.assertNotIn('class="toast', variants_source)

    def test_basic_example_source_panel_documents_default_html_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/toast.html")
        code_marker = 'id="basic-code"'
        code_start = page.index(code_marker)
        pre_start = page.rfind("<pre", 0, code_start)
        pre_end = page.index("</pre>", code_start)
        basic_code = page[pre_start:pre_end]

        self.assertIn("toast", basic_code)
        self.assertIn("role", basic_code)
        self.assertIn("aria-live", basic_code)
        self.assertNotIn("data-toast-variant", basic_code)
        self.assertNotIn("data-toast-target", basic_code)
        self.assertIn('data-toast-target="#toast-basic-template"', page)

    def test_variants_example_source_panel_documents_variant_html_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/toast.html")
        code_marker = 'id="variants-code"'
        code_start = page.index(code_marker)
        pre_start = page.rfind("<pre", 0, code_start)
        pre_end = page.index("</pre>", code_start)
        variants_code = page[pre_start:pre_end]

        self.assertIn("data-toast-variant", variants_code)
        self.assertIn("success", variants_code)
        self.assertIn("info", variants_code)
        self.assertIn("warning", variants_code)
        self.assertIn("destructive", variants_code)
        self.assertIn("loading", variants_code)
        self.assertIn("role", variants_code)
        self.assertIn("aria-live", variants_code)
        self.assertIn("toast-status-icon", variants_code)
        self.assertNotIn("toast_template(", variants_code)
        self.assertNotIn("variant=&quot;success&quot;", variants_code)
        self.assertNotIn("data-toast-target", variants_code)
        self.assertIn('data-toast-target="#toast-variant-success-template"', page)
        self.assertIn('data-toast-variant="success"', page)
        self.assertIn('data-toast-variant="loading"', page)

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
        self.assertIn("sharedToastStacks", script)
        self.assertIn("container.dataset.mooCatalogToastStack = \"shared\"", script)
        self.assertIn("root.body.appendChild(container)", script)
        self.assertIn("data-toast-stack-active", script)
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
        self.assertIn("[data-toast-stack-active]", styles)
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
        self.assertIn("data-toast-stack-entering", styles)
        self.assertIn("data-toast-stack-hovering", styles)
        self.assertIn(
            "var(--moo-toast-stack-enter-y, 150%)",
            styles,
        )
        self.assertIn("opacity: 0", styles)
        self.assertIn("pointer-events: none", styles)
        self.assertIn("transform-origin: bottom center", styles)
        self.assertIn("$moo-toast-stack-transition-timing-function", styles)
        self.assertIn("height $moo-toast-stack-height-transition-duration ease", styles)
        self.assertIn("focus-within", styles)
        self.assertIn("prefers-reduced-motion", styles)
        self.assertIn("toast-status-icon", styles)
        self.assertIn('[data-toast-variant="success"]', styles)
        self.assertIn('[data-toast-variant="info"]', styles)
        self.assertIn('[data-toast-variant="warning"]', styles)
        self.assertIn('[data-toast-variant="destructive"]', styles)
        self.assertIn('[data-toast-variant="loading"]', styles)
        self.assertIn('.toast[data-toast-variant="loading"] .toast-status-icon [data-icon]', styles)
        self.assertIn("animation: none", styles)
        self.assertIn("$moo-toast-status-icon-size", styles)
        self.assertIn("$moo-toast-status-icon-gap", styles)
        self.assertIn("$moo-toast-status-icon-size", settings)
        self.assertIn("$moo-toast-status-icon-gap", settings)
        self.assertIn("$moo-toast-stack-gap", settings)
        self.assertIn("$moo-toast-stack-peek", settings)
        self.assertIn("$moo-toast-stack-scale-step", settings)
        self.assertIn("$moo-toast-stack-min-scale", settings)
        self.assertIn("$moo-toast-stack-enter-y", settings)
        self.assertIn("$moo-toast-stack-transition-duration", settings)
        self.assertIn("$moo-toast-stack-height-transition-duration", settings)
        self.assertIn("$moo-toast-stack-transition-timing-function", settings)
        self.assertIn("cubic-bezier(.22, 1, .36, 1)", settings)
        self.assertIn("$moo-toast-stack-gap", primary)
        self.assertIn("$moo-toast-stack-peek", primary)
        self.assertIn("$moo-toast-stack-scale-step", primary)
        self.assertIn("$moo-toast-stack-min-scale", primary)
        self.assertIn("$moo-toast-stack-enter-y", primary)
        self.assertIn("$moo-toast-stack-transition-duration", primary)
        self.assertIn("$moo-toast-stack-height-transition-duration", primary)
        self.assertIn("$moo-toast-stack-transition-timing-function", primary)

    def test_catalog_stack_uses_live_reference_geometry_and_newest_dom_order(self) -> None:
        script = BOOTSTRAP_PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn('computed.getPropertyValue("--moo-toast-stack-gap")', script)
        self.assertIn('computed.getPropertyValue("--moo-toast-stack-peek")', script)
        self.assertIn('computed.getPropertyValue("--moo-toast-stack-min-scale")', script)
        self.assertIn("container.prepend(toast)", script)
        self.assertIn("data-toast-stack-entering", script)
        self.assertIn("requestAnimationFrame", script)
        self.assertIn("Toast.getOrCreateInstance(toast, { animation: false })", script)
        self.assertIn("toast.setAttribute(\"inert\", \"\")", script)
        self.assertIn("toast.removeAttribute(\"inert\")", script)
        self.assertIn("data-toast-stack-hovering", script)
        self.assertIn("isPointerInsideToastStack", script)
        self.assertIn('listen(root, "pointerover"', script)
        self.assertIn('listen(root, "pointermove"', script)
        self.assertIn('container.setAttribute("data-toast-stack-hovering", "")', script)
        self.assertIn('container.removeAttribute("data-toast-stack-hovering")', script)
        self.assertIn("1000 - index", script)
        self.assertIn("(1 - scale) * stackHeight", script)

    def test_certification_fixture_matches_current_stacked_deck_contract(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")

        self.assertIn('data-toast-target="#certification-toast-template"', source)
        self.assertIn(
            'class="toast-container toast-container--stacked position-fixed bottom-0 end-0 p-3"',
            source,
        )
        self.assertIn('data-toast-stack="deck"', source)
        self.assertIn('<template id="certification-toast-template" data-toast-template="toast">', source)
        self.assertIn('id="certification-toast-template"', source)
        self.assertIn(
            'import { initBootstrapPreview } from "/assets/js/catalog/bootstrap-preview.js";',
            source,
        )
        self.assertIn("initBootstrapPreview(document)", source)
        self.assertNotIn("bootstrapPreviewPaths", source)
        self.assertNotIn("position-fixed top-0 end-0", source)
        self.assertNotIn("window.certificationToast", source)
