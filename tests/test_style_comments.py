from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import tinycss2

import build


def comments_in(css: str) -> list[str]:
    comments = []

    def visit(tokens):
        for token in tokens:
            if token.type == "comment":
                comments.append(token.value)
            visit(getattr(token, "content", ()))
            visit(getattr(token, "arguments", ()))

    visit(tinycss2.parse_component_value_list(css))
    return comments


class StyleCommentTests(unittest.TestCase):
    def test_scss_cleaning_preserves_strings_urls_blocks_and_interpolation(self) -> None:
        from scripts.style_comments import strip_scss_line_comments

        cases = (
            ("// Private note\n$x: 1; // Inline note\n", "$x: 1;\n"),
            ("/// Documentation\n$x: 1; // At EOF", "$x: 1;"),
            ("/* Public // note */\n$x: 1;", "/* Public // note */\n$x: 1;"),
            ('content: "a\\\" // b"; // note\n', 'content: "a\\\" // b";\n'),
            ('content: "#{"// string"}"; // note\n', 'content: "#{"// string"}";\n'),
            ('content: "#{1 + // note\n 2}";', 'content: "#{1 +\n 2}";'),
            ('background: url(https://example.org/a//b); // note\n', 'background: url(https://example.org/a//b);\n'),
            ('background: url(//example.org/a); // note\n', 'background: url(//example.org/a);\n'),
            ('background: url("data:image/svg+xml,<svg>//</svg>");', 'background: url("data:image/svg+xml,<svg>//</svg>");'),
            ('background: url(https://example.org/#{"//path"});', 'background: url(https://example.org/#{"//path"});'),
            ('background: url($image // note\n);', 'background: url($image\n);'),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(strip_scss_line_comments(source), expected)

    def test_compressed_core_css_contains_license_notices_only(self) -> None:
        for name in ("moo-ui.scss", "moo-core.scss"):
            with self.subTest(entrypoint=name):
                comments = comments_in(build.compile_style(build.SCSS / name, output_style="compressed"))
                self.assertEqual(len(comments), 1)
                self.assertTrue(comments[0].startswith("!"))
                self.assertIn("Copyright 2026 WPMoo Authors", comments[0])
                self.assertIn("Copyright 2011-2024 The Bootstrap Authors", comments[0])
                self.assertIn("Moo UI", comments[0])
                self.assertIn("Bootstrap v5.3.3", comments[0])

    def test_css_entrypoints_start_with_moo_and_bootstrap_licenses(self) -> None:
        version = json.loads((build.ROOT / "package.json").read_text())["version"]
        for name in ("moo-ui.scss", "moo-core.scss"):
            for style in ("expanded", "compressed"):
                with self.subTest(entrypoint=name, style=style):
                    css = build.compile_style(build.SCSS / name, output_style=style)
                    self.assertTrue(css.startswith(
                        f"/*!\n * Moo UI v{version} (https://wpmoo.org/)\n"
                        " * Copyright 2026 WPMoo Authors\n"
                    ))
                    end = css.index("*/") + 2
                    banner = css[:end]
                    self.assertIn("\n *\n * Bootstrap v5.3.3", banner)
                    self.assertIn(
                        "Licensed under MIT (https://github.com/wpmoo-org/ui/blob/main/LICENSE)",
                        banner,
                    )
                    self.assertIn(
                        "Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)",
                        banner,
                    )
                    self.assertLess(banner.index("Moo UI"), banner.index("Bootstrap"))
                    if style == "compressed":
                        body = css[end:]
                        self.assertTrue(body.startswith("\n\n"))
                        self.assertEqual(len(body.strip().splitlines()), 1)

    def test_expanded_core_css_has_readable_sections(self) -> None:
        for name in ("moo-ui.scss", "moo-core.scss"):
            with self.subTest(entrypoint=name):
                comments = comments_in(build.compile_style(build.SCSS / name))
                sections = [value.strip() for value in comments]
                self.assertEqual(
                    sections[1],
                    "Bootstrap configuration" if name == "moo-ui.scss" else "Global styles",
                )
                for heading in ("Theme tokens", "Bootstrap Components", "Moo Components", "Buttons", "Data Table", "Application layout"):
                    self.assertIn(heading, sections)
                self.assertLess(sections.index("Theme tokens"), sections.index("Bootstrap Components"))
                self.assertLess(sections.index("Bootstrap Components"), sections.index("Moo Components"))
                self.assertLess(sections.index("Buttons"), sections.index("Data Table"))

    def test_expanded_css_separates_comment_blocks_with_a_blank_line(self) -> None:
        for name in ("moo-ui.scss", "moo-core.scss"):
            with self.subTest(entrypoint=name):
                css = build.compile_style(build.SCSS / name)
                lines = css.splitlines()
                from scripts.style_comments import css_comments

                for comment in css_comments(css):
                    index = comment.source_line - 1
                    if index and not lines[index][:comment.source_column - 1].strip():
                        self.assertEqual(lines[index - 1].strip(), "")

    def test_compressed_css_preserves_comment_like_strings_and_urls(self) -> None:
        source = '''/*! Fixture. Copyright 2026. Licensed under MIT. */
/* Section heading */
/*! Internal note that is not a license */
.example {
  content: "/* text */ // text";
  background: url("https://example.org/a//b/*data*/");
  color: red #{"/* rtl:ignore */"};
}
'''
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "example.scss"
            path.write_text(source, encoding="utf-8")
            css = build.compile_style(path, output_style="compressed")
        self.assertEqual(comments_in(css), ["! Fixture. Copyright 2026. Licensed under MIT. "])
        self.assertIn('"/* text */ // text"', css)
        self.assertIn("https://example.org/a//b/*data*/", css)
        self.assertIn("color:red", css)


if __name__ == "__main__":
    unittest.main()
