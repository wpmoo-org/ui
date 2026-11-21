from __future__ import annotations

import json
import re
import unittest

import build
from tests.helpers import ROOT

SCSS = ROOT / "scss"
PAGE = ROOT / "site/src/pages/utils/text-measure.html.jinja"


class TextMeasureTests(unittest.TestCase):
    def test_utility_reads_the_measure_knob(self) -> None:
        palette = (SCSS / "settings/_palette.scss").read_text(encoding="utf-8")
        self.assertIn("$moo-text-measure: 68ch !default;", palette)
        source = (SCSS / "utilities/_text_measure.scss").read_text(encoding="utf-8")
        self.assertIn("max-inline-size: #{$moo-text-measure};", source)

    def test_utility_is_scoped_to_a_moo_owner_in_both_builds(self) -> None:
        scope = (SCSS / "foundations/_scope.scss").read_text(encoding="utf-8")
        self.assertIn('@import "../utilities/text_measure";', scope)
        for entry in ("moo-ui.scss", "moo-core.scss"):
            css = build.sass.compile(
                filename=str(SCSS / entry),
                include_paths=[str(SCSS), str(build.BOOTSTRAP.parent)],
                output_style="expanded",
            )
            start = css.index("@scope (.moo-ui)")
            open_at = css.index("{", start)
            depth, end = 0, open_at
            for end in range(open_at, len(css)):
                depth += {"{": 1, "}": -1}.get(css[end], 0)
                if depth == 0:
                    break
            block, outside = css[open_at : end + 1], css[:open_at] + css[end + 1 :]
            self.assertRegex(block, r"\.text-measure \{\s*max-inline-size: 68ch;")
            self.assertNotIn(".text-measure", outside, entry)

    def test_utility_has_a_catalog_page_and_registry_entry(self) -> None:
        self.assertTrue(PAGE.is_file())
        utilities = json.loads(
            (ROOT / "site/src/registry/utilities.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            {"slug": "text-measure", "label": "Text Measure", "status": "ready"},
            utilities,
        )
        self.assertIn("text-measure", PAGE.read_text(encoding="utf-8"))

    def test_typography_page_shows_the_website_profile_attribute(self) -> None:
        page = (ROOT / "site/src/pages/components/typography.html.jinja").read_text(
            encoding="utf-8"
        )
        self.assertRegex(page, r'data-moo-typography="website"')
        self.assertIn('"website-profile"', page)


if __name__ == "__main__":
    unittest.main()
