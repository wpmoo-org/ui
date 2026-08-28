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
CHART_MACRO = ROOT / "src/components/chart.html.jinja"
PAGE = ROOT / "site/src/pages/components/chart.html.jinja"
CHARTS_PAGE = ROOT / "site/src/pages/charts.html.jinja"
PUBLIC_CHART_TYPES = (
    "area",
    "line",
    "bar",
    "pie",
    "doughnut",
    "polarArea",
    "radar",
    "scatter",
    "bubble",
)

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
const candidates = [null, undefined, {}, "chart", { nodeType: 3 }];
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
            ["MooChart requires a .chart root element."] * 6,
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
            "MooChart requires a child <canvas> element inside the .chart root.",
        )

    def test_dataset_type_stays_chartjs_native_and_public_aliases_are_root_only(self) -> None:
        source = CHART_JS.read_text(encoding="utf-8")
        self.assertNotIn("function datasetMetadata", source)

        case = self.run_chart_case(
            """
const data = {
  labels: ["Jan", "Feb"],
  datasets: [{ type: "line", label: "Revenue", data: [1, 2] }]
};
const root = makeRoot({
  "data-chart": "bar",
  "data-chart-data": JSON.stringify(data),
});
const instance = MooChart.getOrCreateInstance(root);
report("dataset-native-type", {
  chartType: instance.chart.config.type,
  datasetType: instance.chart.data.datasets[0].type,
});
instance.dispose();
"""
        )
        self.assertEqual(case["chartType"], "bar")
        self.assertEqual(case["datasetType"], "line")

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

    def test_supported_chart_types_are_the_public_rc3_contract(self) -> None:
        case = self.run_chart_case(
            f"""
const chartDataByType = {{
  area: {{ labels: ["Apr", "May"], datasets: [{{ label: "Desktop", data: [142, 188] }}] }},
  line: {{ labels: ["Apr", "May"], datasets: [{{ label: "Mobile", data: [85, 122] }}] }},
  bar: {{ labels: ["Apr", "May"], datasets: [{{ label: "Orders", data: [44, 58] }}] }},
  pie: {{ labels: ["Direct", "Search"], datasets: [{{ label: "Traffic", data: [62, 38] }}] }},
  doughnut: {{ labels: ["Direct", "Search"], datasets: [{{ label: "Traffic", data: [62, 38] }}] }},
  polarArea: {{ labels: ["North", "South"], datasets: [{{ label: "Regions", data: [30, 45] }}] }},
  radar: {{ labels: ["Speed", "Quality"], datasets: [{{ label: "Score", data: [7, 9] }}] }},
  scatter: {{ labels: [], datasets: [{{ label: "Leads", data: [{{ x: 1, y: 4 }}, {{ x: 2, y: 8 }}] }}] }},
  bubble: {{ labels: [], datasets: [{{ label: "Deals", data: [{{ x: 1, y: 4, r: 6 }}, {{ x: 2, y: 8, r: 12 }}] }}] }},
}};
const reportByType = {{}};
for (const publicType of {json.dumps(PUBLIC_CHART_TYPES)}) {{
  const root = makeRoot({{
    "data-chart": publicType,
    "data-chart-data": JSON.stringify(chartDataByType[publicType]),
  }});
  const instance = MooChart.getOrCreateInstance(root);
  const dataset = instance.chart.data.datasets[0];
  reportByType[publicType] = {{
    chartType: instance.chart.config.type,
    labels: instance.chart.data.labels,
    fill: dataset.fill ?? null,
    pointRadius: dataset.pointRadius ?? null,
    dataIsArray: Array.isArray(dataset.data),
  }};
  instance.dispose();
}}
report("supported-types", {{ reportByType }});
"""
        )
        report_by_type = case["reportByType"]
        self.assertEqual(set(report_by_type), set(PUBLIC_CHART_TYPES))
        self.assertEqual(report_by_type["area"]["chartType"], "line")
        self.assertTrue(report_by_type["area"]["fill"])
        self.assertEqual(report_by_type["area"]["pointRadius"], 0)
        self.assertEqual(report_by_type["line"]["chartType"], "line")
        self.assertTrue(report_by_type["line"]["fill"])
        self.assertEqual(report_by_type["bar"]["chartType"], "bar")
        for chart_type in ("pie", "doughnut", "polarArea", "radar", "scatter", "bubble"):
            with self.subTest(chart_type=chart_type):
                self.assertEqual(report_by_type[chart_type]["chartType"], chart_type)
                self.assertTrue(report_by_type[chart_type]["dataIsArray"])
        self.assertEqual(report_by_type["scatter"]["labels"], [])
        self.assertEqual(report_by_type["bubble"]["labels"], [])

    def test_chart_family_defaults_match_cartesian_arc_radial_and_point_types(self) -> None:
        case = self.run_chart_case(
            f"""
const familyData = {{
  pie: {{ labels: ["Direct", "Search"], datasets: [{{ label: "Traffic", data: [62, 38] }}] }},
  doughnut: {{ labels: ["Direct", "Search"], datasets: [{{ label: "Traffic", data: [62, 38] }}] }},
  polarArea: {{ labels: ["North", "South"], datasets: [{{ label: "Regions", data: [30, 45] }}] }},
  radar: {{ labels: ["Speed", "Quality"], datasets: [{{ label: "Score", data: [7, 9] }}] }},
  scatter: {{ labels: [], datasets: [{{ label: "Leads", data: [{{ x: 1, y: 4 }}, {{ x: 2, y: 8 }}] }}] }},
  bubble: {{ labels: [], datasets: [{{ label: "Deals", data: [{{ x: 1, y: 4, r: 6 }}, {{ x: 2, y: 8, r: 12 }}] }}] }},
}};
const reportByType = {{}};
for (const publicType of ["pie", "doughnut", "polarArea", "radar", "scatter", "bubble"]) {{
  const root = makeRoot({{
    "data-chart": publicType,
    "data-chart-data": JSON.stringify(familyData[publicType]),
  }});
  const instance = MooChart.getOrCreateInstance(root);
  const scales = instance.chart.options.scales || {{}};
  reportByType[publicType] = {{
    hasX: Object.prototype.hasOwnProperty.call(scales, "x"),
    hasY: Object.prototype.hasOwnProperty.call(scales, "y"),
    hasR: Object.prototype.hasOwnProperty.call(scales, "r"),
    xType: scales.x?.type ?? null,
    yType: scales.y?.type ?? null,
    mode: instance.chart.options.interaction?.mode ?? null,
    intersect: instance.chart.options.interaction?.intersect ?? null,
  }};
  instance.dispose();
}}
report("family-defaults", {{ reportByType }});
"""
        )
        report_by_type = case["reportByType"]
        for chart_type in ("pie", "doughnut"):
            with self.subTest(chart_type=chart_type):
                self.assertFalse(report_by_type[chart_type]["hasX"])
                self.assertFalse(report_by_type[chart_type]["hasY"])
                self.assertFalse(report_by_type[chart_type]["hasR"])
                self.assertEqual(report_by_type[chart_type]["mode"], "nearest")
        for chart_type in ("polarArea", "radar"):
            with self.subTest(chart_type=chart_type):
                self.assertFalse(report_by_type[chart_type]["hasX"])
                self.assertFalse(report_by_type[chart_type]["hasY"])
                self.assertTrue(report_by_type[chart_type]["hasR"])
                self.assertEqual(report_by_type[chart_type]["mode"], "nearest")
        for chart_type in ("scatter", "bubble"):
            with self.subTest(chart_type=chart_type):
                self.assertTrue(report_by_type[chart_type]["hasX"])
                self.assertTrue(report_by_type[chart_type]["hasY"])
                self.assertEqual(report_by_type[chart_type]["xType"], "linear")
                self.assertEqual(report_by_type[chart_type]["yType"], "linear")
                self.assertEqual(report_by_type[chart_type]["mode"], "nearest")
                self.assertTrue(report_by_type[chart_type]["intersect"])

    def test_line_points_use_series_colors_in_light_mode(self) -> None:
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
report("line-point-colors", {{
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

    def test_chart_palette_tokens_override_bootstrap_semantic_fallbacks(self) -> None:
        chart_data = {
            "labels": ["Jan", "Feb"],
            "datasets": [
                {"label": "Desktop", "data": [18, 24]},
                {"label": "Mobile", "data": [12, 20]},
            ],
        }
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(json.dumps(chart_data))},
}});
const tokenColors = new Map([
  ["--bs-body-color", "rgb(33, 37, 41)"],
  ["--bs-body-bg", "rgb(255, 255, 255)"],
  ["--bs-secondary-color", "rgb(108, 117, 125)"],
  ["--bs-border-color", "rgb(222, 226, 230)"],
  ["--bs-info", "rgb(13, 110, 253)"],
  ["--bs-success", "rgb(25, 135, 84)"],
  ["--bs-warning", "rgb(255, 193, 7)"],
  ["--bs-danger", "rgb(220, 53, 69)"],
  ["--moo-chart-1", "rgb(103, 169, 232)"],
  ["--moo-chart-2", "rgb(118, 187, 170)"],
]);
window.getComputedStyle = (element) => {{
  if (element === documentElement) {{
    return {{ getPropertyValue: (token) => tokenColors.get(token) || "" }};
  }}
  return {{ color: element.style.color, getPropertyValue: () => "" }};
}};
const instance = MooChart.getOrCreateInstance(root);
const datasets = instance.chart.data.datasets;
report("chart-palette-tokens", {{
  firstPoint: datasets[0].pointBackgroundColor,
  firstHover: datasets[0].pointHoverBackgroundColor,
  secondPoint: datasets[1].pointBackgroundColor,
  secondHover: datasets[1].pointHoverBackgroundColor,
}});
"""
        )
        self.assertEqual(case["firstPoint"], "rgb(103, 169, 232)")
        self.assertEqual(case["firstHover"], "rgb(103, 169, 232)")
        self.assertEqual(case["secondPoint"], "rgb(118, 187, 170)")
        self.assertEqual(case["secondHover"], "rgb(118, 187, 170)")

    def test_line_area_and_radar_strokes_are_thin_enough_for_points(self) -> None:
        case = self.run_chart_case(
            f"""
const dataByType = {{
  area: {VALID_DATA},
  line: {VALID_DATA},
  radar: {{ labels: ["Speed", "Quality"], datasets: [{{ label: "Score", data: [7, 9] }}] }},
}};
const reportByType = {{}};
for (const publicType of Object.keys(dataByType)) {{
  const root = makeRoot({{
    "data-chart": publicType,
    "data-chart-data": JSON.stringify(dataByType[publicType]),
  }});
  const instance = MooChart.getOrCreateInstance(root);
  const dataset = instance.chart.data.datasets[0];
  const legendItem = instance.chart.legend.legendItems[0];
  const tooltipColor = instance.chart.options.plugins.tooltip.callbacks.labelColor({{
    chart: instance.chart,
    datasetIndex: 0,
    dataIndex: 0,
  }});
  reportByType[publicType] = {{
    borderWidth: dataset.borderWidth ?? null,
    legendLineWidth: legendItem.lineWidth ?? null,
    tooltipBorderWidth: tooltipColor.borderWidth ?? null,
    pointRadius: dataset.pointRadius ?? null,
    pointHoverRadius: dataset.pointHoverRadius ?? null,
  }};
  instance.dispose();
}}
report("thin-strokes", {{ reportByType }});
"""
        )
        report_by_type = case["reportByType"]
        self.assertEqual(report_by_type["area"]["borderWidth"], 1.5)
        self.assertEqual(report_by_type["area"]["legendLineWidth"], 1)
        self.assertEqual(report_by_type["area"]["tooltipBorderWidth"], 1)
        self.assertEqual(report_by_type["area"]["pointRadius"], 0)
        self.assertEqual(report_by_type["area"]["pointHoverRadius"], 5)
        for chart_type in ("line", "radar"):
            with self.subTest(chart_type=chart_type):
                self.assertEqual(report_by_type[chart_type]["borderWidth"], 1.5)
                self.assertEqual(report_by_type[chart_type]["legendLineWidth"], 1)
                self.assertEqual(report_by_type[chart_type]["tooltipBorderWidth"], 1)
                self.assertEqual(report_by_type[chart_type]["pointRadius"], 3)
                self.assertEqual(report_by_type[chart_type]["pointHoverRadius"], 5)

    def test_explicit_dataset_colors_are_preserved_during_retheme(self) -> None:
        chart_data = {
            "labels": ["Jan", "Feb"],
            "datasets": [
                {
                    "label": "Custom",
                    "data": [18, 24],
                    "backgroundColor": "rgb(9, 10, 11)",
                    "borderColor": "rgb(1, 2, 3)",
                }
            ],
        }
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(json.dumps(chart_data))},
}});
const tokenColors = new Map([
  ["--bs-body-color", "rgb(33, 37, 41)"],
  ["--bs-body-bg", "rgb(255, 255, 255)"],
  ["--bs-secondary-color", "rgb(108, 117, 125)"],
  ["--bs-border-color", "rgb(222, 226, 230)"],
  ["--bs-info", "rgb(13, 110, 253)"],
  ["--bs-success", "rgb(25, 135, 84)"],
  ["--bs-warning", "rgb(255, 193, 7)"],
  ["--bs-danger", "rgb(220, 53, 69)"],
  ["--moo-chart-1", "rgb(103, 169, 232)"],
]);
window.getComputedStyle = (element) => {{
  if (element === documentElement) {{
    return {{ getPropertyValue: (token) => tokenColors.get(token) || "" }};
  }}
  return {{ color: element.style.color, getPropertyValue: () => "" }};
}};
const instance = MooChart.getOrCreateInstance(root);
const observer = observerLog.at(-1);
const dataset = instance.chart.data.datasets[0];
const before = {{
  backgroundColor: dataset.backgroundColor,
  borderColor: dataset.borderColor,
  pointBackgroundColor: dataset.pointBackgroundColor,
}};

tokenColors.set("--moo-chart-1", "rgb(37, 99, 235)");
observer.callback([{{ attributeName: "style" }}]);
await new Promise((resolve) => setTimeout(resolve, 20));

report("explicit-colors", {{
  before,
  after: {{
    backgroundColor: dataset.backgroundColor,
    borderColor: dataset.borderColor,
    pointBackgroundColor: dataset.pointBackgroundColor,
  }},
}});
"""
        )
        self.assertEqual(case["before"]["backgroundColor"], "rgb(9, 10, 11)")
        self.assertEqual(case["before"]["borderColor"], "rgb(1, 2, 3)")
        self.assertEqual(case["before"]["pointBackgroundColor"], "rgb(103, 169, 232)")
        self.assertEqual(case["after"]["backgroundColor"], "rgb(9, 10, 11)")
        self.assertEqual(case["after"]["borderColor"], "rgb(1, 2, 3)")
        self.assertEqual(case["after"]["pointBackgroundColor"], "rgb(37, 99, 235)")

    def test_unset_dataset_colors_follow_inline_chart_tokens_during_retheme(self) -> None:
        chart_data = {
            "labels": ["Mon", "Tue"],
            "datasets": [{"label": "Visitors", "data": [120, 190]}],
        }
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "bar",
  "data-chart-data": {json.dumps(json.dumps(chart_data))},
}});
const tokenColors = new Map([
  ["--bs-body-color", "rgb(33, 37, 41)"],
  ["--bs-body-bg", "rgb(255, 255, 255)"],
  ["--bs-secondary-color", "rgb(108, 117, 125)"],
  ["--bs-border-color", "rgb(222, 226, 230)"],
  ["--bs-info", "rgb(13, 110, 253)"],
  ["--bs-success", "rgb(25, 135, 84)"],
  ["--bs-warning", "rgb(255, 193, 7)"],
  ["--bs-danger", "rgb(220, 53, 69)"],
  ["--moo-chart-1", "rgb(103, 169, 232)"],
]);
window.getComputedStyle = (element) => {{
  if (element === documentElement) {{
    return {{ getPropertyValue: (token) => tokenColors.get(token) || "" }};
  }}
  return {{ color: element.style.color, getPropertyValue: () => "" }};
}};
const instance = MooChart.getOrCreateInstance(root);
const observer = observerLog.at(-1);
const dataset = instance.chart.data.datasets[0];
instance.chart.data.datasets[0] = {{ ...dataset }};
const rethemedDataset = instance.chart.data.datasets[0];
const before = {{
  backgroundColor: rethemedDataset.backgroundColor,
  borderColor: rethemedDataset.borderColor,
  hoverBackgroundColor: rethemedDataset.hoverBackgroundColor,
}};

tokenColors.set("--moo-chart-1", "rgb(174, 62, 201)");
observer.callback([{{ attributeName: "style" }}]);
await new Promise((resolve) => setTimeout(resolve, 20));

report("unset-colors-retheme", {{
  before,
  after: {{
    backgroundColor: rethemedDataset.backgroundColor,
    borderColor: rethemedDataset.borderColor,
    hoverBackgroundColor: rethemedDataset.hoverBackgroundColor,
  }},
}});
"""
        )
        self.assertEqual(case["before"]["backgroundColor"], "rgb(103, 169, 232)")
        self.assertEqual(case["before"]["borderColor"], "rgb(103, 169, 232)")
        self.assertEqual(case["before"]["hoverBackgroundColor"], "rgb(103, 169, 232)")
        self.assertEqual(case["after"]["backgroundColor"], "rgb(174, 62, 201)")
        self.assertEqual(case["after"]["borderColor"], "rgb(174, 62, 201)")
        self.assertEqual(case["after"]["hoverBackgroundColor"], "rgb(174, 62, 201)")

    def test_unsupported_chart_type_is_rejected(self) -> None:
        case = self.run_chart_case(
            """
const root = makeRoot({ "data-chart": "radial" });
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
            'MooChart supports area, line, bar, pie, doughnut, polarArea, radar, scatter, and bubble charts; received "radial".',
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

    def test_invalid_data_chart_options_json_produces_an_explicit_diagnostic(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
  "data-chart-options": "{{not valid json",
}});
let message = "";
let isSyntaxError = false;
try {{
  new MooChart(root);
}} catch (error) {{
  message = error.message;
  isSyntaxError = error instanceof SyntaxError;
}}
report("invalid-options-json", {{ message, isSyntaxError }});
"""
        )
        self.assertTrue(case["isSyntaxError"])
        self.assertIn(
            "MooChart could not parse data-chart-options as JSON:", case["message"]
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

    def test_data_chart_options_json_merges_into_chart_options(self) -> None:
        options = {
            "indexAxis": "y",
            "scales": {"x": {"stacked": True}, "y": {"stacked": True}},
            "plugins": {"legend": {"display": False}},
        }
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "bar",
  "data-chart-data": {json.dumps(VALID_DATA)},
  "data-chart-options": {json.dumps(json.dumps(options))},
}});
const instance = MooChart.getOrCreateInstance(root);
report("options-merge", {{
  indexAxis: instance.chart.options.indexAxis,
  xStacked: instance.chart.options.scales.x.stacked,
  yStacked: instance.chart.options.scales.y.stacked,
  legendDisplay: instance.chart.options.plugins.legend.display,
}});
"""
        )
        self.assertEqual(case["indexAxis"], "y")
        self.assertTrue(case["xStacked"])
        self.assertTrue(case["yStacked"])
        self.assertFalse(case["legendDisplay"])

    def test_legend_point_markers_are_compact_circles(self) -> None:
        case = self.run_chart_case(
            f"""
const root = makeRoot({{
  "data-chart": "pie",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const instance = MooChart.getOrCreateInstance(root);
const labels = instance.chart.options.plugins.legend.labels;
const tooltip = instance.chart.options.plugins.tooltip;
const tooltipPoint = tooltip.callbacks.labelPointStyle();
const legendItem = instance.chart.legend.legendItems[0];
const tooltipColor = tooltip.callbacks.labelColor({{
  chart: instance.chart,
  datasetIndex: 0,
  dataIndex: 0,
}});
report("legend-point-markers", {{
  legendUsePointStyle: labels.usePointStyle,
  legendPointStyle: labels.pointStyle ?? null,
  legendBoxWidth: labels.boxWidth ?? null,
  legendBoxHeight: labels.boxHeight ?? null,
  legendFontSize: labels.font.size,
  legendPointStyleWidth: labels.pointStyleWidth ?? null,
  legendTextOffset: labels.boxWidth + labels.font.size / 2,
  legendVisualDiameter: labels.boxHeight * Math.SQRT2,
  legendFillStyle: legendItem.fillStyle,
  legendStrokeStyle: legendItem.strokeStyle,
  legendLineWidth: legendItem.lineWidth,
  tooltipUsePointStyle: tooltip.usePointStyle,
  tooltipBoxWidth: tooltip.boxWidth ?? null,
  tooltipBoxHeight: tooltip.boxHeight ?? null,
  tooltipBoxPadding: tooltip.boxPadding ?? null,
  tooltipTextOffset: tooltip.boxWidth + 2 + tooltip.boxPadding,
  tooltipVisualDiameter: Math.min(tooltip.boxWidth, tooltip.boxHeight),
  tooltipPointStyle: tooltipPoint.pointStyle ?? null,
  tooltipRotation: tooltipPoint.rotation ?? null,
  tooltipBorderColor: tooltipColor.borderColor,
  tooltipBackgroundColor: tooltipColor.backgroundColor,
  tooltipBorderWidth: tooltipColor.borderWidth,
}});
"""
        )
        self.assertTrue(case["legendUsePointStyle"])
        self.assertEqual(case["legendPointStyle"], "circle")
        self.assertEqual(case["legendBoxWidth"], 6)
        self.assertEqual(case["legendBoxHeight"], 6)
        self.assertIsNone(case["legendPointStyleWidth"])
        self.assertTrue(case["tooltipUsePointStyle"])
        self.assertAlmostEqual(
            case["tooltipBoxWidth"],
            case["legendVisualDiameter"],
            places=4,
        )
        self.assertAlmostEqual(
            case["tooltipBoxHeight"],
            case["legendVisualDiameter"],
            places=4,
        )
        self.assertAlmostEqual(
            case["tooltipVisualDiameter"],
            case["legendVisualDiameter"],
            places=4,
        )
        self.assertAlmostEqual(
            case["tooltipTextOffset"],
            case["legendTextOffset"],
            places=4,
        )
        self.assertEqual(case["tooltipPointStyle"], "circle")
        self.assertEqual(case["tooltipRotation"], 0)
        self.assertEqual(case["tooltipBackgroundColor"], case["legendFillStyle"])
        self.assertEqual(case["tooltipBorderColor"], case["legendStrokeStyle"])
        self.assertEqual(case["tooltipBorderWidth"], case["legendLineWidth"])

    def test_point_hover_markers_stay_readable_without_oversizing_legend(self) -> None:
        case = self.run_chart_case(
            f"""
const dataByType = {{
  area: {VALID_DATA},
  line: {VALID_DATA},
  radar: {{ labels: ["Speed", "Quality"], datasets: [{{ label: "Score", data: [7, 9] }}] }},
  scatter: {{ labels: [], datasets: [{{ label: "Leads", data: [{{ x: 1, y: 4 }}, {{ x: 2, y: 8 }}] }}] }},
}};
const reportByType = {{}};
for (const publicType of Object.keys(dataByType)) {{
  const root = makeRoot({{
    "data-chart": publicType,
    "data-chart-data": JSON.stringify(dataByType[publicType]),
  }});
  const instance = MooChart.getOrCreateInstance(root);
  const dataset = instance.chart.data.datasets[0];
  const labels = instance.chart.options.plugins.legend.labels;
  reportByType[publicType] = {{
    markerSize: labels.boxWidth,
    pointRadius: dataset.pointRadius ?? null,
    pointHoverRadius: dataset.pointHoverRadius ?? null,
    pointHoverBorderWidth: dataset.pointHoverBorderWidth ?? null,
  }};
  instance.dispose();
}}
report("line-area-hover-points", {{ reportByType }});
"""
        )
        report_by_type = case["reportByType"]
        self.assertEqual(report_by_type["area"]["pointRadius"], 0)
        for chart_type in ("area", "line", "radar", "scatter"):
            with self.subTest(chart_type=chart_type):
                report = report_by_type[chart_type]
                self.assertEqual(report["markerSize"], 6)
                self.assertEqual(report["pointHoverRadius"] * 2, 10)
                self.assertEqual(report["pointHoverBorderWidth"], 0)
        for chart_type in ("line", "radar", "scatter"):
            with self.subTest(chart_type=chart_type):
                self.assertEqual(
                    report_by_type[chart_type]["pointRadius"] * 2,
                    report_by_type[chart_type]["markerSize"],
                )

    def test_data_chart_options_are_safe_json_pass_through_with_config_precedence(
        self,
    ) -> None:
        raw_options = (
            '{"indexAxis":"y","plugins":{"legend":{"display":false}},'
            '"__proto__":{"polluted":"yes"},'
            '"constructor":{"prototype":{"polluted":"yes"}},'
            '"prototype":{"polluted":"yes"}}'
        )
        case = self.run_chart_case(
            f"""
delete Object.prototype.polluted;
const root = makeRoot({{
  "data-chart": "bar",
  "data-chart-data": {json.dumps(VALID_DATA)},
  "data-chart-options": {json.dumps(raw_options)},
}});
const instance = MooChart.getOrCreateInstance(root, {{
  options: {{
    plugins: {{
      legend: {{ display: true }},
    }},
  }},
}});
report("safe-options", {{
  indexAxis: instance.chart.options.indexAxis,
  legendDisplay: instance.chart.options.plugins.legend.display,
  protoPolluted: Object.prototype.polluted === "yes",
  hasOwnConstructor: Object.prototype.hasOwnProperty.call(
    instance.chart.options,
    "constructor",
  ),
  hasOwnPrototype: Object.prototype.hasOwnProperty.call(
    instance.chart.options,
    "prototype",
  ),
  hasOwnProto: Object.prototype.hasOwnProperty.call(
    instance.chart.options,
    "__proto__",
  ),
}});
"""
        )
        self.assertEqual(case["indexAxis"], "y")
        self.assertTrue(case["legendDisplay"])
        self.assertFalse(case["protoPolluted"])
        self.assertFalse(case["hasOwnConstructor"])
        self.assertFalse(case["hasOwnPrototype"])
        self.assertFalse(case["hasOwnProto"])

    def test_reduced_motion_prefers_zero_duration_chart_animation(self) -> None:
        case = self.run_chart_case(
            f"""
window.matchMedia = (query) => ({{
  matches: query === "(prefers-reduced-motion: reduce)",
  media: query,
  addEventListener() {{}},
  removeEventListener() {{}},
}});
const root = makeRoot({{
  "data-chart": "line",
  "data-chart-data": {json.dumps(VALID_DATA)},
}});
const instance = MooChart.getOrCreateInstance(root);
report("reduced-motion", {{
  animation: instance.chart.options.animation,
  hoverDuration: instance.chart.options.hover.animationDuration,
}});
"""
        )
        self.assertFalse(case["animation"])
        self.assertEqual(case["hoverDuration"], 0)

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
        self.assertEqual(case["attributeFilter"], ["data-bs-theme", "style"])
        # One unrelated mutation plus one data-bs-theme mutation must produce
        # exactly one coalesced re-theme update.
        self.assertEqual(case["updates"], 1)

    def test_theme_observer_rethemes_when_inline_chart_tokens_change(self) -> None:
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
const observer = observerLog.at(-1);
const before = instance.chart.data.datasets[0].pointBackgroundColor;

tokenColors.set("--moo-chart-1", "rgb(103, 169, 232)");
observer.callback([{{ attributeName: "style" }}]);
await new Promise((resolve) => setTimeout(resolve, 20));

report("style-token-retheme", {{
  before,
  after: instance.chart.data.datasets[0].pointBackgroundColor,
}});
"""
        )
        self.assertEqual(case["before"], "rgb(13, 110, 253)")
        self.assertEqual(case["after"], "rgb(103, 169, 232)")

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

    def test_catalog_adapter_initializes_and_disposes_chart_roots(self) -> None:
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
  querySelectorAll: (selector) => (selector === ".chart" ? roots : []),
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
    if (selector === ".chart") return chartRoot;
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
    if (selector === ".chart") return [chartRoot];
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
    if (selector === ".chart") return chartRoot;
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
    if (selector === ".chart") return [chartRoot];
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
        page = self.read_output("charts.html")
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

    def test_chart_toolbar_copy_icons_use_toggleable_wrappers(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("charts.html")
        toolbar = page.split('class="moo-chart-example__actions"', 1)[1].split(
            "</button>",
            1,
        )[0]

        self.assertIn('data-moo-code-copy-target="#chart-area-default-example-code"', toolbar)
        self.assertIn('<span data-moo-copy-icon="copy">', toolbar)
        self.assertIn('<span data-moo-copy-icon="check" hidden>', toolbar)
        self.assertNotIn("<svg data-moo-copy-icon", toolbar)

    def test_lifecycle_controls_are_centered_in_preview(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("charts.html")
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
        page = self.read_output("charts.html")
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
        self.assertIn('attributeFilter: ["data-bs-theme", "style"]', source)

        # The documented getters must actually exist in the source so the
        # API freeze cannot drift from the implementation.
        self.assertIn("get chart()", source)
        self.assertIn("get element()", source)

    def test_chart_macro_accepts_all_public_types_and_options(self) -> None:
        source = CHART_MACRO.read_text(encoding="utf-8")

        self.assertIn("options=None", source)
        self.assertIn("data-chart-options", source)
        self.assertIn('data-chart="{{ type }}"', source)
        self.assertIn("data-chart-data", source)
        self.assertIn('<canvas role="img" aria-label="{{ aria_label }}"></canvas>', source)
        self.assertNotIn('["line", "bar"]', source)
        for chart_type in PUBLIC_CHART_TYPES:
            with self.subTest(chart_type=chart_type):
                self.assertIn(f'"{chart_type}"', source)

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
        self.assertIn('class="chart"', source)
        self.assertIn('data-chart="line"', source)
        self.assertIn('data-chart="bar"', source)
        self.assertIn("data-chart-data", source)
        self.assertIn("role=\"img\"", source)
        self.assertIn("aria-label", source)
        self.assertNotIn("cdn.jsdelivr.net", source)
        self.assertNotIn("window.Chart", source)

    def test_component_page_covers_the_public_contract(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(PAGE.is_file(), "Chart page is not implemented")
        source = self.read_output("components/chart.html")

        self.assertIn("Chart.js documentation", source)
        self.assertIn(".chart", source)
        self.assertNotIn('class="moo-chart"', source)
        self.assertNotIn('document.querySelector(".moo-chart")', source)
        self.assertNotIn("<code>.moo-chart</code>", source)
        self.assertNotIn(".moo-chart root", source)
        self.assertIn("data-chart", source)
        self.assertIn("data-chart-data", source)
        self.assertIn("data-chart-options", source)
        self.assertIn('href="../../charts/"', source)
        self.assertIn("View chart examples", source)
        for chart_type in PUBLIC_CHART_TYPES:
            with self.subTest(chart_type=chart_type):
                self.assertIn(chart_type, source)
        self.assertRegex(
            source,
            r'class="chart w-100"\s+id="chart-area-default"',
        )
        for gallery_id in (
            "chart-area-step",
            "chart-area-stacked",
            "chart-bar-default",
            "chart-bar-horizontal",
            "chart-bar-multiple",
            "chart-bar-stacked",
            "chart-bar-negative",
            "chart-line-default",
            "chart-line-plain",
            "chart-line-step",
            "chart-line-multiple",
            "chart-pie-default",
            "chart-doughnut-default",
            "chart-doughnut-ring",
            "chart-radar-default",
            "chart-radar-multiple",
            "chart-polar-area",
            "chart-radial-progress",
            "chart-scatter-default",
            "chart-bubble-default",
            "chart-tooltip-index",
            "chart-tooltip-nearest",
            "chart-lifecycle",
            "chart-lifecycle-example",
        ):
            self.assertNotIn(gallery_id, source)
        self.assertIn('role="img"', source)
        self.assertIn("aria-label", source)
        for topic in (
            "<code>line</code>",
            "<code>bar</code>",
            "theme",
            "dispose",
            "resize",
            "aria-label",
            "mobile",
        ):
            self.assertIn(topic, source)
        self.assertNotIn("window.Chart", source)
        self.assertNotIn("Recharts", source)

    def test_component_page_labels_adjacent_javascript_snippets(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        source = self.read_output("components/chart.html")

        ordered_contracts = (
            '<h2 id="chart-javascript"',
            '<h3 class="h6" id="chart-javascript-init">Initialize a chart</h3>',
            '<p class="mb-0"><span class="text-body-secondary">Use this when a page already renders a .chart root',
            "Use this when a page already renders a .chart root and needs the wrapper to attach Chart.js.",
            'id="chart-javascript-import-code"',
            '<h3 class="h6" id="chart-javascript-callbacks">Customize tooltips</h3>',
            '<p class="mb-0"><span class="text-body-secondary">Use this for non-serializable Chart.js options',
            "Use this for non-serializable Chart.js options, such as tooltip callback functions.",
            'id="chart-tooltip-callback-code"',
            '<h2 id="chart-theming"',
        )
        last_index = -1
        for contract in ordered_contracts:
            with self.subTest(contract=contract):
                index = source.find(contract)
                self.assertGreater(index, last_index)
                last_index = index

        template = (ROOT / "site/src/includes/chart-template.html.jinja").read_text(
            encoding="utf-8"
        )
        self.assertIn("render_chart_code_section(", template)
        self.assertIn('variant="subsection-title"', template)
        self.assertNotIn('<h3 id="chart-javascript-init"', template)
        self.assertNotIn('<h3 id="chart-javascript-callbacks"', template)

    def test_charts_page_contains_the_live_gallery(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(CHARTS_PAGE.is_file(), "Charts gallery page is not implemented")
        source = self.read_output("charts.html")

        self.assertIn(">Charts<", source)
        self.assertIn("Chart.js documentation", source)
        self.assertIn('href="../components/chart/"', source)
        for chart_type in PUBLIC_CHART_TYPES:
            with self.subTest(chart_type=chart_type):
                self.assertIn(f'data-chart="{chart_type}"', source)
        for chart_id in (
            "chart-area-default",
            "chart-area-step",
            "chart-area-stacked",
            "chart-bar-default",
            "chart-bar-horizontal",
            "chart-bar-multiple",
            "chart-bar-stacked",
            "chart-bar-negative",
            "chart-line-default",
            "chart-line-plain",
            "chart-line-step",
            "chart-line-multiple",
            "chart-pie-default",
            "chart-doughnut-default",
            "chart-doughnut-ring",
            "chart-radar-default",
            "chart-radar-multiple",
            "chart-polar-area",
            "chart-radial-progress",
            "chart-scatter-default",
            "chart-bubble-default",
            "chart-tooltip-index",
            "chart-tooltip-nearest",
            "chart-lifecycle-example",
        ):
            self.assertRegex(
                source,
                rf'class="chart w-100"\s+id="{chart_id}"',
            )
        self.assertRegex(
            source,
            r'class="[^"]*\bd-grid\b[^"]*\bgap-3\b[^"]*\bw-100\b[^"]*"\s+data-chart-live',
        )
        self.assertIn("data-chart-lifecycle", source)
        self.assertNotIn("window.Chart", source)
        self.assertNotIn("Recharts", source)


if __name__ == "__main__":
    unittest.main()
