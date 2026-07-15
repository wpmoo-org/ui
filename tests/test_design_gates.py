from __future__ import annotations

import re

from tests.helpers import ROOT, CatalogTestCase

COMPONENTS_SCSS = ROOT / "scss/components"

# Component partials must consume shared primitives (--bs-* scales and
# --moo-* theme tokens); literal colors, shadows, and radii are defects.
LITERAL_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch)\(")
DECLARATION = re.compile(r"^\s*(--[\w-]+|[a-z-]+)\s*:\s*([^;]+);")
GATED_PROP = re.compile(r"color|background|-bg$|shadow|radius|outline|border")
ALLOWED_LITERALS = {"0", "none", "transparent", "inherit", "currentcolor"}


class DesignGateTests(CatalogTestCase):
    def test_component_styles_consume_shared_primitives_only(self) -> None:
        offenders: list[str] = []
        for path in sorted(COMPONENTS_SCSS.glob("_*.scss")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for lineno, raw in enumerate(lines, start=1):
                line = raw.split("//", 1)[0]
                if LITERAL_COLOR.search(line):
                    offenders.append(
                        f"{path.name}:{lineno}: literal color value"
                    )
                    continue
                match = DECLARATION.match(line)
                if not match:
                    continue
                prop, value = match.group(1), match.group(2).strip()
                if not GATED_PROP.search(prop):
                    continue
                if "var(" in value or value.lower() in ALLOWED_LITERALS:
                    continue
                offenders.append(
                    f"{path.name}:{lineno}: '{prop}: {value}' must consume"
                    " a shared --bs-* scale or --moo-* token"
                )
        self.assertEqual(offenders, [])

    def test_private_tokens_are_prefixed_and_documented(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        primary_variables = (
            ROOT / "scss/_primary_variables.scss"
        ).read_text(encoding="utf-8")

        for path in sorted(COMPONENTS_SCSS.glob("_*.scss")):
            component = path.stem.removeprefix("_")
            prefix = f"--moo-{component.replace('_', '-')}"
            source = path.read_text(encoding="utf-8")
            tokens = set(re.findall(r"--moo-[\w-]+(?=\s*:)", source))

            for token in sorted(tokens):
                self.assertTrue(
                    token.startswith(prefix),
                    f"{path.name}: {token} is outside the {prefix}-* namespace",
                )

            if not tokens:
                continue

            page = self.read_output(
                f"components/{component.replace('_', '-')}.html"
            )
            reference = page.split('class="moo-component-reference"', 1)[1]
            for token in sorted(tokens):
                knob = f"${token.removeprefix('--')}"
                self.assertRegex(
                    primary_variables,
                    rf"{re.escape(knob)}\s*:[^;]+!default;",
                    f"{token} must have a matching {knob} !default Sass knob",
                )
                self.assertIn(
                    token,
                    reference,
                    f"{token} must be documented, with its reason, in the"
                    f" {component} API Reference",
                )
                row = next(
                    (
                        table_row
                        for table_row in re.findall(
                            r"<tr>.*?</tr>", reference, re.DOTALL
                        )
                        if token in table_row
                    ),
                    "",
                )
                self.assertIn(
                    knob,
                    row,
                    f"{token} API Reference row must name its {knob} knob",
                )

    def test_shared_primitives_live_on_bootstrap_scales(self) -> None:
        primary_variables = (ROOT / "scss/_primary_variables.scss").read_text(
            encoding="utf-8"
        )
        for scale_variable in (
            "$box-shadow-sm:",
            "$box-shadow:",
            "$box-shadow-lg:",
            "$border-radius-xl:",
            "$focus-ring-width:",
            "$btn-font-size-sm:",
            "$btn-font-size-lg:",
        ):
            self.assertIn(scale_variable, primary_variables)

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn("--bs-box-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);", css)
        self.assertIn("--bs-border-radius-xl: 0.75rem;", css)
        self.assertIn("--bs-focus-ring-width: 2px;", css)
