from __future__ import annotations

import json
import re
import subprocess

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
  style: "soft",
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
                "style": "soft",
                "baseColor": "neutral",
                "themeColor": "blue",
                "chartColor": "neutral",
                "headingFont": "system",
                "bodyFont": "geist",
                "radius": "compact",
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

    def test_theme_builder_schema_resolves_public_style_tokens(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  resolveThemeBuilderTokens,
} from "./site/src/js/catalog/theme-builder-schema.js";

const lightTokens = resolveThemeBuilderTokens({
  style: "nova",
  baseColor: "zinc",
  themeColor: "blue",
});
const darkTokens = resolveThemeBuilderTokens({
  style: "nova",
  baseColor: "zinc",
  themeColor: "blue",
}, { theme: "dark" });
const softTokens = resolveThemeBuilderTokens({ style: "soft" });
const tokenNames = [
  ...Object.keys(lightTokens),
  ...Object.keys(darkTokens),
  ...Object.keys(softTokens),
];

console.log(JSON.stringify({
  lightMutedSurface: lightTokens["--moo-muted-surface"],
  lightCardBg: lightTokens["--bs-card-bg"],
  lightSidebarAccent: lightTokens["--moo-sidebar-accent"],
  darkSidebarAccent: darkTokens["--moo-sidebar-accent"],
  softMutedSurface: softTokens["--moo-muted-surface"],
  softBorder: softTokens["--moo-border"],
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
        self.assertEqual(
            case["lightMutedSurface"],
            "color-mix(in srgb, var(--bs-primary) 9%, var(--bs-body-bg))",
        )
        self.assertEqual(
            case["lightCardBg"],
            "color-mix(in srgb, var(--bs-primary) 3%, var(--bs-body-bg))",
        )
        self.assertEqual(
            case["lightSidebarAccent"],
            "color-mix(in srgb, var(--moo-ring) 20%, var(--moo-sidebar))",
        )
        self.assertEqual(
            case["darkSidebarAccent"],
            "color-mix(in srgb, var(--moo-ring) 32%, var(--moo-sidebar))",
        )
        self.assertEqual(
            case["softMutedSurface"],
            "color-mix(in srgb, var(--bs-body-bg) 92%, var(--bs-body-color))",
        )
        self.assertEqual(
            case["softBorder"],
            "color-mix(in srgb, var(--bs-body-color) 14%, transparent)",
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
        self.assertIn(
            "--moo-muted-surface: color-mix(in srgb, var(--bs-body-bg) 92%, var(--bs-body-color));",
            css,
        )
        self.assertIn(
            "--bs-card-bg: color-mix(in srgb, var(--bs-body-bg) 98%, var(--bs-body-color));",
            css,
        )
        self.assertIn(
            "--moo-sidebar-accent: color-mix(in srgb, var(--moo-ring) 20%, var(--moo-sidebar));",
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
                "style": "soft",
                "baseColor": "zinc",
                "themeColor": "green",
                "chartColor": "purple",
                "headingFont": "system",
                "bodyFont": "geist",
                "radius": "compact",
            },
        )

    def test_theme_builder_first_paint_payload_matches_contract(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                """
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  createThemeBuilderFirstPaintPayload,
} from "./site/src/js/catalog/theme-builder-schema.js";
import {
  createThemeBuilderPreset,
} from "./site/src/js/catalog/theme-builder-export.js";

console.log(JSON.stringify({
  allowList: PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
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
        contract_path = ROOT.parent / "docs/contracts/THEME_PRESETS.md"
        self.assertTrue(contract_path.is_file(), "missing theme preset contract")
        contract = contract_path.read_text(encoding="utf-8")

        def contract_json_block(name: str) -> list[str]:
            match = re.search(
                rf"<!-- {re.escape(name)}:start -->\s*```json\s*(.*?)\s*```\s*<!-- {re.escape(name)}:end -->",
                contract,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(match, f"missing {name} contract block")
            return json.loads(match.group(1))

        self.assertEqual(
            contract_json_block("theme-preset-schema-fields"),
            case["presetFields"],
        )
        self.assertEqual(
            contract_json_block("theme-preset-public-token-allow-list"),
            case["allowList"],
        )

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

    def test_examples_chart_delegates_to_the_public_moo_chart(self) -> None:
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
  querySelectorAll: (selector) => (selector === ".moo-chart" ? roots : []),
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
        self.assertIn("mooCatalogThemeBuilderStyle", source)
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
    root: {
      querySelectorAll: (selector) =>
        selector === "[data-moo-catalog-theme-builder-option]" ? options : [],
      querySelector: (selector) =>
        selector === "[data-moo-catalog-theme-builder-value]" ? value : null,
    },
  };
}

function makeRadio(value, checked = false) {
  return makeEmitter({ value, checked });
}

const selectors = {
  style: "[data-moo-catalog-theme-builder-style]",
  baseColor: "[data-moo-catalog-theme-builder-base-color]",
  themeColor: "[data-moo-catalog-theme-builder-theme-color]",
  chartColor: "[data-moo-catalog-theme-builder-chart-color]",
  headingFont: "[data-moo-catalog-theme-builder-heading-font]",
  bodyFont: "[data-moo-catalog-theme-builder-body-font]",
  radius: "[data-moo-catalog-theme-builder-radius]",
};

const controls = {
  style: makeControl({ default: "Default", soft: "Soft", solid: "Solid" }),
  baseColor: makeControl({ neutral: "Neutral", zinc: "Zinc" }),
  themeColor: makeControl({ neutral: "Neutral", blue: "Blue" }),
  chartColor: makeControl({ neutral: "Neutral", teal: "Teal" }),
  headingFont: makeControl({ default: "Default", system: "System" }),
  bodyFont: makeControl({ default: "Default", geist: "Geist" }),
  radius: makeControl({ default: "Default", compact: "Compact" }),
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
    selector === "[data-moo-settings-reset]" ? reset : fieldRoots[selector] || null,
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
  styleDataset: documentElement.dataset.mooCatalogThemeBuilderStyle,
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
  selectedStyle: selectedValue("style"),
  selectedBase: selectedValue("baseColor"),
  selectedTheme: selectedValue("themeColor"),
  selectedChart: selectedValue("chartColor"),
  styleLabel: controls.style.value.textContent,
  softPressed: optionFor("style", "soft").attributes["aria-pressed"],
  migratedBuilder: JSON.parse(localStorage.getItem("moo:theme-builder")),
};

optionFor("baseColor", "zinc").click();
const afterBaseLight = {
  baseDataset: documentElement.dataset.mooCatalogThemeBuilderBaseColor,
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  foreground: documentElement.style.getPropertyValue("--moo-foreground"),
  sidebar: documentElement.style.getPropertyValue("--moo-sidebar"),
  bodyBg: documentElement.style.getPropertyValue("--bs-body-bg"),
  bodyBgRgb: documentElement.style.getPropertyValue("--bs-body-bg-rgb"),
  secondaryBg: documentElement.style.getPropertyValue("--bs-secondary-bg"),
};

const darkInput = themeInputs.find((input) => input.value === "dark");
darkInput.checked = true;
darkInput.dispatch("change");
const afterThemeDark = {
  theme: documentElement.dataset.bsTheme,
  surface: documentElement.style.getPropertyValue("--moo-surface"),
  foreground: documentElement.style.getPropertyValue("--moo-foreground"),
  sidebar: documentElement.style.getPropertyValue("--moo-sidebar"),
  bodyBg: documentElement.style.getPropertyValue("--bs-body-bg"),
  bodyBgRgb: documentElement.style.getPropertyValue("--bs-body-bg-rgb"),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  darkChecked: darkInput.checked,
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
  selectedStyle: selectedValue("style"),
  selectedBase: selectedValue("baseColor"),
  selectedTheme: selectedValue("themeColor"),
  selectedChart: selectedValue("chartColor"),
  storedBuilder: localStorage.getItem("moo:theme-builder"),
};

dispose();
console.log(JSON.stringify({
  initial,
  afterBaseLight,
  afterThemeDark,
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
        self.assertEqual(case["initial"]["styleDataset"], "soft")
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
            "color-mix(in srgb, var(--bs-body-bg) 92%, var(--bs-body-color))",
        )
        self.assertEqual(case["initial"]["secondaryBg"], "var(--moo-muted-surface)")
        self.assertEqual(
            case["initial"]["cardBg"],
            "color-mix(in srgb, var(--bs-body-bg) 98%, var(--bs-body-color))",
        )
        self.assertEqual(
            case["initial"]["heading"],
            'system-ui, -apple-system, "Segoe UI", sans-serif',
        )
        self.assertEqual(
            case["initial"]["body"],
            '"Geist", system-ui, -apple-system, "Segoe UI", sans-serif',
        )
        self.assertEqual(case["initial"]["radius"], "0.25rem")
        self.assertEqual(case["initial"]["selectedStyle"], "soft")
        self.assertEqual(case["initial"]["selectedBase"], "neutral")
        self.assertEqual(case["initial"]["selectedTheme"], "blue")
        self.assertEqual(case["initial"]["selectedChart"], "neutral")
        self.assertEqual(case["initial"]["styleLabel"], "Soft")
        self.assertEqual(case["initial"]["softPressed"], "true")
        self.assertEqual(case["initial"]["migratedBuilder"]["schemaVersion"], 1)
        self.assertEqual(case["initial"]["migratedBuilder"]["baseColor"], "neutral")
        self.assertEqual(case["initial"]["migratedBuilder"]["themeColor"], "blue")
        self.assertEqual(case["initial"]["migratedBuilder"]["chartColor"], "neutral")
        self.assertNotIn("chartPalette", case["initial"]["migratedBuilder"])
        self.assertEqual(case["afterBaseLight"]["baseDataset"], "zinc")
        self.assertEqual(case["afterBaseLight"]["surface"], "oklch(1 0 0)")
        self.assertEqual(
            case["afterBaseLight"]["foreground"],
            "oklch(0.141 0.005 285.823)",
        )
        self.assertEqual(case["afterBaseLight"]["sidebar"], "oklch(0.985 0 0)")
        self.assertEqual(case["afterBaseLight"]["bodyBg"], "var(--moo-surface)")
        self.assertEqual(case["afterBaseLight"]["bodyBgRgb"], "")
        self.assertEqual(case["afterBaseLight"]["secondaryBg"], "var(--moo-muted-surface)")
        self.assertEqual(case["afterThemeDark"]["theme"], "dark")
        self.assertEqual(
            case["afterThemeDark"]["surface"],
            "oklch(0.141 0.005 285.823)",
        )
        self.assertEqual(
            case["afterThemeDark"]["foreground"],
            "oklch(0.985 0 0)",
        )
        self.assertEqual(case["afterThemeDark"]["sidebar"], "oklch(0.21 0.006 285.885)")
        self.assertEqual(case["afterThemeDark"]["bodyBg"], "var(--moo-surface)")
        self.assertEqual(case["afterThemeDark"]["bodyBgRgb"], "")
        self.assertEqual(case["afterThemeDark"]["primary"], "rgb(6, 111, 209)")
        self.assertTrue(case["afterThemeDark"]["darkChecked"])
        self.assertEqual(case["afterClick"]["chart5"], "rgb(7, 100, 72)")
        self.assertEqual(case["afterClick"]["selectedChart"], "teal")
        self.assertEqual(case["afterClick"]["persistedChart"], "teal")
        self.assertFalse(case["afterReset"]["styleDataset"])
        self.assertFalse(case["afterReset"]["baseDataset"])
        self.assertFalse(case["afterReset"]["themeDataset"])
        self.assertEqual(case["afterReset"]["chart1"], "rgb(82, 82, 91)")
        self.assertEqual(case["afterReset"]["bodyBg"], "")
        self.assertEqual(case["afterReset"]["bodyBgRgb"], "")
        self.assertEqual(case["afterReset"]["primary"], "")
        self.assertEqual(case["afterReset"]["primaryRgb"], "")
        self.assertEqual(case["afterReset"]["selectedStyle"], "default")
        self.assertEqual(case["afterReset"]["selectedBase"], "neutral")
        self.assertEqual(case["afterReset"]["selectedTheme"], "neutral")
        self.assertEqual(case["afterReset"]["selectedChart"], "neutral")
        self.assertIsNone(case["afterReset"]["storedBuilder"])

    def test_catalog_entrypoint_only_orchestrates_public_components(self) -> None:
        source = without_comments(
            (CATALOG_JS / "index.js").read_text(encoding="utf-8")
        )

        for module_name, initializer in MODULES.items():
            if initializer is None:
                continue
            self.assertRegex(
                source,
                rf'import \{{ {initializer} \}} from "\./{re.escape(module_name)}";',
            )
            self.assertIn(f"{initializer}(root)", source)

        self.assertIn(
            'import Combobox from "../../../../src/js/components/combobox.js";',
            source,
        )
        self.assertIn(
            'import Sidebar from "../../../../src/js/components/sidebar.js";',
            source,
        )
        self.assertIn(
            'import ContextMenu from "../../../../src/js/components/context-menu.js";',
            source,
        )
        self.assertIn(
            'import Slider from "../../../../src/js/components/slider.js";',
            source,
        )
        self.assertIn("Combobox.getOrCreateInstance(element)", source)
        self.assertIn("Sidebar.getOrCreateInstance(element)", source)
        self.assertIn("ContextMenu.getOrCreateInstance(element)", source)
        self.assertIn("Slider.getOrCreateInstance(element)", source)
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
