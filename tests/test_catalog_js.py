from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from tests.helpers import DIST, ROOT, CatalogTestCase
from tests.helpers.node_harness import NODE_PREAMBLE, NODE_TEST_TIMEOUT, VALID_DATA


CATALOG_JS = ROOT / "site/src/js/catalog"
MODULES = {
    "acceptance.js": "initAcceptancePortal",
    "theme.js": "initTheme",
    "catalog-filter.js": "initCatalogFilter",
    "catalog-view-toggle.js": "initCatalogViewToggle",
    "command.js": "initCommand",
    "examples-chart.js": "initExamplesChart",
    "examples-forms.js": "initExamplesForms",
    "examples-tasks.js": "initExamplesTasks",
    "examples-users.js": "initExamplesUsers",
    "toc.js": "initToc",
    "code-preview.js": "initCodePreview",
    "bootstrap-preview.js": "initBootstrapPreview",
    "home-motion.js": "initHomeMotion",
    "block-frame.js": "initBlockFrames",
    "card-spacing.js": "initCardSpacing",
    "settings-panel.js": "initSettingsPanel",
    "theme-builder-export.js": None,
    "theme-builder-schema.js": None,
}
LAZY_CATALOG_MODULES = {
    "examples-chart.js",
    "examples-tasks.js",
    "examples-users.js",
}
LAZY_COMPONENT_MODULES = (
    "combobox.js",
    "context-menu.js",
    "datatable.js",
    "datepicker.js",
    "slider.js",
)


def theme_preset_contract_paths() -> list[Path]:
    return [
        ROOT / "docs/contracts/THEME_PRESETS.md",
        ROOT.parent / "docs/contracts/THEME_PRESETS.md",
    ]


def without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^[ \t]*//.*$", "", source, flags=re.MULTILINE)


class CatalogJavaScriptTests(CatalogTestCase):
    def test_catalog_module_surface_is_explicit(self) -> None:
        discovered = {
            path.relative_to(CATALOG_JS).as_posix()
            for path in CATALOG_JS.rglob("*.js")
        }
        self.assertEqual(discovered, {*MODULES, "index.js"})

    def test_catalog_features_have_idempotent_init_and_disposal(self) -> None:
        for module_name, initializer in MODULES.items():
            if initializer is None:
                continue
            with self.subTest(module_name=module_name):
                source = without_comments(
                    (CATALOG_JS / module_name).read_text(encoding="utf-8")
                )
                self.assertIn(f"export function {initializer}(root = document)", source)
                self.assertIn("if (states.has(root))", source)
                if module_name == "examples-chart.js":
                    self.assertIn("states.set(root, release);", source)
                else:
                    self.assertIn("states.set(root, dispose);", source)
                self.assertIn("states.delete(root);", source)

    def test_catalog_feature_imports_have_no_document_side_effect(self) -> None:
        imports = "\n".join(
            f'import * as module{index} from "./site/src/js/catalog/{module_name}";\n'
            f'if ({json.dumps(initializer)} && typeof module{index}.{initializer} !== "function") process.exit(2);'
            for index, (module_name, initializer) in enumerate(MODULES.items())
        )
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", imports],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_theme_init_does_not_rewrite_the_prepainted_theme(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { initTheme } from "./site/src/js/catalog/theme.js";

const assignments = [];
const dataset = new Proxy({ bsTheme: "dark" }, {
  set(target, key, value) {
    assignments.push({ key, value });
    target[key] = value;
    return true;
  },
});
const button = {
  addEventListener() {},
  removeEventListener() {},
  setAttribute() {},
};
const view = {
  localStorage: { getItem: () => "dark", setItem() {} },
  matchMedia: () => ({
    matches: true,
    addEventListener() {},
    removeEventListener() {},
  }),
};
const root = {
  documentElement: { dataset },
  defaultView: view,
  querySelector: () => button,
};

initTheme(root);
console.log(JSON.stringify({ assignments, theme: dataset.bsTheme }));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(report["assignments"], [])
        self.assertEqual(report["theme"], "dark")

    def test_theme_builder_schema_migrates_legacy_state(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  normalizeThemeBuilderState,
} from "./site/src/js/catalog/theme-builder-schema.js";

const state = normalizeThemeBuilderState({
  style: "nova",
  baseColor: "blue",
  chartPalette: "pastel",
  headingFont: "system",
  bodyFont: "geist",
  radius: "compact",
});

console.log(JSON.stringify(state));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(
            state,
            {
                "schemaVersion": 1,
                "baseColor": "neutral",
                "themeColor": "blue",
                "chartColor": "neutral",
                "headingFont": "system",
                "bodyFont": "geist",
                "radius": "small",
            },
        )

    def test_theme_builder_schema_resolves_only_public_tokens(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./site/src/js/catalog/theme-builder-schema.js";

const tokens = resolveThemeBuilderTokens(normalizeThemeBuilderState({
  themeColor: "emerald",
  chartColor: "violet",
}));
const darkTokens = resolveThemeBuilderTokens(
  normalizeThemeBuilderState({ baseColor: "zinc" }),
  { theme: "dark" }
);
const tokenNames = Object.keys(tokens);
console.log(JSON.stringify({
  tokenNames,
  unknownTokens: tokenNames.filter(
    (token) => !PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST.includes(token)
  ),
  hasDataSelectorToken: tokenNames.some((token) => token.includes("data-moo")),
  primaryRgb: tokens["--bs-primary-rgb"],
  foreground: tokens["--moo-primary-foreground"],
  foregroundDark: tokens["--moo-primary-foreground-dark"],
  chart1: tokens["--moo-chart-1"],
  darkBodyBg: darkTokens["--bs-body-bg"],
  darkSurface: darkTokens["--moo-surface"],
  darkSecondaryBg: darkTokens["--bs-secondary-bg"],
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(case["unknownTokens"], [])
        self.assertFalse(case["hasDataSelectorToken"])
        self.assertEqual(case["primaryRgb"], "28, 107, 41")
        self.assertEqual(case["foreground"], "rgb(255, 255, 255)")
        self.assertEqual(case["foregroundDark"], "rgb(255, 255, 255)")
        self.assertEqual(case["chart1"], "rgb(174, 62, 201)")
        self.assertEqual(case["darkBodyBg"], "var(--moo-surface)")
        self.assertEqual(case["darkSurface"], "oklch(0.141 0.005 285.823)")
        self.assertEqual(case["darkSecondaryBg"], "var(--moo-muted-surface)")

    def test_theme_builder_neutral_base_aligns_bootstrap_borders(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./site/src/js/catalog/theme-builder-schema.js";

const lightTokens = resolveThemeBuilderTokens(
  normalizeThemeBuilderState({ baseColor: "neutral" }),
  { theme: "light" }
);
const darkTokens = resolveThemeBuilderTokens(
  normalizeThemeBuilderState({ baseColor: "neutral" }),
  { theme: "dark" }
);

console.log(JSON.stringify({
  lightMooBorder: lightTokens["--moo-border"] ?? null,
  lightBootstrapBorder: lightTokens["--bs-border-color"] ?? null,
  lightCardBorder: lightTokens["--bs-card-border-color"] ?? null,
  darkMooBorder: darkTokens["--moo-border"] ?? null,
  darkBootstrapBorder: darkTokens["--bs-border-color"] ?? null,
  darkCardBorder: darkTokens["--bs-card-border-color"] ?? null,
  darkSidebarBorder: darkTokens["--moo-sidebar-border"] ?? null,
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(case["lightMooBorder"], "#e4e4e7")
        self.assertEqual(case["lightBootstrapBorder"], "var(--moo-border)")
        self.assertEqual(case["lightCardBorder"], "var(--moo-border)")
        self.assertEqual(case["darkMooBorder"], "oklch(1 0 0 / 10%)")
        self.assertEqual(case["darkBootstrapBorder"], "var(--moo-border)")
        self.assertEqual(case["darkCardBorder"], "var(--moo-border)")
        self.assertEqual(case["darkSidebarBorder"], "oklch(1 0 0 / 10%)")

    def test_theme_builder_public_token_allow_list_is_alphabetized(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
} from "./site/src/js/catalog/theme-builder-schema.js";

console.log(JSON.stringify(PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        tokens = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(tokens, sorted(tokens))

    def test_theme_builder_action_colors_keep_primary_text_readable(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { resolveThemeBuilderTokens } from "./site/src/js/catalog/theme-builder-schema.js";

const themeColors = ["orange", "yellow", "lime", "green", "teal", "cyan", "azure"];
const parseRgb = (value) => value.match(/\\d+/g).map(Number);
const relativeLuminance = (rgb) => {
  const channels = rgb.map((channel) => {
    const value = channel / 255;
    return value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
};
const contrastRatio = (left, right) => {
  const [lighter, darker] = [relativeLuminance(left), relativeLuminance(right)]
    .sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
};

console.log(JSON.stringify(Object.fromEntries(themeColors.map((themeColor) => {
  const tokens = resolveThemeBuilderTokens({ themeColor });
  const primary = parseRgb(tokens["--moo-primary"]);
  const foreground = parseRgb(tokens["--moo-primary-foreground"]);
  return [themeColor, {
    primary: tokens["--moo-primary"],
    foreground: tokens["--moo-primary-foreground"],
    contrast: contrastRatio(primary, foreground),
  }];
}))));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        cases = json.loads(result.stdout.splitlines()[-1])
        expected_foregrounds = {
            "orange": "rgb(255, 255, 255)",
            "yellow": "rgb(17, 24, 39)",
            "lime": "rgb(255, 255, 255)",
            "green": "rgb(255, 255, 255)",
            "teal": "rgb(255, 255, 255)",
            "cyan": "rgb(255, 255, 255)",
            "azure": "rgb(255, 255, 255)",
        }
        for theme_color, expected_foreground in expected_foregrounds.items():
            tokens = cases[theme_color]
            with self.subTest(theme_color=theme_color):
                self.assertEqual(tokens["foreground"], expected_foreground)
                self.assertGreaterEqual(tokens["contrast"], 4.5)
        self.assertEqual(cases["yellow"]["primary"], "rgb(250, 204, 21)")

    def test_theme_builder_ignores_legacy_style_axis(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  THEME_BUILDER_DEFAULTS,
  THEME_BUILDER_OPTIONS,
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./site/src/js/catalog/theme-builder-schema.js";

const defaultTokens = resolveThemeBuilderTokens({});
const ignoredStyleCases = Object.fromEntries(
  ["soft", "solid", "tinted", "nova"].map((style) => [
    style,
    JSON.stringify(resolveThemeBuilderTokens({ style })) === JSON.stringify(defaultTokens),
  ])
);
const tokens = resolveThemeBuilderTokens({
  style: "tinted",
  baseColor: "zinc",
  themeColor: "blue",
});
const tokenNames = Object.keys(tokens);
const normalized = normalizeThemeBuilderState({ style: "nova", baseColor: "zinc" });

console.log(JSON.stringify({
  defaultKeys: Object.keys(THEME_BUILDER_DEFAULTS),
  optionKeys: Object.keys(THEME_BUILDER_OPTIONS),
  options: THEME_BUILDER_OPTIONS,
  normalizedKeys: Object.keys(normalized),
  ignoredStyleCases,
  mutedSurface: tokens["--moo-muted-surface"],
  cardBg: tokens["--bs-card-bg"],
  sidebarAccent: tokens["--moo-sidebar-accent"],
  unknownTokens: tokenNames.filter(
    (token) => !PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST.includes(token)
  ),
  hasDataSelectorToken: tokenNames.some((token) => token.includes("data-moo")),
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertNotIn("style", case["defaultKeys"])
        self.assertNotIn("style", case["optionKeys"])
        self.assertNotIn("style", case["normalizedKeys"])
        self.assertEqual(
            case["options"]["radius"],
            ["default", "none", "small", "medium", "large"],
        )
        self.assertEqual(
            case["ignoredStyleCases"],
            {"soft": True, "solid": True, "tinted": True, "nova": True},
        )
        self.assertEqual(
            case["mutedSurface"],
            "oklch(0.967 0.001 286.375)",
        )
        self.assertEqual(
            case["cardBg"],
            "oklch(1 0 0)",
        )
        self.assertEqual(
            case["sidebarAccent"],
            "color-mix(in srgb, var(--moo-ring) 10%, var(--moo-sidebar))",
        )
        self.assertEqual(case["unknownTokens"], [])
        self.assertFalse(case["hasDataSelectorToken"])

    def test_theme_builder_export_emits_json_and_safe_css(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
} from "./site/src/js/catalog/theme-builder-schema.js";
import {
  serializeThemeBuilderPresetCss,
  serializeThemeBuilderPresetJson,
} from "./site/src/js/catalog/theme-builder-export.js";

const candidate = {
  style: "soft",
  baseColor: "zinc",
  themeColor: "emerald",
  chartColor: "violet",
  headingFont: "system",
  bodyFont: "geist",
  radius: "compact",
  chartPalette: "pastel",
};
const css = serializeThemeBuilderPresetCss(candidate);
const json = JSON.parse(
  serializeThemeBuilderPresetJson(candidate, { mooUiVersion: "1.0.0-test" })
);
const declarationTokens = Array.from(
  css.matchAll(/^\\s*(--[\\w-]+):/gm),
  (match) => match[1]
);
console.log(JSON.stringify({
  css,
  json,
  forbiddenSelector: css.includes("[data-moo"),
  leakedCatalogToken: css.includes("--moo-catalog-font-family"),
  unknownTokens: declarationTokens.filter(
    (token) => !PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST.includes(token)
  ),
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        css = case["css"]
        self.assertIn(':root,\n[data-bs-theme="light"] {', css)
        self.assertIn('[data-bs-theme="dark"] {', css)
        self.assertIn("--bs-primary-rgb: 28, 107, 41;", css)
        self.assertIn("--moo-primary-foreground: rgb(255, 255, 255);", css)
        self.assertIn("--moo-primary-foreground-dark: rgb(255, 255, 255);", css)
        self.assertIn("--moo-chart-1: rgb(174, 62, 201);", css)
        self.assertIn("--bs-body-bg: var(--moo-surface);", css)
        self.assertIn("--moo-surface: oklch(1 0 0);", css)
        self.assertIn("--moo-surface: oklch(0.141 0.005 285.823);", css)
        self.assertIn("--moo-muted-surface: oklch(0.967 0.001 286.375);", css)
        self.assertIn("--bs-card-bg: oklch(1 0 0);", css)
        self.assertNotIn("color-mix(in srgb, var(--bs-body-bg) 92%", css)
        self.assertNotIn("color-mix(in srgb, var(--bs-body-bg) 98%", css)
        self.assertIn(
            "--moo-sidebar-accent: color-mix(in srgb, var(--moo-ring) 10%, var(--moo-sidebar));",
            css,
        )
        self.assertIn(
            "--moo-sidebar-accent: color-mix(in srgb, var(--moo-ring) 32%, var(--moo-sidebar));",
            css,
        )
        self.assertFalse(case["forbiddenSelector"])
        self.assertFalse(case["leakedCatalogToken"])
        self.assertEqual(case["unknownTokens"], [])
        self.assertEqual(
            case["json"],
            {
                "schemaVersion": 1,
                "mooUiVersion": "1.0.0-test",
                "baseColor": "zinc",
                "themeColor": "green",
                "chartColor": "purple",
                "headingFont": "system",
                "bodyFont": "geist",
                "radius": "small",
            },
        )

    def test_theme_builder_export_does_not_advertise_unresolved_rgb_companions(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
} from "./site/src/js/catalog/theme-builder-schema.js";
import {
  serializeThemeBuilderPresetCss,
} from "./site/src/js/catalog/theme-builder-export.js";

const unsupportedRgb = [
  "--bs-body-bg-rgb",
  "--bs-secondary-bg-rgb",
  "--bs-tertiary-bg-rgb",
];
const css = serializeThemeBuilderPresetCss({
  baseColor: "zinc",
  style: "soft",
  themeColor: "blue",
});
const declarationTokens = Array.from(
  css.matchAll(/^\\s*(--[\\w-]+):/gm),
  (match) => match[1]
);
console.log(JSON.stringify({
  cssRgb: unsupportedRgb.filter((token) => declarationTokens.includes(token)),
  allowListRgb: unsupportedRgb.filter((token) =>
    PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST.includes(token)
  ),
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(case["cssRgb"], [])
        self.assertEqual(case["allowListRgb"], [])

    def test_theme_builder_first_paint_payload_matches_contract(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  THEME_BUILDER_OPTIONS,
  createThemeBuilderFirstPaintPayload,
} from "./site/src/js/catalog/theme-builder-schema.js";
import {
  createThemeBuilderPreset,
} from "./site/src/js/catalog/theme-builder-export.js";

console.log(JSON.stringify({
  allowList: PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  options: THEME_BUILDER_OPTIONS,
  payload: createThemeBuilderFirstPaintPayload(),
  presetFields: Object.keys(createThemeBuilderPreset({})),
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        public_contract = ROOT / "docs/contracts/THEME_PRESETS.md"
        self.assertTrue(
            public_contract.is_file(),
            "missing public Theme Preset contract",
        )

        def contract_json_block(contract: str, name: str):
            match = re.search(
                rf"<!-- {re.escape(name)}:start -->\s*```json\s*(.*?)\s*```\s*<!-- {re.escape(name)}:end -->",
                contract,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(match, f"missing {name} contract block")
            return json.loads(match.group(1))

        for contract_path in theme_preset_contract_paths():
            if not contract_path.is_file():
                continue
            with self.subTest(contract_path=contract_path):
                contract = contract_path.read_text(encoding="utf-8")
                self.assertEqual(
                    contract_json_block(contract, "theme-preset-schema-fields"),
                    case["presetFields"],
                )
                self.assertEqual(
                    contract_json_block(contract, "theme-preset-schema-enums"),
                    case["options"],
                )
                self.assertEqual(
                    contract_json_block(
                        contract,
                        "theme-preset-public-token-allow-list",
                    ),
                    case["allowList"],
                )
                if contract_path == public_contract:
                    self.assertIn('"radius": "compact"', contract)
                    self.assertIn('normalizes that value to `"small"`', contract)
                    self.assertIn('`"compact"` is not emitted', contract)

        build_result = self.run_build()
        self.assertEqual(build_result.returncode, 0, build_result.stderr)
        page = (DIST / "index.html").read_text(encoding="utf-8")
        payload_match = re.search(
            r"const themeBuilderFirstPaint = (\{.*?\});\n",
            page,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(payload_match, "missing first-paint payload")
        self.assertEqual(json.loads(payload_match.group(1)), case["payload"])

    def test_theme_builder_first_paint_payload_is_defensive_copy(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  createThemeBuilderFirstPaintPayload,
  resolveThemeBuilderTokens,
} from "./site/src/js/catalog/theme-builder-schema.js";

const first = createThemeBuilderFirstPaintPayload();
first.defaults.baseColor = "mutated";
first.options.baseColor.push("mutated");
first.aliases.baseColor.slate = "mutated";
first.tokens.themeColor.blue["--bs-primary"] = "mutated";

const second = createThemeBuilderFirstPaintPayload();
const tokens = resolveThemeBuilderTokens({ themeColor: "blue" });

console.log(JSON.stringify({
  secondDefaultBaseColor: second.defaults.baseColor,
  secondBaseColorOptions: second.options.baseColor,
  secondSlateAlias: second.aliases.baseColor.slate,
  secondBluePrimary: second.tokens.themeColor.blue["--bs-primary"],
  resolvedBluePrimary: tokens["--bs-primary"],
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(case["secondDefaultBaseColor"], "neutral")
        self.assertNotIn("mutated", case["secondBaseColorOptions"])
        self.assertEqual(case["secondSlateAlias"], "mist")
        self.assertEqual(case["secondBluePrimary"], "rgb(6, 111, 209)")
        self.assertEqual(case["resolvedBluePrimary"], "rgb(6, 111, 209)")

    def test_theme_builder_first_paint_script_matches_schema_tokens(self) -> None:
        build_result = self.run_build()
        self.assertEqual(build_result.returncode, 0, build_result.stderr)
        page = (DIST / "index.html").read_text(encoding="utf-8")
        inline_scripts = re.findall(
            r"<script>\s*(\(\(\) => \{.*?\}\)\(\);)\s*</script>",
            page,
            flags=re.DOTALL,
        )
        inline_script = next(
            (script for script in inline_scripts if "themeBuilderFirstPaint" in script),
            None,
        )
        self.assertIsNotNone(inline_script, "missing Theme Builder first-paint script")

        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  THEME_BUILDER_DEFAULTS,
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./site/src/js/catalog/theme-builder-schema.js";

const inlineScript = process.env.MOO_THEME_BUILDER_FIRST_PAINT_SCRIPT;
const fixtures = [
  {
    label: "legacy alias light",
    theme: "light",
    state: { baseColor: "slate", chartPalette: "pastel" },
  },
  {
    label: "legacy action dark",
    theme: "dark",
    state: { baseColor: "blue", chartPalette: "violet" },
  },
  {
    label: "legacy style ignored",
    theme: "light",
    state: { style: "nova", baseColor: "zinc" },
  },
  {
    label: "full modern light",
    theme: "light",
    state: {
      style: "tinted",
      baseColor: "mauve",
      themeColor: "amber",
      chartColor: "emerald",
      headingFont: "geist",
      bodyFont: "system",
      radius: "large",
    },
  },
  {
    label: "invalid enums dark",
    theme: "dark",
    applies: false,
    state: {
      style: "broken",
      baseColor: "broken",
      themeColor: "broken",
      chartColor: "broken",
      headingFont: "broken",
      bodyFont: "broken",
      radius: "broken",
    },
  },
  {
    label: "stored defaults dark",
    theme: "dark",
    applies: false,
    state: {},
  },
];

function makeStyle() {
  const values = {};
  return {
    values,
    setProperty(name, value) {
      values[name] = value;
    },
  };
}

function makeStorage(fixture) {
  const values = new Map([
    ["moo:theme", fixture.theme],
    ["moo:theme-builder", JSON.stringify(fixture.state)],
  ]);
  return {
    getItem: (key) => values.get(key) ?? null,
  };
}

function expectedDataset(state, mode) {
  const dataset = { bsTheme: mode };
  Object.entries({
    baseColor: "mooCatalogThemeBuilderBaseColor",
    themeColor: "mooCatalogThemeBuilderThemeColor",
  }).forEach(([key, datasetKey]) => {
    if (state[key] !== THEME_BUILDER_DEFAULTS[key]) {
      dataset[datasetKey] = state[key];
    }
  });
  return dataset;
}

function diffObject(actual, expected) {
  const keys = new Set([...Object.keys(actual), ...Object.keys(expected)]);
  return Array.from(keys)
    .filter((key) => actual[key] !== expected[key])
    .map((key) => ({ key, actual: actual[key] ?? null, expected: expected[key] ?? null }));
}

function runInlineScript(fixture) {
  const style = makeStyle();
  const documentElement = {
    // The real document runs the theme-restoration inline script before the
    // Theme Builder first-paint script. Seed the same state here so dark
    // fixtures exercise the catalog-surface token branch.
    dataset: { bsTheme: fixture.theme },
    dir: "ltr",
    style,
  };
  globalThis.window = {
    localStorage: makeStorage(fixture),
    matchMedia: () => ({ matches: fixture.theme === "dark" }),
    setTimeout: () => 0,
  };
  globalThis.document = {
    documentElement,
    querySelector: () => null,
  };

  eval(inlineScript);

  return {
    dataset: { ...documentElement.dataset },
    tokens: style.values,
  };
}

const reports = fixtures.map((fixture) => {
  const actual = runInlineScript(fixture);
  const state = normalizeThemeBuilderState(fixture.state);
  const expectedTokens =
    fixture.applies === false
      ? {}
      : resolveThemeBuilderTokens(state, {
          theme: fixture.theme,
          surface: "catalog",
        });
  const expectedData =
    fixture.applies === false
      ? { bsTheme: fixture.theme }
      : expectedDataset(state, fixture.theme);
  return {
    label: fixture.label,
    tokenDiff: diffObject(actual.tokens, expectedTokens),
    datasetDiff: diffObject(actual.dataset, expectedData),
  };
});
const failures = reports.filter(
  (report) => report.tokenDiff.length || report.datasetDiff.length
);
if (failures.length) {
  console.error(JSON.stringify(failures, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(reports.map((report) => report.label)));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
            env={
                **os.environ,
                "MOO_THEME_BUILDER_FIRST_PAINT_SCRIPT": inline_script,
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout.splitlines()[-1]),
            [
                "legacy alias light",
                "legacy action dark",
                "legacy style ignored",
                "full modern light",
                "invalid enums dark",
                "stored defaults dark",
            ],
        )

    def test_theme_builder_resolver_surface_option_is_preserved(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { resolveThemeBuilderTokens } from "./site/src/js/catalog/theme-builder-schema.js";

const candidate = { baseColor: "zinc", chartColor: "neutral" };
const defaultTokens = resolveThemeBuilderTokens(candidate);
const exportTokens = resolveThemeBuilderTokens(candidate, { surface: "export" });
const catalogTokens = resolveThemeBuilderTokens(candidate, { surface: "catalog" });

console.log(JSON.stringify({
  defaultEqualsExport: JSON.stringify(defaultTokens) === JSON.stringify(exportTokens),
  exportBodyBg: exportTokens["--bs-body-bg"] ?? null,
  exportBodyColor: exportTokens["--bs-body-color"] ?? null,
  exportSurface: exportTokens["--moo-surface"] ?? null,
  exportForeground: exportTokens["--moo-foreground"] ?? null,
  exportSidebar: exportTokens["--moo-sidebar"] ?? null,
  exportSidebarForeground: exportTokens["--moo-sidebar-foreground"] ?? null,
  catalogBodyBg: catalogTokens["--bs-body-bg"] ?? null,
  catalogBodyColor: catalogTokens["--bs-body-color"] ?? null,
  catalogCardBg: catalogTokens["--bs-card-bg"] ?? null,
  catalogSurface: catalogTokens["--moo-surface"] ?? null,
  catalogForeground: catalogTokens["--moo-foreground"] ?? null,
  catalogSecondaryColor: catalogTokens["--bs-secondary-color"] ?? null,
  catalogMutedForeground: catalogTokens["--moo-muted-foreground"] ?? null,
  catalogSidebar: catalogTokens["--moo-sidebar"] ?? null,
  catalogSidebarForeground: catalogTokens["--moo-sidebar-foreground"] ?? null,
  catalogChart1: catalogTokens["--moo-chart-1"] ?? null,
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(case["defaultEqualsExport"])
        self.assertEqual(case["exportBodyBg"], "var(--moo-surface)")
        self.assertEqual(case["exportBodyColor"], "var(--moo-foreground)")
        self.assertEqual(case["exportSurface"], "oklch(1 0 0)")
        self.assertEqual(case["exportForeground"], "oklch(0.141 0.005 285.823)")
        self.assertEqual(case["exportSidebar"], "oklch(0.985 0 0)")
        self.assertEqual(case["exportSidebarForeground"], "oklch(0.141 0.005 285.823)")
        self.assertEqual(case["catalogBodyBg"], "var(--moo-surface)")
        self.assertIsNone(case["catalogBodyColor"])
        self.assertEqual(case["catalogCardBg"], "oklch(1 0 0)")
        self.assertEqual(case["catalogSurface"], "oklch(1 0 0)")
        self.assertIsNone(case["catalogForeground"])
        self.assertIsNone(case["catalogSecondaryColor"])
        self.assertIsNone(case["catalogMutedForeground"])
        self.assertEqual(case["catalogSidebar"], "oklch(0.985 0 0)")
        self.assertIsNone(case["catalogSidebarForeground"])
        self.assertEqual(case["catalogChart1"], "rgb(82, 82, 91)")

    def test_theme_builder_settings_options_match_schema(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { THEME_BUILDER_OPTIONS } from "./site/src/js/catalog/theme-builder-schema.js";
console.log(JSON.stringify(THEME_BUILDER_OPTIONS));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        schema_options = json.loads(result.stdout.splitlines()[-1])
        template = (ROOT / "site/src/includes/settings-panel.html.jinja").read_text(
            encoding="utf-8"
        )

        def kebab_case(value: str) -> str:
            return re.sub(r"(?<!^)([A-Z])", r"-\1", value).lower()

        for key, expected in schema_options.items():
            hook = f"data-moo-catalog-theme-builder-{kebab_case(key)}"
            pattern = (
                rf'"{re.escape(hook)}",\s*'
                r"\[(.*?)\]\s*"
                r'(?:,\s*selected="[^"]+")?\s*'
                r'(?:,\s*swatch_group="[^"]+")?\s*'
                r'(?:,\s*preview_group="[^"]+")?\s*'
                r"\)\s*\}\}"
            )
            match = re.search(pattern, template, flags=re.DOTALL)
            self.assertIsNotNone(match, f"missing settings hook for {key}")
            actual = re.findall(r'\{"value":\s*"([^"]+)"', match.group(1))
            self.assertEqual(actual, expected, key)

        self.assertNotIn("data-moo-catalog-theme-builder-style", template)
        self.assertNotIn("moo-theme-builder-style", template)
        self.assertNotIn("settings_radius_dropdown", template)
        self.assertNotIn("moo-settings-panel__radius", template)

    def test_theme_builder_settings_panel_omits_surface_style_axis(self) -> None:
        template = (ROOT / "site/src/includes/settings-panel.html.jinja").read_text(
            encoding="utf-8"
        )

        self.assertNotIn('"Surface"', template)
        self.assertNotIn('"Style"', template)
        self.assertNotIn("data-moo-catalog-theme-builder-preview", template)
        self.assertNotIn("moo-settings-panel__surface-preview", template)

    def test_settings_direction_uses_standard_theme_grid_size(self) -> None:
        template = (ROOT / "site/src/includes/settings-panel.html.jinja").read_text(
            encoding="utf-8"
        )
        direction_start = template.index('{% call fieldset("Direction"')
        direction_markup = template[
            direction_start : template.index("{{ separator() }}", direction_start)
        ]

        self.assertRegex(
            direction_markup,
            r'class="[^"]*\bmoo-settings-panel__theme-group\b',
        )
        self.assertNotIn("moo-settings-panel__theme-group--compact", direction_markup)

    def test_examples_chart_delegates_to_the_public_chart_root(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                NODE_PREAMBLE.replace(
                    'import MooChart from "./src/js/components/chart.js";',
                    'import MooChart from "./src/js/components/chart.js";\n'
                    'import { initExamplesChart } from "./site/src/js/catalog/examples-chart.js";',
                )
                + f"""
const roots = [makeRoot({{"data-chart": "line", "data-chart-data": {json.dumps(VALID_DATA)}}})];
const catalogRoot = {{
  querySelectorAll: (selector) => (selector === ".chart" ? roots : []),
}};
const release = initExamplesChart(catalogRoot);
const sameRelease = initExamplesChart(catalogRoot);
const initialized = MooChart.getInstance(roots[0]) instanceof MooChart;
release();
const disposed = MooChart.getInstance(roots[0]) === null;
report("catalog-delegation", {{
  sameRelease: release === sameRelease,
  initialized,
  disposed,
}});
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertTrue(lines, f"No report emitted; stderr: {result.stderr}")
        self.assertEqual(
            json.loads(lines[-1]),
            {
                "name": "catalog-delegation",
                "ok": True,
                "sameRelease": True,
                "initialized": True,
                "disposed": True,
            },
        )

    def test_component_toc_links_top_level_sections_and_examples_in_dom_order(
        self,
    ) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { initToc } from "./site/src/js/catalog/toc.js";

const elementsById = new Map();
let top = 0;

function makeClassList(element) {
  return {
    toggle(name, force) {
      const classes = new Set((element.className || "").split(/\\s+/).filter(Boolean));
      if (force) classes.add(name);
      else classes.delete(name);
      element.className = Array.from(classes).join(" ");
    },
  };
}

function element(tagName, attrs = {}, textContent = "") {
  const attributes = new Map(Object.entries(attrs));
  const node = {
    nodeType: 1,
    tagName: tagName.toUpperCase(),
    className: attrs.class || "",
    textContent,
    children: [],
    hidden: false,
    style: {},
    classList: null,
    appendChild(child) {
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    remove() {
      if (!this.parentElement) return;
      this.parentElement.children = this.parentElement.children.filter(
        (child) => child !== this,
      );
    },
    getAttribute(name) {
      if (name === "class") return this.className;
      if (name === "href" && this.href) return this.href;
      return attributes.has(name) ? attributes.get(name) : null;
    },
    setAttribute(name, value) {
      attributes.set(name, String(value));
      if (name === "class") this.className = String(value);
      if (name === "href") this.href = String(value);
    },
    removeAttribute(name) {
      attributes.delete(name);
    },
    addEventListener() {},
    removeEventListener() {},
    matches(selector) {
      if (selector === "h2[id]") return this.tagName === "H2" && Boolean(this.getAttribute("id"));
      if (selector === ".moo-example[aria-labelledby]") {
        return (this.className || "").split(/\\s+/).includes("moo-example")
          && Boolean(this.getAttribute("aria-labelledby"));
      }
      return false;
    },
    querySelector(selector) {
      if (selector === "[data-moo-component-toc-nav]") {
        return this.children.find((child) => child.getAttribute("data-moo-component-toc-nav") !== null) || null;
      }
      return null;
    },
    querySelectorAll() {
      return [];
    },
    getBoundingClientRect() {
      top += 48;
      return { top, bottom: top + 24, left: 0, right: 160, width: 160, height: 24 };
    },
  };
  node.classList = makeClassList(node);
  const id = node.getAttribute("id");
  if (id) elementsById.set(id, node);
  return node;
}

const view = {
  Node: { DOCUMENT_POSITION_FOLLOWING: 4 },
  location: { hash: "" },
  history: { pushState() {} },
  scrollX: 0,
  scrollY: 0,
  setTimeout(callback) { callback(); return 1; },
  clearTimeout() {},
  requestAnimationFrame(callback) { callback(); return 1; },
  cancelAnimationFrame() {},
  getComputedStyle() { return { fontSize: "16px" }; },
  matchMedia() { return { matches: false }; },
  scrollTo() {},
  addEventListener() {},
  removeEventListener() {},
};

const componentNav = element("nav", { "data-moo-component-toc-nav": "" });
const componentToc = element("aside", { "data-moo-component-toc": "" });
componentToc.appendChild(componentNav);

const usage = element("h2", { id: "usage" }, "Usage");
const exampleTitle = element("h2", { id: "application-shell" }, "Application shell");
const example = element(
  "section",
  { class: "moo-example", "aria-labelledby": "application-shell" },
);
const composition = element("h2", { id: "composition" }, "Composition");
const anatomy = element("h2", { id: "sidebar-html-anatomy" }, "HTML Anatomy");
const componentExamples = element("div", { class: "moo-component-examples" });
componentExamples.children = [usage, example, composition, anatomy];

const main = element("main", { class: "moo-catalog__main" });
main.scrollTop = 0;
main.clientHeight = 800;
main.scrollHeight = 1600;
main.scrollTo = ({ top: nextTop }) => { main.scrollTop = nextTop; };

const root = {
  defaultView: view,
  documentElement: element("html"),
  createElement: (tagName) => element(tagName),
  getElementById: (id) => elementsById.get(id) || null,
  querySelector(selector) {
    if (selector === "[data-moo-component-toc]") return componentToc;
    if (selector === ".moo-component-examples") return componentExamples;
    if (selector === ".moo-catalog__main") return main;
    if (selector === "[data-moo-chart-template-nav]") return null;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === ".moo-component-examples > .moo-example[aria-labelledby]") {
      return [example];
    }
    if (selector === ".moo-doc-toc .nav-link") {
      return componentNav.children;
    }
    return [];
  },
};

initToc(root);

console.log(JSON.stringify({
  hidden: componentToc.hidden,
  links: componentNav.children.map((link) => ({
    href: link.getAttribute("href"),
    text: link.textContent,
  })),
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertFalse(case["hidden"])
        self.assertEqual(
            case["links"],
            [
                {"href": "#usage", "text": "Usage"},
                {"href": "#application-shell", "text": "Application shell"},
                {"href": "#composition", "text": "Composition"},
                {"href": "#sidebar-html-anatomy", "text": "HTML Anatomy"},
            ],
        )

    def test_component_toc_preserves_server_rendered_links_without_duplicates(
        self,
    ) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { initToc } from "./site/src/js/catalog/toc.js";

const elementsById = new Map();
let top = 0;

function makeClassList(element) {
  return {
    toggle(name, force) {
      const classes = new Set((element.className || "").split(/\\s+/).filter(Boolean));
      if (force) classes.add(name);
      else classes.delete(name);
      element.className = Array.from(classes).join(" ");
    },
  };
}

function element(tagName, attrs = {}, textContent = "") {
  const attributes = new Map(Object.entries(attrs));
  const node = {
    nodeType: 1,
    tagName: tagName.toUpperCase(),
    className: attrs.class || "",
    textContent,
    children: [],
    hidden: false,
    style: {},
    classList: null,
    appendChild(child) {
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    remove() {
      if (!this.parentElement) return;
      this.parentElement.children = this.parentElement.children.filter(
        (child) => child !== this,
      );
    },
    getAttribute(name) {
      if (name === "class") return this.className;
      if (name === "href" && this.href) return this.href;
      return attributes.has(name) ? attributes.get(name) : null;
    },
    setAttribute(name, value) {
      attributes.set(name, String(value));
      if (name === "class") this.className = String(value);
      if (name === "href") this.href = String(value);
    },
    removeAttribute(name) {
      attributes.delete(name);
    },
    addEventListener() {},
    removeEventListener() {},
    matches(selector) {
      if (selector === "h2[id]") return this.tagName === "H2" && Boolean(this.getAttribute("id"));
      if (selector === ".moo-example[aria-labelledby]") {
        return (this.className || "").split(/\\s+/).includes("moo-example")
          && Boolean(this.getAttribute("aria-labelledby"));
      }
      return false;
    },
    querySelector(selector) {
      if (selector === "[data-moo-component-toc-nav]") {
        return this.children.find((child) => child.getAttribute("data-moo-component-toc-nav") !== null) || null;
      }
      return null;
    },
    querySelectorAll() {
      return [];
    },
    getBoundingClientRect() {
      top += 48;
      return { top, bottom: top + 24, left: 0, right: 160, width: 160, height: 24 };
    },
  };
  node.classList = makeClassList(node);
  const id = node.getAttribute("id");
  if (id) elementsById.set(id, node);
  return node;
}

const view = {
  Node: { DOCUMENT_POSITION_FOLLOWING: 4 },
  location: { hash: "" },
  history: { pushState() {} },
  scrollX: 0,
  scrollY: 0,
  setTimeout(callback) { callback(); return 1; },
  clearTimeout() {},
  requestAnimationFrame(callback) { callback(); return 1; },
  cancelAnimationFrame() {},
  getComputedStyle() { return { fontSize: "16px" }; },
  matchMedia() { return { matches: false }; },
  scrollTo() {},
  addEventListener() {},
  removeEventListener() {},
};

const componentNav = element("nav", { "data-moo-component-toc-nav": "" });
const componentToc = element("aside", { "data-moo-component-toc": "" });
componentToc.hidden = true;
componentToc.appendChild(componentNav);
componentNav.appendChild(element("a", { class: "nav-link", href: "#usage" }, "Usage"));
componentNav.appendChild(element("a", { class: "nav-link", href: "#basic" }, "Basic"));

const usage = element("h2", { id: "usage" }, "Usage");
const basicTitle = element("h2", { id: "basic" }, "Basic");
const basic = element(
  "section",
  { class: "moo-example", "aria-labelledby": "basic" },
);
const componentExamples = element("div", { class: "moo-component-examples" });
componentExamples.children = [usage, basic];

const main = element("main", { class: "moo-catalog__main" });
main.scrollTop = 0;
main.clientHeight = 800;
main.scrollHeight = 1600;
main.scrollTo = ({ top: nextTop }) => { main.scrollTop = nextTop; };

const root = {
  defaultView: view,
  documentElement: element("html"),
  createElement: (tagName) => element(tagName),
  getElementById: (id) => elementsById.get(id) || null,
  querySelector(selector) {
    if (selector === "[data-moo-component-toc]") return componentToc;
    if (selector === ".moo-component-examples") return componentExamples;
    if (selector === ".moo-catalog__main") return main;
    if (selector === "[data-moo-chart-template-nav]") return null;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === ".moo-doc-toc .nav-link") {
      return componentNav.children;
    }
    return [];
  },
};

initToc(root);

console.log(JSON.stringify({
  hidden: componentToc.hidden,
  links: componentNav.children.map((link) => ({
    href: link.getAttribute("href"),
    text: link.textContent,
  })),
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertFalse(case["hidden"])
        self.assertEqual(
            case["links"],
            [
                {"href": "#usage", "text": "Usage"},
                {"href": "#basic", "text": "Basic"},
            ],
        )

    def test_examples_chart_import_resolves_to_the_canonical_bundle(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        built = (DIST / "assets/js/catalog/examples-chart.js").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            built,
            r'import MooChart from "\.\./components/chart\.js\?v=[0-9a-f]+";',
        )
        self.assertTrue((DIST / "assets/js/components/chart.js").is_file())
        self.assertNotIn("src/js/components", without_comments(built))

    def test_build_versions_dynamic_catalog_imports(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        built = without_comments(
            (DIST / "assets/js/catalog/index.js").read_text(encoding="utf-8")
        )
        for module_name in LAZY_CATALOG_MODULES:
            with self.subTest(module_name=module_name):
                self.assertRegex(
                    built,
                    rf'import\("\./{re.escape(module_name)}\?v=[0-9a-f]{{12}}"\)',
                )
        for module_name in LAZY_COMPONENT_MODULES:
            with self.subTest(module_name=module_name):
                self.assertRegex(
                    built,
                    rf'import\("\.\./components/{re.escape(module_name)}\?v=[0-9a-f]{{12}}"\)',
                )
        self.assertNotIn("../../../../src/js/components", built)

    def test_examples_chart_themeing_moves_with_the_public_component(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-chart.js").read_text(encoding="utf-8")
        )

        # Theming, palettes, and re-theme observers all live in the public
        # MooChart now; the adapter keeps zero Chart.js knowledge.
        self.assertNotIn("lightPalette", source)
        self.assertNotIn("darkPalette", source)
        self.assertNotIn("--bs-info-text-emphasis", source)
        self.assertNotIn("color-mix", source)
        self.assertNotIn("datasetType", source)

    def test_settings_theme_builder_state_attributes_are_catalog_scoped(self) -> None:
        source = without_comments(
            (CATALOG_JS / "settings-panel.js").read_text(encoding="utf-8")
        )
        styles = without_comments(
            (ROOT / "site/scss/catalog/_docs.scss").read_text(encoding="utf-8")
        )

        self.assertNotIn("mooThemeStyle", source)
        self.assertNotIn("mooBaseColor", source)
        self.assertNotIn("data-moo-theme-style", styles)
        self.assertNotIn("data-moo-base-color", styles)
        self.assertNotIn("mooCatalogThemeBuilderStyle", source)
        self.assertIn("mooCatalogThemeBuilderBaseColor", source)
        self.assertIn("data-moo-catalog-theme-builder-updating", styles)
        self.assertNotIn("data-moo-catalog-theme-builder-style=", styles)
        self.assertNotIn(
            "[data-moo-catalog-theme-builder-theme-color] .moo-catalog",
            styles,
        )

    def test_settings_theme_builder_applies_tokens_persistence_and_reset(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { initSettingsPanel } from "./site/src/js/catalog/settings-panel.js";

const storage = new Map();
const localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
};

function makeClassList(initial = []) {
  const values = new Set(initial);
  return {
    toggle(name, force) {
      const shouldAdd = force ?? !values.has(name);
      if (shouldAdd) values.add(name);
      else values.delete(name);
      return shouldAdd;
    },
    contains: (name) => values.has(name),
  };
}

function makeEmitter(node = {}) {
  const listeners = new Map();
  node.addEventListener = (type, handler) => {
    listeners.set(type, [...(listeners.get(type) || []), handler]);
  };
  node.removeEventListener = (type, handler) => {
    listeners.set(
      type,
      (listeners.get(type) || []).filter((candidate) => candidate !== handler)
    );
  };
  node.dispatch = (type) => {
    (listeners.get(type) || []).forEach((handler) =>
      handler({ type, currentTarget: node, target: node })
    );
  };
  node.click = () => node.dispatch("click");
  return node;
}

function makeStyle() {
  const values = new Map();
  return {
    setProperty: (name, value) => values.set(name, value),
    removeProperty: (name) => values.delete(name),
    getPropertyValue: (name) => values.get(name) || "",
  };
}

function makeOption(value, label) {
  const attributes = {};
  return makeEmitter({
    dataset: { mooCatalogThemeBuilderOption: value },
    classList: makeClassList(),
    attributes,
    setAttribute: (name, value) => {
      attributes[name] = String(value);
    },
    querySelector: (selector) =>
      selector === "[data-moo-catalog-theme-builder-option-label]"
        ? { textContent: label }
        : null,
  });
}

function makeControl(labels) {
  const options = Object.entries(labels).map(([value, label]) =>
    makeOption(value, label)
  );
  const value = { textContent: "" };
  return {
    options,
    value,
    root: makeEmitter({
      querySelectorAll: (selector) =>
        selector === "[data-moo-catalog-theme-builder-option]" ? options : [],
      querySelector: (selector) =>
        selector === "[data-moo-catalog-theme-builder-value]" ? value : null,
    }),
  };
}

function makeRadio(value, checked = false) {
  return makeEmitter({ value, checked });
}

const selectors = {
  baseColor: "[data-moo-catalog-theme-builder-base-color]",
  themeColor: "[data-moo-catalog-theme-builder-theme-color]",
  chartColor: "[data-moo-catalog-theme-builder-chart-color]",
  headingFont: "[data-moo-catalog-theme-builder-heading-font]",
  bodyFont: "[data-moo-catalog-theme-builder-body-font]",
  radius: "[data-moo-catalog-theme-builder-radius]",
};

const controls = {
  baseColor: makeControl({ neutral: "Neutral", zinc: "Zinc" }),
  themeColor: makeControl({ neutral: "Neutral", blue: "Blue" }),
  chartColor: makeControl({ neutral: "Neutral", teal: "Teal" }),
  headingFont: makeControl({ default: "Default", system: "System" }),
  bodyFont: makeControl({ default: "Default", geist: "Geist" }),
  radius: makeControl({
    default: "Default",
    none: "None",
    small: "Small",
    medium: "Medium",
    large: "Large",
  }),
};

const fieldRoots = Object.fromEntries(
  Object.entries(selectors).map(([key, selector]) => [selector, controls[key].root])
);
const reset = makeEmitter();
const themeInputs = [
  makeRadio("system", true),
  makeRadio("light"),
  makeRadio("dark"),
];
const sheet = makeEmitter({
  querySelectorAll: (selector) =>
    selector === "[data-moo-settings-theme]" ? themeInputs : [],
  querySelector: (selector) =>
    selector === "[data-moo-settings-reset]"
      ? reset
      : fieldRoots[selector] || null,
});
const documentElement = {
  dataset: { bsTheme: "light" },
  dir: "ltr",
  style: makeStyle(),
};
const root = {
  documentElement,
  defaultView: { localStorage, matchMedia: () => ({ matches: false }) },
  querySelector: (selector) => (selector === "#catalog-settings" ? sheet : null),
};

localStorage.setItem(
  "moo:theme-builder",
  JSON.stringify({
    style: "soft",
    baseColor: "blue",
    chartPalette: "pastel",
    headingFont: "system",
    bodyFont: "geist",
    radius: "compact",
  })
);

const dispose = initSettingsPanel(root);

function selectedValue(key) {
  return (
    controls[key].options.find((option) => option.classList.contains("active"))
      ?.dataset.mooCatalogThemeBuilderOption || null
  );
}

function optionFor(key, value) {
  return controls[key].options.find(
    (option) => option.dataset.mooCatalogThemeBuilderOption === value
  );
}

const initial = {
  styleDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderStyle"
  ),
  baseDataset: documentElement.dataset.mooCatalogThemeBuilderBaseColor,
  themeDataset: documentElement.dataset.mooCatalogThemeBuilderThemeColor,
  broadStyleDataset: Object.hasOwn(documentElement.dataset, "mooThemeStyle"),
  broadBaseDataset: Object.hasOwn(documentElement.dataset, "mooBaseColor"),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  primaryRgb: documentElement.style.getPropertyValue("--bs-primary-rgb"),
  foreground: documentElement.style.getPropertyValue("--moo-primary-foreground"),
  chart1: documentElement.style.getPropertyValue("--moo-chart-1"),
  mutedSurface: documentElement.style.getPropertyValue("--moo-muted-surface"),
  secondaryBg: documentElement.style.getPropertyValue("--bs-secondary-bg"),
  cardBg: documentElement.style.getPropertyValue("--bs-card-bg"),
  heading: documentElement.style.getPropertyValue("--moo-heading-font-family"),
  body: documentElement.style.getPropertyValue("--bs-body-font-family"),
  radius: documentElement.style.getPropertyValue("--bs-border-radius"),
  selectedBase: selectedValue("baseColor"),
  selectedTheme: selectedValue("themeColor"),
  selectedChart: selectedValue("chartColor"),
  migratedBuilder: JSON.parse(localStorage.getItem("moo:theme-builder")),
};

optionFor("baseColor", "zinc").dispatch("pointerenter");
const afterBasePreview = {
  baseDataset: documentElement.dataset.mooCatalogThemeBuilderBaseColor || null,
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  selectedBase: selectedValue("baseColor"),
  persistedBase: JSON.parse(localStorage.getItem("moo:theme-builder")).baseColor,
};
controls.baseColor.root.dispatch("hidden.bs.dropdown");
const afterBasePreviewHiddenClear = {
  baseDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderBaseColor"
  ),
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  selectedBase: selectedValue("baseColor"),
  persistedBase: JSON.parse(localStorage.getItem("moo:theme-builder")).baseColor,
};
optionFor("baseColor", "zinc").dispatch("pointerenter");
optionFor("baseColor", "zinc").dispatch("pointerleave");
const afterBasePreviewClear = {
  baseDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderBaseColor"
  ),
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  selectedBase: selectedValue("baseColor"),
  persistedBase: JSON.parse(localStorage.getItem("moo:theme-builder")).baseColor,
};

optionFor("themeColor", "neutral").dispatch("pointerenter");
const afterThemePreview = {
  themeDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderThemeColor"
  ),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  selectedTheme: selectedValue("themeColor"),
  persistedTheme: JSON.parse(localStorage.getItem("moo:theme-builder")).themeColor,
};
optionFor("themeColor", "neutral").dispatch("pointerleave");
const afterThemePreviewClear = {
  themeDataset: documentElement.dataset.mooCatalogThemeBuilderThemeColor || null,
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  selectedTheme: selectedValue("themeColor"),
  persistedTheme: JSON.parse(localStorage.getItem("moo:theme-builder")).themeColor,
};

optionFor("baseColor", "zinc").click();
const afterBaseLight = {
  baseDataset: documentElement.dataset.mooCatalogThemeBuilderBaseColor,
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  foreground: documentElement.style.getPropertyValue("--moo-foreground"),
  mutedForeground: documentElement.style.getPropertyValue("--moo-muted-foreground"),
  sidebar: documentElement.style.getPropertyValue("--moo-sidebar"),
  sidebarForeground: documentElement.style.getPropertyValue("--moo-sidebar-foreground"),
  bodyBg: documentElement.style.getPropertyValue("--bs-body-bg"),
  bodyColor: documentElement.style.getPropertyValue("--bs-body-color"),
  bodyBgRgb: documentElement.style.getPropertyValue("--bs-body-bg-rgb"),
  secondaryBg: documentElement.style.getPropertyValue("--bs-secondary-bg"),
  secondaryColor: documentElement.style.getPropertyValue("--bs-secondary-color"),
};

const darkInput = themeInputs.find((input) => input.value === "dark");
darkInput.checked = true;
darkInput.dispatch("change");
const afterThemeDark = {
  theme: documentElement.dataset.bsTheme,
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  foreground: documentElement.style.getPropertyValue("--moo-foreground"),
  mutedForeground: documentElement.style.getPropertyValue("--moo-muted-foreground"),
  sidebar: documentElement.style.getPropertyValue("--moo-sidebar"),
  sidebarForeground: documentElement.style.getPropertyValue("--moo-sidebar-foreground"),
  bodyBg: documentElement.style.getPropertyValue("--bs-body-bg"),
  bodyColor: documentElement.style.getPropertyValue("--bs-body-color"),
  bodyBgRgb: documentElement.style.getPropertyValue("--bs-body-bg-rgb"),
  secondaryColor: documentElement.style.getPropertyValue("--bs-secondary-color"),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  darkChecked: darkInput.checked,
};

optionFor("chartColor", "teal").dispatch("focusin");
const afterChartPreview = {
  chart5: documentElement.style.getPropertyValue("--moo-chart-5"),
  selectedChart: selectedValue("chartColor"),
  persistedChart: JSON.parse(localStorage.getItem("moo:theme-builder")).chartColor,
};
optionFor("chartColor", "teal").dispatch("focusout");
const afterChartPreviewClear = {
  chart5: documentElement.style.getPropertyValue("--moo-chart-5"),
  selectedChart: selectedValue("chartColor"),
  persistedChart: JSON.parse(localStorage.getItem("moo:theme-builder")).chartColor,
};

optionFor("chartColor", "teal").click();
const persisted = JSON.parse(localStorage.getItem("moo:theme-builder"));
const afterClick = {
  chart5: documentElement.style.getPropertyValue("--moo-chart-5"),
  selectedChart: selectedValue("chartColor"),
  persistedChart: persisted.chartColor,
};

reset.click();
const afterReset = {
  styleDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderStyle"
  ),
  baseDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderBaseColor"
  ),
  themeDataset: Object.hasOwn(
    documentElement.dataset,
    "mooCatalogThemeBuilderThemeColor"
  ),
  chart1: documentElement.style.getPropertyValue("--moo-chart-1"),
  bodyBg: documentElement.style.getPropertyValue("--bs-body-bg"),
  bodyBgRgb: documentElement.style.getPropertyValue("--bs-body-bg-rgb"),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  primaryRgb: documentElement.style.getPropertyValue("--bs-primary-rgb"),
  selectedBase: selectedValue("baseColor"),
  selectedTheme: selectedValue("themeColor"),
  selectedChart: selectedValue("chartColor"),
  storedBuilder: localStorage.getItem("moo:theme-builder"),
};

dispose();
console.log(JSON.stringify({
  initial,
  afterBasePreview,
  afterBasePreviewHiddenClear,
  afterBasePreviewClear,
  afterThemePreview,
  afterThemePreviewClear,
  afterBaseLight,
  afterThemeDark,
  afterChartPreview,
  afterChartPreviewClear,
  afterClick,
  afterReset,
}));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertFalse(case["initial"]["styleDataset"])
        self.assertIsNone(case["initial"].get("baseDataset"))
        self.assertEqual(case["initial"]["themeDataset"], "blue")
        self.assertFalse(case["initial"]["broadStyleDataset"])
        self.assertFalse(case["initial"]["broadBaseDataset"])
        self.assertEqual(case["initial"]["primary"], "rgb(6, 111, 209)")
        self.assertEqual(case["initial"]["primaryRgb"], "6, 111, 209")
        self.assertEqual(case["initial"]["foreground"], "rgb(255, 255, 255)")
        self.assertEqual(case["initial"]["chart1"], "rgb(82, 82, 91)")
        self.assertEqual(
            case["initial"]["mutedSurface"],
            "",
        )
        self.assertEqual(case["initial"]["secondaryBg"], "")
        self.assertEqual(case["initial"]["cardBg"], "")
        self.assertEqual(
            case["initial"]["heading"],
            'system-ui, -apple-system, "Segoe UI", sans-serif',
        )
        self.assertEqual(
            case["initial"]["body"],
            '"Geist", system-ui, -apple-system, "Segoe UI", sans-serif',
        )
        self.assertEqual(case["initial"]["radius"], "0.25rem")
        self.assertEqual(case["initial"]["selectedBase"], "neutral")
        self.assertEqual(case["initial"]["selectedTheme"], "blue")
        self.assertEqual(case["initial"]["selectedChart"], "neutral")
        self.assertEqual(case["initial"]["migratedBuilder"]["schemaVersion"], 1)
        self.assertNotIn("style", case["initial"]["migratedBuilder"])
        self.assertEqual(case["initial"]["migratedBuilder"]["baseColor"], "neutral")
        self.assertEqual(case["initial"]["migratedBuilder"]["themeColor"], "blue")
        self.assertEqual(case["initial"]["migratedBuilder"]["chartColor"], "neutral")
        self.assertEqual(case["initial"]["migratedBuilder"]["radius"], "small")
        self.assertNotIn("chartPalette", case["initial"]["migratedBuilder"])
        self.assertEqual(case["afterBasePreview"]["baseDataset"], "zinc")
        self.assertEqual(case["afterBasePreview"]["surface"], "oklch(1 0 0)")
        self.assertEqual(case["afterBasePreview"]["selectedBase"], "neutral")
        self.assertEqual(case["afterBasePreview"]["persistedBase"], "neutral")
        self.assertFalse(case["afterBasePreviewHiddenClear"]["baseDataset"])
        self.assertEqual(case["afterBasePreviewHiddenClear"]["surface"], "")
        self.assertEqual(case["afterBasePreviewHiddenClear"]["selectedBase"], "neutral")
        self.assertEqual(case["afterBasePreviewHiddenClear"]["persistedBase"], "neutral")
        self.assertFalse(case["afterBasePreviewClear"]["baseDataset"])
        self.assertEqual(case["afterBasePreviewClear"]["surface"], "")
        self.assertEqual(case["afterBasePreviewClear"]["selectedBase"], "neutral")
        self.assertEqual(case["afterBasePreviewClear"]["persistedBase"], "neutral")
        self.assertFalse(case["afterThemePreview"]["themeDataset"])
        self.assertEqual(case["afterThemePreview"]["primary"], "")
        self.assertEqual(case["afterThemePreview"]["selectedTheme"], "blue")
        self.assertEqual(case["afterThemePreview"]["persistedTheme"], "blue")
        self.assertEqual(case["afterThemePreviewClear"]["themeDataset"], "blue")
        self.assertEqual(case["afterThemePreviewClear"]["primary"], "rgb(6, 111, 209)")
        self.assertEqual(case["afterThemePreviewClear"]["selectedTheme"], "blue")
        self.assertEqual(case["afterThemePreviewClear"]["persistedTheme"], "blue")
        self.assertEqual(case["afterBaseLight"]["baseDataset"], "zinc")
        self.assertEqual(case["afterBaseLight"]["surface"], "oklch(1 0 0)")
        self.assertEqual(case["afterBaseLight"]["foreground"], "")
        self.assertEqual(case["afterBaseLight"]["mutedForeground"], "")
        self.assertEqual(case["afterBaseLight"]["sidebar"], "oklch(0.985 0 0)")
        self.assertEqual(case["afterBaseLight"]["sidebarForeground"], "")
        self.assertEqual(case["afterBaseLight"]["bodyBg"], "var(--moo-surface)")
        self.assertEqual(case["afterBaseLight"]["bodyColor"], "")
        self.assertEqual(case["afterBaseLight"]["bodyBgRgb"], "")
        self.assertEqual(case["afterBaseLight"]["secondaryBg"], "var(--moo-muted-surface)")
        self.assertEqual(case["afterBaseLight"]["secondaryColor"], "")
        self.assertEqual(case["afterThemeDark"]["theme"], "dark")
        self.assertEqual(
            case["afterThemeDark"]["surface"],
            "oklch(0.141 0.005 285.823)",
        )
        self.assertEqual(case["afterThemeDark"]["foreground"], "")
        self.assertEqual(case["afterThemeDark"]["mutedForeground"], "")
        self.assertEqual(case["afterThemeDark"]["sidebar"], "oklch(0.21 0.006 285.885)")
        self.assertEqual(case["afterThemeDark"]["sidebarForeground"], "")
        self.assertEqual(case["afterThemeDark"]["bodyBg"], "var(--moo-surface)")
        self.assertEqual(case["afterThemeDark"]["bodyColor"], "")
        self.assertEqual(case["afterThemeDark"]["bodyBgRgb"], "")
        self.assertEqual(case["afterThemeDark"]["secondaryColor"], "")
        self.assertEqual(case["afterThemeDark"]["primary"], "rgb(6, 111, 209)")
        self.assertTrue(case["afterThemeDark"]["darkChecked"])
        self.assertEqual(case["afterChartPreview"]["chart5"], "rgb(7, 100, 72)")
        self.assertEqual(case["afterChartPreview"]["selectedChart"], "neutral")
        self.assertEqual(case["afterChartPreview"]["persistedChart"], "neutral")
        self.assertEqual(case["afterChartPreviewClear"]["chart5"], "rgb(39, 39, 42)")
        self.assertEqual(case["afterChartPreviewClear"]["selectedChart"], "neutral")
        self.assertEqual(case["afterChartPreviewClear"]["persistedChart"], "neutral")
        self.assertEqual(case["afterClick"]["chart5"], "rgb(7, 100, 72)")
        self.assertEqual(case["afterClick"]["selectedChart"], "teal")
        self.assertEqual(case["afterClick"]["persistedChart"], "teal")
        self.assertFalse(case["afterReset"]["styleDataset"])
        self.assertFalse(case["afterReset"]["baseDataset"])
        self.assertFalse(case["afterReset"]["themeDataset"])
        self.assertEqual(case["afterReset"]["chart1"], "")
        self.assertEqual(case["afterReset"]["bodyBg"], "")
        self.assertEqual(case["afterReset"]["bodyBgRgb"], "")
        self.assertEqual(case["afterReset"]["primary"], "")
        self.assertEqual(case["afterReset"]["primaryRgb"], "")
        self.assertEqual(case["afterReset"]["selectedBase"], "neutral")
        self.assertEqual(case["afterReset"]["selectedTheme"], "neutral")
        self.assertEqual(case["afterReset"]["selectedChart"], "neutral")
        self.assertIsNone(case["afterReset"]["storedBuilder"])

    def test_settings_theme_builder_does_not_write_default_tokens_without_storage(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import { initSettingsPanel } from "./site/src/js/catalog/settings-panel.js";

const writes = [];
const storage = new Map();
const localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
};

function makeEmitter(node = {}) {
  const listeners = new Map();
  node.addEventListener = (type, handler) => {
    listeners.set(type, [...(listeners.get(type) || []), handler]);
  };
  node.removeEventListener = (type, handler) => {
    listeners.set(
      type,
      (listeners.get(type) || []).filter((candidate) => candidate !== handler)
    );
  };
  return node;
}

const sheet = makeEmitter({
  querySelectorAll: () => [],
  querySelector: () => null,
});
const documentElement = {
  dataset: { bsTheme: "dark" },
  dir: "ltr",
  style: {
    setProperty: (name, value) => writes.push(["set", name, value]),
    removeProperty: (name) => writes.push(["remove", name]),
    getPropertyValue: () => "",
  },
};
const root = {
  documentElement,
  defaultView: {
    localStorage,
    matchMedia: () => ({ matches: true }),
    requestAnimationFrame: (callback) => callback(),
    setTimeout: (callback) => callback(),
  },
  querySelector: (selector) => (selector === "#catalog-settings" ? sheet : null),
};

const dispose = initSettingsPanel(root);
const report = {
  writes,
  dataset: { ...documentElement.dataset },
  storedBuilder: localStorage.getItem("moo:theme-builder"),
};
dispose();
console.log(JSON.stringify(report));
""",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(case["writes"], [])
        self.assertEqual(case["dataset"], {"bsTheme": "dark"})
        self.assertIsNone(case["storedBuilder"])

    def test_catalog_entrypoint_only_orchestrates_public_components(self) -> None:
        source = without_comments(
            (CATALOG_JS / "index.js").read_text(encoding="utf-8")
        )

        for module_name, initializer in MODULES.items():
            if initializer is None:
                continue
            static_import = (
                rf'import \{{ {initializer} \}} from "\./{re.escape(module_name)}";'
            )
            if module_name in LAZY_CATALOG_MODULES:
                self.assertNotRegex(source, static_import)
                self.assertIn(f'import("./{module_name}")', source)
            else:
                self.assertRegex(source, static_import)
            self.assertIn(f"{initializer}(root)", source)

        self.assertIn(
            'import Sidebar from "../../../../src/js/components/sidebar.js";',
            source,
        )
        for module_name in LAZY_COMPONENT_MODULES:
            with self.subTest(module_name=module_name):
                self.assertNotIn(
                    f'from "../../../../src/js/components/{module_name}";',
                    source,
                )
                self.assertIn(
                    f'import("../../../../src/js/components/{module_name}")',
                    source,
                )
        self.assertIn("Combobox.getOrCreateInstance(element)", source)
        self.assertIn("Sidebar.getOrCreateInstance(element)", source)
        self.assertIn("DataTable.getOrCreateInstance(element)", source)
        self.assertIn("Datepicker.getOrCreateInstance(element)", source)
        self.assertIn("MooCalendar.getOrCreateInstance(element)", source)
        self.assertIn("MooDateRangePicker.getOrCreateInstance(element)", source)
        self.assertIn("ContextMenu.getOrCreateInstance(element)", source)
        self.assertIn("Slider.getOrCreateInstance(element)", source)
        for selector in (
            ".chart, [data-chart-live]",
            "[data-moo-example-tasks]",
            "[data-moo-example-users]",
            ".combobox",
            ".context-menu",
            ".datatable",
            "[data-datepicker], [data-datepicker-range], [data-calendar]",
            "[data-slider]",
        ):
            with self.subTest(selector=selector):
                self.assertIn(f'"{selector}"', source)
        self.assertIn("export function initCatalog(root = document)", source)
        self.assertIn("[...disposers].reverse()", source)
        self.assertNotIn(".combobox-input", source)
        self.assertNotIn("sidebarState", source)
        self.assertFalse((ROOT / "site/static/js/preview.js").exists())

    def test_examples_row_actions_survive_reparented_menus(self) -> None:
        for module_name in ("examples-tasks.js", "examples-users.js"):
            with self.subTest(module_name=module_name):
                source = without_comments(
                    (CATALOG_JS / module_name).read_text(encoding="utf-8")
                )

                self.assertIn("const documentRoot = root.ownerDocument || root;", source)
                self.assertIn(
                    'target.closest(".dropdown-menu[data-datatable-row-action-owner]")',
                    source,
                )
                self.assertIn("rowById(ownerId)", source)
                self.assertIn(
                    'getAttribute("data-datatable-row-action-trigger")',
                    source,
                )
                self.assertIn("documentRoot.getElementById(triggerId)", source)
                self.assertIn('documentRoot.addEventListener("click", onPageClick);', source)
                self.assertIn(
                    'documentRoot.removeEventListener("click", onPageClick);',
                    source,
                )

    def test_examples_users_bulk_updates_keep_datatable_metadata_fresh(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-users.js").read_text(encoding="utf-8")
        )

        self.assertIn("const syncBulkMetadata = (row, values) => {", source)
        self.assertRegex(
            source,
            r'row\.setAttribute\(\s*"data-datatable-search"',
        )
        self.assertIn('row.setAttribute("data-datatable-facet-status", status);', source)
        self.assertIn('row.setAttribute("data-datatable-facet-team", team);', source)
        self.assertIn(
            "row.querySelector('[data-datatable-column=\"team\"]')?.setAttribute",
            source,
        )
        self.assertIn(
            "row.querySelector('[data-datatable-column=\"status\"]')?.setAttribute",
            source,
        )
        self.assertIn('if (key !== "status" && key !== "team")', source)
        self.assertIn("queueMicrotask(reinitTable);", source)

    def test_build_copies_catalog_tree_recursively(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for module_name in (*MODULES, "index.js"):
            self.assertTrue((DIST / f"assets/js/catalog/{module_name}").is_file())
