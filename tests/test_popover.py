from __future__ import annotations

import re

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/popover.html.jinja"
PAGE = ROOT / "src/pages/components/popover.html.jinja"

# Bootstrap's Popover shares Tooltip's sanitizer contract: data-bs-html
# content is run through the same default allowlist (see
# vendor/bootstrap/js/src/util/sanitizer.js -> DefaultAllowlist) before it
# ever reaches the page, and disallowed elements are removed outright.
# sanitize/allowList/sanitizeFn cannot be relaxed via data-bs-* attributes.
BOOTSTRAP_DEFAULT_TOOLTIP_ALLOWLIST = {
    "a", "area", "b", "br", "col", "code", "dd", "div", "dl", "dt", "em",
    "hr", "h1", "h2", "h3", "h4", "h5", "h6", "i", "img", "li", "ol", "p",
    "pre", "s", "small", "span", "sub", "sup", "strong", "u", "ul",
}


class PopoverTests(CatalogTestCase):
    def render_popover(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Popover macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/popover.html.jinja" import popover_dismiss_trigger %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_popover_dismiss_trigger_uses_bootstrap_plugin_contract(self) -> None:
        output = self.render_popover(
            'popover_dismiss_trigger("Dismissible popover", "Some content.", title="Dismissible")'
        )

        self.assertIn('data-bs-toggle="popover"', output)
        self.assertIn('data-bs-trigger="focus"', output)
        self.assertIn('data-bs-title="Dismissible"', output)
        self.assertIn('data-bs-content="Some content."', output)
        self.assertIn('data-bs-placement="top"', output)
        self.assertIn('tabindex="0"', output)
        self.assertIn('role="button"', output)
        self.assertIn(">Dismissible popover</a>", output)
        self.assertNotIn("data-bs-html", output)

    def test_popover_dismiss_trigger_default_href_does_not_jump_to_page_top(
        self,
    ) -> None:
        # Regression test: href="#" is a real anchor navigation that browsers
        # special-case to scroll to the very top of the document, and
        # nothing here calls preventDefault() on the click. "#!" matches no
        # element, so it stays a real, focusable anchor without the jump.
        output = self.render_popover(
            'popover_dismiss_trigger("Dismissible popover", "Some content.")'
        )

        self.assertIn('href="#!"', output)

    def test_popover_dismiss_trigger_title_is_optional(self) -> None:
        output = self.render_popover(
            'popover_dismiss_trigger("Label", "Content only.")'
        )

        self.assertNotIn("data-bs-title", output)

    def test_popover_dismiss_trigger_placement_is_configurable(self) -> None:
        output = self.render_popover(
            'popover_dismiss_trigger("Label", "Content.", placement="left")'
        )

        self.assertIn('data-bs-placement="left"', output)

    def test_popover_dismiss_trigger_rejects_unknown_placement(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown popover placement: huge"):
            self.render_popover(
                'popover_dismiss_trigger("Label", "Content.", placement="huge")'
            )

    def test_popover_dismiss_trigger_requires_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Popover trigger label is required"):
            self.render_popover('popover_dismiss_trigger("   ", "Content.")')

    def test_popover_dismiss_trigger_requires_content(self) -> None:
        with self.assertRaisesRegex(ValueError, "Popover content is required"):
            self.render_popover('popover_dismiss_trigger("Label", "   ")')

    def test_popover_dismiss_trigger_html_opts_into_data_bs_html(self) -> None:
        output = self.render_popover(
            'popover_dismiss_trigger("Label", "See <code>docs</code>.", html=true)'
        )

        self.assertIn('data-bs-html="true"', output)
        # The attribute value is HTML-escaped (Jinja's normal attribute
        # escaping); browsers decode entities back to the literal markup
        # when Bootstrap reads the attribute via getAttribute(), so its own
        # sanitizer still receives the real <code> tag. Only the outer HTML
        # attribute stays well-formed regardless of content -- see
        # test_popover_dismiss_trigger_html_content_cannot_break_out_of_the_attribute.
        self.assertIn("data-bs-content=\"See &lt;code&gt;docs&lt;/code&gt;.\"", output)
        self.assertNotIn('data-bs-content="See <code>', output)

    def test_popover_dismiss_trigger_html_content_cannot_break_out_of_the_attribute(
        self,
    ) -> None:
        # Regression test for a real attribute-injection bug: html=true
        # content used to be piped through |safe directly into
        # data-bs-content="...", which only suppresses Jinja's tag escaping,
        # not its quote escaping. A literal " in the content used to close
        # the attribute early and let anything after it become a new, live
        # HTML attribute, bypassing Bootstrap's own content sanitizer, which
        # never even runs on it.
        output = self.render_popover(
            "popover_dismiss_trigger(\"Label\", 'safe <code>x</code> quote \" "
            "onclick=\"bad', html=true)"
        )

        self.assertEqual(output.count("data-bs-content="), 1)
        self.assertNotIn('onclick="bad"', output)
        self.assertIn("&#34;", output)

    def test_popover_dismiss_trigger_escapes_plain_text_by_default(self) -> None:
        output = self.render_popover(
            'popover_dismiss_trigger("Label", "<script>alert(1)</script>")'
        )

        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)

    def test_page_composes_popover_and_button_triggers(self) -> None:
        self.assertTrue(PAGE.is_file(), "Popover page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/button.html.jinja" import button %}', source)
        self.assertIn(
            '{% from "components/popover.html.jinja" import popover_dismiss_trigger %}',
            source,
        )
        self.assertIn("popover_content=", source)
        self.assertIn('popover_placement="right"', source)
        self.assertIn('popover_placement="bottom"', source)
        self.assertIn('popover_placement="left"', source)
        self.assertIn("popover_html=true", source)
        self.assertIn("popover_dismiss_trigger(", source)
        self.assertIn('data-bs-trigger="hover focus"', source)
        self.assertIn("disabled=true", source)
        self.assertIn('dir="rtl"', source)

    def test_page_mirrors_bootstraps_disabled_element_wrapper_guidance(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertRegex(
            source,
            r'<span[^>]*data-bs-toggle="popover"[^>]*>\s*{{\s*button\("Archive", variant="outline", disabled=true\)\s*}}',
        )

    def test_html_popover_examples_only_use_bootstraps_default_allowlisted_tags(
        self,
    ) -> None:
        # Regression coverage mirroring Tooltip's sanitizer test: any
        # popover_html=true content must stay within Bootstrap's default
        # sanitizer allowlist, or it is silently stripped at runtime despite
        # looking correct in the static page source.
        source = PAGE.read_text(encoding="utf-8")

        html_true_calls = [
            call
            for call in re.findall(r"button\([^)]*\)", source)
            if "popover_html=true" in call
        ]
        self.assertTrue(html_true_calls, "expected at least one popover_html=true example")

        for call in html_true_calls:
            content_match = re.search(r'popover_content="([^"]*)"', call)
            self.assertIsNotNone(content_match, call)
            for tag in re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)[ >]", content_match.group(1)):
                self.assertIn(
                    tag.lower(),
                    BOOTSTRAP_DEFAULT_TOOLTIP_ALLOWLIST,
                    f"<{tag}> is not in Bootstrap's default Popover sanitizer "
                    "allowlist and would be silently stripped at runtime",
                )

    def test_html_popover_examples_do_not_embed_interactive_controls(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        html_true_calls = [
            call
            for call in re.findall(r"button\([^)]*\)", source)
            if "popover_html=true" in call
        ]
        self.assertTrue(html_true_calls)
        for call in html_true_calls:
            self.assertNotRegex(
                call,
                r"<(?:a|button|input|select|textarea)\b",
                "Bootstrap Popover is not a focus-managed dialog; interactive "
                "content belongs in Dialog",
            )
