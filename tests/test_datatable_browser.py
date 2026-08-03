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
