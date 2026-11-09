from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


class VideoDialogTests(CatalogTestCase):
    def render(self, call: str) -> str:
        template = create_environment().from_string(
            '{% from "blocks/video_dialog.html.jinja" import video_dialog, video_play %}'
            + call
        )
        return " ".join(template.render().split())

    def test_round_trigger_composes_button_ring_and_motion(self) -> None:
        output = self.render('{{ video_play("film", aria_label="Watch <the> film") }}')
        self.assertIn(
            'class="d-inline-flex rounded-circle p-3 bg-white bg-opacity-25 animate-breathe"',
            output,
        )
        self.assertIn(
            'class="btn btn-light btn-lg rounded-circle p-4 shadow text-primary"',
            output,
        )
        self.assertIn('data-bs-toggle="modal" data-bs-target="#film"', output)
        self.assertIn('aria-label="Watch &lt;the&gt; film"', output)
        self.assertIn('fill="currentColor" stroke="none"', output)
        self.assertIn('width="2em" height="2em"', output)
        self.assertNotIn("data-icon", output)

    def test_labelled_trigger_is_a_pill_with_a_breathing_circle(self) -> None:
        output = self.render(
            '{{ video_play("film", label="Film ansehen", icon_class="text-danger", extra_class="mt-3") }}'
        )
        self.assertIn(
            "btn rounded-pill d-inline-flex align-items-center gap-3 p-0 pe-4 "
            "border-0 bg-white bg-opacity-25 text-white fw-semibold mt-3",
            output,
        )
        self.assertIn(
            'class="d-inline-flex rounded-circle bg-white p-3 shadow animate-breathe text-danger"',
            output,
        )
        self.assertIn("Film ansehen </button>", output)
        self.assertNotIn("aria-label", output)

    def test_trigger_requires_an_accessible_name_and_a_target(self) -> None:
        for call in ('{{ video_play("film") }}', '{{ video_play("", aria_label="Film") }}'):
            with self.subTest(call=call):
                with self.assertRaises(Exception):
                    self.render(call)

    def test_dialog_defers_the_video_until_it_opens(self) -> None:
        output = self.render(
            '{{ video_dialog("film", "Our film", "https://www.youtube-nocookie.com/embed/M7lc1UVf-VE") }}'
        )
        self.assertIn('class="modal fade"', output)
        self.assertIn('id="film"', output)
        self.assertIn("modal-dialog modal-xl modal-dialog-centered", output)
        self.assertIn('<h1 class="modal-title" id="film-title">Our film</h1>', output)
        self.assertIn('class="modal-body p-0"', output)
        self.assertIn('class="ratio ratio-16x9"', output)
        self.assertIn(
            'data-video-src="https://www.youtube-nocookie.com/embed/M7lc1UVf-VE"',
            output,
        )
        self.assertNotIn(" src=", output)
        self.assertIn('referrerpolicy="strict-origin-when-cross-origin"', output)
        with self.assertRaises(Exception):
            self.render('{{ video_dialog("film", "Our film", "") }}')

    def test_motion_utility_respects_reduced_motion(self) -> None:
        motion = (ROOT / "scss/utilities/_motion.scss").read_text(encoding="utf-8")
        primitives = (ROOT / "scss/utilities/_motion_primitives.scss").read_text(
            encoding="utf-8"
        )
        self.assertIn("@media (prefers-reduced-motion: no-preference)", motion)
        self.assertIn(".animate-breathe", motion)
        self.assertIn("animation: moo-breathe 2s ease-in-out infinite;", motion)
        self.assertIn("@keyframes moo-breathe", primitives)
