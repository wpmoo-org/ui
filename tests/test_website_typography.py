from __future__ import annotations

import re
import unittest

import build
from tests.helpers import ROOT

SCSS = ROOT / "scss"
OWNER = '.moo-ui[data-moo-typography="website"]'
WHERE_OWNER = ':where(.moo-ui[data-moo-typography="website"])'


def compile_entry(name: str) -> str:
    return build.sass.compile(
        filename=str(SCSS / name),
        include_paths=[str(SCSS), str(build.BOOTSTRAP.parent)],
        output_style="expanded",
    )


def top_level_rules(css: str) -> list[tuple[str, str]]:
    return [
        (selector.strip(), body)
        for selector, body in re.findall(r"([^{}@][^{}]*)\{([^{}]*)\}", css)
    ]


class WebsiteTypographyTests(unittest.TestCase):
    def test_profile_knobs_are_default_sass_settings(self) -> None:
        palette = (SCSS / "settings/_palette.scss").read_text(encoding="utf-8")
        for knob in (
            "$moo-website-font-size",
            "$moo-website-line-height",
            "$moo-website-small-font-size",
            "$moo-website-lead-font-size",
            "$moo-website-heading-line-height",
            "$moo-website-heading-fluid-sizes",
            "$moo-website-heading-fixed-sizes",
            "$moo-website-display-fluid-sizes",
            "$moo-text-measure",
        ):
            with self.subTest(knob=knob):
                self.assertRegex(palette, rf"{re.escape(knob)}:[^;]+!default;")
        self.assertIn("$moo-website-font-size: 1rem !default;", palette)
        self.assertIn("$moo-website-line-height: 1.6 !default;", palette)

    def test_every_rule_the_profile_emits_starts_at_the_opt_in_owner(self) -> None:
        profile_import = '@import "foundations/typography_website";\n'
        for entry in ("moo-ui.scss", "moo-core.scss"):
            source = (SCSS / entry).read_text(encoding="utf-8")
            self.assertIn(profile_import, source)
            without = build.sass.compile(
                string=source.replace(profile_import, ""),
                include_paths=[str(SCSS), str(build.BOOTSTRAP.parent)],
                output_style="expanded",
            )
            with_profile = compile_entry(entry)
            before = set(top_level_rules(without))
            emitted = [r for r in top_level_rules(with_profile) if r not in before]
            self.assertGreater(len(emitted), 15, entry)
            self.assertFalse(
                [r for r in before if r not in set(top_level_rules(with_profile))],
                "the profile must only add rules",
            )
            for selector, _body in emitted:
                for part in (p.strip() for p in selector.split(",\n")):
                    with self.subTest(entry=entry, selector=part):
                        self.assertTrue(
                            part.startswith((OWNER, WHERE_OWNER)),
                            "profile selector must start at the opt-in owner",
                        )

    def test_fluid_sizes_hit_endpoints_and_respect_the_zoom_rule(self) -> None:
        css = compile_entry("moo-ui.scss")
        fluid = re.findall(
            r"clamp\(([\d.]+)rem, ([\d.]+)rem \+ ([\d.]+)vw, ([\d.]+)rem\)", css
        )
        self.assertEqual(len(fluid), 9)  # h1-h3 and display-1..6
        for low, a, b, high in map(lambda t: tuple(map(float, t)), fluid):
            min_px, max_px = low * 16, high * 16
            with self.subTest(min=low, max=high):
                self.assertAlmostEqual(a * 16 + b * 3.2, min_px, delta=0.05)
                self.assertAlmostEqual(a * 16 + b * 14.0, max_px, delta=0.05)
                self.assertLessEqual(max_px, 2.5 * min_px)

    def test_non_german_islands_reset_hyphenation(self) -> None:
        css = compile_entry("moo-ui.scss")
        selector = (
            f"{WHERE_OWNER} :is(p, li, dd, blockquote, figcaption):lang(de) "
            "[lang]:not(:lang(de))"
        )
        rules = dict(top_level_rules(css))
        self.assertIn(selector, rules)
        self.assertIn("hyphens: manual;", rules[selector])
        self.assertIn("overflow-wrap: normal;", rules[selector])
        self.assertGreater(css.index(selector), css.index("hyphens: auto;"))

    def test_default_owner_values_stay_the_app_profile(self) -> None:
        css = compile_entry("moo-ui.scss")
        self.assertRegex(
            css,
            r"\.moo-ui\[data-bs-theme\] \{[^}]*--bs-body-font-size: 0\.875rem;"
            r"[^}]*--bs-body-line-height: 1\.5;",
        )
        self.assertRegex(css, r"--moo-small-font-size: 0\.75rem;")

    def test_profile_sets_body_tokens_on_owner_and_nested_owners(self) -> None:
        css = compile_entry("moo-ui.scss")
        match = re.search(
            r"\.moo-ui\[data-moo-typography=\"website\"\]\[data-bs-theme\],\s*"
            r"\.moo-ui\[data-moo-typography=\"website\"\] \.moo-ui\[data-bs-theme\] \{"
            r"([^}]*)\}",
            css,
        )
        self.assertIsNotNone(match, "nested owners must receive the profile")
        body = match.group(1)
        self.assertIn("--bs-body-font-size: 1rem;", body)
        self.assertIn("--bs-body-line-height: 1.6;", body)
        self.assertIn("--moo-small-font-size: 0.875rem;", body)

        def specificity(selector: str) -> int:
            return selector.count(".") + selector.count("[")

        nested = f"{OWNER} .moo-ui[data-bs-theme]"
        reset = ".moo-ui[data-bs-theme]"
        self.assertGreater(specificity(nested), specificity(reset))
        reset_body = next(
            body
            for selector, body in top_level_rules(css)
            if selector.split("*/")[-1].strip() == reset and "--bs-body-font-size" in body
        )
        self.assertIn("--bs-body-font-size", reset_body)

    def test_profile_text_rules(self) -> None:
        css = compile_entry("moo-ui.scss")
        self.assertIn(f"{WHERE_OWNER} p {{\n  text-wrap: pretty;", css)
        self.assertRegex(css, r"text-wrap: balance;")
        self.assertRegex(
            css,
            re.escape(WHERE_OWNER)
            + r" :is\(p, li, dd, blockquote, figcaption\):lang\(de\) \{\s*"
            r"hyphens: auto;\s*overflow-wrap: break-word;",
        )
        self.assertRegex(css, re.escape(WHERE_OWNER) + r" :is\(h1, \.h1\) \{\s*font-size: clamp\(2rem, 1\.7037rem \+ 1\.4815vw, 3rem\);")
        self.assertRegex(css, re.escape(WHERE_OWNER) + r" \.display-1 \{\s*font-size: clamp\(")
        self.assertRegex(css, re.escape(WHERE_OWNER) + r" \.lead \{\s*font-size: 1\.25rem;")

    def test_profile_does_not_cap_paragraph_width(self) -> None:
        source = (SCSS / "foundations/_typography_website.scss").read_text(encoding="utf-8")
        self.assertNotIn("max-inline-size", source)
        self.assertNotIn("max-width", source)

    def test_entrypoints_import_profile_before_scope(self) -> None:
        for entry in ("moo-ui.scss", "moo-core.scss"):
            source = (SCSS / entry).read_text(encoding="utf-8")
            self.assertLess(
                source.index('"foundations/typography_website"'),
                source.index('"foundations/scope"'),
                entry,
            )


if __name__ == "__main__":
    unittest.main()
