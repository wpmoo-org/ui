from __future__ import annotations

import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
)


PREVIEW_PATH = "/site-dist/blocks/previews/datatable-release-review/index.html"
CERTIFICATION_FIXTURE_PATH = "/tests/fixtures/certification/datatable.html"
TABLE_ID = "standalone-datatable-release-reviews"


class DataTableBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright_manager.__exit__(None, None, None)
        cls.server.__exit__(None, None, None)

    def open_preview(self):
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        page = context.new_page()
        evidence = BrowserEvidence(page)
        response = page.goto(f"{self.base_url}{PREVIEW_PATH}", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, CERTIFICATION_CASES[0])
        return context, page, evidence

    def open_certification_fixture(self):
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        page = context.new_page()
        evidence = BrowserEvidence(page)
        response = page.goto(
            f"{self.base_url}{CERTIFICATION_FIXTURE_PATH}", wait_until="networkidle"
        )
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, CERTIFICATION_CASES[0])
        return context, page, evidence

    def test_search_filters_rows_without_opening_filter_menu(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            search = root.locator("input[data-datatable-search]")
            filter_button = root.locator("[data-datatable-filter-menu-trigger]")
            filter_menu = root.locator(".datatable-search-filter-menu")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")

            search.focus()
            expect(filter_button).to_have_attribute("aria-expanded", "false")
            search.click()
            self.assertFalse(
                filter_menu.evaluate("element => element.classList.contains('show')")
            )
            search.fill("Combobox keyboard pass")

            expect(rows).to_have_count(1)
            expect(rows).to_contain_text("REV-1042")
            self.assertFalse(
                filter_menu.evaluate("element => element.classList.contains('show')")
            )

            filter_button.click()
            expect(filter_menu).to_be_visible()
            expect(filter_button).to_have_attribute("aria-expanded", "true")
            evidence.assert_clean()
        finally:
            context.close()

    def test_filter_picker_selects_facet_chip_and_reset_restores_rows(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            filter_button = root.locator("[data-datatable-filter-menu-trigger]")
            status_facet = root.locator('[data-datatable-facet="status"]')
            status_summary = status_facet.locator("[data-datatable-facet-summary]")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")

            filter_button.click()
            root.locator('[data-datatable-filter-group="status"]').click()
            ready_option = root.locator(
                '[data-datatable-filter-option-key="status"]'
                '[data-datatable-filter-option="ready"]'
            )
            ready_option.click()

            expect(ready_option).to_have_attribute("aria-pressed", "true")
            expect(status_facet).to_be_visible()
            expect(status_summary).to_be_visible()
            expect(status_summary).to_contain_text("Ready")
            expect(rows).to_have_count(7)

            root.locator("[data-datatable-reset]").click()
            expect(status_summary).to_be_hidden()
            expect(root.locator("[data-datatable-reset]")).to_be_hidden()
            expect(rows).to_have_count(10)
            evidence.assert_clean()
        finally:
            context.close()

    def test_view_toggle_persists_and_cards_keep_review_identity(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            cards_input = root.locator('.datatable-view-toggle input[value="cards"]')
            storage_key = f"moo-datatable-view:{TABLE_ID}"

            root.locator('label[for$="-view-cards"]').click()
            expect(root).to_have_attribute("data-datatable-view", "cards")
            expect(cards_input).to_be_checked()
            self.assertEqual(
                page.evaluate("key => localStorage.getItem(key)", storage_key),
                "cards",
            )

            root.locator('[aria-label="View columns"]').click()
            status_toggle = root.locator('[data-datatable-column-toggle="status"]')
            status_toggle.click()
            self.assertTrue(
                root.locator('[data-datatable-column="status"]').first.evaluate(
                    "element => element.classList.contains('datatable-col-hidden')"
                )
            )

            card = root.locator('[data-datatable-card-for="review-rev-1042"]')
            expect(card).to_be_visible()
            expect(card.locator(".datatable-card-title")).to_have_text(
                "Combobox keyboard pass"
            )
            expect(card.locator('[data-datatable-detail-column="id"]')).to_contain_text(
                "REV-1042"
            )

            page.reload(wait_until="networkidle")
            prepare_page(page, CERTIFICATION_CASES[0])
            root = page.locator(f"#{TABLE_ID}")
            expect(root).to_have_attribute("data-datatable-view", "cards")
            expect(
                root.locator('.datatable-view-toggle input[value="cards"]')
            ).to_be_checked()
            evidence.assert_clean()
        finally:
            context.close()

    def test_select_all_checkbox_inset_matches_header_breathing(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")

            def measure(frame_selector: str, header_selector: str) -> dict[str, float]:
                return root.evaluate(
                    """
                    (datatable, selectors) => {
                      const frame = datatable.querySelector(selectors.frame);
                      const header = frame.querySelector(selectors.header);
                      const checkbox = header.querySelector(
                        "[data-datatable-select-all]"
                      );
                      const frameRect = frame.getBoundingClientRect();
                      const headerRect = header.getBoundingClientRect();
                      const checkboxRect = checkbox.getBoundingClientRect();
                      const verticalInset = (
                        checkboxRect.top - headerRect.top +
                        headerRect.bottom - checkboxRect.bottom
                      ) / 2;
                      return {
                        leftInset: checkboxRect.left - frameRect.left,
                        verticalInset,
                      };
                    }
                    """,
                    {"frame": frame_selector, "header": header_selector},
                )

            table_metrics = measure(".datatable-frame", "thead tr")
            self.assertAlmostEqual(
                table_metrics["leftInset"],
                table_metrics["verticalInset"],
                delta=1,
            )

            root.locator('label[for$="-view-cards"]').click()
            expect(root).to_have_attribute("data-datatable-view", "cards")
            card_metrics = measure(".datatable-card-frame", ".datatable-frame-header")
            self.assertAlmostEqual(
                card_metrics["leftInset"],
                card_metrics["verticalInset"],
                delta=1,
            )

            evidence.assert_clean()
        finally:
            context.close()

    def test_card_row_action_menu_escapes_short_card(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")

            root.locator('label[for$="-view-cards"]').click()
            expect(root).to_have_attribute("data-datatable-view", "cards")

            root.locator('[aria-label="View columns"]').click()
            for key in ("status", "priority", "area", "owner"):
                toggle = root.locator(f'[data-datatable-column-toggle="{key}"]')
                if toggle.count():
                    toggle.click()
            page.keyboard.press("Escape")

            action = root.locator(
                ".datatable-card:visible .table-row-actions > button"
            ).first
            action.click()
            menu = root.locator(".datatable-card .dropdown-menu.show")
            expect(menu).to_be_visible()

            result = page.evaluate(
                """
                () => {
                  const menu = document.querySelector(
                    "#standalone-datatable-release-reviews .datatable-card .dropdown-menu.show"
                  );
                  const card = menu?.closest(".datatable-card");
                  const rect = (element) => {
                    const box = element.getBoundingClientRect();
                    return {
                      top: box.top,
                      right: box.right,
                      bottom: box.bottom,
                      left: box.left,
                      width: box.width,
                      height: box.height,
                    };
                  };
                  const allItemsHit = Array.from(
                    menu.querySelectorAll(".dropdown-item")
                  ).every((item) => {
                    const box = item.getBoundingClientRect();
                    const hit = document.elementFromPoint(
                      box.left + Math.min(8, box.width / 2),
                      box.top + box.height / 2
                    );
                    return hit && item.contains(hit);
                  });
                  return {
                    cardOverflow: getComputedStyle(card).overflow,
                    menuExtendsPastCard: rect(menu).bottom > rect(card).bottom,
                    allItemsHit,
                  };
                }
                """
            )

            self.assertEqual(result["cardOverflow"], "visible")
            self.assertTrue(result["menuExtendsPastCard"])
            self.assertTrue(result["allItemsHit"])
            evidence.assert_clean()
        finally:
            context.close()

    def test_bulk_clear_hides_its_tooltip(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            root.locator(
                "[data-datatable-row]:visible [data-datatable-select-row]"
            ).first.click()

            clear = root.locator("[data-datatable-bulk-clear]")
            expect(clear).to_be_visible()
            clear.evaluate(
                """element => {
                    window.bootstrap.Tooltip.getOrCreateInstance(element, {
                        animation: false,
                    }).show();
                }"""
            )
            expect(page.locator(".tooltip.show")).to_contain_text("Clear selection")

            clear.click()
            expect(root.locator("[data-datatable-bulk-actions]")).to_be_hidden()
            expect(page.locator(".tooltip.show")).to_have_count(0)
            evidence.assert_clean()
        finally:
            context.close()

    def test_no_matching_results_hide_frames_and_clear_restores_rows(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            search = root.locator("input[data-datatable-search]")
            empty = root.locator("[data-datatable-empty]")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")
            cards = root.locator('[data-datatable-card]:not([hidden])')

            search.fill("no review can have this exact phrase")

            expect(root.locator(".datatable-frame")).to_be_hidden()
            expect(root.locator(".datatable-card-frame")).to_be_hidden()
            expect(empty).to_be_visible()
            expect(rows).to_have_count(0)
            expect(cards).to_have_count(0)

            root.locator("[data-datatable-reset]").click()
            expect(root.locator(".datatable-frame")).to_be_visible()
            expect(empty).to_be_hidden()
            expect(rows).to_have_count(10)
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_no_results_shows_empty_state(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            search = root.locator("input[data-datatable-search]")
            empty = root.locator("[data-datatable-empty]")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")

            search.fill("no ticket can match this exact phrase")

            expect(root.locator(".datatable-frame")).to_be_hidden()
            expect(root.locator(".datatable-card-frame")).to_be_hidden()
            expect(empty).to_be_visible()
            expect(empty).to_contain_text("No matching results")
            expect(rows).to_have_count(0)

            root.locator("[data-datatable-empty-reset]").click()
            expect(root.locator(".datatable-frame")).to_be_visible()
            expect(empty).to_be_hidden()
            expect(rows).to_have_count(2)
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_filter_picker_filters_rows(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            filter_button = root.locator("[data-datatable-filter-menu-trigger]")
            filter_menu = root.locator(".datatable-search-filter-menu")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")

            expect(filter_button).to_have_count(1)
            expect(filter_button).to_have_attribute("aria-expanded", "false")
            filter_button.click()
            expect(filter_button).to_have_attribute("aria-expanded", "true")
            expect(filter_menu).to_be_visible()
            expect(filter_menu).to_contain_text("Filter by")

            root.locator('[data-datatable-filter-group="status"]').click()
            resolved_option = root.locator(
                '[data-datatable-filter-option-key="status"]'
                '[data-datatable-filter-option="resolved"]'
            )
            status_facet = root.locator('[data-datatable-facet="status"]')
            status_summary = status_facet.locator("[data-datatable-facet-summary]")
            expect(resolved_option).to_be_visible()
            resolved_option.click()

            expect(resolved_option).to_have_attribute("aria-pressed", "true")
            expect(status_facet).to_be_visible()
            expect(status_summary).to_contain_text("Resolved")
            expect(
                root.locator('[data-datatable-filter-group-summary="status"]')
            ).to_contain_text("1 selected")
            expect(root.locator("[data-datatable-reset]")).to_be_visible()
            expect(rows).to_have_count(1)
            expect(rows).to_contain_text("TCK-2")

            root.locator("[data-datatable-reset]").click()
            expect(root.locator("[data-datatable-reset]")).to_be_hidden()
            expect(rows).to_have_count(2)
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_filter_trigger_shows_keyboard_focus(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            filter_button = root.locator("[data-datatable-filter-menu-trigger]")
            expect(filter_button).to_have_count(1)

            for _ in range(20):
                if filter_button.evaluate("element => element === document.activeElement"):
                    break
                page.keyboard.press("Tab")

            self.assertTrue(
                filter_button.evaluate("element => element === document.activeElement")
            )
            focus = filter_button.evaluate(
                """
                element => {
                  const style = getComputedStyle(element);
                  return {
                    focusVisible: element.matches(":focus-visible"),
                    outlineStyle: style.outlineStyle,
                    outlineWidth: Number.parseFloat(style.outlineWidth) || 0,
                    outlineOffset: style.outlineOffset,
                    zIndex: style.zIndex,
                  };
                }
                """
            )
            self.assertTrue(focus["focusVisible"], focus)
            self.assertEqual(focus["outlineStyle"], "solid", focus)
            self.assertGreaterEqual(focus["outlineWidth"], 2, focus)
            self.assertEqual(focus["outlineOffset"], "0px", focus)
            self.assertEqual(focus["zIndex"], "3", focus)
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_table_cells_center_content_vertically(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            table = root.locator("#certification-datatable-table")
            row = root.locator("#cert-row-1")

            table_class = table.get_attribute("class") or ""
            self.assertIn("align-middle", table_class.split())
            measurements = row.evaluate(
                """
                element => {
                  const rowBox = element.getBoundingClientRect();
                  const rowCenter = rowBox.top + rowBox.height / 2;
                  return Array.from(element.cells).map((cell) => {
                    const target =
                      cell.querySelector(".form-check-input") ||
                      cell.querySelector(".table-row-actions > button") ||
                      cell.querySelector("span") ||
                      cell;
                    const targetBox = target.getBoundingClientRect();
                    return {
                      column: cell.dataset.datatableColumn || "select",
                      verticalAlign: getComputedStyle(cell).verticalAlign,
                      delta: Math.abs(
                        rowCenter - (targetBox.top + targetBox.height / 2)
                      ),
                    };
                  });
                }
                """
            )
            for measurement in measurements:
                self.assertEqual(measurement["verticalAlign"], "middle", measurement)
                self.assertLessEqual(measurement["delta"], 2, measurement)
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_narrow_table_exposes_horizontal_scroll_cue(
        self,
    ) -> None:
        context = self.browser.new_context(
            viewport={"width": 540, "height": 720},
            color_scheme="light",
            reduced_motion="reduce",
            locale="en-US",
        )
        page = context.new_page()
        evidence = BrowserEvidence(page)
        try:
            response = page.goto(
                f"{self.base_url}{CERTIFICATION_FIXTURE_PATH}",
                wait_until="networkidle",
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[0])

            root = page.locator("#certification-datatable")
            frame = root.locator(".datatable-frame")
            scroll_frame = frame.locator(".table-responsive")
            expect(frame).to_be_visible()
            expect(scroll_frame).to_be_visible()

            class_name = scroll_frame.get_attribute("class") or ""
            self.assertIn("scrollbar-thin", class_name)
            self.assertIn("scroll-fade-x", class_name)
            metrics = scroll_frame.evaluate(
                """
                element => ({
                  clientWidth: element.clientWidth,
                  scrollWidth: element.scrollWidth,
                  overflowX: getComputedStyle(element).overflowX,
                })
                """
            )
            self.assertGreater(metrics["scrollWidth"], metrics["clientWidth"])
            self.assertIn(metrics["overflowX"], {"auto", "scroll"})
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_card_view_keeps_actions_and_selection(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            table_frame = root.locator(".datatable-frame")
            card_frame = root.locator(".datatable-card-frame")
            card_toggle = root.locator(
                'label[for="certification-datatable-view-cards"]'
            )
            first_card = root.locator('[data-datatable-card-for="cert-row-1"]')
            first_table_row = root.locator("#cert-row-1")

            card_toggle.click()
            expect(root).to_have_attribute("data-datatable-view", "cards")
            expect(table_frame).to_be_hidden()
            expect(card_frame).to_be_visible()
            expect(first_card).to_be_visible()
            expect(first_card).to_contain_text("Login redirect loops")
            expect(first_card).to_contain_text("TCK-1")

            first_card.locator('[data-datatable-select-row]').check()
            self.assertTrue(
                first_table_row.locator("[data-datatable-select-row]").is_checked()
            )

            trigger = first_card.locator(".table-row-actions > button")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(first_card.locator(".table-row-actions .dropdown-menu")).to_be_visible()
            expect(first_card.locator(".table-row-actions .dropdown-menu")).to_contain_text(
                "Open ticket"
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_keeps_identity_columns_fixed(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            root.locator(".datatable-view-trigger").click()

            for key in ("ticket", "subject"):
                expect(
                    root.locator(f'th[data-datatable-column="{key}"]')
                ).to_have_attribute(
                    "data-datatable-column-fixed",
                    "true",
                )
                self.assertEqual(
                    root.locator(f'[data-datatable-column-toggle="{key}"]').count(),
                    0,
                )
                self.assertEqual(
                    root.locator(
                        f'th[data-datatable-column="{key}"] '
                        '[data-datatable-sort-action="hide"]'
                    ).count(),
                    0,
                )

            status_toggle = root.locator('[data-datatable-column-toggle="status"]')
            expect(status_toggle).to_be_visible()
            status_toggle.click()
            expect(status_toggle).to_have_attribute("aria-pressed", "false")
            self.assertTrue(
                page.locator('[data-datatable-column="status"]').first.evaluate(
                    "element => element.classList.contains('datatable-col-hidden')"
                )
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_row_action_menu_opens(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            first_row = root.locator("#cert-row-1")
            trigger = first_row.locator(".table-row-actions > button")
            menu = first_row.locator(".table-row-actions .dropdown-menu")

            expect(trigger).to_have_attribute("aria-expanded", "false")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(menu).to_be_visible()
            expect(menu).to_contain_text("Open ticket")
            expect(menu).to_contain_text("Assign owner")
            expect(menu).to_contain_text("Copy link")
            self.assertEqual(
                root.locator(".datatable-frame").evaluate(
                    "element => getComputedStyle(element).overflowY"
                ),
                "visible",
            )

            trigger.press("Escape")
            expect(trigger).to_have_attribute("aria-expanded", "false")
            expect(trigger).to_be_focused()
            evidence.assert_clean()
        finally:
            context.close()

    def test_required_columns_stay_fixed_while_optional_columns_toggle(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            root.locator('[aria-label="View columns"]').click()

            for key in ("id", "item"):
                expect(
                    root.locator(f'th[data-datatable-column="{key}"]')
                ).to_have_attribute(
                    "data-datatable-column-fixed",
                    "true",
                )
                self.assertEqual(
                    root.locator(f'[data-datatable-column-toggle="{key}"]').count(),
                    0,
                )
                self.assertFalse(
                    page.locator(f'[data-datatable-column="{key}"]').first.evaluate(
                        "element => element.classList.contains('datatable-col-hidden')"
                    )
                )

            status_toggle = root.locator('[data-datatable-column-toggle="status"]')
            status_toggle.click()
            expect(status_toggle).to_have_attribute("aria-pressed", "false")
            self.assertTrue(
                page.locator('[data-datatable-column="status"]').first.evaluate(
                    "element => element.classList.contains('datatable-col-hidden')"
                )
            )

            status_toggle.click()
            expect(status_toggle).to_have_attribute("aria-pressed", "true")
            self.assertFalse(
                page.locator('[data-datatable-column="status"]').first.evaluate(
                    "element => element.classList.contains('datatable-col-hidden')"
                )
            )
            evidence.assert_clean()
        finally:
            context.close()
