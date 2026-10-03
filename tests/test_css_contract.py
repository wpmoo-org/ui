from __future__ import annotations

import unittest

from tests.helpers.css_contract import assert_safe_assets


class CssAssetContractTests(unittest.TestCase):
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
