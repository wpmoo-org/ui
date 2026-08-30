from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/alert.html.jinja"
PAGE = ROOT / "site/src/pages/components/alert.html.jinja"


class AlertTests(CatalogTestCase):
    def render_alert(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Alert macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/alert.html.jinja" import alert %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_alert_renders_title_and_description(self) -> None:
        self.assertEqual(
            self.render_alert('alert("Heads up!")'),
            '<div class="alert" role="alert"> <div class="alert-body">'
            ' <div class="alert-heading">Heads up!</div> </div> </div>',
        )
        self.assertEqual(
            self.render_alert('alert("Heads up!", description="Body text.")'),
            '<div class="alert" role="alert"> <div class="alert-body">'
            ' <div class="alert-heading">Heads up!</div>'
            ' <p class="mb-0">Body text.</p> </div> </div>',
        )

    def test_alert_destructive_variant_maps_to_bootstrap_danger(self) -> None:
        self.assertIn('class="alert alert-danger"', self.render_alert('alert("Payment failed", variant="destructive")'))

    def test_alert_semantic_variants_map_to_bootstrap_contexts(self) -> None:
        for variant, expected_class in (
            ("warning", "alert-warning"),
            ("success", "alert-success"),
            ("info", "alert-info"),
        ):
            with self.subTest(variant=variant):
                self.assertIn(
                    f'class="alert {expected_class}"',
                    self.render_alert(f'alert("Heads up!", variant="{variant}")'),
                )

    def test_alert_rejects_unknown_variant(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown alert variant: urgent"):
            self.render_alert('alert("Heads up!", variant="urgent")')

    def test_alert_requires_visible_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "Alert title is required"):
            self.render_alert('alert("   ")')

    def test_alert_icon_renders_inside_hidden_wrapper(self) -> None:
        output = self.render_alert('alert("Heads up!", icon="info")')
        self.assertIn('<span class="alert-icon" aria-hidden="true">', output)
        self.assertIn('data-icon="inline-start"', output)

    def test_alert_dismissible_composes_close_button(self) -> None:
        output = self.render_alert('alert("Heads up!", dismissible=true)')
        self.assertIn('class="alert alert-dismissible fade show"', output)
        self.assertIn(
            '<button type="button" class="btn-close" aria-label="Close"'
            ' data-bs-dismiss="alert"></button>',
            output,
        )

    def test_alert_dismissible_reserves_tokenized_close_button_space(self) -> None:
        source = (ROOT / "scss/components/_alert.scss").read_text(encoding="utf-8")

        self.assertIn(
            "$moo-alert-dismissible-close-space: "
            "$btn-close-width + ($btn-close-padding-x * 2) + 0.5rem !default;",
            source,
        )
        self.assertIn(
            "padding-inline-end: calc(var(--bs-alert-padding-x) + "
            "#{$moo-alert-dismissible-close-space});",
            source,
        )
        self.assertIn("inset-block-start: 50%;", source)
        self.assertIn("transform: translateY(-50%);", source)

    def test_alert_action_renders_trusted_markup(self) -> None:
        output = self.render_alert('alert("Heads up!", action="<button>Go</button>")')
        self.assertIn('<div class="alert-action"><button>Go</button></div>', output)

    def test_rtl_tabbed_examples_use_medium_preview_width(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn("render_rtl_example", source)
        self.assertIn('"alert"', source)
        # RTL examples use --medium to match other examples
        self.assertIn('preview_class="moo-example__preview--medium"', source)
        self.assertNotIn(
            'preview_class="moo-example__preview--fit"',
            source,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/alert.html")
        self.assertIn("alert-direction-tabs", page)
        self.assertIn("rtl-arabic-code", page)
