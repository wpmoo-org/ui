from __future__ import annotations

from pathlib import Path
import re
import tempfile

from tests.helpers import ROOT, CatalogTestCase, read_primary_variables

SCSS = ROOT / "scss"
COMPONENTS_SCSS = SCSS / "components"
ROOT_THEME_CONSUMER_SCSS = (
    SCSS / "themes/_standalone_root.scss",
    SCSS / "themes/_scoped_core.scss",
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
CSS_VAR = re.compile(r"var\((--[\w-]+)")
SASS_VAR = re.compile(r"\$[\w-]+")
APPROVED_CSS_TOKEN = re.compile(r"--(?:bs|moo)-")


def token_names(value: str) -> tuple[set[str], set[str]]:
    return set(CSS_VAR.findall(value)), set(SASS_VAR.findall(value))


def approved_token_names(value: str) -> bool:
    css_tokens, _ = token_names(value)
    return bool(css_tokens) and all(APPROVED_CSS_TOKEN.match(token) for token in css_tokens)


def semantic_tokens_only(value: str, semantic: str) -> bool:
    css_tokens, sass_tokens = token_names(value)
    if not css_tokens and not sass_tokens:
        return False
    if not all(APPROVED_CSS_TOKEN.match(token) for token in css_tokens):
        return False
    names = css_tokens | sass_tokens
    if semantic == "radius":
        return all("radius" in name or "border-width" in name for name in names)
    if semantic == "shadow":
        return all("shadow" in name for name in names)
    if semantic == "width":
        return all("border-width" in name or "ring-width" in name for name in names)
    return False


def approved_border_shorthand(value: str) -> bool:
    clean = value.replace("!important", "").strip()
    if clean.lower() in {"0", "none"}:
        return True
    css_tokens, sass_tokens = token_names(clean)
    if not all(APPROVED_CSS_TOKEN.match(token) for token in css_tokens):
        return False
    width_tokens = {
        token for token in css_tokens | sass_tokens
        if "border-width" in token or "ring-width" in token
    }
    color_tokens = {
        token for token in css_tokens | sass_tokens
        if any(part in token for part in ("color", "-bg", "border"))
        and token not in width_tokens
    }
    has_style = " solid " in f" {clean} " or "--bs-border-style" in clean
    return bool(width_tokens and color_tokens and has_style)


def approved_shared_value(prop: str, value: str, allow_sass_interpolation: bool) -> bool:
    clean = value.replace("!important", "").strip()
    if clean.lower() in ALLOWED_LITERALS:
        return True
    if allow_sass_interpolation and "#{" in clean:
        return True
    if prop.startswith("--"):
        if "radius" in prop:
            return semantic_tokens_only(clean, "radius")
        if "shadow" in prop:
            return semantic_tokens_only(clean, "shadow")
        if prop.endswith("width"):
            return semantic_tokens_only(clean, "width")
        return approved_token_names(clean) or bool(SASS_VAR.fullmatch(clean))
    if "radius" in prop:
        return semantic_tokens_only(clean, "radius")
    if "shadow" in prop:
        return semantic_tokens_only(clean, "shadow")
    if "border" in prop:
        if prop.endswith("border-color") or prop == "border-color":
            return approved_token_names(clean) or bool(
                SASS_VAR.fullmatch(clean) and "color" in clean
            )
        if prop.endswith("border-width") or prop == "border-width":
            return semantic_tokens_only(clean, "width")
        if prop.endswith("border-style") or prop == "border-style":
            return clean in {"solid", "dashed", "dotted"} or clean == "var(--bs-border-style)"
        return approved_border_shorthand(clean)
    if "outline" in prop:
        return approved_token_names(clean) or bool(
            SASS_VAR.fullmatch(clean) and "color" in clean
        )
    if any(part in prop for part in ("color", "background", "-bg")):
        return approved_token_names(clean) or bool(
            SASS_VAR.fullmatch(clean)
            and any(part in clean for part in ("color", "-bg"))
        )
    return False


def active_scss_imports(source: str) -> set[str]:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    active_source = "\n".join(
        line.split("//", 1)[0] for line in source.splitlines()
    )
    return set(
        re.findall(
            r'^\s*@import\s+["\']([^"\']+)["\']\s*;',
            active_source,
            re.MULTILINE,
        )
    )


def active_component_imports(source: str) -> set[str]:
    return {
        target.removeprefix("components/")
        for target in active_scss_imports(source)
        if target.startswith("components/")
    }


def component_partials() -> tuple[Path, ...]:
    return tuple(COMPONENTS_SCSS.rglob("_*.scss"))


def component_owner(path: Path) -> str:
    relative = path.relative_to(COMPONENTS_SCSS)
    return relative.parts[0] if len(relative.parts) > 1 else path.stem.removeprefix("_")


def catalog_style_partials() -> tuple[Path, ...]:
    paths = [SCSS / "catalog.scss"]
    catalog_directory = SCSS / "catalog"
    paths.extend(
        catalog_directory.rglob("_*.scss") if catalog_directory.exists() else ()
    )
    return tuple(path for path in paths if path.exists())


def sidebar_style_partials() -> tuple[Path, ...]:
    paths = [COMPONENTS_SCSS / "_sidebar.scss"]
    sidebar_directory = COMPONENTS_SCSS / "sidebar"
    paths.extend(
        sidebar_directory.rglob("_*.scss") if sidebar_directory.exists() else ()
    )
    return tuple(path for path in paths if path.exists())


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
            if approved_shared_value(prop, value, allow_sass_interpolation):
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
    def test_primary_variables_import_settings_in_dependency_order(self) -> None:
        primary_variables = (SCSS / "_primary_variables.scss").read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            [
                target
                for target in re.findall(
                    r'^\s*@import\s+["\']([^"\']+)["\']\s*;',
                    primary_variables,
                    re.MULTILINE,
                )
                if target.startswith("settings/")
            ],
            [
                "settings/palette",
                "settings/forms",
                "settings/components",
                "settings/catalog",
                "settings/bootstrap_overrides",
            ],
        )

    def test_entrypoints_import_theme_and_foundation_layers_in_order(self) -> None:
        entrypoint_imports: dict[str, list[str]] = {}
        for entrypoint in ("moo-ui.scss", "moo-core.scss"):
            source = (SCSS / entrypoint).read_text(encoding="utf-8")
            entrypoint_imports[entrypoint] = re.findall(
                r'^\s*@import\s+["\']([^"\']+)["\']\s*;',
                source,
                re.MULTILINE,
            )

        self.assertEqual(
            [
                target
                for target in entrypoint_imports["moo-ui.scss"]
                if target.startswith(("themes/", "foundations/"))
            ],
            [
                "themes/standalone_root",
                "foundations/focus",
                "foundations/overlay_backdrop",
            ],
        )
        self.assertEqual(
            [
                target
                for target in entrypoint_imports["moo-core.scss"]
                if target.startswith(("themes/", "foundations/"))
            ],
            [
                "themes/scoped_core",
                "foundations/core_global_primitives",
                "foundations/focus",
                "foundations/core_state_layer",
                "foundations/overlay_backdrop",
            ],
        )

        imported = set().union(*entrypoint_imports.values())
        for directory in (SCSS / "themes", SCSS / "foundations"):
            for path in directory.glob("_*.scss"):
                target = path.relative_to(SCSS).with_name(
                    path.stem.removeprefix("_")
                ).with_suffix("").as_posix()
                self.assertIn(
                    target,
                    imported,
                    f"{path.relative_to(SCSS)} is not imported",
                )

    def test_catalog_settings_own_catalog_knobs_only(self) -> None:
        catalog_settings = (SCSS / "settings/_catalog.scss").read_text(
            encoding="utf-8"
        )
        variables = re.findall(
            r"^\s*(\$[\w-]+)\s*:",
            catalog_settings,
            re.MULTILINE,
        )

        self.assertTrue(variables)
        self.assertTrue(
            all(variable.startswith("$moo-catalog-") for variable in variables),
            variables,
        )

    def test_commented_component_imports_are_not_active(self) -> None:
        source = """
            @import "components/active";
            // @import "components/line_commented";
            /*
            @import "components/block_commented";
            */
        """

        self.assertEqual(active_component_imports(source), {"active"})

    def test_property_aware_gate_rejects_semantic_token_mismatches(self) -> None:
        source = """
        .bad {
          border-width: var(--moo-foreground);
          border-color: var(--project-color);
          border-radius: var(--moo-border);
          box-shadow: var(--moo-border);
        }
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "_bad.scss"
            path.write_text(source, encoding="utf-8")
            offenders = shared_primitive_offenders((path,))

        self.assertEqual(len(offenders), 4)
        self.assertTrue(any("border-width" in offender for offender in offenders))
        self.assertTrue(any("border-color" in offender for offender in offenders))
        self.assertTrue(any("border-radius" in offender for offender in offenders))
        self.assertTrue(any("box-shadow" in offender for offender in offenders))

    def test_property_aware_gate_accepts_framework_scales(self) -> None:
        source = """
        .good {
          border: var(--bs-border-width) solid var(--moo-border);
          border-radius: var(--bs-border-radius-lg);
          box-shadow: var(--bs-box-shadow-sm);
          background: color-mix(in srgb, var(--moo-surface) 80%, var(--bs-body-bg));
        }
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "_good.scss"
            path.write_text(source, encoding="utf-8")
            offenders = shared_primitive_offenders((path,))

        self.assertEqual(offenders, [])

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

    def test_nested_component_partials_are_referenced(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SCSS.rglob("*.scss")
        )
        imports = active_scss_imports(source)

        for path in component_partials():
            relative = path.relative_to(SCSS)
            target = relative.with_name(
                relative.stem.removeprefix("_")
            ).with_suffix("").as_posix()
            self.assertIn(target, imports, f"{relative} is not imported")

    def test_component_styles_consume_shared_primitives_only(self) -> None:
        self.assertEqual(
            shared_primitive_offenders(component_partials()),
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
        offenders = [
            offender
            for path in catalog_style_partials()
            for offender in catalog_literal_offenders(path)
        ]
        self.assertEqual(offenders, [])

    def test_scoped_theme_rgb_values_derive_from_sass_colors(self) -> None:
        core_theme = (SCSS / "themes/_scoped_core.scss").read_text(
            encoding="utf-8"
        )

        self.assertEqual(RAW_RGB_TRIPLET.findall(core_theme), [])

    def test_sidebar_styles_own_the_public_sidebar_namespace(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sidebar_style_partials()
        )
        selectors = set(re.findall(r"\.([a-z][a-z0-9_-]*)", source))

        self.assertTrue(selectors)
        self.assertTrue(
            all(selector.startswith("sidebar") for selector in selectors),
            sorted(selector for selector in selectors if not selector.startswith("sidebar")),
        )

    def test_private_tokens_are_prefixed_and_backed_by_sass_knobs(self) -> None:
        primary_variables = read_primary_variables()
        primary_lines = primary_variables.splitlines()

        for path in sorted(component_partials()):
            component = component_owner(path)
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
                declaration_line = next(
                    index
                    for index, line in enumerate(primary_lines)
                    if re.search(rf"^\s*{re.escape(knob)}\s*:", line)
                )
                rationale = " ".join(
                    line.removeprefix("//").strip().lower()
                    for line in primary_lines[max(0, declaration_line - 8):declaration_line]
                    if line.strip().startswith("//")
                )
                self.assertIn(
                    "bootstrap",
                    rationale,
                    f"{knob} must document its Bootstrap ownership gap",
                )
                self.assertTrue(
                    any(
                        phrase in rationale
                        for phrase in ("has no", " no ", "scoped", "not a global")
                    ),
                    f"{knob} must explain why a private component knob is needed",
                )

    def test_root_and_core_theme_tokens_share_sass_sources(self) -> None:
        primary_variables = read_primary_variables()
        tokens_root = (SCSS / "themes/_standalone_root.scss").read_text(
            encoding="utf-8"
        )
        core_theme = (SCSS / "themes/_scoped_core.scss").read_text(
            encoding="utf-8"
        )

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
                f"{token} must use shared Sass variables in themes/_standalone_root.scss",
            )
            self.assertEqual(
                declarations_for(core_theme).get(token),
                {
                    sass_var_reference(light_variable),
                    sass_var_reference(dark_variable),
                },
                f"{token} must use shared Sass variables in themes/_scoped_core.scss",
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
                f"{token} must be emitted once in themes/_standalone_root.scss",
            )
            self.assertEqual(
                declaration_values_for(core_theme).get(token),
                [expected],
                f"{token} must be emitted once in themes/_scoped_core.scss",
            )

    def test_shared_primitives_live_on_bootstrap_scales(self) -> None:
        primary_variables = read_primary_variables()
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
