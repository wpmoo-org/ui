from __future__ import annotations

import json
import importlib
import subprocess
import sys
import unittest

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase, scss_rule_body
from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    run_axe,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)
from tests.helpers.node_harness import NODE_TEST_TIMEOUT


COMPONENT = ROOT / "src/components/slider.html.jinja"
PAGE = ROOT / "site/src/pages/components/slider.html.jinja"
SLIDER_JS = ROOT / "src/js/components/slider.js"
SLIDER_SCSS = ROOT / "scss/components/_slider.scss"
FIXTURE = ROOT / "tests/fixtures/certification/slider.html"
FIXTURE_PATH = "/tests/fixtures/certification/slider.html"


class SliderTests(CatalogTestCase):
    def render_slider(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Slider macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/slider.html.jinja" import slider, slider_range %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def run_node(self, script: str) -> dict[str, object]:
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", script],
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

    def test_single_slider_renders_native_range_with_output(self) -> None:
        output = self.render_slider(
            'slider(id="volume", label="Volume", name="volume", value=60)'
        )

        self.assertIn('class="slider"', output)
        self.assertIn("data-slider", output)
        self.assertIn('data-slider-orientation="horizontal"', output)
        self.assertIn('style="--moo-slider-start: 0%; --moo-slider-end: 60.0%;"', output)
        self.assertIn('<label class="form-label mb-0" for="volume">Volume</label>', output)
        self.assertIn('class="form-range slider-input"', output)
        self.assertIn('type="range"', output)
        self.assertIn('name="volume"', output)
        self.assertIn("data-slider-input", output)
        self.assertIn('<output class="small text-body-secondary" for="volume" data-slider-output>60</output>', output)
        self.assertNotIn('role="slider"', output)
        self.assertNotIn('role="progressbar"', output)

    def test_range_slider_renders_two_named_native_inputs(self) -> None:
        output = self.render_slider(
            'slider_range(id="price", label="Price", start_name="price_min", '
            'end_name="price_max", start_value=25, end_value=75, step=5)'
        )

        self.assertIn('class="slider slider--range"', output)
        self.assertIn('role="group"', output)
        self.assertEqual(output.count('type="range"'), 2)
        self.assertIn('id="price-start"', output)
        self.assertIn('id="price-end"', output)
        self.assertIn('name="price_min"', output)
        self.assertIn('name="price_max"', output)
        self.assertIn('data-slider-thumb="start"', output)
        self.assertIn('data-slider-thumb="end"', output)
        self.assertIn('aria-label="Minimum Price"', output)
        self.assertIn('aria-label="Maximum Price"', output)
        self.assertIn('data-slider-output>25 - 75</output>', output)
        self.assertNotIn('role="slider"', output)

    def test_vertical_slider_renders_native_orientation_metadata(self) -> None:
        single = self.render_slider(
            'slider(id="height", label="Height", value=40, orientation="vertical")'
        )
        range_slider = self.render_slider(
            'slider_range(id="range-height", label="Height range", '
            'start_value=30, end_value=70, orientation="vertical")'
        )

        self.assertIn('class="slider slider--vertical"', single)
        self.assertIn('aria-orientation="vertical"', single)
        self.assertEqual(range_slider.count('aria-orientation="vertical"'), 2)

    def test_slider_rejects_invalid_macro_contracts(self) -> None:
        invalid_calls = (
            'slider(id="", label="Volume")',
            'slider(id="volume")',
            'slider(id="volume", label="Volume", aria_label="Volume")',
            'slider(id="volume", label="Volume", min=10, max=10)',
            'slider(id="volume", label="Volume", value=120)',
            'slider(id="volume", label="Volume", orientation="diagonal")',
            'slider_range(id="price", label="Price", start_value=80, end_value=20)',
        )
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    self.render_slider(call)

    def test_slider_js_lifecycle_syncs_output_fill_and_range_order(self) -> None:
        case = self.run_node(
            r'''
import Slider from "./src/js/components/slider.js";

class EventStub {
  constructor(type, options = {}) {
    this.type = type;
    this.bubbles = Boolean(options.bubbles);
  }
}

class CustomEventStub extends EventStub {}

const ownerWindow = {
  Event: EventStub,
  CustomEvent: CustomEventStub,
  getComputedStyle: () => ({ direction: "ltr" }),
  setTimeout: (callback) => callback(),
};
let ownerDocument;

function makeStyle() {
  const props = new Map();
  return {
    props,
    setProperty: (name, value) => props.set(name, value),
    getPropertyValue: (name) => props.get(name) || "",
  };
}

function makeEventTarget(base = {}) {
  const handlers = new Map();
  return {
    ...base,
    addEventListener(type, handler) {
      handlers.set(type, [...(handlers.get(type) || []), handler]);
    },
    removeEventListener(type, handler) {
      handlers.set(type, (handlers.get(type) || []).filter((item) => item !== handler));
    },
    dispatchEvent(event) {
      (handlers.get(event.type) || []).forEach((handler) => handler(event));
      return true;
    },
  };
}

ownerDocument = makeEventTarget({ defaultView: ownerWindow });

function makeInput({ value, min = "0", max = "100", step = "5", disabled = false, form = null }) {
  const attrs = new Map();
  return makeEventTarget({
    nodeType: 1,
    type: "range",
    value: String(value),
    min,
    max,
    step,
    disabled,
    defaultValue: String(value),
    form,
    focused: false,
    ownerDocument,
    setAttribute(name, nextValue) { attrs.set(name, String(nextValue)); },
    getAttribute(name) { return attrs.get(name) || null; },
    focus() { this.focused = true; },
  });
}

function makeRoot(inputs, orientation = "horizontal") {
  const output = { textContent: "" };
  const attrs = new Map();
  const track = makeEventTarget({
    getBoundingClientRect: () => ({ left: 0, right: 200, top: 0, bottom: 20, width: 200, height: 20 }),
  });
  const root = makeEventTarget({
    nodeType: 1,
    dataset: { sliderOrientation: orientation },
    style: makeStyle(),
    ownerDocument,
    matches: (selector) => selector === "[data-slider]",
    setAttribute(name, value) { attrs.set(name, String(value)); },
    removeAttribute(name) { attrs.delete(name); },
    getAttribute(name) { return attrs.get(name) || null; },
    querySelectorAll: () => inputs,
    querySelector: (selector) => {
      if (selector === "[data-slider-track]") return track;
      if (selector === "[data-slider-output]") return output;
      return null;
    },
  });
  return { root, track, output, inputs };
}

const single = makeRoot([makeInput({ value: 60 })]);
const singleInstance = Slider.getOrCreateInstance(single.root);
const sameSingle = Slider.getOrCreateInstance(single.root);
single.inputs[0].value = "80";
single.inputs[0].dispatchEvent(new EventStub("input", { bubbles: true }));

const range = makeRoot([
  makeInput({ value: 25 }),
  makeInput({ value: 75 }),
]);
Slider.getOrCreateInstance(range.root);
range.inputs[0].value = "95";
range.inputs[0].dispatchEvent(new EventStub("input", { bubbles: true }));

const collapsedRange = makeRoot([
  makeInput({ value: 50 }),
  makeInput({ value: 50 }),
]);
Slider.getOrCreateInstance(collapsedRange.root);
collapsedRange.track.dispatchEvent({ type: "pointerdown", button: 0, clientX: 150, clientY: 10, preventDefault() {} });
ownerDocument.dispatchEvent({ type: "pointerup", clientX: 150, clientY: 10, preventDefault() {} });

const stepAny = makeRoot([makeInput({ value: 0, step: "any" })]);
Slider.getOrCreateInstance(stepAny.root);
stepAny.track.dispatchEvent({ type: "pointerdown", button: 0, clientX: 67, clientY: 10, preventDefault() {} });
ownerDocument.dispatchEvent({ type: "pointerup", clientX: 67, clientY: 10, preventDefault() {} });

const resetForm = makeEventTarget();
const resettable = makeRoot([makeInput({ value: 20, form: resetForm })]);
Slider.getOrCreateInstance(resettable.root);
resettable.inputs[0].value = "90";
resettable.inputs[0].dispatchEvent(new EventStub("input", { bubbles: true }));
resettable.inputs[0].value = resettable.inputs[0].defaultValue;
resetForm.dispatchEvent(new EventStub("reset", { bubbles: true }));

const staleLifecycle = makeRoot([makeInput({ value: 30 })]);
const staleInstance = Slider.getOrCreateInstance(staleLifecycle.root);
staleInstance.dispose();
const replacementInstance = Slider.getOrCreateInstance(staleLifecycle.root);
staleInstance.dispose();

single.track.dispatchEvent({ type: "pointerdown", button: 0, clientX: 100, clientY: 10, preventDefault() {} });
ownerDocument.dispatchEvent({ type: "pointermove", clientX: 150, clientY: 10, preventDefault() {} });
ownerDocument.dispatchEvent({ type: "pointerup", clientX: 150, clientY: 10, preventDefault() {} });
const pointerFocusState = single.root.getAttribute("data-slider-pointer-focus");
const dragStateAfterRelease = single.root.getAttribute("data-slider-dragging");
singleInstance.dispose();

console.log(JSON.stringify({
  name: "slider-js",
  ok: true,
  idempotent: sameSingle === singleInstance,
  singleOutput: single.output.textContent,
  singleStart: single.root.style.getPropertyValue("--moo-slider-start"),
  singleEnd: single.root.style.getPropertyValue("--moo-slider-end"),
  rangeStartValue: range.inputs[0].value,
  rangeEndValue: range.inputs[1].value,
  rangeOutput: range.output.textContent,
  collapsedRangeStartValue: collapsedRange.inputs[0].value,
  collapsedRangeEndValue: collapsedRange.inputs[1].value,
  collapsedRangeFocusedEnd: collapsedRange.inputs[1].focused,
  stepAnyValue: stepAny.inputs[0].value,
  resetOutput: resettable.output.textContent,
  resetEnd: resettable.root.style.getPropertyValue("--moo-slider-end"),
  staleDisposeKeepsReplacement: Slider.getInstance(staleLifecycle.root) === replacementInstance,
  trackClickFocusedInput: single.inputs[0].focused,
  pointerFocusState,
  dragStateAfterRelease,
  pointerFocusDisposed: single.root.getAttribute("data-slider-pointer-focus"),
  disposed: Slider.getInstance(single.root) === null,
}));
'''
        )

        self.assertEqual(case["name"], "slider-js")
        self.assertTrue(case["idempotent"])
        self.assertEqual(case["singleOutput"], "75")
        self.assertEqual(case["singleStart"], "0%")
        self.assertEqual(case["singleEnd"], "75%")
        self.assertEqual(case["rangeStartValue"], "75")
        self.assertEqual(case["rangeEndValue"], "75")
        self.assertEqual(case["rangeOutput"], "75 - 75")
        self.assertEqual(case["collapsedRangeStartValue"], "50")
        self.assertEqual(case["collapsedRangeEndValue"], "75")
        self.assertTrue(case["collapsedRangeFocusedEnd"])
        self.assertEqual(case["stepAnyValue"], "33.5")
        self.assertEqual(case["resetOutput"], "20")
        self.assertEqual(case["resetEnd"], "20%")
        self.assertTrue(case["staleDisposeKeepsReplacement"])
        self.assertTrue(case["trackClickFocusedInput"])
        self.assertEqual(case["pointerFocusState"], "true")
        self.assertIsNone(case["dragStateAfterRelease"])
        self.assertIsNone(case["pointerFocusDisposed"])
        self.assertTrue(case["disposed"])

    def test_slider_source_stays_native_and_self_contained(self) -> None:
        source = SLIDER_JS.read_text(encoding="utf-8")

        self.assertIn('matches("[data-slider]")', source)
        self.assertIn('input[type="range"][data-slider-input]', source)
        self.assertIn('"data-slider-pointer-focus"', source)
        self.assertIn('"data-slider-dragging"', source)
        self.assertIn('"--moo-slider-start"', source)
        self.assertIn('"--moo-slider-end"', source)
        self.assertIn("WeakMap", source)
        self.assertIn("dispose()", source)
        self.assertNotIn("role=\"slider\"", source)
        self.assertNotIn("from \"@radix-ui", source)
        self.assertNotIn("from '" + "@radix-ui", source)

    def test_slider_styles_reuse_bootstrap_range_and_progress_tokens(self) -> None:
        styles = SLIDER_SCSS.read_text(encoding="utf-8")

        self.assertIn("$form-range-track-bg", styles)
        self.assertIn("border-radius: var(--bs-border-radius-pill);", styles)
        self.assertIn("box-shadow: var(--bs-box-shadow-inset);", styles)
        self.assertIn("$form-range-thumb-width * 0.75", styles)
        self.assertIn("$slider-thumb-margin-top", styles)
        self.assertIn("$progress-height", styles)
        self.assertIn("background-color: var(--moo-primary);", styles)
        self.assertIn("border-color: var(--moo-primary);", styles)
        self.assertIn("var(--bs-body-bg)", styles)
        self.assertIn(".slider-input::-webkit-slider-thumb:active", styles)
        self.assertIn(".slider-input::-moz-range-thumb:active", styles)
        self.assertIn(".slider-input:disabled::-webkit-slider-thumb", styles)
        self.assertIn("background-color: var(--moo-muted-surface);", styles)
        self.assertIn("border-color: var(--moo-disabled-foreground);", styles)
        self.assertIn(".slider:has(.slider-input:disabled) .slider-track", styles)
        self.assertIn(".slider:has(.slider-input:disabled) .slider-range", styles)
        self.assertIn("writing-mode: vertical-lr;", styles)
        self.assertIn(".slider[data-slider-pointer-focus]", styles)
        self.assertIn(".slider[data-slider-dragging]", styles)
        self.assertIn(
            ".slider[data-slider-pointer-focus]:not([data-slider-dragging]) .slider-input:focus::-webkit-slider-thumb",
            styles,
        )
        self.assertIn(
            ".slider[data-slider-pointer-focus]:not([data-slider-dragging]) .slider-input:focus::-moz-range-thumb",
            styles,
        )
        self.assertNotIn(
            ".slider[data-slider-pointer-focus]:not([data-slider-dragging]) .slider-input:focus-visible::-webkit-slider-thumb",
            styles,
        )
        self.assertNotIn(
            ".slider[data-slider-pointer-focus]:not([data-slider-dragging]) .slider-input:focus-visible::-moz-range-thumb",
            styles,
        )
        self.assertNotIn("border-color: var(--moo-ring);", styles)
        self.assertNotIn("#0", styles)

    def test_vertical_slider_output_reserves_stable_digit_width(self) -> None:
        scss = SLIDER_SCSS.read_text(encoding="utf-8")
        output_block = scss_rule_body(scss, ".slider--vertical [data-slider-output]")

        self.assertIn("min-width: 3ch;", output_block)
        self.assertIn("text-align: end;", output_block)
        self.assertIn("font-variant-numeric: tabular-nums;", output_block)

    def test_slider_catalog_page_and_fixture_are_wired(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        fixture = FIXTURE.read_text(encoding="utf-8")

        self.assertIn('from "components/slider.html.jinja" import slider, slider_range', page)
        self.assertIn("Bootstrap Range documentation", page)
        self.assertIn("data-slider", fixture)
        self.assertNotIn("data-moo-slider", fixture)
        self.assertIn('import Slider from "/dist/js/slider.js";', fixture)
        self.assertIn('document.body.dataset.sliderReady = "true";', fixture)


class _SliderBrowserMixin:
    @classmethod
    def setUpClass(cls) -> None:
        global expect
        playwright_sync = importlib.import_module("playwright.sync_api")

        expect = playwright_sync.expect
        skip_if_browser_launch_is_sandboxed()
        build = subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if build.returncode:
            raise AssertionError(build.stderr)
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright_manager = playwright_sync.sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.addClassCleanup(cls.playwright_manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def open_fixture(self, case=CERTIFICATION_CASES[0]):
        context = new_case_context(self.browser, case)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        response = page.goto(f"{self.base_url}{FIXTURE_PATH}", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, case)
        return context, page, evidence

    def click_track_percent(self, page, selector: str, percent: float) -> None:
        track = page.locator(selector).locator("[data-slider-track]")
        box = track.bounding_box()
        self.assertIsNotNone(box)
        assert box is not None
        track.click(position={"x": box["width"] * percent, "y": box["height"] / 2})

    def test_fixture_proves_slider_lifecycle_form_pointer_and_accessibility(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-slider-ready", "true")

            single = page.locator("#certification-slider")
            single_input = page.locator("#certification-slider-input")
            single_input.focus()
            single_input.press("ArrowRight")
            expect(single_input).to_have_value("65")
            expect(single.locator("[data-slider-output]")).to_have_text("65")
            self.assertEqual(
                single.evaluate("element => element.style.getPropertyValue('--moo-slider-end')"),
                "65%",
            )

            range_slider = page.locator("#certification-slider-range")
            page.locator("#certification-slider-range-start").evaluate(
                """
                input => {
                  input.value = "95";
                  input.dispatchEvent(new Event("input", { bubbles: true }));
                }
                """
            )
            expect(page.locator("#certification-slider-range-start")).to_have_value("75")
            expect(page.locator("#certification-slider-range-end")).to_have_value("75")
            expect(range_slider.locator("[data-slider-output]")).to_have_text("75 - 75")

            self.click_track_percent(page, "#certification-slider-collapsed-range", 0.75)
            expect(page.locator("#certification-slider-collapsed-range-start")).to_have_value("50")
            expect(page.locator("#certification-slider-collapsed-range-end")).to_have_value("75")
            expect(
                page.locator("#certification-slider-collapsed-range [data-slider-output]")
            ).to_have_text("50 - 75")

            self.click_track_percent(page, "#certification-slider-step-any", 0.335)
            expect(page.locator("#certification-slider-step-any-input")).to_have_value("33.5")
            expect(page.locator("#certification-slider-step-any [data-slider-output]")).to_have_text("33.5")

            expect(page.locator("#certification-slider-vertical-input")).to_have_attribute(
                "aria-orientation",
                "vertical",
            )

            self.click_track_percent(page, "#certification-slider-disabled", 0.8)
            expect(page.locator("#certification-slider-disabled-input")).to_have_value("40")

            page.locator("#slider-fixture-reset").click()
            expect(single_input).to_have_value("60")
            expect(single.locator("[data-slider-output]")).to_have_text("60")
            expect(page.locator("#certification-slider-step-any-input")).to_have_value("10")
            expect(page.locator("#certification-slider-step-any [data-slider-output]")).to_have_text("10")
            expect(page.locator("#certification-slider-collapsed-range-end")).to_have_value("50")
            expect(
                page.locator("#certification-slider-collapsed-range [data-slider-output]")
            ).to_have_text("50 - 50")

            form_data = page.evaluate(
                """
                () => Object.fromEntries(new FormData(document.querySelector("#slider-fixture-form")))
                """
            )
            self.assertEqual(
                form_data,
                {
                    "volume": "60",
                    "price_min": "25",
                    "price_max": "75",
                    "gain": "70",
                    "opacity": "10",
                    "collapsed_price_min": "50",
                    "collapsed_price_max": "50",
                },
            )
            self.assertEqual(run_axe(page), [])
            evidence.assert_clean()
        finally:
            context.close()

    def test_vertical_slider_reserves_value_width_as_output_digits_change(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-slider-ready", "true")
            slider = page.locator("#certification-slider-vertical")
            input_control = page.locator("#certification-slider-vertical-input")

            def measure(value: str) -> dict[str, float | str]:
                input_control.evaluate(
                    """
                    (input, value) => {
                      input.value = value;
                      input.dispatchEvent(new Event("input", { bubbles: true }));
                    }
                    """,
                    value,
                )
                return slider.evaluate(
                    """
                    element => {
                      const track = element.querySelector("[data-slider-track]");
                      const output = element.querySelector("[data-slider-output]");
                      const rootRect = element.getBoundingClientRect();
                      const trackRect = track.getBoundingClientRect();
                      const outputRect = output.getBoundingClientRect();

                      return {
                        output: output.textContent,
                        outputLeft: outputRect.left,
                        outputRight: outputRect.right,
                        outputWidth: outputRect.width,
                        rootLeft: rootRect.left,
                        rootRight: rootRect.right,
                        rootWidth: rootRect.width,
                        trackWidth: trackRect.width,
                      };
                    }
                    """
                )

            metrics = [measure(value) for value in ("0", "50", "100")]

            self.assertEqual([metric["output"] for metric in metrics], ["0", "50", "100"])
            output_widths = [metric["outputWidth"] for metric in metrics]
            track_widths = [metric["trackWidth"] for metric in metrics]
            self.assertLessEqual(max(output_widths) - min(output_widths), 1, metrics)
            self.assertLessEqual(max(track_widths) - min(track_widths), 1, metrics)
            self.assertGreaterEqual(
                min(metric["rootWidth"] for metric in metrics),
                max(metric["outputWidth"] for metric in metrics),
            )
            self.assertTrue(
                all(
                    metric["outputLeft"] >= metric["rootLeft"] - 1
                    and metric["outputRight"] <= metric["rootRight"] + 1
                    for metric in metrics
                ),
                metrics,
            )
            self.assertTrue(all(metric["trackWidth"] > 0 for metric in metrics), metrics)
            evidence.assert_clean()
        finally:
            context.close()


class SliderBrowserTests(_SliderBrowserMixin, CatalogTestCase):
    pass
