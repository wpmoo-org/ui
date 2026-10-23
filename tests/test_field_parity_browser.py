from __future__ import annotations

import itertools
import subprocess
import sys
import unittest

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT
from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


COMPOSITION = """
{% from "components/field.html.jinja" import field, field_group, form %}
{% from "components/input.html.jinja" import input %}
{% from "components/textarea.html.jinja" import textarea %}
{% from "components/select.html.jinja" import select %}
{% from "components/combobox.html.jinja" import combobox %}
{% from "components/datepicker.html.jinja" import datepicker, date_range_picker %}
<!doctype html><html lang="en" dir="{{ direction }}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/dist/assets/css/moo-ui.css"></head><body>
<main class="moo-ui p-3" data-bs-theme="{{ theme }}">
{% call form() %}{% call field_group() %}
{% call field() %}{{ input(id="text", label="Text", placeholder="Prompt") }}{% endcall %}
{% call field() %}{{ textarea(id="notes", label="Notes", placeholder="Prompt") }}{% endcall %}
{% call field() %}{{ select(id="choice", label="Choice", options=options) }}{% endcall %}
{% call field() %}{{ combobox(id="combo", label="Search", placeholder="Prompt", items=[{"value":"a","label":"Alpha"}], show_clear=true) }}{% endcall %}
{% call field() %}{{ datepicker(id="date", name="date", label="Date") }}{% endcall %}
{% call field() %}{{ date_range_picker(id="range", start_name="start", end_name="end", label="Range") }}{% endcall %}
{{ select(id="valid-empty", label="Default", options=[{"value":"","label":"Default"},{"value":0,"label":"Zero"}]) }}
{{ select(id="listbox", label="List", options=options, rows="3") }}
{{ select(id="multiple", label="Multiple", options=options, multiple=true) }}
{{ select(id="disabled", label="Disabled", options=options, disabled=true) }}
{{ select(id="required", label="Required", options=options, required=true, invalid=true) }}
{% endcall %}{% endcall %}</main>
<script type="module">
import Combobox from '/dist/js/combobox.js';
import Datepicker, {MooDateRangePicker} from '/dist/js/datepicker.js';
Combobox.getOrCreateInstance(document.querySelector('.combobox'));
Datepicker.getOrCreateInstance(document.querySelector('#date'));
MooDateRangePicker.getOrCreateInstance(document.querySelector('#range'));
document.body.dataset.ready = 'true';
</script></body></html>
"""


class FieldParityBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        built = subprocess.run(
            [sys.executable, "build.py"], cwd=ROOT,
            capture_output=True, text=True, check=False,
        )
        if built.returncode:
            raise AssertionError(built.stderr)
        server = serve_repository()
        cls.base_url = server.__enter__()
        cls.addClassCleanup(server.__exit__, None, None, None)
        manager = sync_playwright()
        cls.playwright = manager.__enter__()
        cls.addClassCleanup(manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def open_composition(self, theme, direction, width):
        context = self.browser.new_context(viewport={"width": width, "height": 900})
        self.addCleanup(context.close)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        html = create_environment().from_string(COMPOSITION).render(
            theme=theme, direction=direction,
            options=[
                {"value": "", "label": "Prompt", "placeholder": True},
                {"label": "Group", "options": [{"value": "a", "label": "Alpha"}]},
            ],
        )
        page.route("**/field-parity", lambda route: route.fulfill(
            content_type="text/html", body=html,
        ))
        page.goto(f"{self.base_url}/field-parity", wait_until="networkidle")
        expect(page.locator("body")).to_have_attribute("data-ready", "true")
        return page, evidence

    def test_labels_spacing_and_enabled_prompt_contrast(self):
        for theme, direction, width in itertools.product(
            ("light", "dark"), ("ltr", "rtl"), (390, 1440),
        ):
            with self.subTest(theme=theme, direction=direction, width=width):
                page, evidence = self.open_composition(theme, direction, width)
                metrics = page.evaluate("""() => {
                  const input = document.querySelector('#text');
                  const style = getComputedStyle(input);
                  const prompt = getComputedStyle(input, '::placeholder').color;
                  const canvas = document.createElement('canvas');
                  canvas.width = canvas.height = 1;
                  const ctx = canvas.getContext('2d', {willReadFrequently: true});
                  const paint = color => { ctx.fillStyle = color; ctx.fillRect(0, 0, 1, 1); };
                  const pixel = () => [...ctx.getImageData(0, 0, 1, 1).data].slice(0, 3);
                  paint('white');
                  const ancestors = [];
                  for (let element = input; element; element = element.parentElement) ancestors.push(element);
                  for (const element of ancestors.reverse()) paint(getComputedStyle(element).backgroundColor);
                  const background = pixel();
                  paint(prompt);
                  const foreground = pixel();
                  const luminance = color => color.map(v => {
                    v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
                  }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
                  const a = luminance(foreground), b = luminance(background);
                  return {
                    rootSize: parseFloat(getComputedStyle(document.documentElement).fontSize),
                    labels: [...document.querySelectorAll('.field .form-label')].map(e => getComputedStyle(e).fontWeight),
                    gap: getComputedStyle(document.querySelector('.field')).gap,
                    groupGap: getComputedStyle(document.querySelector('.field-group')).gap,
                    prompt, textarea: getComputedStyle(document.querySelector('#notes'), '::placeholder').color,
                    combo: getComputedStyle(document.querySelector('#combo-input'), '::placeholder').color,
                    select: getComputedStyle(document.querySelector('#choice')).color,
                    date: getComputedStyle(document.querySelector('#date [data-datepicker-label]')).color,
                    dateWeight: getComputedStyle(document.querySelector('#date [data-datepicker-label]')).fontWeight,
                    inputWeight: style.fontWeight,
                    contrast: (Math.max(a, b) + .05) / (Math.min(a, b) + .05),
                  };
                }""")
                self.assertEqual(set(metrics["labels"]), {"500"})
                self.assertEqual(float(metrics["gap"].removesuffix("px")), metrics["rootSize"] * 0.5)
                self.assertEqual(float(metrics["groupGap"].removesuffix("px")), metrics["rootSize"] * 1.25)
                for control in ("textarea", "combo", "select", "date"):
                    self.assertEqual(metrics[control], metrics["prompt"], control)
                self.assertEqual(metrics["dateWeight"], metrics["inputWeight"])
                self.assertGreaterEqual(metrics["contrast"], 4.5)
                evidence.assert_clean()

    def test_native_prompt_selection_reset_and_listbox_semantics(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                page, evidence = self.open_composition(theme, "ltr", 1040)
                normal = page.locator("#valid-empty").evaluate("e => getComputedStyle(e).color")
                prompt = page.locator("#choice").evaluate("e => getComputedStyle(e).color")
                self.assertNotEqual(normal, prompt)
                for selector in ("#listbox", "#multiple"):
                    expect(page.locator(selector)).to_have_css("color", normal)
                page.locator("#valid-empty").select_option("0")
                expect(page.locator("#valid-empty")).to_have_css("color", normal)
                for option in ("a", ""):
                    page.locator("#choice").select_option(option)
                    expect(page.locator("#choice")).to_have_css("color", normal if option else prompt)
                page.locator("#choice").evaluate("e => e.value = 'a'")
                expect(page.locator("#choice")).to_have_css("color", normal)
                expect(page.locator("#choice option[value=a]")).to_have_css("color", normal)
                page.locator("form").evaluate("e => e.reset()")
                expect(page.locator("#choice")).to_have_value("")
                expect(page.locator("#choice")).to_have_css("color", prompt)
                expect(page.locator("#disabled")).to_be_disabled()
                self.assertNotEqual(page.locator("#disabled").evaluate("e => getComputedStyle(e).color"), prompt)
                self.assertFalse(page.locator("#required").evaluate("e => e.checkValidity()"))
                evidence.assert_clean()

    def test_date_setters_partial_range_clear_and_form_reset(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                page, evidence = self.open_composition(theme, "rtl", 390)
                label = page.locator("#date [data-datepicker-label]")
                range_label = page.locator("#range [data-datepicker-label]")
                normal = page.locator("#valid-empty").evaluate("e => getComputedStyle(e).color")
                prompt = label.evaluate("e => getComputedStyle(e).color")
                page.evaluate("""async () => {
                  const {default: Picker, MooDateRangePicker: Range} = await import('/dist/js/datepicker.js');
                  Picker.getInstance(document.querySelector('#date')).setDate('2026-10-23');
                  Range.getInstance(document.querySelector('#range')).setDates('2026-10-23', '');
                }""")
                expect(label).to_have_attribute("data-datepicker-empty", "false")
                expect(label).to_have_css("color", normal)
                expect(label).to_have_css("font-weight", "400")
                expect(range_label).to_have_attribute("data-datepicker-empty", "false")
                expect(range_label).to_have_css("color", normal)
                page.locator("form").evaluate("e => e.reset()")
                for current in (label, range_label):
                    expect(current).to_have_attribute("data-datepicker-empty", "true")
                    expect(current).to_have_css("color", prompt)
                evidence.assert_clean()

    def test_empty_date_trigger_preserves_interaction_foregrounds(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                page, evidence = self.open_composition(theme, "ltr", 1040)
                for root in ("#date", "#range"):
                    trigger = page.locator(f"{root} [data-datepicker-trigger]")
                    label = page.locator(f"{root} [data-datepicker-label]")
                    trigger.hover()
                    expected = trigger.evaluate("e => getComputedStyle(e).color")
                    expect(label).to_have_css("color", expected)
                    trigger.focus()
                    expect(label).to_have_css("color", expected)
                    trigger.click()
                    expect(trigger).to_have_attribute("aria-expanded", "true")
                    expect(label).to_have_css("color", trigger.evaluate("e => getComputedStyle(e).color"))
                    page.keyboard.press("Escape")
                evidence.assert_clean()
