from __future__ import annotations

import json
import re
import subprocess
import unittest

from tests.helpers import DIST, PACKAGE_DIST, ROOT, CatalogTestCase
from tests.helpers.node_harness import NODE_PREAMBLE, NODE_TEST_TIMEOUT, VALID_DATA


CHART_JS = ROOT / "src/js/components/chart.js"
CATALOG_ADAPTER = ROOT / "site/src/js/catalog/examples-chart.js"
CATALOG_INDEX = ROOT / "site/src/js/catalog/index.js"
FIXTURE = ROOT / "tests/fixtures/certification/chart.html"
PAGE = ROOT / "site/src/pages/components/chart.html.jinja"

def without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^[ \t]*//.*$", "", source, flags=re.MULTILINE)


class ChartJavaScriptTests(CatalogTestCase):
    def run_chart_case(self, script: str) -> dict[str, object]:
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", NODE_PREAMBLE + script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertTrue(lines, f"No report emitted; stderr: {result.stderr}")
        return json.loads(lines[-1])

    def test_constructor_rejects_invalid_elements(self) -> None:
        case = self.run_chart_case(
            """
const candidates = [null, undefined, {}, "moo-chart", { nodeType: 3 }];
const messages = [];
for (const candidate of candidates) {
  try {
    new MooChart(candidate);
    messages.push("no-throw");
  } catch (error) {
    messages.push(error.message);
  }
}
const wrongRoot = makeRoot({}, { withCanvas: true });
wrongRoot.matches = () => false;
try {
  new MooChart(wrongRoot);
  messages.push("no-throw");
} catch (error) {
  messages.push(error.message);
}
report("invalid-elements", { messages });
"""
        )
        self.assertEqual(
            case["messages"],
            ["MooChart requires a .moo-chart root element."] * 6,
        )

    def test_constructor_requires_child_canvas(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}}, {{ withCanvas: false }});
let message = "";
try {{
  new MooChart(root);
}} catch (error) {{
  message = error.message;
}}
report("missing-canvas", {{ message }});
"""
        )
        self.assertEqual(
            case["message"],
            "MooChart requires a child <canvas> element inside the .moo-chart root.",
        )

    def test_instance_lookup_is_idempotent(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const before = MooChart.getInstance(root);
const created = MooChart.getOrCreateInstance(root);
const lookup = MooChart.getInstance(root);
const again = MooChart.getOrCreateInstance(root, {{ type: "bar" }});
report("instances", {{
  beforeNull: before === null,
  created: created instanceof MooChart,
  lookupMatches: lookup === created,
  idempotent: again === created,
  nonElement: MooChart.getInstance("nope") === null,
  chartType: created.chart.config.type,
}});
"""
        )
        self.assertEqual(
            case,
            {
                "name": "instances",
                "ok": True,
                "beforeNull": True,
                "created": True,
                "lookupMatches": True,
                "idempotent": True,
                "nonElement": True,
                "chartType": "line",
            },
        )

    def test_dispose_destroys_chart_disconnects_observer_and_clears_state(
        self,
    ) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const instance = MooChart.getOrCreateInstance(root);
const observer = observerLog.at(-1);
const inner = instance.chart;
let observerStateAtDestroy = "not-captured";
const realDestroy = inner.destroy.bind(inner);
inner.destroy = () => {{
  observerStateAtDestroy = instance._observer === null ? "cleared" : "live";
  realDestroy();
}};
// Schedule a re-theme so dispose has pending work to cancel.
observer.callback([{{ attributeName: "data-bs-theme" }}]);
instance.dispose();
const pendingCleared = instance._rethemeFrame === null;
report("dispose", {{
  observerDisconnected: observer.disconnected,
  observerStateAtDestroy,
  pendingCleared,
  canceledFrames: canceledFrames >= 1,
  chartCleared: instance.chart === null,
  instanceRemoved: MooChart.getInstance(root) === null,
}});
"""
        )
        self.assertEqual(
            case,
            {
                "name": "dispose",
                "ok": True,
                "observerDisconnected": True,
                "observerStateAtDestroy": "cleared",
                "pendingCleared": True,
                "canceledFrames": True,
                "chartCleared": True,
                "instanceRemoved": True,
            },
        )

    def test_stale_dispose_does_not_clear_a_newer_instance(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const stale = MooChart.getOrCreateInstance(root);
stale.dispose();
const current = MooChart.getOrCreateInstance(root);
stale.dispose();
report("stale-dispose", {{
  keptCurrent: MooChart.getInstance(root) === current,
  staleCleared: stale.chart === null,
}});
"""
        )
        self.assertEqual(
            case,
            {
                "name": "stale-dispose",
                "ok": True,
                "keptCurrent": True,
                "staleCleared": True,
            },
        )

    def test_data_attribute_feeds_chart_data_and_type(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "bar",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const instance = MooChart.getOrCreateInstance(root);
report("data-attributes", {{
  labels: instance.chart.data.labels,
  datasetLabel: instance.chart.data.datasets[0].label,
  values: instance.chart.data.datasets[0].data,
  type: instance.chart.config.type,
  themed: typeof instance.chart.data.datasets[0].backgroundColor === "string"
    && instance.chart.data.datasets[0].backgroundColor.length > 0,
}});
"""
        )
        self.assertEqual(case["labels"], ["Jan", "Feb"])
        self.assertEqual(case["datasetLabel"], "Revenue")
        self.assertEqual(case["values"], [1, 2])
        self.assertEqual(case["type"], "bar")
        self.assertTrue(case["themed"])

    def test_line_points_use_series_colored_halos_in_light_mode(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const tokenColors = new Map([
  ["--bs-body-color", "rgb(33, 37, 41)"],
  ["--bs-body-bg", "rgb(255, 255, 255)"],
  ["--bs-secondary-color", "rgb(108, 117, 125)"],
  ["--bs-border-color", "rgb(222, 226, 230)"],
  ["--bs-info", "rgb(13, 110, 253)"],
  ["--bs-info-text-emphasis", "rgb(5, 44, 101)"],
  ["--bs-success", "rgb(25, 135, 84)"],
  ["--bs-warning", "rgb(255, 193, 7)"],
  ["--bs-danger", "rgb(220, 53, 69)"],
]);
window.getComputedStyle = (element) => {{
  if (element === documentElement) {{
    return {{ getPropertyValue: (token) => tokenColors.get(token) || "" }};
  }}
  return {{ color: element.style.color, getPropertyValue: () => "" }};
}};
const instance = MooChart.getOrCreateInstance(root);
const dataset = instance.chart.data.datasets[0];
report("line-point-halo", {{
  borderColor: dataset.borderColor,
  pointBackgroundColor: dataset.pointBackgroundColor,
  pointBorderColor: dataset.pointBorderColor,
  pointHoverBorderColor: dataset.pointHoverBorderColor,
}});
"""
        )
        self.assertEqual(case["pointBackgroundColor"], "rgb(13, 110, 253)")
        self.assertEqual(case["pointBorderColor"], "rgb(13, 110, 253)")
        self.assertEqual(case["pointHoverBorderColor"], "rgb(13, 110, 253)")
        self.assertNotIn(
            case["pointBorderColor"],
            {"rgb(33, 37, 41)", "rgb(222, 226, 230)"},
        )

    def test_unsupported_chart_type_is_rejected(self) -> None:
        case = self.run_chart_case(
            """
const root = makeRoot({ "data-chart": "pie" });
let message = "";
try {
  new MooChart(root);
} catch (error) {
  message = error.message;
}
report("unsupported-type", { message });
"""
        )
        self.assertEqual(
            case["message"],
            'MooChart supports line and bar charts; received "pie".',
        )

    def test_invalid_json_produces_an_explicit_diagnostic(self) -> None:
        case = self.run_chart_case(
            """
const root = makeRoot({
  "data-chart": "line",
  "data-chart-data": "{not valid json",
});
let message = "";
let isSyntaxError = false;
try {
  new MooChart(root);
} catch (error) {
  message = error.message;
  isSyntaxError = error instanceof SyntaxError;
}
report("invalid-json", { message, isSyntaxError });
"""
        )
        self.assertTrue(case["isSyntaxError"])
        self.assertIn(
            "MooChart could not parse data-chart-data as JSON:", case["message"]
        )

    def test_invalid_data_shape_produces_an_explicit_diagnostic(self) -> None:
        case = self.run_chart_case(
            """
const root = makeRoot({
  "data-chart": "line",
  "data-chart-data": "null",
});
let message = "";
try {
  new MooChart(root);
} catch (error) {
  message = error.message;
}
report("invalid-data-shape", { message });
"""
        )
        self.assertEqual(
            case["message"],
            "MooChart data-chart-data must contain labels and datasets arrays.",
        )

    def test_missing_markup_data_produces_an_explicit_diagnostic(self) -> None:
        case = self.run_chart_case(
            """
const root = makeRoot({ "data-chart": "line" });
let message = "";
try {
  new MooChart(root);
} catch (error) {
  message = error.message;
}
report("missing-markup-data", { message });
"""
        )
        self.assertEqual(
            case["message"],
            "MooChart data-chart-data is required unless config.data is provided.",
        )

    def test_configuration_precedence_overrides_data_attributes(self) -> None:
        case = self.run_chart_case(
            f"""
const attributeOnly = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const defaults = MooChart.getOrCreateInstance(attributeOnly);

const overridden = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const configData = {{ labels: ["Q1"], datasets: [{{ label: "Target", data: [9] }}] }};
const configured = MooChart.getOrCreateInstance(overridden, {{
  type: "bar",
  data: configData,
}});

const programmaticRoot = makeRoot({{ "data-chart": "line" }});
const programmatic = MooChart.getOrCreateInstance(programmaticRoot, {{
  data: configData,
}});
report("precedence", {{
  defaultType: defaults.chart.config.type,
  defaultLabels: defaults.chart.data.labels,
  overriddenType: configured.chart.config.type,
  overriddenLabels: configured.chart.data.labels,
  overriddenDataset: configured.chart.data.datasets[0].label,
  defaultFallbackType: programmatic.chart.config.type,
  programmaticLabels: programmatic.chart.data.labels,
}});
"""
        )
        self.assertEqual(case["defaultType"], "line")
        self.assertEqual(case["defaultLabels"], ["Jan", "Feb"])
        self.assertEqual(case["overriddenType"], "bar")
        self.assertEqual(case["overriddenLabels"], ["Q1"])
        self.assertEqual(case["overriddenDataset"], "Target")
        self.assertEqual(case["defaultFallbackType"], "line")
        self.assertEqual(case["programmaticLabels"], ["Q1"])

    def test_theme_observer_watches_data_bs_theme_and_rethemes(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const instance = MooChart.getOrCreateInstance(root);
const observer = observerLog.at(-1);
const observation = observer.observed[0];

let updates = 0;
const inner = instance.chart;
const realUpdate = inner.update.bind(inner);
inner.update = (...args) => {{
  updates += 1;
  return realUpdate(...args);
}};

documentElement.dataset.bsTheme = "dark";
observer.callback([{{ attributeName: "class" }}]);
observer.callback([{{ attributeName: "data-bs-theme" }}]);
await new Promise((resolve) => setTimeout(resolve, 20));

report("theme-observer", {{
  observedDocumentElement: observation.target === documentElement,
  attributes: observation.options.attributes,
  attributeFilter: observation.options.attributeFilter,
  updates,
}});
"""
        )
        self.assertTrue(case["observedDocumentElement"])
        self.assertTrue(case["attributes"])
        self.assertEqual(case["attributeFilter"], ["data-bs-theme"])
        # One unrelated mutation plus one data-bs-theme mutation must produce
        # exactly one coalesced re-theme update.
        self.assertEqual(case["updates"], 1)

    def test_theme_observer_uses_the_nearest_data_bs_theme_scope(self) -> None:
        case = self.run_chart_case(
            f"""
const scopedTheme = {{
  dataset: {{ bsTheme: "dark" }},
  getAttribute: (name) => (name === "data-bs-theme" ? scopedTheme.dataset.bsTheme : null),
}};
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
root.closest = (selector) => (selector === "[data-bs-theme]" ? scopedTheme : null);
const scopedColors = new Map([
  ["--bs-body-color", "rgb(222, 226, 230)"],
  ["--bs-body-bg", "rgb(33, 37, 41)"],
  ["--bs-secondary-color", "rgb(173, 181, 189)"],
  ["--bs-border-color", "rgb(73, 80, 87)"],
  ["--bs-info", "rgb(13, 202, 240)"],
  ["--bs-info-text-emphasis", "rgb(110, 223, 246)"],
  ["--bs-success", "rgb(25, 135, 84)"],
  ["--bs-warning", "rgb(255, 193, 7)"],
  ["--bs-danger", "rgb(220, 53, 69)"],
]);
const documentColors = new Map([
  ["--bs-info", "rgb(13, 110, 253)"],
  ["--bs-info-text-emphasis", "rgb(5, 44, 101)"],
]);
window.getComputedStyle = (element) => {{
  const colors = element === scopedTheme ? scopedColors : documentColors;
  return {{
    color: element.style?.color || "",
    getPropertyValue: (token) => colors.get(token) || "",
  }};
}};
const instance = MooChart.getOrCreateInstance(root);
const observer = observerLog.at(-1);
const observation = observer.observed[0];
const dataset = instance.chart.data.datasets[0];
report("scoped-theme-observer", {{
  observedScopedTheme: observation.target === scopedTheme,
  pointBackgroundColor: dataset.pointBackgroundColor,
}});
"""
        )
        self.assertTrue(case["observedScopedTheme"])
        self.assertEqual(case["pointBackgroundColor"], "rgb(110, 223, 246)")

    def test_catalog_adapter_initializes_and_disposes_moo_charts(self) -> None:
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
function chartRoot() {{
  return makeRoot({{
    "data-chart": "line",
    "data-chart-data": {json.dumps(VALID_DATA)},
  }});
}}
const roots = [chartRoot(), chartRoot()];
const root = {{
  querySelectorAll: (selector) => (selector === ".moo-chart" ? roots : []),
}};
const release = initExamplesChart(root);
const reentered = initExamplesChart(root);
const initialized = roots.every((element) => MooChart.getInstance(element) instanceof MooChart);
release();
release();
const cleared = roots.every((element) => MooChart.getInstance(element) === null);
const secondRelease = initExamplesChart(root);
const secondInstance = MooChart.getInstance(roots[0]);
release();
const staleReleaseKeptNewState = MooChart.getInstance(roots[0]) === secondInstance;
report("catalog-adapter", {{
  releaseIsFunction: typeof release === "function",
  idempotent: reentered === release,
  initialized,
  cleared,
  reinitializable: typeof secondRelease === "function" && secondRelease !== release,
  repeatedReleaseIsSafe: cleared,
  staleReleaseKeptNewState,
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
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(
            case,
            {
                "name": "catalog-adapter",
                "ok": True,
                "releaseIsFunction": True,
                "idempotent": True,
                "initialized": True,
                "cleared": True,
                "reinitializable": True,
                "repeatedReleaseIsSafe": True,
                "staleReleaseKeptNewState": True,
            },
        )

    def test_catalog_adapter_scopes_lifecycle_theme_to_the_example(self) -> None:
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
function makeButton() {{
  const handlers = new Map();
  return {{
    addEventListener: (name, handler) => handlers.set(name, handler),
    removeEventListener: (name) => handlers.delete(name),
    click: () => handlers.get("click")?.(),
  }};
}}
const themeButton = makeButton();
const status = {{ textContent: "" }};
const previewScope = {{
  dataset: {{}},
  ownerDocument,
}};
const chartRoot = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const container = {{
  dataset: {{}},
  ownerDocument,
  querySelector: (selector) => {{
    if (selector === ".moo-chart") return chartRoot;
    if (selector === "[data-chart-status]") return status;
    if (selector === "[data-chart-theme]") return themeButton;
    return null;
  }},
  closest: (selector) => (selector === ".moo-example__preview" ? previewScope : null),
}};
chartRoot.closest = (selector) => (selector === "[data-bs-theme]" ? previewScope : null);
documentElement.dataset.bsTheme = "dark";
const root = {{
  querySelectorAll: (selector) => {{
    if (selector === "[data-chart-live]") return [container];
    if (selector === ".moo-chart") return [chartRoot];
    return [];
  }},
}};
const release = initExamplesChart(root);
const initialLocalTheme = previewScope.dataset.bsTheme;
themeButton.click();
const afterToggleLocalTheme = previewScope.dataset.bsTheme;
const afterToggleDocumentTheme = documentElement.dataset.bsTheme;
release();
report("scoped-lifecycle-theme", {{
  initialLocalTheme,
  afterToggleLocalTheme,
  afterToggleDocumentTheme,
  containerTheme: container.dataset.bsTheme || null,
  statusMessage: status.textContent,
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
        case = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(case.get("initialLocalTheme"), "dark")
        self.assertEqual(case.get("afterToggleLocalTheme"), "light")
        self.assertEqual(case.get("afterToggleDocumentTheme"), "dark")
        self.assertIsNone(case["containerTheme"])
        self.assertEqual(case["statusMessage"], "Example theme: light")

    def test_catalog_adapter_uses_one_stateful_lifecycle_button(self) -> None:
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
function makeLifecycleButton() {{
  const handlers = new Map();
  const attributes = {{}};
  const makeIcon = (initialHidden = false) => {{
    const iconAttributes = new Set(initialHidden ? ["hidden"] : []);
    return {{
      getAttribute: (name) => (iconAttributes.has(name) ? "" : null),
      toggleAttribute: (name, force) => {{
        if (force) iconAttributes.add(name);
        else iconAttributes.delete(name);
      }},
    }};
  }};
  const label = {{ textContent: "Dispose" }};
  const disposeIcon = makeIcon(false);
  const reinitIcon = makeIcon(true);
  const button = {{
    dataset: {{}},
    setAttribute: (name, value) => {{ attributes[name] = value; }},
    getAttribute: (name) => attributes[name] || null,
    addEventListener: (name, handler) => handlers.set(name, handler),
    removeEventListener: (name) => handlers.delete(name),
    click: () => handlers.get("click")?.(),
    querySelector: (selector) => {{
      if (selector === "[data-chart-lifecycle-label]") return label;
      if (selector === '[data-chart-lifecycle-icon="dispose"]') return disposeIcon;
      if (selector === '[data-chart-lifecycle-icon="reinit"]') return reinitIcon;
      return null;
    }},
  }};
  return {{ button, label, disposeIcon, reinitIcon }};
}}
const themeButton = {{
  addEventListener: () => {{}},
  removeEventListener: () => {{}},
}};
const lifecycle = makeLifecycleButton();
const status = {{ textContent: "" }};
const previewScope = {{ dataset: {{}}, ownerDocument }};
const chartRoot = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const container = {{
  ownerDocument,
  querySelector: (selector) => {{
    if (selector === ".moo-chart") return chartRoot;
    if (selector === "[data-chart-status]") return status;
    if (selector === "[data-chart-theme]") return themeButton;
    if (selector === "[data-chart-lifecycle]") return lifecycle.button;
    return null;
  }},
  closest: (selector) => (selector === ".moo-example__preview" ? previewScope : null),
}};
chartRoot.closest = (selector) => (selector === "[data-bs-theme]" ? previewScope : null);
const root = {{
  querySelectorAll: (selector) => {{
    if (selector === "[data-chart-live]") return [container];
    if (selector === ".moo-chart") return [chartRoot];
    return [];
  }},
}};
const release = initExamplesChart(root);
const initial = {{
  hasInstance: MooChart.getInstance(chartRoot) instanceof MooChart,
  label: lifecycle.label.textContent,
  state: lifecycle.button.dataset.chartLifecycleState,
  ariaLabel: lifecycle.button.getAttribute("aria-label"),
  disposeIconHidden: lifecycle.disposeIcon.getAttribute("hidden"),
  reinitIconHidden: lifecycle.reinitIcon.getAttribute("hidden"),
}};
lifecycle.button.click();
const afterDispose = {{
  hasInstance: MooChart.getInstance(chartRoot) instanceof MooChart,
  label: lifecycle.label.textContent,
  state: lifecycle.button.dataset.chartLifecycleState,
  ariaLabel: lifecycle.button.getAttribute("aria-label"),
  disposeIconHidden: lifecycle.disposeIcon.getAttribute("hidden"),
  reinitIconHidden: lifecycle.reinitIcon.getAttribute("hidden"),
  status: status.textContent,
}};
lifecycle.button.click();
const afterReinit = {{
  hasInstance: MooChart.getInstance(chartRoot) instanceof MooChart,
  label: lifecycle.label.textContent,
  state: lifecycle.button.dataset.chartLifecycleState,
  ariaLabel: lifecycle.button.getAttribute("aria-label"),
  disposeIconHidden: lifecycle.disposeIcon.getAttribute("hidden"),
  reinitIconHidden: lifecycle.reinitIcon.getAttribute("hidden"),
  status: status.textContent,
}};
release();
report("stateful-lifecycle-button", {{
  initial,
  afterDispose,
  afterReinit,
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
        case = json.loads(result.stdout.splitlines()[-1])

        self.assertEqual(
            case["initial"],
            {
                "hasInstance": True,
                "label": "Dispose",
                "state": "live",
                "ariaLabel": "Dispose chart",
                "disposeIconHidden": None,
                "reinitIconHidden": "",
            },
        )
        self.assertEqual(
            case["afterDispose"],
            {
                "hasInstance": False,
                "label": "Reinitialize",
                "state": "disposed",
                "ariaLabel": "Reinitialize chart",
                "disposeIconHidden": "",
                "reinitIconHidden": None,
                "status": "Disposed",
            },
        )
        self.assertEqual(
            case["afterReinit"],
            {
                "hasInstance": True,
                "label": "Dispose",
                "state": "live",
                "ariaLabel": "Dispose chart",
                "disposeIconHidden": None,
                "reinitIconHidden": "",
                "status": "Live",
            },
        )

    def test_lifecycle_preview_surface_is_the_theme_scope(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/chart.html")
        lifecycle = page.split('data-example="chart-lifecycle"', 1)[1].split(
            'data-moo-code-panel',
            1,
        )[0]

        self.assertRegex(
            lifecycle,
            r'<div class="moo-example__preview[^"]*\bmoo-example__preview--medium\b'
            r'[^"]*\bbg-body\b[^"]*\btext-body\b[^"]*"',
        )
        self.assertIn('data-chart-live', lifecycle)

    def test_lifecycle_controls_are_centered_in_preview(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/chart.html")
        lifecycle = page.split('data-chart-live', 1)[1].split(
            'id="chart-lifecycle-example"',
            1,
        )[0]

        self.assertRegex(
            lifecycle,
            r'class="[^"]*\bd-flex\b[^"]*\bflex-wrap\b[^"]*'
            r'\balign-items-center\b[^"]*\bjustify-content-center\b[^"]*'
            r'\bgap-2\b[^"]*"',
        )

    def test_lifecycle_status_is_accessible_without_a_visible_badge(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/chart.html")
        lifecycle = page.split('data-chart-live', 1)[1].split(
            'id="chart-lifecycle-example"',
            1,
        )[0]

        self.assertIn('data-chart-status', lifecycle)
        self.assertIn('aria-live="polite"', lifecycle)
        self.assertIn('visually-hidden', lifecycle)
        self.assertNotIn('class="badge', lifecycle)
        self.assertIn('data-chart-lifecycle', lifecycle)
        self.assertIn('data-chart-lifecycle-icon="dispose"', lifecycle)
        self.assertIn('data-chart-lifecycle-icon="reinit"', lifecycle)
        self.assertNotIn('data-chart-lifecycle-icon="&quot;dispose&quot;"', lifecycle)
        self.assertNotIn('data-chart-lifecycle-icon="&quot;reinit&quot;"', lifecycle)
        self.assertNotIn('data-chart-reinit', lifecycle)
        self.assertNotIn('data-chart-dispose', lifecycle)

    def test_public_module_contracts_the_frozen_api(self) -> None:
        source = CHART_JS.read_text(encoding="utf-8")

        self.assertIn('import Chart from "chart.js/auto";', source)
        self.assertIn("export default class MooChart", source)
        self.assertIn("constructor(element, config = {})", source)
        self.assertIn("static getInstance(element)", source)
        self.assertIn("static getOrCreateInstance(element, config = {})", source)
        self.assertIn("dispose()", source)
        self.assertIn("const instances = new WeakMap();", source)
        self.assertIn("this._observer", source)
        self.assertIn('attributeFilter: ["data-bs-theme"]', source)

        # The documented getters must actually exist in the source so the
        # API freeze cannot drift from the implementation.
        self.assertIn("get chart()", source)
        self.assertIn("get element()", source)

    def test_no_catalog_source_uses_a_chart_cdn_or_window_chart(self) -> None:
        for path in (CHART_JS, CATALOG_ADAPTER, CATALOG_INDEX):
            with self.subTest(path=path.relative_to(ROOT)):
                source = without_comments(path.read_text(encoding="utf-8"))
                for forbidden in (
                    "window.Chart",
                    "CHART_CDN",
                    "CHART_SRI",
                    "loadChartJs",
                    "cdn.jsdelivr.net",
                    "unpkg.com",
                    "chart.umd",
                    "script.integrity",
                    "crossOrigin",
                ):
                    self.assertNotIn(forbidden, source)

    def test_public_bundle_import_architecture(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        adapter = without_comments(CATALOG_ADAPTER.read_text(encoding="utf-8"))
        self.assertIn(
            'import MooChart from "../../../../src/js/components/chart.js";',
            adapter,
        )

        # The catalog must consume the copied canonical bundle, never
        # dist/js/, the minified bundle, or a runtime CDN.
        built_adapter = (DIST / "assets/js/catalog/examples-chart.js").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            built_adapter,
            r'import MooChart from "\.\./components/chart\.js\?v=[0-9a-f]+";',
        )
        canonical_copy = DIST / "assets/js/components/chart.js"
        self.assertTrue(canonical_copy.is_file())

        bundle = (PACKAGE_DIST / "js/chart.js").read_text(encoding="utf-8")
        self.assertRegex(bundle, r"export\s*{\s*MooChart as default\s*}")
        self.assertIn("Chart.js v4.5.1", bundle)
        self.assertNotIn("cdn.jsdelivr.net", bundle)
        self.assertNotIn("unpkg.com", bundle)
        self.assertNotIn("window.Chart", bundle)

        self.assertTrue((PACKAGE_DIST / "js/chart.min.js").is_file())

    def test_certification_fixture_uses_the_public_bundle(self) -> None:
        self.assertTrue(FIXTURE.is_file(), "Chart certification fixture is missing")
        source = FIXTURE.read_text(encoding="utf-8")

        self.assertIn('import MooChart from "/dist/js/chart.js";', source)
        self.assertIn('class="moo-chart"', source)
        self.assertIn('data-chart="line"', source)
        self.assertIn('data-chart="bar"', source)
        self.assertIn("data-chart-data", source)
        self.assertIn("role=\"img\"", source)
        self.assertIn("aria-label", source)
        self.assertNotIn("cdn.jsdelivr.net", source)
        self.assertNotIn("window.Chart", source)

    def test_component_page_covers_the_public_contract(self) -> None:
        self.assertTrue(PAGE.is_file(), "Chart page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn("render_reference(", source)
        self.assertIn(".moo-chart", source)
        self.assertIn("data-chart", source)
        self.assertIn("data-chart-data", source)
        for chart_id in (
            "chart-line-example",
            "chart-bar-example",
            "chart-lifecycle-example",
        ):
            self.assertRegex(
                source,
                rf'class="moo-chart w-100"\s+id="{chart_id}"',
            )
        self.assertRegex(
            source,
            r'class="[^"]*\bd-grid\b[^"]*\bgap-3\b[^"]*\bw-100\b[^"]*"\s+data-chart-live',
        )
        self.assertEqual(source.count('preview_class="moo-example__preview--medium'), 3)
        self.assertNotIn('preview_class="moo-example__preview--wide"', source)
        for topic in (
            '"line"',
            '"bar"',
            "theme",
            "data-chart-live",
            "data-chart-lifecycle",
            "dispose",
            "resize",
            "aria-label",
            "mobile",
        ):
            self.assertIn(topic, source)


if __name__ == "__main__":
    unittest.main()
