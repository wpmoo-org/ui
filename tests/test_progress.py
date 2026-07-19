from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/progress.html.jinja"
PAGE = ROOT / "src/pages/components/progress.html.jinja"


class ProgressTests(CatalogTestCase):
    def render_progress(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Progress macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/progress.html.jinja" import progress %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_progress_renders_accessible_bar_with_computed_width(self) -> None:
        self.assertEqual(
            self.render_progress('progress(66, aria_label="Upload progress")'),
            '<div> <div class="progress" role="progressbar"'
            ' aria-label="Upload progress" aria-valuenow="66"'
            ' aria-valuemin="0" aria-valuemax="100" >'
            ' <div class="progress-bar" style="width: 66%"></div> </div> </div>',
        )

    def test_progress_computes_percent_against_custom_max(self) -> None:
        self.assertIn(
            'style="width: 50%"',
            self.render_progress('progress(25, max=50, aria_label="Half")'),
        )

    def test_progress_show_label_renders_name_and_percent_above_bar(self) -> None:
        output = self.render_progress(
            'progress(40, aria_label="Download progress", show_label=true)'
        )
        self.assertIn(
            '<div class="d-flex justify-content-between small mb-1">'
            " <span>Download progress</span>"
            ' <span class="text-body-secondary">40%</span> </div>',
            output,
        )
        # The label sits before the track in document order.
        self.assertLess(output.index("Download progress"), output.index('class="progress"'))

    def test_progress_requires_visible_aria_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Progress aria_label is required"):
            self.render_progress("progress(10, aria_label=\"   \")")

    def test_progress_rejects_value_outside_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "Progress value must be between 0 and max"):
            self.render_progress('progress(-1, aria_label="Invalid")')
        with self.assertRaisesRegex(ValueError, "Progress value must be between 0 and max"):
            self.render_progress('progress(150, aria_label="Invalid")')

    def test_progress_rejects_non_positive_max(self) -> None:
        with self.assertRaisesRegex(ValueError, "Progress max must be positive"):
            self.render_progress('progress(0, max=0, aria_label="Invalid")')
        with self.assertRaisesRegex(ValueError, "Progress max must be positive"):
            self.render_progress('progress(0, max=-10, aria_label="Invalid")')
