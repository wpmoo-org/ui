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
    skip_if_browser_launch_is_sandboxed,
)


PREVIEW_PATH = "/site-dist/blocks/previews/datatable-release-review/index.html"
CERTIFICATION_FIXTURE_PATH = "/tests/fixtures/certification/datatable.html"
TABLE_ID = "standalone-datatable-release-reviews"

_CAPTURE_DATATABLE_STATE_JS = """
(tableId) => {
    const root = document.getElementById(tableId);
    const rows = Array.from(
        root.querySelectorAll(
            "tbody > tr[data-datatable-row]"
        )
    ).map((tr) => tr.id);
    const summary = root.querySelector(
        "[data-datatable-results-summary]"
    );
    const pageNumbers = Array.from(
        root.querySelectorAll(
            "li[data-datatable-page-number]"
        )
    ).map((li) => li.getAttribute("data-datatable-page-number"));
    const first = root.querySelector(
        "[data-datatable-page-first]"
    );
    const prev = root.querySelector(
        "[data-datatable-page-prev]"
    );
    const sortStates = {};
    root.querySelectorAll("th[data-datatable-column]").forEach(
        (th) => {
            sortStates[
                th.getAttribute("data-datatable-column")
            ] = th.getAttribute("aria-sort") || "none";
        }
    );
    return {
        rowIds: rows,
        summaryText: summary ? summary.textContent : "",
        pageNumbers: pageNumbers,
        firstDisabled: first ? first.disabled : null,
        prevDisabled: prev ? prev.disabled : null,
        sortStates: sortStates,
    };
}
"""


def _capture_datatable_state(page, table_id: str) -> dict:
    """Read the row order, results summary, pagination, and sort state a
    visitor would currently see for the given Data Table root.

    Shared by the pre-JS and post-JS captures in
    ``test_initial_server_render_matches_post_js_render`` so both sides read
    the exact same DOM shape — a selector change only needs to happen once.
    """
    return page.evaluate(_CAPTURE_DATATABLE_STATE_JS, table_id)


class DataTableBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
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
            menu = page.locator("body > .dropdown-menu.show")
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()

            result = page.evaluate(
                """
                () => {
                  const menu = document.querySelector("body > .dropdown-menu.show");
                  const trigger = document.querySelector(
                    "#standalone-datatable-release-reviews .datatable-card "
                      + ".table-row-actions > [aria-expanded='true']"
                  );
                  const card = trigger?.closest(".datatable-card");
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
                    menuParentIsBody: menu?.parentElement === document.body,
                    menuExtendsPastCard: rect(menu).bottom > rect(card).bottom,
                    allItemsHit,
                  };
                }
                """
            )

            self.assertTrue(result["menuParentIsBody"])
            self.assertTrue(result["menuExtendsPastCard"])
            self.assertTrue(result["allItemsHit"])
            action.press("Escape")
            expect(action).to_have_attribute("aria-expanded", "false")
            expect(page.locator("body > .dropdown-menu.show")).to_have_count(0)
            self.assertTrue(
                action.evaluate(
                    "element => element.parentElement.querySelector(':scope > .dropdown-menu') !== null"
                )
            )
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
            menu = page.locator("body > .dropdown-menu.show")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()
            expect(menu).to_contain_text("Open ticket")
            self.assertTrue(menu.evaluate("element => element.parentElement === document.body"))

            trigger.press("Escape")
            expect(trigger).to_have_attribute("aria-expanded", "false")
            expect(page.locator("body > .dropdown-menu.show")).to_have_count(0)
            expect(first_card.locator(".table-row-actions .dropdown-menu")).to_have_count(1)
            expect(trigger).to_be_focused()
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
            menu = page.locator("body > .dropdown-menu.show")

            expect(trigger).to_have_attribute("aria-expanded", "false")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()
            expect(menu).to_contain_text("Open ticket")
            expect(menu).to_contain_text("Assign owner")
            expect(menu).to_contain_text("Copy link")
            self.assertTrue(menu.evaluate("element => element.parentElement === document.body"))
            self.assertEqual(
                root.locator(".datatable-frame").evaluate(
                    "element => getComputedStyle(element).overflowY"
                ),
                "hidden",
            )
            self.assertEqual(
                menu.evaluate("element => getComputedStyle(element).position"),
                "fixed",
            )

            trigger.press("Escape")
            expect(trigger).to_have_attribute("aria-expanded", "false")
            expect(page.locator("body > .dropdown-menu.show")).to_have_count(0)
            expect(first_row.locator(".table-row-actions .dropdown-menu")).to_have_count(1)
            expect(trigger).to_be_focused()
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_sort_updates_aria_sort_and_row_order(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            root.locator(".datatable-page-size-trigger").click()
            root.locator('[data-datatable-page-size-option="10"]').click()
            ticket_header = root.locator('th[data-datatable-column="ticket"]')
            ticket_trigger = ticket_header.locator("[data-datatable-sort-key]")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")

            expect(ticket_header).to_have_attribute("aria-sort", "none")

            ticket_trigger.click()
            ticket_header.locator('[data-datatable-sort-action="desc"]').click()

            expect(ticket_header).to_have_attribute("aria-sort", "descending")
            expect(rows).to_have_count(3)
            expect(rows.nth(0)).to_contain_text("TCK-3")
            expect(rows.nth(2)).to_contain_text("TCK-1")

            ticket_trigger.click()
            ticket_header.locator('[data-datatable-sort-action="asc"]').click()

            expect(ticket_header).to_have_attribute("aria-sort", "ascending")
            expect(rows.nth(0)).to_contain_text("TCK-1")
            expect(rows.nth(2)).to_contain_text("TCK-3")

            subject_header = root.locator('th[data-datatable-column="subject"]')
            expect(subject_header).to_have_attribute("aria-sort", "none")
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_pagination_controls_navigate_pages(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")
            summary = root.locator("[data-datatable-results-summary]")
            first_button = root.locator("[data-datatable-page-first]")
            prev_button = root.locator("[data-datatable-page-prev]")
            next_button = root.locator("[data-datatable-page-next]")
            last_button = root.locator("[data-datatable-page-last]")
            page_nav = root.locator(".datatable-page-nav")

            def read_page_nav_metrics() -> dict:
                return page_nav.evaluate(
                    """
                    element => {
                      const links = Array.from(element.querySelectorAll(".page-link"));
                      return {
                        overflowX: getComputedStyle(element).overflowX,
                        overflowY: getComputedStyle(element).overflowY,
                        clientHeight: element.clientHeight,
                        scrollHeight: element.scrollHeight,
                        linkBoxes: links.map(link => {
                          const rect = link.getBoundingClientRect();
                          return {
                            text: link.textContent.trim(),
                            width: rect.width,
                            height: rect.height,
                          };
                        }),
                      };
                    }
                    """
                )

            expect(rows).to_have_count(2)
            expect(rows.nth(0)).to_contain_text("TCK-1")
            expect(rows.nth(1)).to_contain_text("TCK-2")
            expect(summary).to_have_text("Showing 1-2 of 3")
            expect(first_button).to_be_disabled()
            expect(prev_button).to_be_disabled()
            expect(next_button).to_be_enabled()
            expect(last_button).to_be_enabled()
            metrics = read_page_nav_metrics()
            self.assertIn(metrics["overflowX"], {"auto", "scroll"})
            self.assertEqual(metrics["overflowY"], "hidden")
            self.assertLessEqual(metrics["scrollHeight"], metrics["clientHeight"] + 1)
            for box in metrics["linkBoxes"]:
                self.assertAlmostEqual(box["width"], 32, delta=1)
                self.assertAlmostEqual(box["height"], 32, delta=1)

            next_button.click()
            expect(rows).to_have_count(1)
            expect(rows.nth(0)).to_contain_text("TCK-3")
            expect(summary).to_have_text("Showing 3-3 of 3")
            expect(next_button).to_be_disabled()
            expect(last_button).to_be_disabled()
            expect(prev_button).to_be_enabled()
            metrics = read_page_nav_metrics()
            self.assertEqual(metrics["overflowY"], "hidden")
            self.assertLessEqual(metrics["scrollHeight"], metrics["clientHeight"] + 1)

            first_button.click()
            expect(rows).to_have_count(2)
            expect(rows.nth(0)).to_contain_text("TCK-1")
            expect(summary).to_have_text("Showing 1-2 of 3")
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_page_size_select_updates_rows_per_page(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")
            summary = root.locator("[data-datatable-results-summary]")
            trigger = root.locator(".datatable-page-size-trigger")

            expect(rows).to_have_count(2)

            trigger.click()
            root.locator('[data-datatable-page-size-option="10"]').click()

            expect(rows).to_have_count(3)
            expect(summary).to_have_text("Showing 1-3 of 3")
            expect(root.locator('[data-datatable-page-size-value]')).to_have_text("10")
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_bulk_update_changes_status_across_selection(
        self,
    ) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            root.locator(".datatable-page-size-trigger").click()
            root.locator('[data-datatable-page-size-option="10"]').click()
            root.locator("#cert-row-1 [data-datatable-select-row]").check()
            root.locator("#cert-row-3 [data-datatable-select-row]").check()

            bulk_actions = root.locator("[data-datatable-bulk-actions]")
            expect(bulk_actions).to_be_visible()
            expect(root.locator("[data-datatable-bulk-count]")).to_have_text("2")

            root.locator('[data-bs-toggle="dropdown"][aria-label="Update status"]').click()
            root.locator(
                '[data-datatable-bulk-update="status"][data-datatable-bulk-update-value="resolved"]'
            ).click()

            expect(root.locator("#cert-row-1 [data-datatable-column=\"status\"]")).to_contain_text(
                "Resolved"
            )
            expect(root.locator("#cert-row-3 [data-datatable-column=\"status\"]")).to_contain_text(
                "Resolved"
            )
            expect(root.locator("#cert-row-2 [data-datatable-column=\"status\"]")).to_contain_text(
                "Resolved"
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_bulk_delete_removes_selected_rows(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            root.locator(".datatable-page-size-trigger").click()
            root.locator('[data-datatable-page-size-option="10"]').click()
            root.locator("#cert-row-2 [data-datatable-select-row]").check()

            bulk_actions = root.locator("[data-datatable-bulk-actions]")
            expect(bulk_actions).to_be_visible()

            root.locator('[data-datatable-bulk-action="delete"]').click()

            rows = root.locator("tbody > tr[data-datatable-row]:not([hidden])")
            expect(rows).to_have_count(2)
            self.assertEqual(root.locator("#cert-row-2").count(), 0)
            expect(bulk_actions).to_be_hidden()
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_select_all_scopes_to_current_page_and_indeterminate(
        self,
    ) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            select_all = root.locator(
                '.datatable-frame [data-datatable-select-all]'
            )

            select_all.check()
            expect(root.locator("#cert-row-1 [data-datatable-select-row]")).to_be_checked()
            expect(root.locator("#cert-row-2 [data-datatable-select-row]")).to_be_checked()
            expect(root.locator("[data-datatable-bulk-count]")).to_have_text("2")

            root.locator("#cert-row-1 [data-datatable-select-row]").uncheck()
            self.assertTrue(
                select_all.evaluate("element => element.indeterminate")
            )

            root.locator("#cert-row-1 [data-datatable-select-row]").check()
            root.locator("[data-datatable-page-next]").click()
            self.assertFalse(
                select_all.evaluate("element => element.checked")
            )
            self.assertFalse(
                select_all.evaluate("element => element.indeterminate")
            )
            expect(root.locator("#cert-row-3 [data-datatable-select-row]")).not_to_be_checked()
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_dark_mobile_case_renders_clean(self) -> None:
        context = new_case_context(self.browser, CERTIFICATION_CASES[1])
        page = context.new_page()
        evidence = BrowserEvidence(page)
        try:
            response = page.goto(
                f"{self.base_url}{CERTIFICATION_FIXTURE_PATH}", wait_until="networkidle"
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)
            prepare_page(page, CERTIFICATION_CASES[1])

            root = page.locator("#certification-datatable")
            expect(root).to_be_visible()
            expect(root.locator("tbody > tr[data-datatable-row]:not([hidden])")).to_have_count(2)

            filter_button = root.locator("[data-datatable-filter-menu-trigger]")
            filter_button.click()
            expect(root.locator(".datatable-search-filter-menu")).to_be_visible()

            body_background = page.evaluate(
                "getComputedStyle(document.body).backgroundColor"
            )
            self.assertNotEqual(body_background, "rgba(0, 0, 0, 0)")

            overflow = page.evaluate(
                """
                () => ({
                  scrollWidth: document.documentElement.scrollWidth,
                  clientWidth: document.documentElement.clientWidth,
                })
                """
            )
            self.assertLessEqual(overflow["scrollWidth"], overflow["clientWidth"] + 1)
            evidence.assert_clean()
        finally:
            context.close()

    def test_preview_page_never_exposes_page_level_horizontal_overflow(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            for width in (390, 768, 1040):
                page.set_viewport_size({"width": width, "height": 844})
                overflow = page.evaluate(
                    """
                    () => ({
                      scrollWidth: document.documentElement.scrollWidth,
                      clientWidth: document.documentElement.clientWidth,
                    })
                    """
                )
                self.assertLessEqual(
                    overflow["scrollWidth"],
                    overflow["clientWidth"] + 1,
                    f"page-level horizontal overflow at width={width}: {overflow}",
                )
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

    def test_initial_server_render_matches_post_js_render(self) -> None:
        """Lock the 'no-op re-render' claim from commit 5f1b87e.

        Loads the Jinja-rendered preview page twice: once with JS disabled
        (pure server HTML) and once with JS enabled. The two states must be
        identical for row order, results summary, pagination, and sort —
        proving datatable.js's initial render is a no-op.
        """
        case = CERTIFICATION_CASES[0]

        # --- Pre-JS state: server-rendered HTML with no JS execution ---
        pre_context = self.browser.new_context(
            viewport=case.viewport,
            color_scheme=case.color_scheme,
            java_script_enabled=False,
            reduced_motion="reduce",
            locale="en-US",
        )
        pre_page = pre_context.new_page()
        try:
            response = pre_page.goto(
                f"{self.base_url}{PREVIEW_PATH}", wait_until="networkidle"
            )
            self.assertIsNotNone(response)
            self.assertTrue(response.ok)

            pre_state = _capture_datatable_state(pre_page, TABLE_ID)
        finally:
            pre_context.close()

        # --- Post-JS state: normal rendering with datatable.js active ---
        context, page, evidence = self.open_preview()
        try:
            post_state = _capture_datatable_state(page, TABLE_ID)
            evidence.assert_clean()
        finally:
            context.close()

        # --- Parity assertions ---
        self.assertEqual(
            pre_state["rowIds"],
            post_state["rowIds"],
            "Row order differs between server render and JS render",
        )
        self.assertEqual(
            pre_state["summaryText"],
            post_state["summaryText"],
            "Results summary differs between server render and JS render",
        )
        self.assertEqual(
            pre_state["pageNumbers"],
            post_state["pageNumbers"],
            "Pagination page numbers differ between server render and JS render",
        )
        self.assertEqual(
            pre_state["firstDisabled"],
            post_state["firstDisabled"],
            "First-page button disabled state differs",
        )
        self.assertEqual(
            pre_state["prevDisabled"],
            post_state["prevDisabled"],
            "Previous-page button disabled state differs",
        )
        self.assertEqual(
            pre_state["sortStates"],
            post_state["sortStates"],
            "Column aria-sort states differ between server render and JS render",
        )
