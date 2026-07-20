from __future__ import annotations

import re

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/tooltip.html.jinja"
PAGE = ROOT / "src/pages/components/tooltip.html.jinja"

# Bootstrap's Tooltip runs data-bs-html content through its own default
# sanitizer allowlist before it ever reaches the page (see
# vendor/bootstrap/js/src/util/sanitizer.js -> DefaultAllowlist); tags not on
# it are removed outright, not merely unwrapped. `sanitize`/`allowList` are
# also in Bootstrap's DISALLOWED_ATTRIBUTES set, so they cannot be relaxed
# via data-bs-* attributes — only trusted, allowlisted markup survives.
BOOTSTRAP_DEFAULT_TOOLTIP_ALLOWLIST = {
    "a", "area", "b", "br", "col", "code", "dd", "div", "dl", "dt", "em",
    "hr", "h1", "h2", "h3", "h4", "h5", "h6", "i", "img", "li", "ol", "p",
    "pre", "s", "small", "span", "sub", "sup", "strong", "u", "ul",
}


class TooltipTests(CatalogTestCase):
    def render_tooltip(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Tooltip macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/tooltip.html.jinja" import tooltip_trigger %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_tooltip_trigger_uses_bootstrap_plugin_contract(self) -> None:
        output = self.render_tooltip(
            'tooltip_trigger("Hover over me", "Default tooltip")'
        )

        self.assertIn('data-bs-toggle="tooltip"', output)
        self.assertIn('data-bs-title="Default tooltip"', output)

    def test_tooltip_trigger_default_href_does_not_jump_to_page_top(self) -> None:
        # Regression test: href="#" is a real anchor navigation that browsers
        # special-case to scroll to the very top of the document, and
        # nothing here calls preventDefault() on the click. "#!" matches no
        # element, so it stays a real, focusable anchor without the jump.
        output = self.render_tooltip(
            'tooltip_trigger("Hover over me", "Default tooltip")'
        )

        self.assertIn('href="#!"', output)
        self.assertIn('data-bs-placement="top"', output)
        self.assertIn(">Hover over me</a>", output)
        self.assertNotIn("data-bs-html", output)

    def test_tooltip_trigger_placement_is_configurable(self) -> None:
        output = self.render_tooltip(
            'tooltip_trigger("Right", "Tooltip on right", placement="right")'
        )

        self.assertIn('data-bs-placement="right"', output)

    def test_tooltip_trigger_rejects_unknown_placement(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Unknown tooltip placement: huge"
        ):
            self.render_tooltip(
                'tooltip_trigger("Label", "Text", placement="huge")'
            )

    def test_tooltip_trigger_requires_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tooltip trigger label is required"):
            self.render_tooltip('tooltip_trigger("   ", "Text")')

    def test_tooltip_trigger_requires_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tooltip text is required"):
            self.render_tooltip('tooltip_trigger("Label", "   ")')

    def test_tooltip_trigger_html_opts_into_data_bs_html(self) -> None:
        output = self.render_tooltip(
            'tooltip_trigger("Tooltip with HTML", '
            '"<em>Tooltip</em> <u>with</u> <b>HTML</b>", html=true)'
        )

        self.assertIn("data-bs-html=\"true\"", output)
        # The attribute value is HTML-escaped (Jinja's normal attribute
        # escaping); browsers decode entities back to the literal markup
        # when Bootstrap reads the attribute via getAttribute(), so its own
        # sanitizer still receives the real <em> tag. Only the outer HTML
        # attribute stays well-formed regardless of content -- see
        # test_tooltip_trigger_html_content_cannot_break_out_of_the_attribute.
        self.assertIn("&lt;em&gt;Tooltip&lt;/em&gt;", output)
        self.assertNotIn('data-bs-title="<em>', output)

    def test_tooltip_trigger_html_content_cannot_break_out_of_the_attribute(
        self,
    ) -> None:
        # Regression test for a real attribute-injection bug: html=true
        # content used to be piped through |safe directly into
        # data-bs-title="...", which only suppresses Jinja's tag escaping,
        # not its quote escaping. A literal " in the content used to close
        # the attribute early and let anything after it become a new, live
        # HTML attribute, bypassing Bootstrap's own content sanitizer, which
        # never even runs on it.
        output = self.render_tooltip(
            "tooltip_trigger(\"Label\", 'safe <code>x</code> quote \" "
            "onclick=\"bad', html=true)"
        )

        self.assertEqual(output.count("data-bs-title="), 1)
        self.assertNotIn('onclick="bad"', output)
        self.assertIn("&#34;", output)

    def test_tooltip_trigger_escapes_plain_text_by_default(self) -> None:
        output = self.render_tooltip(
            'tooltip_trigger("Label", "<script>alert(1)</script>")'
        )

        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)

    def test_page_composes_tooltip_and_button_triggers(self) -> None:
        self.assertTrue(PAGE.is_file(), "Tooltip page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "components/tooltip.html.jinja" import tooltip_trigger %}',
            source,
        )
        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn("tooltip_trigger(", source)
        self.assertIn('tooltip_placement="right"', source)
        self.assertIn('tooltip_placement="bottom"', source)
        self.assertIn('tooltip_placement="left"', source)
        self.assertIn("tooltip_html=true", source)
        self.assertIn('data-bs-toggle="tooltip"', source)
        self.assertIn("disabled=true", source)
        self.assertIn('dir="rtl"', source)

    def test_page_mirrors_bootstraps_disabled_element_wrapper_guidance(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertRegex(
            source,
            r'<span[^>]*data-bs-toggle="tooltip"[^>]*>\s*{{\s*button\("Archive", variant="outline", disabled=true\)\s*}}',
        )

    def test_html_tooltip_examples_only_use_bootstraps_default_allowlisted_tags(
        self,
    ) -> None:
        # Regression coverage for a real bug caught before shipping: an
        # earlier draft put a <kbd> tag inside a tooltip_html=true tooltip.
        # Bootstrap's Tooltip sanitizes data-bs-html content through its own
        # default allowlist (kbd is not on it) and *removes* disallowed
        # elements entirely, so the shortcut text would have silently
        # vanished at runtime despite rendering fine in the static page
        # source. Every tag used inside an html=true / tooltip_html=true
        # value on this page must stay inside Bootstrap's default allowlist.
        source = PAGE.read_text(encoding="utf-8")

        html_true_calls = [
            call
            for call in re.findall(r"button\([^)]*\)", source)
            if "tooltip_html=true" in call
        ]
        self.assertTrue(html_true_calls, "expected at least one tooltip_html=true example")

        for call in html_true_calls:
            title_match = re.search(r'tooltip="([^"]*)"', call)
            self.assertIsNotNone(title_match, call)
            for tag in re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)[ >]", title_match.group(1)):
                self.assertIn(
                    tag.lower(),
                    BOOTSTRAP_DEFAULT_TOOLTIP_ALLOWLIST,
                    f"<{tag}> is not in Bootstrap's default Tooltip sanitizer "
                    "allowlist and would be silently stripped at runtime",
                )
