from __future__ import annotations

import hashlib

import tinycss2

from tests.helpers import DIST, ROOT, CatalogTestCase


ACCEPTED_INTERNAL_RENAMES = {
    "--scroll-fade-t": "--moo-scroll-fade-t",
    "--scroll-fade-b": "--moo-scroll-fade-b",
    "--scroll-fade-s": "--moo-scroll-fade-s",
    "--scroll-fade-e": "--moo-scroll-fade-e",
    "--scroll-fade-t-size": "--moo-scroll-fade-t-size",
    "--scroll-fade-b-size": "--moo-scroll-fade-b-size",
    "--scroll-fade-s-size": "--moo-scroll-fade-s-size",
    "--scroll-fade-e-size": "--moo-scroll-fade-e-size",
    "--scroll-fade-mask": "--moo-scroll-fade-mask",
    "scroll-fade-reveal-t": "moo-scroll-fade-reveal-t",
    "scroll-fade-reveal-b": "moo-scroll-fade-reveal-b",
    "scroll-fade-reveal-s": "moo-scroll-fade-reveal-s",
    "scroll-fade-reveal-e": "moo-scroll-fade-reveal-e",
}


def _rewrite_identifiers(values: list[object]) -> None:
    for token in values:
        if getattr(token, "type", None) == "ident":
            token.value = ACCEPTED_INTERNAL_RENAMES.get(token.value, token.value)
        if hasattr(token, "content") and token.content is not None:
            _rewrite_identifiers(token.content)
        if hasattr(token, "arguments") and token.arguments is not None:
            _rewrite_identifiers(token.arguments)
        if hasattr(token, "prelude") and token.prelude is not None:
            _rewrite_identifiers(token.prelude)


def normalize_standalone_css(css: str) -> str:
    normalized = css.replace("\r\n", "\n").replace("\r", "\n")
    rules = tinycss2.parse_stylesheet(
        normalized,
        skip_comments=False,
        skip_whitespace=False,
    )
    _rewrite_identifiers(rules)
    return tinycss2.serialize(rules).replace("\r\n", "\n").replace("\r", "\n")


class StyleEquivalenceTests(CatalogTestCase):
    def test_standalone_moo_ui_output_matches_accepted_baseline(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        digest = hashlib.sha256(
            normalize_standalone_css(css).encode("utf-8")
        ).hexdigest()
        baseline = (
            ROOT / "tests/fixtures/moo-ui-baseline.sha256"
        ).read_text(encoding="utf-8").strip()
        self.assertEqual(digest, baseline)
