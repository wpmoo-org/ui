from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import DIST, ROOT, STATIC, CatalogTestCase, is_valid_webp
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


COMPONENT = ROOT / "src/components/datepicker.html.jinja"
DATEPICKER_JS = ROOT / "src/js/components/datepicker.js"
DATEPICKER_SCSS = ROOT / "scss/components/_datepicker.scss"
COMPONENT_PAGE = ROOT / "site/src/pages/components/datepicker.html.jinja"
CERTIFICATION_FIXTURE = ROOT / "tests/fixtures/certification/datepicker.html"
REGISTRY = ROOT / "src/registry/components.json"
EVIDENCE_INVENTORY = ROOT / "src/certification/evidence-inventory.json"
CERTIFICATION_FIXTURE_PATH = "/tests/fixtures/certification/datepicker.html"


class DatepickerMacroTests(CatalogTestCase):
    def render_datepicker(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Datepicker macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/datepicker.html.jinja" import '
            "datepicker, date_range_picker, calendar %}"
            + source
        )
        return " ".join(template.render().split())

    def test_single_datepicker_renders_shadcn_popover_composition(self) -> None:
        output = self.render_datepicker(
            '{{ datepicker('
            'id="deploy-date", '
            'label="Deploy date", '
            'name="deploy_date", '
            'placeholder="Pick a date", '
            'value="2026-08-18", '
            'required=true, '
            'describedby="deploy-date-help"'
            ') }}'
        )

        self.assertIn('class="moo-datepicker"', output)
        self.assertIn('id="deploy-date"', output)
        self.assertIn("data-datepicker", output)
        self.assertIn('<label class="form-label" for="deploy-date-trigger">Deploy date</label>', output)
        self.assertIn('type="button"', output)
        self.assertIn('id="deploy-date-trigger"', output)
        self.assertIn('data-datepicker-trigger', output)
        self.assertIn('aria-haspopup="dialog"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertIn('aria-controls="deploy-date-popover"', output)
        self.assertIn('data-lucide="calendar"', output)
        self.assertIn('data-datepicker-label', output)
        self.assertIn(">Aug 18, 2026<", output)
        self.assertIn(
            '<div class="moo-datepicker__popover" id="deploy-date-popover" '
            'data-datepicker-popover role="dialog" aria-modal="false" hidden>',
            output,
        )
        self.assertIn('class="moo-calendar"', output)
        self.assertIn('data-calendar', output)
        self.assertIn('tabindex="-1"', output)
        self.assertIn(
            'type="hidden" name="deploy_date" value="2026-08-18" '
            "data-datepicker-input required",
            output,
        )
        self.assertIn('aria-describedby="deploy-date-help"', output)
        self.assertNotIn('class="datepicker', output)

    def test_single_datepicker_label_uses_placeholder_for_invalid_values(self) -> None:
        output = self.render_datepicker(
            '{{ datepicker('
            'id="deploy-date", '
            'label="Deploy date", '
            'name="deploy_date", '
            'placeholder="Pick a date", '
            'value="2026-13-40"'
            ') }}'
        )

        self.assertIn(">Pick a date<", output)
        self.assertIn('type="hidden" name="deploy_date" value="2026-13-40"', output)

    def test_range_picker_uses_two_hidden_inputs_and_one_calendar(self) -> None:
        output = self.render_datepicker(
            '{{ date_range_picker('
            'id="billing-window", '
            'aria_label="Billing window", '
            'start_name="billing_start", '
            'end_name="billing_end", '
            'start_value="2026-08-10", '
            'end_value="2026-08-18"'
            ') }}'
        )

        self.assertIn('class="moo-datepicker moo-datepicker--range"', output)
        self.assertIn("data-datepicker-range", output)
        self.assertIn('data-datepicker-mode="range"', output)
        self.assertIn('aria-label="Billing window"', output)
        self.assertIn(">Aug 10, 2026 - Aug 18, 2026<", output)
        self.assertIn('data-calendar-mode="range"', output)
        self.assertEqual(len(re.findall(r"\sdata-calendar(?:\s|>)", output)), 1)
        self.assertIn('type="hidden" name="billing_start" value="2026-08-10"', output)
        self.assertIn('type="hidden" name="billing_end" value="2026-08-18"', output)
        self.assertIn('data-datepicker-range-start', output)
        self.assertIn('data-datepicker-range-end', output)

    def test_inline_calendar_renders_standalone_grid_contract(self) -> None:
        output = self.render_datepicker(
            '{{ calendar('
            'id="release-calendar", '
            'aria_label="Release calendar", '
            'value="2026-08-18", '
            'min_date="2026-08-10", '
            'max_date="2026-08-31", '
            'disabled_dates=["2026-08-22"]'
            ') }}'
        )

        self.assertIn('class="moo-calendar"', output)
        self.assertIn('id="release-calendar"', output)
        self.assertIn('data-calendar', output)
        self.assertIn('data-calendar-mode="single"', output)
        self.assertIn('data-calendar-value="2026-08-18"', output)
        self.assertIn('data-calendar-min-date="2026-08-10"', output)
        self.assertIn('data-calendar-max-date="2026-08-31"', output)
        self.assertIn('data-calendar-disabled-dates=\'["2026-08-22"]\'', output)
        self.assertNotIn('role="application"', output)
        self.assertIn('aria-label="Release calendar"', output)
        self.assertIn('tabindex="-1"', output)
        self.assertNotIn('data-datepicker-popover', output)


class DatepickerSourceTests(CatalogTestCase):
    def test_public_module_exports_are_dom_safe_to_import(self) -> None:
        script = """
        const module = await import("./src/js/components/datepicker.js");
        const messages = [];
        for (const Constructor of [
          module.default,
          module.MooCalendar,
          module.MooDateRangePicker,
        ]) {
          messages.push(Constructor.getInstance(null) === null);
          try {
            new Constructor(null);
            messages.push("no-throw");
          } catch (error) {
            messages.push(error.message);
          }
        }
        console.log(JSON.stringify({
          keys: Object.keys(module).sort(),
          defaultName: module.default.name,
          messages,
        }));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["keys"], ["MooCalendar", "MooDateRangePicker", "default"])
        self.assertEqual(payload["defaultName"], "MooDatepicker")
        self.assertEqual(
            payload["messages"],
            [
                True,
                "MooDatepicker requires a [data-datepicker] root element.",
                True,
                "MooCalendar requires a [data-calendar] root element.",
                True,
                "MooDateRangePicker requires a [data-datepicker-range] root element.",
            ],
        )

    def test_source_has_no_third_party_runtime_imports(self) -> None:
        source = DATEPICKER_JS.read_text(encoding="utf-8")

        self.assertNotIn("vanillajs-datepicker", source)
        self.assertNotIn('from "', source)
        self.assertNotIn("from '", source)
        self.assertNotIn("import(", source)
        self.assertNotIn("window.Datepicker", source)
        self.assertNotIn("bootstrap-datepicker", source)

    def test_catalog_registration_fixture_and_preview_art_are_present(self) -> None:
        catalog = json.loads(REGISTRY.read_text(encoding="utf-8"))
        datepicker = next(
            (item for item in catalog if item["slug"] == "datepicker"),
            None,
        )
        self.assertIsNotNone(datepicker)
        assert datepicker is not None
        self.assertEqual(datepicker["label"], "Date Picker")
        self.assertEqual(datepicker["status"], "ready")

        inventory = json.loads(EVIDENCE_INVENTORY.read_text(encoding="utf-8"))
        evidence = next(
            (item for item in inventory["components"] if item["slug"] == "datepicker"),
            None,
        )
        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertEqual(evidence["profile"], "t3-runtime-composite")
        self.assertIn("tests/test_datepicker.py", evidence["evidence"])
        self.assertIn("src/js/components/datepicker.js", evidence["evidence"])

        self.assertTrue(COMPONENT_PAGE.is_file())
        self.assertTrue(CERTIFICATION_FIXTURE.is_file())
        self.assertTrue(DATEPICKER_SCSS.is_file())
        preview = STATIC / "images/components/datepicker.webp"
        self.assertTrue(preview.is_file(), "Datepicker preview art is missing")
        self.assertTrue(is_valid_webp(preview))

    def test_component_page_uses_global_theme_toggle_instead_of_dark_only_example(
        self,
    ) -> None:
        source = COMPONENT_PAGE.read_text(encoding="utf-8")

        self.assertNotIn('"datepicker-dark"', source)
        self.assertNotIn('id="datepicker-dark"', source)
        self.assertNotIn('"Dark"', source)
        self.assertNotIn("Scoped theme tokens update", source)

    def test_certification_fixture_uses_real_datepicker_trigger_icons(self) -> None:
        source = CERTIFICATION_FIXTURE.read_text(encoding="utf-8")

        self.assertNotIn(">□<", source)
        self.assertGreaterEqual(source.count('data-lucide="calendar"'), 1)
        self.assertEqual(source.count('data-lucide="calendar-range"'), 1)

    def test_scss_is_imported_after_field_and_before_combobox(self) -> None:
        imports = re.findall(
            r'@import "([^"]+)";',
            (ROOT / "scss/_component_layer.scss").read_text(encoding="utf-8"),
        )

        self.assertLess(
            imports.index("components/field"),
            imports.index("components/datepicker"),
        )
        self.assertLess(
            imports.index("components/datepicker"),
            imports.index("components/combobox"),
        )

    def test_scss_keeps_selected_day_contrast_on_hover_and_focus(self) -> None:
        source = DATEPICKER_SCSS.read_text(encoding="utf-8")

        self.assertIn(
            '.moo-calendar__day[data-calendar-selected="true"]:hover:not(:disabled),',
            source,
        )
        self.assertIn(
            '.moo-calendar__day[data-calendar-selected="true"]:focus-visible',
            source,
        )
        selected_interaction = source.split(
            '.moo-calendar__day[data-calendar-selected="true"]:hover:not(:disabled),',
            1,
        )[1].split("}", 1)[0]
        self.assertIn("background: var(--moo-primary);", selected_interaction)
        self.assertIn("color: var(--moo-primary-foreground);", selected_interaction)


class DatepickerBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
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
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.addClassCleanup(cls.playwright_manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def open_fixture(self, case=CERTIFICATION_CASES[0]):
        context = new_case_context(self.browser, case)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        response = page.goto(
            f"{self.base_url}{CERTIFICATION_FIXTURE_PATH}",
            wait_until="networkidle",
        )
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, case)
        return context, page, evidence

    def assert_calendar_month(self, calendar, year: int, month: int) -> None:
        payload = calendar.evaluate(
            """
            (element, expected) => {
              const pad = (value) => String(value).padStart(2, "0");
              const expectedPrefix = `${expected.year}-${pad(expected.month)}-`;
              const monthLength = new Date(expected.year, expected.month, 0).getDate();
              const days = [...element.querySelectorAll("[data-calendar-day]")].map((button) => ({
                iso: button.dataset.calendarDay,
                outside: button.dataset.calendarOutside === "true",
              }));
              const present = new Set(days.map((day) => day.iso));
              const missingMonthDays = [];
              for (let day = 1; day <= monthLength; day += 1) {
                const iso = `${expectedPrefix}${pad(day)}`;
                if (!present.has(iso)) missingMonthDays.push(iso);
              }
              return {
                cellCount: days.length,
                monthLength,
                missingMonthDays,
                outsideWithoutFlag: days
                  .filter((day) => !day.iso.startsWith(expectedPrefix) && !day.outside)
                  .map((day) => day.iso),
              };
            }
            """,
            {"year": year, "month": month},
        )

        self.assertGreaterEqual(payload["cellCount"], payload["monthLength"])
        self.assertEqual(payload["missingMonthDays"], [])
        self.assertEqual(payload["outsideWithoutFlag"], [])

    def popover_position_metrics(
        self,
        page,
        *,
        trigger_selector: str,
        popover_selector: str,
        clipping_selector: str | None = None,
    ) -> dict[str, object]:
        return page.evaluate(
            """
            ({ triggerSelector, popoverSelector, clippingSelector }) => {
              const trigger = document.querySelector(triggerSelector);
              const popover = document.querySelector(popoverSelector);
              const clipping = clippingSelector
                ? document.querySelector(clippingSelector)
                : null;
              const rect = (element) => {
                const bounds = element.getBoundingClientRect();
                return {
                  top: bounds.top,
                  right: bounds.right,
                  bottom: bounds.bottom,
                  left: bounds.left,
                  width: bounds.width,
                  height: bounds.height,
                };
              };
              const triggerRect = rect(trigger);
              const popoverRect = rect(popover);
              const clippingRect = clipping ? rect(clipping) : null;
              const root = trigger.closest("[data-datepicker], [data-datepicker-range]");
              const point = {
                x: Math.min(
                  window.innerWidth - 1,
                  Math.max(0, popoverRect.left + Math.min(24, popoverRect.width / 2))
                ),
                y: clippingRect
                  ? Math.min(window.innerHeight - 1, Math.max(0, clippingRect.bottom + 8))
                  : Math.min(window.innerHeight - 1, Math.max(0, popoverRect.top + 8)),
              };
              const hit = document.elementFromPoint(point.x, point.y);
              return {
                placement: popover.dataset.datepickerPlacement || "",
                position: getComputedStyle(popover).position,
                bodyChild: popover.parentElement === document.body,
                rootContainsPopover: root ? root.contains(popover) : false,
                leftDelta: popoverRect.left - triggerRect.left,
                topGap: popoverRect.top - triggerRect.bottom,
                aboveGap: triggerRect.top - popoverRect.bottom,
                popoverRect,
                triggerRect,
                clippingRect,
                clippingOverflow: clipping ? getComputedStyle(clipping).overflow : "",
                extendsPastClipping: clippingRect
                  ? popoverRect.bottom > clippingRect.bottom
                  : false,
                hitInsidePopover: Boolean(hit?.closest?.(popoverSelector)),
                withinViewport: popoverRect.top >= 0 && popoverRect.bottom <= window.innerHeight,
              };
            }
            """,
            {
                "triggerSelector": trigger_selector,
                "popoverSelector": popover_selector,
                "clippingSelector": clipping_selector,
            },
        )

    def test_fixture_proves_single_range_keyboard_and_lifecycle(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-datepicker-ready", "true")

            single = page.locator("#certification-datepicker")
            trigger = single.locator("[data-datepicker-trigger]")
            popover = page.locator("#certification-datepicker-popover")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(popover).to_be_visible()
            self.assert_calendar_month(page.locator("#certification-datepicker-calendar"), 2026, 8)

            # The calendar grid must resolve an accessible name from the
            # caller-provided aria-label, not rely on the root wrapper.
            grid = page.get_by_role("grid", name="Deploy date calendar")
            expect(grid).to_be_visible()
            self.assertGreaterEqual(grid.count(), 1)

            page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-20"]').focus()
            page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-20"]').press("ArrowRight")
            expect(page.locator("#certification-datepicker-calendar")).to_have_attribute(
                "data-calendar-active-date",
                "2026-08-21",
            )
            page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-21"]').press("Enter")
            expect(page.locator('input[name="certification_date"]')).to_have_value(
                "2026-08-21"
            )
            expect(trigger.locator("[data-datepicker-label]")).to_have_text(
                "Aug 21, 2026"
            )
            expect(trigger).to_have_attribute("aria-expanded", "false")
            self.assertTrue(
                trigger.evaluate("element => document.activeElement === element")
            )

            trigger.click()
            expect(page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-22"]')).to_be_disabled()
            self.assertFalse(
                page.evaluate(
                    """
                    () => window.certificationDatepicker.setDate("2026-08-22")
                    """
                )
            )
            expect(page.locator('input[name="certification_date"]')).to_have_value(
                "2026-08-21"
            )
            page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-21"]').focus()
            page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-21"]').press("ArrowRight")
            expect(page.locator("#certification-datepicker-calendar")).to_have_attribute(
                "data-calendar-active-date",
                "2026-08-23",
            )
            page.locator('#certification-datepicker-calendar [data-calendar-day="2026-08-21"]').press("Escape")
            expect(trigger).to_have_attribute("aria-expanded", "false")

            range_picker = page.locator("#certification-date-range")
            range_trigger = range_picker.locator("[data-datepicker-trigger]")
            range_trigger.click()
            page.locator('#certification-date-range-calendar [data-calendar-day="2026-08-24"]').click()
            # Start selected: calendar stays open, roving focus stays on the day.
            expect(page.locator("#certification-date-range-popover")).to_be_visible()
            page.locator('#certification-date-range-calendar [data-calendar-day="2026-08-28"]').click()
            expect(page.locator('#certification-date-range-popover input[name="range_start"]')).to_have_value(
                "2026-08-24"
            )
            expect(page.locator('#certification-date-range-popover input[name="range_end"]')).to_have_value(
                "2026-08-28"
            )
            expect(page.locator('#certification-date-range-calendar [data-calendar-day="2026-08-26"]')).to_have_attribute(
                "data-calendar-range",
                "middle",
            )
            # End selected: the completed range closes the picker and returns
            # focus to the trigger, per the frozen contract.
            expect(range_trigger).to_have_attribute("aria-expanded", "false")
            expect(page.locator("#certification-date-range-popover")).not_to_be_visible()
            self.assertTrue(
                range_trigger.evaluate("element => document.activeElement === element")
            )
            self.assertFalse(
                page.evaluate(
                    """
                    () => document.activeElement.matches("[data-calendar-day]")
                    """
                )
            )
            range_trigger.click()
            expect(page.locator("#certification-date-range-popover")).to_be_visible()
            page.locator("#certification-datepicker-reset-form").locator(
                'button[type="reset"]'
            ).focus()
            expect(range_trigger).to_have_attribute("aria-expanded", "false")
            mode_guards = page.evaluate(
                """
                () => {
                  const singleCalendar = window.certificationDatepicker.calendar;
                  const rangeCalendar = window.certificationDateRangePicker.calendar;
                  const singleRoot = document.querySelector("#certification-datepicker-calendar");
                  const rangeRoot = document.querySelector("#certification-date-range-calendar");
                  return {
                    singleSetDates: singleCalendar.setDates("2026-08-24", "2026-08-28", { emit: false }),
                    singleMode: singleRoot.dataset.calendarMode,
                    singleValue: singleCalendar.getDate("yyyy-mm-dd"),
                    rangeSetDate: rangeCalendar.setDate("2026-08-25", { emit: false }),
                    rangeMode: rangeRoot.dataset.calendarMode,
                    rangeValues: rangeCalendar.getDates("yyyy-mm-dd"),
                  };
                }
                """
            )
            self.assertEqual(
                mode_guards,
                {
                    "singleSetDates": False,
                    "singleMode": "single",
                    "singleValue": "2026-08-21",
                    "rangeSetDate": False,
                    "rangeMode": "range",
                    "rangeValues": ["2026-08-24", "2026-08-28"],
                },
            )

            reset_picker = page.locator("#certification-reset-datepicker")
            reset_trigger = reset_picker.locator("[data-datepicker-trigger]")
            reset_trigger.click()
            page.locator('#certification-reset-datepicker-calendar [data-calendar-day="2026-08-21"]').click()
            expect(page.locator('input[name="reset_date"]')).to_have_value(
                "2026-08-21"
            )
            page.locator("#certification-datepicker-reset-form").locator(
                'button[type="reset"]'
            ).click()
            expect(page.locator('input[name="reset_date"]')).to_have_value("")
            expect(reset_trigger.locator("[data-datepicker-label]")).to_have_text(
                "Pick a date"
            )
            expect(page.locator("#certification-reset-datepicker-calendar")).not_to_have_attribute(
                "data-calendar-value",
                "2026-08-21",
            )

            dropdown_picker = page.locator("#certification-dropdown-datepicker")
            dropdown_trigger = dropdown_picker.locator("[data-datepicker-trigger]")
            dropdown_trigger.click()
            page.locator("#certification-dropdown-datepicker-calendar [data-calendar-year]").select_option("1990")
            page.locator("#certification-dropdown-datepicker-calendar [data-calendar-month]").select_option("0")
            active_day = page.evaluate(
                """
                () => document
                  .querySelector("#certification-dropdown-datepicker-calendar [data-calendar-day][tabindex='0']")
                  ?.dataset.calendarDay || ""
                """
            )
            self.assertRegex(active_day, r"^1990-01-\d{2}$")
            page.locator('#certification-dropdown-datepicker-calendar [data-calendar-day="1990-01-15"]').click()
            expect(page.locator('input[name="birth_date"]')).to_have_value(
                "1990-01-15"
            )
            expect(dropdown_trigger.locator("[data-datepicker-label]")).to_have_text(
                "Jan 15, 1990"
            )

            lifecycle = page.evaluate(
                """
                async () => {
                  const singleRoot = document.querySelector("#certification-datepicker");
                  const calendarRoot = document.querySelector("#certification-calendar");
                  const rangeRoot = document.querySelector("#certification-date-range");

                  window.certificationDatepicker.dispose();
                  const singleDisposed = window.CertificationDatepicker.getInstance(singleRoot) === null;
                  window.certificationDatepicker = window.CertificationDatepicker.getOrCreateInstance(singleRoot);

                  window.certificationCalendar.dispose();
                  const calendarDisposed = window.CertificationCalendar.getInstance(calendarRoot) === null;
                  window.certificationCalendar = window.CertificationCalendar.getOrCreateInstance(calendarRoot);
                  const calendarSet = window.certificationCalendar.setDate("2026-08-19", { emit: false });

                  window.certificationDateRangePicker.dispose();
                  const rangeDisposed = window.CertificationDateRangePicker.getInstance(rangeRoot) === null;
                  window.certificationDateRangePicker = window.CertificationDateRangePicker.getOrCreateInstance(rangeRoot);
                  const rangeSet = window.certificationDateRangePicker.setDates(
                    "2026-08-24",
                    "2026-08-28",
                    { emit: false }
                  );

                  return {
                    singleDisposed,
                    singleValue: window.certificationDatepicker.getDate("yyyy-mm-dd"),
                    calendarDisposed,
                    calendarSet,
                    calendarValue: window.certificationCalendar.getDate("yyyy-mm-dd"),
                    rangeDisposed,
                    rangeSet,
                    rangeValues: window.certificationDateRangePicker.getDates("yyyy-mm-dd"),
                  };
                }
                """
            )
            self.assertEqual(
                lifecycle,
                {
                    "singleDisposed": True,
                    "singleValue": "2026-08-21",
                    "calendarDisposed": True,
                    "calendarSet": True,
                    "calendarValue": "2026-08-19",
                    "rangeDisposed": True,
                    "rangeSet": True,
                    "rangeValues": ["2026-08-24", "2026-08-28"],
                },
            )
            self.assertEqual(run_axe(page), [])
            evidence.assert_clean()
        finally:
            context.close()

    def test_outside_click_returns_focus_to_the_trigger(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-datepicker-ready", "true")

            # Single picker: open, pointer-click a focusable external button,
            # and assert the picker closes and focus lands back on the trigger.
            trigger = page.locator("#certification-datepicker-trigger")
            outside = page.locator("#certification-outside-target")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            outside.click()
            expect(trigger).to_have_attribute("aria-expanded", "false")
            expect(page.locator("#certification-datepicker-popover")).not_to_be_visible()
            self.assertTrue(
                trigger.evaluate("element => document.activeElement === element")
            )

            # Range picker: same contract after the second click of a range.
            range_trigger = page.locator("#certification-date-range-trigger")
            range_trigger.click()
            page.locator('#certification-date-range-calendar [data-calendar-day="2026-08-24"]').click()
            expect(page.locator("#certification-date-range-popover")).to_be_visible()
            outside.click()
            expect(range_trigger).to_have_attribute("aria-expanded", "false")
            expect(page.locator("#certification-date-range-popover")).not_to_be_visible()
            self.assertTrue(
                range_trigger.evaluate("element => document.activeElement === element")
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_selected_day_keeps_selected_contrast_when_hovered(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-datepicker-ready", "true")
            trigger = page.locator("#certification-datepicker-trigger")
            trigger.click()
            day = page.locator(
                '#certification-datepicker-popover [data-calendar-day="2026-08-18"]'
            )
            selected_style = day.evaluate(
                """
                (element) => {
                  const style = getComputedStyle(element);
                  return {
                    backgroundColor: style.backgroundColor,
                    color: style.color,
                  };
                }
                """
            )
            day.hover()
            hovered_style = day.evaluate(
                """
                (element) => {
                  const style = getComputedStyle(element);
                  return {
                    backgroundColor: style.backgroundColor,
                    color: style.color,
                  };
                }
                """
            )

            self.assertEqual(hovered_style, selected_style)
            evidence.assert_clean()
        finally:
            context.close()

    def test_fixture_popover_escapes_clipped_ancestor_and_tracks_trigger(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-datepicker-ready", "true")
            page.locator("#certification-clipped-datepicker-trigger").click()
            expect(page.locator("#certification-clipped-datepicker-popover")).to_be_visible()

            metrics = self.popover_position_metrics(
                page,
                trigger_selector="#certification-clipped-datepicker-trigger",
                popover_selector="#certification-clipped-datepicker-popover",
                clipping_selector="#certification-clipped-card",
            )

            self.assertEqual(metrics["placement"], "top")
            self.assertEqual(metrics["position"], "fixed")
            self.assertTrue(metrics["bodyChild"])
            self.assertFalse(metrics["rootContainsPopover"])
            self.assertLessEqual(abs(metrics["leftDelta"]), 1)
            self.assertGreaterEqual(metrics["aboveGap"], 4)
            self.assertLessEqual(metrics["aboveGap"], 8)
            self.assertEqual(metrics["clippingOverflow"], "hidden")
            page.locator(
                '#certification-clipped-datepicker-popover [data-calendar-day="2026-08-18"]'
            ).press("Escape")
            expect(page.locator("#certification-clipped-datepicker-trigger")).to_have_attribute(
                "aria-expanded",
                "false",
            )
            expect(
                page.locator(
                    "#certification-clipped-datepicker > #certification-clipped-datepicker-popover"
                )
            ).to_have_count(1)
            evidence.assert_clean()
        finally:
            context.close()

    def test_fixture_popover_flips_above_trigger_near_viewport_edge(self) -> None:
        context, page, evidence = self.open_fixture()
        try:
            expect(page.locator("body")).to_have_attribute("data-datepicker-ready", "true")
            page.set_viewport_size({"width": 1040, "height": 520})
            page.evaluate(
                """
                () => document
                  .querySelector("#certification-bottom-datepicker-trigger")
                  .scrollIntoView({ block: "end" })
                """
            )
            page.locator("#certification-bottom-datepicker-trigger").click()
            expect(page.locator("#certification-bottom-datepicker-popover")).to_be_visible()

            metrics = self.popover_position_metrics(
                page,
                trigger_selector="#certification-bottom-datepicker-trigger",
                popover_selector="#certification-bottom-datepicker-popover",
            )

            self.assertEqual(metrics["placement"], "top")
            self.assertEqual(metrics["position"], "fixed")
            self.assertGreaterEqual(metrics["aboveGap"], 4)
            self.assertLessEqual(metrics["aboveGap"], 8)
            self.assertTrue(metrics["withinViewport"])
            evidence.assert_clean()
        finally:
            context.close()

    def test_fixture_supports_dark_rtl_locale_and_inline_calendar(self) -> None:
        context, page, evidence = self.open_fixture(CERTIFICATION_CASES[1])
        try:
            expect(page.locator("body")).to_have_attribute("data-datepicker-ready", "true")
            expect(page.locator("#certification-datepicker")).to_have_attribute(
                "data-datepicker-locale",
                "en",
            )
            expect(page.locator("#certification-rtl-datepicker")).to_have_attribute(
                "dir",
                "rtl",
            )
            expect(page.locator("#certification-rtl-datepicker")).to_have_attribute(
                "data-datepicker-locale",
                "ar",
            )
            # Native locale behavior: opening the Arabic (RTL) picker must
            # render the visible month caption in Arabic script, proving the
            # locale option drives visible formatting without an engine.
            page.locator("#certification-rtl-datepicker-trigger").click()
            expect(page.locator("#certification-rtl-datepicker-popover")).to_be_visible()
            rtl_caption = page.locator(
                "#certification-rtl-datepicker-calendar .moo-calendar__caption"
            )
            expect(rtl_caption).not_to_have_text("")
            rtl_text = rtl_caption.inner_text()
            self.assertTrue(
                any("\u0600" <= ch <= "\u06FF" for ch in rtl_text),
                f"Arabic calendar caption did not render Arabic text: {rtl_text!r}",
            )
            page.locator("#certification-rtl-datepicker-trigger").click()

            bounded = page.locator("#certification-bounded-calendar")
            self.assert_calendar_month(bounded, 2026, 8)
            expect(bounded.locator('[data-calendar-day="2026-08-10"]')).to_be_disabled()
            expect(bounded.locator('[data-calendar-day="2026-09-01"]')).to_be_disabled()

            inline = page.locator("#certification-calendar")
            self.assert_calendar_month(inline, 2026, 8)
            expect(inline.locator('[data-calendar-day="2026-08-18"]')).to_have_attribute(
                "data-calendar-selected",
                "true",
            )
            today_iso = page.evaluate(
                """
                () => {
                  const today = new Date();
                  const pad = (value) => String(value).padStart(2, "0");
                  return [
                    today.getFullYear(),
                    pad(today.getMonth() + 1),
                    pad(today.getDate()),
                  ].join("-");
                }
                """
            )
            inline.locator('[data-calendar-preset="today"]').click()
            expect(inline).to_have_attribute("data-calendar-value", today_iso)
            evidence.assert_clean()
        finally:
            context.close()
