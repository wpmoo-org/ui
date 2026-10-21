from __future__ import annotations

import unittest

from tests.helpers.css_contract import (
    assert_allowed_global_rules,
    assert_owner_scoped_token_bridges,
    assert_safe_assets,
)


class CssAssetContractTests(unittest.TestCase):
    def test_only_the_exact_opt_in_native_scrollbar_bridge_is_global(self) -> None:
        css = """
        html.scrollbar-overlay-native { scrollbar-width: none; }
        html.scrollbar-overlay-native::-webkit-scrollbar { display: none; }
        @media print, (forced-colors: active) {
            html.scrollbar-overlay-native { scrollbar-width: auto !important; }
            html.scrollbar-overlay-native::-webkit-scrollbar { display: revert !important; }
        }
        """
        assert_allowed_global_rules(self, css)
        assert_owner_scoped_token_bridges(self, css, scoped=True)

    def test_native_bridge_cannot_expand_into_document_theme_or_layout_rules(self) -> None:
        for css in (
            "html { scrollbar-width: none; }",
            "body.scrollbar-overlay-native { scrollbar-width: none; }",
            "html.scrollbar-overlay-native { color: red; }",
            "html.scrollbar-overlay-native { --bs-body-bg: red; }",
            "html.scrollbar-overlay-native { scrollbar-width: none; width: 10px; }",
            "html.scrollbar-overlay-native { scrollbar-width: none !important; }",
            "html.scrollbar-overlay-native { scrollbar-width: auto !important; }",
            "html.scrollbar-overlay-native, body { scrollbar-width: none; }",
            "@scope (html) { html.scrollbar-overlay-native { scrollbar-width: auto !important; } }",
            "@scope (.moo-ui) { html.scrollbar-overlay-native { scrollbar-width: none; } }",
        ):
            with self.subTest(css=css):
                for check in (assert_allowed_global_rules, lambda case, value: assert_owner_scoped_token_bridges(case, value, scoped=True)):
                    with self.assertRaises(AssertionError):
                        check(self, css)

    def test_native_fallback_is_limited_to_print_and_forced_colors(self) -> None:
        for css in (
            "@media screen { html.scrollbar-overlay-native { scrollbar-width: none; } }",
            "@media print, (forced-colors: active) { html.scrollbar-overlay-native { scrollbar-width: none; } }",
            "@media print, (forced-colors: active) { html.scrollbar-overlay-native { color: red; } html.scrollbar-overlay-native::-webkit-scrollbar { display: revert !important; } }",
        ):
            with self.subTest(css=css):
                with self.assertRaises(AssertionError):
                    assert_allowed_global_rules(self, css)

    def test_license_and_nested_comment_urls_are_not_assets(self) -> None:
        assert_safe_assets(
            self,
            "/*! Licensed under MIT (https://example.test/LICENSE) */\n"
            ".sample { /* url(https://example.test/note) */ color: red; }",
        )

    def test_real_asset_urls_remain_forbidden(self) -> None:
        for css in (
            '.sample { background: url("https://example.test/image.png"); }',
            '.sample { background: url("../image.png"); }',
            '@import "https://example.test/styles.css";',
            "/* url(https://example.test/note) */\n"
            '.sample { background: url("https://example.test/image.png"); }',
        ):
            with self.subTest(css=css):
                with self.assertRaises(AssertionError):
                    assert_safe_assets(self, css)

    def test_embedded_svg_remains_allowed(self) -> None:
        assert_safe_assets(
            self,
            '.sample { background: url("data:image/svg+xml,'
            '%3Csvg xmlns=\'http://www.w3.org/2000/svg\'%3E%3C/svg%3E"); }',
        )
