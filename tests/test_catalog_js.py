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
            f'if (typeof module{index}.{initializer} !== "function") process.exit(2);'
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
        self.assertIn("data-moo-catalog-theme-builder-style", styles)
        self.assertIn("data-moo-catalog-theme-builder-base-color", styles)

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

const selectors = {
  style: "[data-moo-catalog-theme-builder-style]",
  baseColor: "[data-moo-catalog-theme-builder-base-color]",
  chartPalette: "[data-moo-catalog-theme-builder-chart-palette]",
  headingFont: "[data-moo-catalog-theme-builder-heading-font]",
  bodyFont: "[data-moo-catalog-theme-builder-body-font]",
  radius: "[data-moo-catalog-theme-builder-radius]",
};

const controls = {
  style: makeControl({ default: "Default", soft: "Soft", solid: "Solid" }),
  baseColor: makeControl({ neutral: "Neutral", blue: "Blue" }),
  chartPalette: makeControl({ default: "Default", pastel: "Pastel", vivid: "Vivid" }),
  headingFont: makeControl({ default: "Default", system: "System" }),
  bodyFont: makeControl({ default: "Default", geist: "Geist" }),
  radius: makeControl({ default: "Default", compact: "Compact" }),
};

const fieldRoots = Object.fromEntries(
  Object.entries(selectors).map(([key, selector]) => [selector, controls[key].root])
);
const reset = makeEmitter();
const sheet = makeEmitter({
  querySelectorAll: () => [],
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
  broadStyleDataset: Object.hasOwn(documentElement.dataset, "mooThemeStyle"),
  broadBaseDataset: Object.hasOwn(documentElement.dataset, "mooBaseColor"),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  chart1: documentElement.style.getPropertyValue("--moo-chart-1"),
  heading: documentElement.style.getPropertyValue("--moo-heading-font-family"),
  body: documentElement.style.getPropertyValue("--bs-body-font-family"),
  radius: documentElement.style.getPropertyValue("--bs-border-radius"),
  selectedStyle: selectedValue("style"),
  selectedChart: selectedValue("chartPalette"),
  styleLabel: controls.style.value.textContent,
  softPressed: optionFor("style", "soft").attributes["aria-pressed"],
};

optionFor("chartPalette", "vivid").click();
const persisted = JSON.parse(localStorage.getItem("moo:theme-builder"));
const afterClick = {
  chart5: documentElement.style.getPropertyValue("--moo-chart-5"),
  selectedChart: selectedValue("chartPalette"),
  persistedChart: persisted.chartPalette,
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
  chart1: documentElement.style.getPropertyValue("--moo-chart-1"),
  primary: documentElement.style.getPropertyValue("--bs-primary"),
  selectedStyle: selectedValue("style"),
  selectedBase: selectedValue("baseColor"),
  selectedChart: selectedValue("chartPalette"),
  storedBuilder: localStorage.getItem("moo:theme-builder"),
};

dispose();
console.log(JSON.stringify({ initial, afterClick, afterReset }));
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
        self.assertEqual(case["initial"]["baseDataset"], "blue")
        self.assertFalse(case["initial"]["broadStyleDataset"])
        self.assertFalse(case["initial"]["broadBaseDataset"])
        self.assertEqual(case["initial"]["primary"], "rgb(37, 99, 235)")
        self.assertEqual(case["initial"]["chart1"], "rgb(103, 169, 232)")
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
        self.assertEqual(case["initial"]["selectedChart"], "pastel")
        self.assertEqual(case["initial"]["styleLabel"], "Soft")
        self.assertEqual(case["initial"]["softPressed"], "true")
        self.assertEqual(case["afterClick"]["chart5"], "rgb(225, 29, 72)")
        self.assertEqual(case["afterClick"]["selectedChart"], "vivid")
        self.assertEqual(case["afterClick"]["persistedChart"], "vivid")
        self.assertFalse(case["afterReset"]["styleDataset"])
        self.assertFalse(case["afterReset"]["baseDataset"])
        self.assertEqual(case["afterReset"]["chart1"], "")
        self.assertEqual(case["afterReset"]["primary"], "")
        self.assertEqual(case["afterReset"]["selectedStyle"], "default")
        self.assertEqual(case["afterReset"]["selectedBase"], "neutral")
        self.assertEqual(case["afterReset"]["selectedChart"], "default")
        self.assertIsNone(case["afterReset"]["storedBuilder"])

    def test_catalog_entrypoint_only_orchestrates_public_components(self) -> None:
        source = without_comments(
            (CATALOG_JS / "index.js").read_text(encoding="utf-8")
        )

        for module_name, initializer in MODULES.items():
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
