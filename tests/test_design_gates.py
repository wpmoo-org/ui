from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tempfile

from tests.helpers import ROOT, CatalogTestCase, read_settings
from tests.helpers.node_harness import NODE_TEST_TIMEOUT

SCSS = ROOT / "scss"
SITE_SCSS = ROOT / "site/scss"
COMPONENTS_SCSS = SCSS / "components"
ROOT_THEME_CONSUMER_SCSS = (
    SCSS / "themes/_standalone_root.scss",
    SCSS / "themes/_scoped_core.scss",
)
MOO_THEME_TOKENS = {
    "--moo-surface": ("$moo-surface", "$moo-surface-dark"),
    "--moo-muted-surface": ("$moo-muted-surface", "$moo-muted-surface-dark"),
    "--moo-border": ("$moo-border", "$moo-border-dark"),
    "--moo-primary": ("$moo-primary", "$moo-primary-dark"),
    "--moo-primary-foreground": (
        "$moo-primary-foreground",
        "$moo-primary-foreground-dark",
    ),
    "--moo-foreground": ("$moo-foreground", "$moo-foreground-dark"),
    "--moo-muted-foreground": (
        "$moo-muted-foreground",
        "$moo-muted-foreground-dark",
    ),
    "--moo-disabled-foreground": (
        "$moo-disabled-foreground",
        "$moo-disabled-foreground-dark",
    ),
    "--moo-ring": ("$moo-ring", "$moo-ring-dark"),
    "--moo-destructive": ("$moo-destructive", "$moo-destructive-dark"),
    "--moo-destructive-surface": (
        "$moo-destructive-surface",
        "$moo-destructive-surface-dark",
    ),
    "--moo-destructive-surface-hover": (
        "$moo-destructive-surface-hover",
        "$moo-destructive-surface-hover-dark",
    ),
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
    "--moo-chart-1": "$moo-chart-1",
    "--moo-chart-2": "$moo-chart-2",
    "--moo-chart-3": "$moo-chart-3",
    "--moo-chart-4": "$moo-chart-4",
    "--moo-chart-5": "$moo-chart-5",
}

# Component partials must consume shared primitives (Bootstrap Sass/CSS scales
# and --moo-* theme tokens); literal colors, shadows, and radii are defects.
LITERAL_COLOR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|(?<![\w-])(?:rgba?|hsla?|oklch)\("
)
DECLARATION = re.compile(
    r"^[ \t]*(--(?:[\w-]|#\{\$[\w-]+\})+|[a-z-]+)[ \t]*:[ \t]*([^;]+);",
    re.MULTILINE,
)
GATED_PROP = re.compile(r"color|background|-bg$|shadow|radius|outline|border")
ALLOWED_LITERALS = {"0", "none", "transparent", "inherit", "currentcolor"}
TOKEN_COMPOSED_COLOR_FUNCTION = re.compile(
    r"\b(?:rgba?|hsla?|oklch)\(\s*var\("
)
RAW_RGB_TRIPLET = re.compile(
    r"--[^:]+-rgb:\s*\d+\s*,\s*\d+\s*,\s*\d+\s*;"
)
NONZERO_DIMENSION = re.compile(
    r"(?<![\w.-])(?:\d*\.\d+|[1-9]\d*)(?:px|rem|em|vw|vh|ch|ex)\b"
)
NONZERO_PERCENT = re.compile(r"(?<![\w.-])(?:\d*\.\d+|[1-9]\d*)%\b")
CSS_VAR = re.compile(r"var\((--(?:[\w-]|#\{\$[\w-]+\})+)")
CUSTOM_PROPERTY_DECLARATION = re.compile(r"^[ \t]*(--[\w-]+)[ \t]*:", re.MULTILINE)
SASS_VAR = re.compile(r"\$[\w-]+")
SINGLE_SASS_INTERPOLATION = re.compile(r"^#\{\s*(\$[\w-]+)\s*\}$")
TO_RGB_INTERPOLATION = re.compile(r"^#\{\s*to-rgb\((\$[\w-]+)\)\s*\}$")
ESCAPE_SVG_INTERPOLATION = re.compile(
    r"^#\{\s*escape-svg\((\$[\w-]+)\)\s*\}$"
)
APPROVED_CSS_TOKEN = re.compile(r"--(?:(?:bs|moo)-|#\{\$prefix\})")


def token_names(value: str) -> tuple[set[str], set[str]]:
    css_tokens = set(CSS_VAR.findall(value))
    without_css_tokens = CSS_VAR.sub("var(--token", value)
    return css_tokens, set(SASS_VAR.findall(without_css_tokens))


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


def approved_shared_value(prop: str, value: str) -> bool:
    clean = " ".join(value.replace("!important", "").split())
    if clean.lower() in ALLOWED_LITERALS:
        return True
    if NONZERO_DIMENSION.search(clean):
        return False
    if "radius" in prop and NONZERO_PERCENT.search(clean):
        return False

    interpolation = SINGLE_SASS_INTERPOLATION.fullmatch(clean)
    if interpolation:
        clean = interpolation.group(1)
    rgb_interpolation = TO_RGB_INTERPOLATION.fullmatch(clean)
    if rgb_interpolation:
        return prop.endswith("-rgb")
    svg_interpolation = ESCAPE_SVG_INTERPOLATION.fullmatch(clean)
    if svg_interpolation:
        return "bg" in prop and "image" in svg_interpolation.group(1)

    interpolation_probe = clean.replace("#{$prefix}", "")
    interpolation_probe = re.sub(
        r"#\{\s*(\$[\w-]+)\s*\}",
        r"\1",
        interpolation_probe,
    )
    if "#{" in interpolation_probe:
        return False

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
        if SASS_VAR.fullmatch(clean) and "shadow" in clean:
            return True
        if semantic_tokens_only(clean, "shadow"):
            return True
        css_tokens, sass_tokens = token_names(clean)
        names = css_tokens | sass_tokens
        return (
            "0 0 0" in clean
            and all(APPROVED_CSS_TOKEN.match(token) for token in css_tokens)
            and any("ring-width" in name for name in names)
            and any(
                "color" in name
                or "border" in name
                or "-bg" in name
                or "surface" in name
                for name in names
            )
        )
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


def strip_scss_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return "\n".join(line.split("//", 1)[0] for line in source.splitlines())


def active_scss_import_list(source: str) -> list[str]:
    return re.findall(
        r'^[ \t]*@import[ \t]+["\']([^"\']+)["\'][ \t]*;',
        strip_scss_comments(source),
        re.MULTILINE,
    )


def active_scss_imports(source: str) -> set[str]:
    return set(active_scss_import_list(source))


def partial_import_target(path: Path) -> str:
    for root in (SCSS, SITE_SCSS):
        try:
            relative = path.relative_to(root)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Unsupported Sass partial path: {path}")
    return relative.with_name(
        relative.stem.removeprefix("_")
    ).with_suffix("").as_posix()


def owned_partial_targets(directory: Path) -> set[str]:
    return {
        partial_import_target(path)
        for path in directory.rglob("_*.scss")
    }


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
    paths = [SITE_SCSS / "catalog.scss"]
    catalog_directory = SITE_SCSS / "catalog"
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
    for match in DECLARATION.finditer(strip_scss_comments(source)):
        prop, value = match.groups()
        declarations.setdefault(prop, set()).add(" ".join(value.split()))
    return declarations


def declaration_values_for(source: str) -> dict[str, list[str]]:
    declarations: dict[str, list[str]] = {}
    for match in DECLARATION.finditer(strip_scss_comments(source)):
        prop, value = match.groups()
        declarations.setdefault(prop, []).append(" ".join(value.split()))
    return declarations


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return Path(path.name)


def shared_primitive_offenders(paths: tuple[Path, ...]) -> list[str]:
    offenders: list[str] = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        source = strip_scss_comments(path.read_text(encoding="utf-8"))
        for match in LITERAL_COLOR.finditer(source):
            lineno = source.count("\n", 0, match.start()) + 1
            offenders.append(f"{display_path(path)}:{lineno}: literal color value")
        for match in DECLARATION.finditer(source):
            prop, value = match.group(1), " ".join(match.group(2).split())
            lineno = source.count("\n", 0, match.start()) + 1
            if prop == "color-scheme" or not GATED_PROP.search(prop):
                continue
            if approved_shared_value(prop, value):
                continue
            offenders.append(
                f"{display_path(path)}:{lineno}: '{prop}: {value}' must consume"
                " a shared Bootstrap Sass/CSS scale or --moo-* token"
            )
    return offenders


def catalog_literal_offenders(path: Path) -> list[str]:
    source = strip_scss_comments(path.read_text(encoding="utf-8"))
    source = TOKEN_COMPOSED_COLOR_FUNCTION.sub("var(", source)
    return [
        f"{display_path(path)}:{source.count(chr(10), 0, match.start()) + 1}: literal color value"
        for match in LITERAL_COLOR.finditer(source)
    ]


class DesignGateTests(CatalogTestCase):
    def test_neutral_chart_defaults_match_theme_builder_schema(self) -> None:
        palette = (ROOT / "scss/settings/_palette.scss").read_text(encoding="utf-8")
        sass_values = dict(
            re.findall(
                r"\$(moo-chart-[1-5]):\s*(#[0-9a-fA-F]{6})\s*!default;",
                palette,
            )
        )
        self.assertEqual(len(sass_values), 5)
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { resolveThemeBuilderTokens } from "./site/src/js/catalog/theme-builder-schema.js";
const tokens = resolveThemeBuilderTokens({ chartColor: "neutral" });
console.log(JSON.stringify(Object.fromEntries(
  [1, 2, 3, 4, 5].map((index) => [`moo-chart-${index}`, tokens[`--moo-chart-${index}`]])
)));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        js_values = json.loads(result.stdout.splitlines()[-1])
        expected = {
            key: (
                f"rgb({int(value[1:3], 16)}, "
                f"{int(value[3:5], 16)}, "
                f"{int(value[5:7], 16)})"
            )
            for key, value in sass_values.items()
        }
        self.assertEqual(js_values, expected)

    def test_scss_source_surface_uses_only_owned_layers(self) -> None:
        root_files = {
            path.name for path in SCSS.glob("*.scss")
        }
        self.assertEqual(
            root_files,
            {
                "_components.scss",
                "_facade-settings.scss",
                "_settings.scss",
                "moo-core.scss",
                "moo-ui.scss",
            },
        )
        directories = {
            path.name for path in SCSS.iterdir() if path.is_dir()
        }
        self.assertEqual(
            directories,
            {"components", "foundations", "settings", "themes", "utilities"},
        )
        site_root_files = {
            path.name for path in SITE_SCSS.glob("*.scss")
        }
        self.assertEqual(site_root_files, {"catalog.scss"})
        site_directories = {
            path.name for path in SITE_SCSS.iterdir() if path.is_dir()
        }
        self.assertEqual(
            site_directories,
            {"catalog"},
        )
        self.assertEqual(
            {
                path.relative_to(SCSS / "utilities").as_posix()
                for path in (SCSS / "utilities").rglob("*.scss")
            },
            {"_scroll_fade.scss", "_scroll_fade_primitives.scss"},
        )

    def test_settings_aggregate_imports_partials_in_dependency_order(self) -> None:
        settings = (SCSS / "_settings.scss").read_text(
            encoding="utf-8"
        )
        expected = [
            "settings/palette",
            "settings/forms",
            "settings/component_variables",
            "settings/bootstrap_overrides",
        ]
        imports = [
            target
            for target in active_scss_import_list(settings)
            if target.startswith("settings/")
        ]

        self.assertEqual(imports, expected)
        # _facade_public.scss is the narrow public allow-list: it is owned
        # by _palette.scss's leading import (and by the public facade), not
        # a direct _settings.scss import.
        self.assertEqual(
            owned_partial_targets(SCSS / "settings"),
            set(expected) | {"settings/facade_public"},
        )
        palette_imports = active_scss_import_list(
            (SCSS / "settings/_palette.scss").read_text(encoding="utf-8")
        )
        self.assertEqual(palette_imports[:1], ["facade_public"])

    def test_entrypoints_import_theme_and_foundation_layers_in_order(self) -> None:
        entrypoint_imports = {
            entrypoint: active_scss_import_list(
                (SCSS / entrypoint).read_text(encoding="utf-8")
            )
            for entrypoint in ("moo-ui.scss", "moo-core.scss")
        }

        self.assertEqual(
            entrypoint_imports["moo-ui.scss"],
            [
                "settings",
                "../vendor/bootstrap/scss/mixins/banner",
                "../vendor/bootstrap/scss/functions",
                "../vendor/bootstrap/scss/variables",
                "../vendor/bootstrap/scss/variables-dark",
                "../vendor/bootstrap/scss/maps",
                "../vendor/bootstrap/scss/mixins",
                "../vendor/bootstrap/scss/utilities",
                "../vendor/bootstrap/scss/root",
                "../vendor/bootstrap/scss/reboot",
                "../vendor/bootstrap/scss/type",
                "../vendor/bootstrap/scss/images",
                "../vendor/bootstrap/scss/containers",
                "../vendor/bootstrap/scss/grid",
                "../vendor/bootstrap/scss/forms/form-range",
                "../vendor/bootstrap/scss/forms/floating-labels",
                "../vendor/bootstrap/scss/transitions",
                "../vendor/bootstrap/scss/navbar",
                "../vendor/bootstrap/scss/progress",
                "../vendor/bootstrap/scss/list-group",
                "../vendor/bootstrap/scss/carousel",
                "../vendor/bootstrap/scss/spinners",
                "../vendor/bootstrap/scss/placeholders",
                "../vendor/bootstrap/scss/helpers/clearfix",
                "../vendor/bootstrap/scss/helpers/colored-links",
                "../vendor/bootstrap/scss/helpers/focus-ring",
                "../vendor/bootstrap/scss/helpers/icon-link",
                "../vendor/bootstrap/scss/helpers/ratio",
                "../vendor/bootstrap/scss/helpers/position",
                "../vendor/bootstrap/scss/helpers/stacks",
                "../vendor/bootstrap/scss/helpers/visually-hidden",
                "../vendor/bootstrap/scss/helpers/stretched-link",
                "../vendor/bootstrap/scss/helpers/text-truncation",
                "../vendor/bootstrap/scss/helpers/vr",
                "../vendor/bootstrap/scss/utilities/api",
                "themes/standalone_root",
                "utilities/scroll_fade_primitives",
                "components",
                "foundations/overlay_backdrop",
            ],
        )
        self.assertEqual(
            entrypoint_imports["moo-core.scss"],
            [
                "functions",
                "settings",
                "variables",
                "variables-dark",
                "maps",
                "mixins",
                "utilities",
                "themes/scoped_core",
                "foundations/core_global_primitives",
                "components",
                "foundations/core_state_layer",
                "foundations/overlay_backdrop",
            ],
        )

        components_imports = active_scss_import_list(
            (SCSS / "_components.scss").read_text(encoding="utf-8")
        )
        imported = set().union(*entrypoint_imports.values(), components_imports)
        for directory in (SCSS / "themes", SCSS / "foundations"):
            for target in owned_partial_targets(directory):
                self.assertIn(target, imported, f"{target} is not imported")

    def test_sidebar_aggregate_imports_ownership_layers_in_order(self) -> None:
        sidebar = (COMPONENTS_SCSS / "_sidebar.scss").read_text(encoding="utf-8")
        expected = [
            "components/sidebar/layout",
            "components/sidebar/menus",
            "components/sidebar/identity",
            "components/sidebar/inset",
            "components/sidebar/collapsed",
        ]
        imports = active_scss_import_list(sidebar)

        self.assertEqual(imports, expected)
        self.assertEqual(
            owned_partial_targets(COMPONENTS_SCSS / "sidebar"),
            set(expected),
        )

    def test_catalog_aggregate_imports_ownership_layers_in_order(self) -> None:
        catalog = (SITE_SCSS / "catalog.scss").read_text(encoding="utf-8")
        expected = [
            "catalog/settings",
            "catalog/shell",
            "catalog/home",
            "catalog/docs",
            "catalog/examples",
            "catalog/blocks",
            "catalog/code",
            "catalog/command",
            "catalog/acceptance",
        ]
        imports = [
            target
            for target in active_scss_import_list(catalog)
            if target.startswith("catalog/")
        ]

        self.assertEqual(imports, expected)
        self.assertEqual(owned_partial_targets(SITE_SCSS / "catalog"), set(expected))

    def test_catalog_settings_own_catalog_knobs_only(self) -> None:
        catalog_settings = (SITE_SCSS / "catalog/_settings.scss").read_text(
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

    def test_property_aware_gate_rejects_multiline_literals_and_interpolation(self) -> None:
        source = """
        .bad {
          border-width:
            999px;
          border-radius: #{999px};
          border-width: calc(var(--bs-border-width) + 1px);
        }
        """
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "_bad.scss"
            path.write_text(source, encoding="utf-8")
            offenders = shared_primitive_offenders((path,))

        self.assertEqual(len(offenders), 3)
        self.assertEqual(
            sum("border-width" in offender for offender in offenders),
            2,
        )
        self.assertTrue(any("border-radius" in offender for offender in offenders))

    def test_ordered_import_parser_ignores_commented_imports(self) -> None:
        source = """
        /* @import "catalog/block-commented"; */
        // @import "catalog/line-commented";
        @import "catalog/active";
        """

        self.assertEqual(active_scss_import_list(source), ["catalog/active"])

    def test_all_component_partials_are_imported(self) -> None:
        entrypoint = (SCSS / "moo-ui.scss").read_text(encoding="utf-8")
        components = (SCSS / "_components.scss").read_text(
            encoding="utf-8"
        )
        if '@import "components"' in entrypoint:
            entrypoint += "\n" + components
        imported_components = active_component_imports(entrypoint)

        aggregate_imports = active_scss_import_list(components)
        self.assertEqual(len(aggregate_imports), len(set(aggregate_imports)))
        self.assertIn("utilities/scroll_fade", aggregate_imports)
        self.assertTrue(
            all(
                target.startswith("components/")
                for target in aggregate_imports
                if target != "utilities/scroll_fade"
                and target != "foundations/focus"
                and not target.startswith("forms/")
                and target not in {
                    "tables",
                    "buttons",
                    "dropdown",
                    "button-group",
                    "nav",
                    "card",
                    "accordion",
                    "breadcrumb",
                    "pagination",
                    "badge",
                    "alert",
                    "close",
                    "toasts",
                    "modal",
                    "tooltip",
                    "popover",
                    "offcanvas",
                    "helpers/color-bg",
                }
            )
        )

        for path in sorted(COMPONENTS_SCSS.glob("_*.scss")):
            component = path.stem.removeprefix("_")
            self.assertIn(component, imported_components)

    def test_components_aggregate_imports_all_component_partials(self) -> None:
        components = SCSS / "_components.scss"

        self.assertTrue(components.is_file())
        imported_components = active_component_imports(
            components.read_text(encoding="utf-8")
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
            target = partial_import_target(path)
            self.assertIn(target, imports, f"{target} is not imported")

    def test_component_styles_consume_shared_primitives_only(self) -> None:
        self.assertEqual(
            shared_primitive_offenders(component_partials()),
            [],
        )

    def test_root_theme_consumers_use_shared_primitives_only(self) -> None:
        self.assertEqual(shared_primitive_offenders(ROOT_THEME_CONSUMER_SCSS), [])

    def test_foundations_use_shared_primitives_only(self) -> None:
        self.assertEqual(
            shared_primitive_offenders(tuple((SCSS / "foundations").rglob("_*.scss"))),
            [],
        )

    def test_catalog_chrome_uses_tokens_for_color_literals(self) -> None:
        offenders = [
            offender
            for path in catalog_style_partials()
            if path.name != "_settings.scss"
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
        settings = read_settings()
        settings_lines = settings.splitlines()

        # Bootstrap's native class family is .btn (not .button), so
        # Button's private tokens use --moo-btn-* to stay aligned with
        # the --bs-btn-* consumption variables they extend.
        token_prefix_aliases = {
            "button": ("--moo-button", "--moo-btn"),
        }

        for path in sorted(component_partials()):
            component = component_owner(path)
            prefix = f"--moo-{component.replace('_', '-')}"
            accepted = token_prefix_aliases.get(component, (prefix,))
            source = path.read_text(encoding="utf-8")
            tokens = set(re.findall(r"--moo-[\w-]+(?=\s*:)", source))

            for token in sorted(tokens):
                self.assertTrue(
                    any(token.startswith(p) for p in accepted),
                    f"{path.name}: {token} is outside the"
                    f" {'/'.join(accepted)}-* namespace",
                )

            for token in sorted(tokens):
                knob = f"${token.removeprefix('--')}"
                self.assertRegex(
                    settings,
                    rf"{re.escape(knob)}\s*:[^;]+!default;",
                    f"{token} must have a matching {knob} !default Sass knob",
                )
                declaration_line = next(
                    index
                    for index, line in enumerate(settings_lines)
                    if re.search(rf"^\s*{re.escape(knob)}\s*:", line)
                )
                rationale = " ".join(
                    line.removeprefix("//").strip().lower()
                    for line in settings_lines[max(0, declaration_line - 8):declaration_line]
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

    def test_component_custom_properties_use_bootstrap_or_moo_namespace(self) -> None:
        for path in sorted(component_partials()):
            source = strip_scss_comments(path.read_text(encoding="utf-8"))
            for token in sorted(set(CUSTOM_PROPERTY_DECLARATION.findall(source))):
                with self.subTest(path=path.name, token=token):
                    self.assertTrue(
                        token.startswith(("--bs-", "--moo-")),
                        f"{path.name}: {token} must use the --bs-* or --moo-* namespace",
                    )

    def test_visual_exception_values_are_configured_by_sass_knobs(self) -> None:
        settings = read_settings()
        component_sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in component_partials()
        }

        expected_knobs = (
            "$badge-border-color: transparent !default;",
            "$moo-close-button-border-color: transparent !default;",
            "$avatar-badge-ring-shadow: 0 0 0 $avatar-badge-ring-width var(--bs-body-bg) !default;",
            "$avatar-group-ring-shadow: 0 0 0 $avatar-group-ring-width var(--bs-body-bg) !default;",
        )
        for knob in expected_knobs:
            with self.subTest(knob=knob):
                self.assertIn(knob, settings)

        self.assertIn("border-color: $badge-border-color;", component_sources["_badge.scss"])
        self.assertIn(
            "--bs-btn-hover-border-color: #{$moo-close-button-border-color};",
            component_sources["_close_button.scss"],
        )
        self.assertIn(
            "border-color: $moo-close-button-border-color;",
            component_sources["_close_button.scss"],
        )
        self.assertIn(
            "box-shadow: $avatar-badge-ring-shadow;",
            component_sources["_avatar.scss"],
        )
        self.assertIn(
            "box-shadow: $avatar-group-ring-shadow;",
            component_sources["_avatar.scss"],
        )

    def test_root_and_core_theme_tokens_share_sass_sources(self) -> None:
        settings = read_settings()
        tokens_root = (SCSS / "themes/_standalone_root.scss").read_text(
            encoding="utf-8"
        )
        core_theme = (SCSS / "themes/_scoped_core.scss").read_text(
            encoding="utf-8"
        )

        for token, variables in MOO_THEME_TOKENS.items():
            for variable in variables:
                self.assertRegex(
                    settings,
                    rf"{re.escape(variable)}\s*:[^;]+!default;",
                    f"{token} must be backed by {variable} in the settings aggregate",
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
        settings = read_settings()
        for scale_variable in (
            "$box-shadow-sm:",
            "$box-shadow:",
            "$box-shadow-lg:",
            "$border-radius-xl:",
            "$focus-ring-width:",
            "$btn-font-size-sm:",
            "$btn-font-size-lg:",
        ):
            self.assertIn(scale_variable, settings)

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn("--bs-box-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);", css)
        self.assertIn("--bs-border-radius-xl: 0.75rem;", css)
        self.assertIn("--bs-focus-ring-width: 2px;", css)
