from __future__ import annotations

import json
import re
import subprocess
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers import DIST, PACKAGE_DIST, ROOT, CatalogTestCase
from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


CHART_JS = ROOT / "src/js/components/chart.js"
CATALOG_ADAPTER = ROOT / "site/src/js/catalog/examples-chart.js"
CATALOG_INDEX = ROOT / "site/src/js/catalog/index.js"
FIXTURE = ROOT / "tests/fixtures/certification/chart.html"
PAGE = ROOT / "site/src/pages/components/chart.html.jinja"

# Shared Node harness: a minimal, permissive DOM stub good enough to run the
# real MooChart (and the Chart.js it bundles) outside a browser. The stub
# tracks MutationObserver activity so lifecycle assertions can inspect what
# the component observed and when it disconnected.
NODE_PREAMBLE = """
import MooChart from "./src/js/components/chart.js";

globalThis.window = globalThis;

const observerLog = [];
class TrackingObserver {
  constructor(callback) {
    this.callback = callback;
    this.observed = [];
    this.disconnected = false;
    observerLog.push(this);
  }
  observe(target, options) { this.observed.push({ target, options }); }
  disconnect() { this.disconnected = true; }
}

let canceledFrames = 0;
window.MutationObserver = TrackingObserver;
window.requestAnimationFrame = (callback) => setTimeout(callback, 0);
window.cancelAnimationFrame = (id) => { canceledFrames += 1; clearTimeout(id); };
window.getComputedStyle = () => ({ getPropertyValue: () => "rgb(13, 110, 253)" });

const documentElement = { dataset: { bsTheme: "light" } };
const ownerDocument = { documentElement, defaultView: window };

function makeCanvas() {
  const contextHandler = {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop === Symbol.toPrimitive) return () => "";
      return () => (prop === "measureText" ? { width: 0 } : undefined);
    },
  };
  const context = new Proxy({}, contextHandler);
  const canvas = {
    nodeType: 1,
    tagName: "CANVAS",
    style: {},
    width: 400,
    height: 200,
    getContext: () => context,
    addEventListener() {},
    removeEventListener() {},
    getBoundingClientRect: () => ({
      x: 0, y: 0, top: 0, left: 0, right: 400, bottom: 200,
      width: 400, height: 200,
    }),
    setAttribute() {},
    getAttribute: () => null,
    ownerDocument,
  };
  context.canvas = canvas;
  return canvas;
}

function makeRoot(attrs = {}, { withCanvas = true } = {}) {
  const attrMap = new Map(Object.entries(attrs));
  const canvas = makeCanvas();
  const root = {
    nodeType: 1,
    tagName: "DIV",
    style: {},
    ownerDocument,
    getAttribute: (name) => (attrMap.has(name) ? attrMap.get(name) : null),
    setAttribute: (name, value) => attrMap.set(name, String(value)),
    matches: (selector) => selector === ".moo-chart",
    querySelector: (selector) =>
      ((selector === ":scope > canvas" || selector === "canvas") && withCanvas
        ? canvas
        : null),
    querySelectorAll: (selector) => (selector === ".moo-chart" ? [root] : []),
  };
  return root;
}

function report(name, details = {}) {
  console.log(JSON.stringify({ name, ok: true, ...details }));
}
"""

VALID_DATA = json.dumps(
    {"labels": ["Jan", "Feb"], "datasets": [{"label": "Revenue", "data": [1, 2]}]}
)
NODE_TEST_TIMEOUT = 30


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
  "data-moo-chart": "line",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
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
  "data-moo-chart": "line",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
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
  "data-moo-chart": "line",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
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

    def test_data_attribute_feeds_chart_data_and_type(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-moo-chart": "bar",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
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

    def test_unsupported_chart_type_is_rejected(self) -> None:
        case = self.run_chart_case(
            """
const root = makeRoot({ "data-moo-chart": "pie" });
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
  "data-moo-chart": "line",
  "data-moo-chart-data": "{not valid json",
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
            "MooChart could not parse data-moo-chart-data as JSON:", case["message"]
        )

    def test_configuration_precedence_overrides_data_attributes(self) -> None:
        case = self.run_chart_case(
            f"""
const attributeOnly = makeRoot({{
  "data-moo-chart": "line",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
}});
const defaults = MooChart.getOrCreateInstance(attributeOnly);

const overridden = makeRoot({{
  "data-moo-chart": "line",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
}});
const configData = {{ labels: ["Q1"], datasets: [{{ label: "Target", data: [9] }}] }};
const configured = MooChart.getOrCreateInstance(overridden, {{
  type: "bar",
  data: configData,
}});

const programmaticRoot = makeRoot({{ "data-moo-chart": "line" }});
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
  "data-moo-chart": "line",
  "data-moo-chart-data": {json.dumps(VALID_DATA)},
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
    "data-moo-chart": "line",
    "data-moo-chart-data": {json.dumps(VALID_DATA)},
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
const cleared = roots.every((element) => MooChart.getInstance(element) === null);
const secondRelease = initExamplesChart(root);
report("catalog-adapter", {{
  releaseIsFunction: typeof release === "function",
  idempotent: reentered === release,
  initialized,
  cleared,
  reinitializable: typeof secondRelease === "function" && secondRelease !== release,
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
            },
        )

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
        self.assertIn(
            'throw new SyntaxError(\n'
            "        `MooChart could not parse data-moo-chart-data as JSON",
            source,
        )

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
        self.assertIn('data-moo-chart="line"', source)
        self.assertIn('data-moo-chart="bar"', source)
        self.assertIn("data-moo-chart-data", source)
        self.assertIn("role=\"img\"", source)
        self.assertIn("aria-label", source)
        self.assertNotIn("cdn.jsdelivr.net", source)
        self.assertNotIn("window.Chart", source)

    def test_certification_fixture_runs_the_built_bundle_in_browser(self) -> None:
        skip_if_browser_launch_is_sandboxed()
        build = self.run_build()
        self.assertEqual(build.returncode, 0, build.stderr)

        with serve_repository() as base_url:
            with sync_playwright() as playwright:
                browser = launch_certification_browser(playwright)
                try:
                    for case in CERTIFICATION_CASES:
                        with self.subTest(case=case.name):
                            context = new_case_context(browser, case)
                            page = context.new_page()
                            evidence = BrowserEvidence(page)
                            response = page.goto(
                                f"{base_url}/tests/fixtures/certification/chart.html",
                                wait_until="networkidle",
                            )
                            self.assertIsNotNone(response)
                            self.assertTrue(response.ok)
                            prepare_page(page, case)

                            expect(page.locator("body")).to_have_attribute(
                                "data-chart-ready", "true"
                            )
                            self.assertEqual(
                                page.evaluate(
                                    """() => [
                                      window.certificationLineChart.chart.config.type,
                                      window.certificationBarChart.chart.config.type,
                                    ]"""
                                ),
                                ["line", "bar"],
                            )
                            self.assertTrue(
                                page.evaluate(
                                    """() => [
                                      ...document.querySelectorAll('.moo-chart canvas'),
                                    ].slice(0, 2).every(canvas => {
                                      const data = canvas.getContext('2d').getImageData(
                                        0, 0, canvas.width, canvas.height
                                      ).data;
                                      return Array.from(data).some(value => value !== 0);
                                    })"""
                                )
                            )
                            self.assertIn(
                                "MooChart could not parse data-moo-chart-data as JSON:",
                                page.evaluate("() => window.certificationInvalidMessage"),
                            )
                            evidence.assert_clean()
                            context.close()
                finally:
                    browser.close()

    def test_component_page_covers_the_public_contract(self) -> None:
        self.assertTrue(PAGE.is_file(), "Chart page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn("render_reference(", source)
        self.assertIn(".moo-chart", source)
        self.assertIn("data-moo-chart", source)
        self.assertIn("data-moo-chart-data", source)
        for topic in (
            '"line"',
            '"bar"',
            "theme",
            "dispose",
            "resize",
            "aria-label",
            "mobile",
        ):
            self.assertIn(topic, source)


if __name__ == "__main__":
    unittest.main()
