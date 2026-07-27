from __future__ import annotations

from pathlib import Path
import re

from tests.helpers import ROOT, CatalogTestCase

SCSS = ROOT / "scss"
COMPONENTS_SCSS = SCSS / "components"
ROOT_THEME_CONSUMER_SCSS = (
    SCSS / "_tokens_root.scss",
    SCSS / "_core_theme.scss",
)
MOO_THEME_TOKENS = {
    "--moo-surface": ("$moo-surface", "$moo-surface-dark"),
    "--moo-muted-surface": ("$moo-muted-surface", "$moo-muted-surface-dark"),
    "--moo-border": ("$moo-border", "$moo-border-dark"),
    "--moo-foreground": ("$moo-foreground", "$moo-foreground-dark"),
    "--moo-muted-foreground": (
        "$moo-muted-foreground",
        "$moo-muted-foreground-dark",
    ),
    "--moo-ring": ("$moo-ring", "$moo-ring-dark"),
    "--moo-destructive": ("$moo-destructive", "$moo-destructive-dark"),
    "--moo-destructive-foreground": (
        "$moo-destructive-foreground",
        "$moo-destructive-foreground-dark",
    ),
    "--moo-sidebar": ("$moo-sidebar", "$moo-sidebar-dark"),
}
MOO_SHARED_TOKENS = {
    "--moo-overlay-backdrop-opacity": "$moo-overlay-backdrop-opacity",
    "--moo-overlay-backdrop-bg": "$moo-overlay-backdrop-bg",
    "--moo-overlay-backdrop-filter": "$moo-overlay-backdrop-filter",
    "--moo-input-group-border-radius": "$moo-input-group-border-radius",
    "--moo-disabled-control-opacity": "$moo-disabled-control-opacity",
    "--moo-sidebar-foreground": "var(--moo-foreground)",
    "--moo-sidebar-accent": "var(--moo-muted-surface)",
    "--moo-sidebar-border": "var(--moo-border)",
}

# Component partials must consume shared primitives (Bootstrap Sass/CSS scales
# and --moo-* theme tokens); literal colors, shadows, and radii are defects.
LITERAL_COLOR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|(?<![\w-])(?:rgba?|hsla?|oklch)\("
)
DECLARATION = re.compile(r"^\s*(--[\w-]+|[a-z-]+)\s*:\s*([^;]+);")
GATED_PROP = re.compile(r"color|background|-bg$|shadow|radius|outline|border")
ALLOWED_LITERALS = {"0", "none", "transparent", "inherit", "currentcolor"}
TOKEN_COMPOSED_COLOR_FUNCTION = re.compile(
    r"\b(?:rgba?|hsla?|oklch)\(\s*var\("
)
RAW_RGB_TRIPLET = re.compile(
    r"--[^:]+-rgb:\s*\d+\s*,\s*\d+\s*,\s*\d+\s*;"
)


def active_component_imports(source: str) -> set[str]:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    active_source = "\n".join(
        line.split("//", 1)[0] for line in source.splitlines()
    )
    return set(
        re.findall(
            r'^\s*@import\s+["\']components/([^"\']+)["\']\s*;',
            active_source,
            re.MULTILINE,
        )
    )


def sass_var_reference(variable: str) -> str:
    return f"#{{{variable}}}"


def declarations_for(source: str) -> dict[str, set[str]]:
    declarations: dict[str, set[str]] = {}
    for line in source.splitlines():
        match = DECLARATION.match(line)
        if match:
            prop, value = match.groups()
            declarations.setdefault(prop, set()).add(value.strip())
    return declarations


def declaration_values_for(source: str) -> dict[str, list[str]]:
    declarations: dict[str, list[str]] = {}
    for line in source.splitlines():
        match = DECLARATION.match(line)
        if match:
            prop, value = match.groups()
            declarations.setdefault(prop, []).append(value.strip())
    return declarations


def shared_primitive_offenders(
    paths: tuple[Path, ...],
    *,
    allow_sass_interpolation: bool = False,
) -> list[str]:
    offenders: list[str] = []
    for path in sorted(paths, key=lambda item: item.name):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, raw in enumerate(lines, start=1):
            line = raw.split("//", 1)[0]
            if LITERAL_COLOR.search(line):
                offenders.append(f"{path.name}:{lineno}: literal color value")
                continue
            match = DECLARATION.match(line)
            if not match:
                continue
            prop, value = match.group(1), match.group(2).strip()
            if prop == "color-scheme":
                continue
            if not GATED_PROP.search(prop):
                continue
            if (
                "var(" in value
                or (allow_sass_interpolation and value.startswith("#{"))
                or value.lower() in ALLOWED_LITERALS
                or value in {
                    "$input-border-radius",
                    "$input-border-width solid $input-border-color",
                    "$input-border-width solid $input-group-addon-border-color",
                    "$input-focus-border-color",
                    "$input-focus-box-shadow",
                }
            ):
                continue
            offenders.append(
                f"{path.name}:{lineno}: '{prop}: {value}' must consume"
                " a shared Bootstrap Sass/CSS scale or --moo-* token"
            )
    return offenders


def catalog_literal_offenders(path: Path) -> list[str]:
    offenders: list[str] = []
    for lineno, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw.split("//", 1)[0]
        line_without_token_color_functions = TOKEN_COMPOSED_COLOR_FUNCTION.sub(
            "var(",
            line,
        )
        if LITERAL_COLOR.search(line_without_token_color_functions):
            offenders.append(f"{path.name}:{lineno}: literal color value")
    return offenders


class DesignGateTests(CatalogTestCase):
    def test_commented_component_imports_are_not_active(self) -> None:
        source = """
            @import "components/active";
            // @import "components/line_commented";
            /*
            @import "components/block_commented";
            */
        """

        self.assertEqual(active_component_imports(source), {"active"})

    def test_all_component_partials_are_imported(self) -> None:
        entrypoint = (SCSS / "moo-ui.scss").read_text(encoding="utf-8")
        if '@import "component_layer"' in entrypoint:
            entrypoint += "\n" + (SCSS / "_component_layer.scss").read_text(
                encoding="utf-8"
            )
        imported_components = active_component_imports(entrypoint)

        for path in sorted(COMPONENTS_SCSS.glob("_*.scss")):
            component = path.stem.removeprefix("_")
            self.assertIn(component, imported_components)

    def test_core_component_layer_imports_all_component_partials(self) -> None:
        component_layer = SCSS / "_component_layer.scss"

        self.assertTrue(component_layer.is_file())
        imported_components = active_component_imports(
            component_layer.read_text(encoding="utf-8")
        )

        for path in sorted(COMPONENTS_SCSS.glob("_*.scss")):
            component = path.stem.removeprefix("_")
            self.assertIn(component, imported_components)

    def test_component_styles_consume_shared_primitives_only(self) -> None:
        self.assertEqual(
            shared_primitive_offenders(tuple(COMPONENTS_SCSS.glob("_*.scss"))),
            [],
        )

    def test_root_theme_consumers_use_shared_primitives_only(self) -> None:
        self.assertEqual(
            shared_primitive_offenders(
                ROOT_THEME_CONSUMER_SCSS,
                allow_sass_interpolation=True,
            ),
            [],
        )

    def test_catalog_chrome_uses_tokens_for_color_literals(self) -> None:
        self.assertEqual(catalog_literal_offenders(SCSS / "catalog.scss"), [])

    def test_scoped_theme_rgb_values_derive_from_sass_colors(self) -> None:
        core_theme = (SCSS / "_core_theme.scss").read_text(encoding="utf-8")

        self.assertEqual(RAW_RGB_TRIPLET.findall(core_theme), [])

    def test_sidebar_styles_own_the_public_sidebar_namespace(self) -> None:
        source = (COMPONENTS_SCSS / "_sidebar.scss").read_text(encoding="utf-8")
        selectors = set(re.findall(r"\.([a-z][a-z0-9_-]*)", source))

        self.assertTrue(selectors)
        self.assertTrue(
            all(selector.startswith("sidebar") for selector in selectors),
            sorted(selector for selector in selectors if not selector.startswith("sidebar")),
        )

    def test_private_tokens_are_prefixed_and_backed_by_sass_knobs(self) -> None:
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

            for token in sorted(tokens):
                knob = f"${token.removeprefix('--')}"
                self.assertRegex(
                    primary_variables,
                    rf"{re.escape(knob)}\s*:[^;]+!default;",
                    f"{token} must have a matching {knob} !default Sass knob",
                )

    def test_root_and_core_theme_tokens_share_sass_sources(self) -> None:
        primary_variables = (SCSS / "_primary_variables.scss").read_text(
            encoding="utf-8"
        )
        tokens_root = (SCSS / "_tokens_root.scss").read_text(encoding="utf-8")
        core_theme = (SCSS / "_core_theme.scss").read_text(encoding="utf-8")

        for token, variables in MOO_THEME_TOKENS.items():
            for variable in variables:
                self.assertRegex(
                    primary_variables,
                    rf"{re.escape(variable)}\s*:[^;]+!default;",
                    f"{token} must be backed by {variable} in primary variables",
                )

        for token, (light_variable, dark_variable) in MOO_THEME_TOKENS.items():
            self.assertEqual(
                declarations_for(tokens_root).get(token),
                {
                    sass_var_reference(light_variable),
                    sass_var_reference(dark_variable),
                },
                f"{token} must use shared Sass variables in _tokens_root.scss",
            )
            self.assertEqual(
                declarations_for(core_theme).get(token),
                {
                    sass_var_reference(light_variable),
                    sass_var_reference(dark_variable),
                },
                f"{token} must use shared Sass variables in _core_theme.scss",
            )

        for token, variable in MOO_SHARED_TOKENS.items():
            expected = (
                sass_var_reference(variable)
                if variable.startswith("$")
                else variable
            )
            self.assertEqual(
                declaration_values_for(tokens_root).get(token),
                [expected],
                f"{token} must be emitted once in _tokens_root.scss",
            )
            self.assertEqual(
                declaration_values_for(core_theme).get(token),
                [expected],
                f"{token} must be emitted once in _core_theme.scss",
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
