from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/alert.html.jinja"
PAGE = ROOT / "src/pages/components/alert.html.jinja"


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

    def test_alert_rejects_unknown_variant(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown alert variant: warning"):
            self.render_alert('alert("Heads up!", variant="warning")')

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

    def test_alert_action_renders_trusted_markup(self) -> None:
        output = self.render_alert('alert("Heads up!", action="<button>Go</button>")')
        self.assertIn('<div class="alert-action"><button>Go</button></div>', output)
