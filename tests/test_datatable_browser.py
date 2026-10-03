from __future__ import annotations

import re
from contextlib import contextmanager
import tempfile
import unittest
from pathlib import Path

from build import create_environment
from playwright.sync_api import expect, sync_playwright

from tests.helpers import ROOT
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

    @contextmanager
    def responsive_fixture(self, *, mode="auto", breakpoint="md", runtime=True, blocked_storage=False, selectable=False, missing_breakpoint=False):
        template = create_environment().from_string("""
            <!doctype html><html><head><meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="/dist/assets/css/moo-ui.css">
            {% if missing_breakpoint %}<style>
              #responsive-items { --moo-datatable-responsive-breakpoint: initial; }
            </style>{% endif %}
            <link rel="icon" href="data:,"></head><body>
            <main class="moo-ui" data-bs-theme="light">
            {% from "components/datatable.html.jinja" import datatable %}
            {% from "components/button.html.jinja" import button %}
            {% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}
            {% set actions %}{% call dropdown('Actions', variant='ghost', align='end') %}
              {{ dropdown_item('View item', href='#item') }}
            {% endcall %}{% endset %}
            {% set rows = [] %}
            {% for title in ['Solar Powered Robot', 'Clean Water Sensor', 'VeryLongUnbrokenProjectTitleThatMustStayInsideItsCell'] %}
              {% set link %}{{ button(title, element='a', href='#item', variant='link', size='sm', extra_class='p-0') }}{% endset %}
              {% set _ = rows.append({'id':'responsive-item-' ~ loop.index, 'label':title,
                'facets':{'status':'draft'}, 'cells':{'project':link,
                'edition':'Olympiad 2027', 'category':'Applied Science',
                'students':'2', 'status':'Draft', 'actions':actions}}) %}
            {% endfor %}
            {{ datatable('responsive-items', [
              {'key':'project', 'label':'Project', 'card_role':'title'},
              {'key':'edition', 'label':'Edition'},
              {'key':'category', 'label':'Category'},
              {'key':'students', 'label':'Students'},
              {'key':'status', 'label':'Status'},
              {'key':'actions', 'label':'Actions', 'sortable':false,
               'hideable':false, 'align':'end', 'card_role':'actions'}
            ], rows, selectable=selectable, responsive_mode=mode,
               responsive_breakpoint=breakpoint) }}
            </main>
            {% if runtime %}
            <script src="/vendor/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
            <script type="module">
              import DataTable from '/dist/js/datatable.js';
              DataTable.getOrCreateInstance(document.querySelector('.datatable'));
              document.body.dataset.datatableReady = 'true';
            </script>{% endif %}</body></html>
        """)
        try:
            rendered = template.render(mode=mode, breakpoint=breakpoint, runtime=runtime, selectable=selectable, missing_breakpoint=missing_breakpoint)
        except ValueError as error:
            self.fail(f"Public responsive configuration rejected: {error}")
        with tempfile.TemporaryDirectory(prefix="datatable-responsive-", dir=ROOT / "site-dist") as temporary:
            fixture = Path(temporary) / "index.html"
            fixture.write_text(rendered, encoding="utf-8")
            context = new_case_context(self.browser, CERTIFICATION_CASES[0]) if runtime else self.browser.new_context(java_script_enabled=False, viewport={'width': 1280, 'height': 900})
            try:
                if blocked_storage:
                    context.add_init_script("""Storage.prototype.getItem = Storage.prototype.setItem = () => {
                        throw new DOMException('Storage blocked', 'SecurityError');
                    };""")
                page = context.new_page()
                evidence = BrowserEvidence(page)
                page.goto(f"{self.base_url}/{fixture.relative_to(ROOT).as_posix()}", wait_until="networkidle")
                if runtime:
                    expect(page.locator('body')).to_have_attribute('data-datatable-ready', 'true')
                yield page, page.locator('#responsive-items'), evidence
            finally:
                context.close()

    def test_card_actions_keep_end_padding_and_distinct_hover_across_themes(self) -> None:
        for selectable in (False, True):
            with self.responsive_fixture(selectable=selectable) as (page, root, evidence):
                page.set_viewport_size({'width': 598, 'height': 900})
                expect(root).to_have_attribute('data-datatable-view', 'cards')
                owner = page.locator('.moo-ui')
                # Presets may map the tertiary background to the Ghost hover role.
                owner.evaluate("e => e.style.setProperty('--bs-tertiary-bg', 'var(--moo-muted-surface)')")
                header = root.locator('.datatable-card-header').first
                trigger = header.get_by_role('button', name='Actions', exact=True)
                for theme in ('light', 'dark'):
                    for direction in ('ltr', 'rtl'):
                        with self.subTest(selectable=selectable, theme=theme, direction=direction):
                            owner.evaluate('(e, state) => { e.dataset.bsTheme = state.theme; e.dir = state.direction; }',
                                           {'theme': theme, 'direction': direction})
                            trigger.hover()
                            measured = header.evaluate("""header => {
                                const button = header.querySelector('[data-bs-toggle="dropdown"]');
                                const h = header.getBoundingClientRect();
                                const b = button.getBoundingClientRect();
                                const style = getComputedStyle(header);
                                const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
                                const color = value => {
                                    ctx.clearRect(0, 0, 1, 1);
                                    ctx.fillStyle = value;
                                    ctx.fillRect(0, 0, 1, 1);
                                    return Array.from(ctx.getImageData(0, 0, 1, 1).data);
                                };
                                return {
                                    inset: style.direction === 'rtl' ? b.left - h.left : h.right - b.right,
                                    padding: parseFloat(style.paddingInlineEnd),
                                    hovered: button.matches(':hover'),
                                    headerColor: color(style.backgroundColor),
                                    buttonColor: color(getComputedStyle(button).backgroundColor),
                                };
                            }""")
                            self.assertAlmostEqual(measured['inset'], measured['padding'], delta=0.5)
                            self.assertTrue(measured['hovered'])
                            self.assertEqual(measured['buttonColor'][3], 255)
                            self.assertNotEqual(measured['buttonColor'], measured['headerColor'])
                evidence.assert_clean()

    def test_auto_view_keeps_preferences_separate_across_breakpoint_and_reload(self) -> None:
        with self.responsive_fixture() as (page, root, evidence):
            page.set_viewport_size({'width': 1280, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.set_viewport_size({'width': 767, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            expect(root.locator('.datatable-card-frame')).to_be_visible()
            expect(root.locator('.datatable-frame')).not_to_be_visible()
            expect(root.locator('input[value="cards"]')).to_be_checked()
            page.evaluate("localStorage.setItem('moo-datatable-view:responsive-items', 'table')")
            page.reload(wait_until='networkidle')
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            page.set_viewport_size({'width': 768, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.set_viewport_size({'width': 375, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            root.locator('label[for$="-view-table"]').click()
            expect(root).to_have_attribute('data-datatable-view', 'table')
            # A resize also closes a popup whose owning frame becomes hidden.
            root.locator('#responsive-item-1').get_by_role('button', name='Actions').click()
            expect(page.locator('.moo-ui > .dropdown-menu.show')).to_have_count(1)
            page.set_viewport_size({'width': 1280, 'height': 900})
            root.locator('label[for$="-view-cards"]').click()
            expect(page.locator('.moo-ui > .dropdown-menu.show')).to_have_count(0)
            page.set_viewport_size({'width': 375, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.reload(wait_until='networkidle')
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.set_viewport_size({'width': 1280, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            page.reload(wait_until='networkidle')
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            expect(root.locator('input[value="cards"]')).to_be_checked()
            evidence.assert_clean()

    def test_auto_view_fallback_and_blocked_storage_lifecycle(self) -> None:
        with self.responsive_fixture(runtime=False, breakpoint='lg') as (page, root, _):
            page.set_viewport_size({'width': 991, 'height': 900})
            expect(root.locator('.datatable-card-frame')).to_be_visible()
            expect(root.locator('.datatable-frame')).not_to_be_visible()
            page.set_viewport_size({'width': 992, 'height': 900})
            expect(root.locator('.datatable-frame')).to_be_visible()
            expect(root.locator('.datatable-card-frame')).not_to_be_visible()
        with self.responsive_fixture(blocked_storage=True) as (page, root, evidence):
            page.set_viewport_size({'width': 375, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            root.locator('label[for$="-view-table"]').click()
            page.set_viewport_size({'width': 1280, 'height': 900})
            root.locator('label[for$="-view-cards"]').click()
            page.set_viewport_size({'width': 375, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.evaluate("""async () => {
                const {default: DataTable} = await import('/dist/js/datatable.js');
                DataTable.getInstance(document.querySelector('.datatable')).dispose();
            }""")
            page.set_viewport_size({'width': 1280, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.evaluate("""async () => {
                const {default: DataTable} = await import('/dist/js/datatable.js');
                DataTable.getOrCreateInstance(document.querySelector('.datatable'));
            }""")
            expect(root).to_have_attribute('data-datatable-view', 'table')
            page.set_viewport_size({'width': 375, 'height': 900})
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            evidence.assert_clean()

    def test_auto_view_keeps_css_fallback_when_runtime_breakpoint_is_missing(self) -> None:
        with self.responsive_fixture(missing_breakpoint=True) as (page, root, evidence):
            expect(root).to_have_attribute('data-datatable-view', 'auto')
            expect(root.locator('.datatable-frame')).to_be_visible()
            page.set_viewport_size({'width': 598, 'height': 900})
            expect(root.locator('.datatable-card-frame')).to_be_visible()
            expect(root.locator('.datatable-frame')).not_to_be_visible()
            root.locator('label[for$="-view-table"]').click()
            expect(root).to_have_attribute('data-datatable-view', 'table')
            expect(root.locator('.datatable-frame')).to_be_visible()
            root.locator('label[for$="-view-cards"]').click()
            expect(root).to_have_attribute('data-datatable-view', 'cards')
            expect(root.locator('.datatable-card-frame')).to_be_visible()
            evidence.assert_clean()

    def test_linked_titles_stay_inside_their_table_cell_and_card_heading(self) -> None:
        with self.responsive_fixture(mode='toggle') as (page, root, evidence):
            page.set_viewport_size({'width': 375, 'height': 900})
            for direction in ('ltr', 'rtl'):
                page.locator('.moo-ui').evaluate('(e, dir) => e.dir = dir', direction)
                links = root.locator('td[data-datatable-column="project"] > .btn-link')
                for link in links.all():
                    self.assertTrue(link.evaluate("""e => {
                        const cell = e.parentElement.getBoundingClientRect();
                        const range = document.createRange(); range.selectNodeContents(e);
                        return [...range.getClientRects()].every(r => r.left >= cell.left - 1 && r.right <= cell.right + 1);
                    }"""), f"Linked title crossed its cell ({direction})")
            root.locator('label[for$="-view-cards"]').click()
            for link in root.locator('.datatable-card-title > .btn-link').all():
                self.assertTrue(link.evaluate("""e => {
                    const title = e.parentElement.getBoundingClientRect();
                    return e.scrollWidth <= title.width + 1;
                }"""))
            evidence.assert_clean()

    def test_leading_sort_trigger_stays_inside_frame_and_aligns_with_body(self) -> None:
        # Accepted 2026-10-01 on shared Core and the live Olympiad consumer.
        # Render the public macro so the check covers selectable and plain
        # tables without adding host-specific padding or copied table markup.
        template = create_environment().from_string("""
            <!doctype html><html><head><meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="/dist/assets/css/moo-ui.css">
            <link rel="icon" href="data:,">
            </head><body><main class="moo-ui" data-bs-theme="light">
            {% from "components/datatable.html.jinja" import datatable %}
            {% for selectable in [false, true] %}
              {% set id = 'leading-select' if selectable else 'leading-plain' %}
              {{ datatable(id, columns, [
                {'id': id ~ '-row', 'label': 'Example',
                 'cells': {'project': 'Example', 'status': 'Ready'}}
              ], selectable=selectable, page_sizes=[10], default_page_size=10) }}
            {% endfor %}
            </main><script src="/vendor/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
            <script type="module">
              import DataTable from '/dist/js/datatable.js';
              document.querySelectorAll('.datatable').forEach(
                root => DataTable.getOrCreateInstance(root)
              );
              document.body.dataset.datatableReady = 'true';
            </script></body></html>
        """)
        columns = [{"key": "project", "label": "Project"},
                   {"key": "status", "label": "Status"}]
        geometry = """
            root => {
              const table = root.querySelector('.datatable-table');
              const visible = cell => getComputedStyle(cell).display !== 'none';
              const header = [...table.querySelectorAll('thead .datatable-col')].find(visible);
              const cell = [...table.querySelectorAll('tbody .datatable-col')].find(visible);
              const trigger = header.querySelector('.datatable-sort-trigger');
              const labels = {project: 'Project', status: 'Status'};
              const labelNodes = document.createTreeWalker(trigger, NodeFilter.SHOW_TEXT, {
                acceptNode: node => node.textContent.trim() === labels[header.dataset.datatableColumn]
                  ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP,
              });
              const labelRange = document.createRange();
              labelRange.selectNodeContents(labelNodes.nextNode());
              const range = document.createRange();
              range.selectNodeContents(cell);
              const rtl = getComputedStyle(table).direction === 'rtl';
              const start = rect => rtl ? -rect.right : rect.left;
              return {
                column: header.dataset.datatableColumn,
                triggerInset: start(trigger.getBoundingClientRect()) - start(table.getBoundingClientRect()),
                labelStart: start(labelRange.getBoundingClientRect()),
                bodyStart: start(range.getBoundingClientRect()),
                triggerBorder: parseFloat(getComputedStyle(trigger).borderInlineStartWidth),
                padding: getComputedStyle(header).paddingInlineStart,
                bodyPadding: getComputedStyle(cell).paddingInlineStart,
                followingPadding: getComputedStyle(table.querySelector('thead [data-datatable-column="status"]')).paddingInlineStart,
              };
            }
        """
        with tempfile.TemporaryDirectory(prefix="datatable-leading-", dir=ROOT / "site-dist") as temporary:
            fixture = Path(temporary) / "index.html"
            fixture.write_text(template.render(columns=columns), encoding="utf-8")
            path = fixture.relative_to(ROOT).as_posix()
            for case in CERTIFICATION_CASES:
                with self.subTest(case=case.name):
                    context = new_case_context(self.browser, case)
                    try:
                        page = context.new_page()
                        evidence = BrowserEvidence(page)
                        page.goto(f"{self.base_url}/{path}", wait_until="networkidle")
                        prepare_page(page, case)
                        expect(page.locator('body')).to_have_attribute('data-datatable-ready', 'true')
                        for selectable in (False, True):
                            root = page.locator('#leading-select' if selectable else '#leading-plain')
                            before = root.evaluate(geometry)
                            self.assertEqual(before['column'], 'project')
                            self.assertGreaterEqual(before['triggerInset'], 0)
                            # A sort button's native border can add one token-
                            # sized inset beyond the matching cell padding.
                            self.assertAlmostEqual(before['labelStart'], before['bodyStart'], delta=before['triggerBorder'] + 0.5)
                            self.assertEqual(before['padding'], before['bodyPadding'])
                            if selectable:
                                self.assertEqual(before['padding'], before['followingPadding'])
                            else:
                                self.assertGreater(float(before['padding'][:-2]), float(before['followingPadding'][:-2]))
                            root.get_by_role('button', name='Sort by Project', exact=True).click()
                            page.locator('.dropdown-menu.show [data-datatable-sort-action="hide"]').click()
                            after = root.evaluate(geometry)
                            self.assertEqual(after['column'], 'status')
                            self.assertGreaterEqual(after['triggerInset'], 0)
                            self.assertAlmostEqual(after['labelStart'], after['bodyStart'], delta=after['triggerBorder'] + 0.5)
                            self.assertEqual(after['padding'], before['padding'])
                            self.assertEqual(after['bodyPadding'], after['padding'])
                        evidence.assert_clean()
                    finally:
                        context.close()

    def test_composed_dropdown_escapes_table_and_card_frames(self) -> None:
        # A public Dropdown in an actions cell has no private row-action class.
        template = create_environment().from_string("""
            <!doctype html><html><head><meta charset="utf-8">
            <link rel="stylesheet" href="/dist/assets/css/moo-ui.css">
            <link rel="icon" href="data:,"></head><body>
            <main class="moo-ui" data-bs-theme="light">
            {% from "components/datatable.html.jinja" import datatable %}
            {% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}
            {% set actions %}
              {% call dropdown('Actions', variant='ghost', align='end') %}
                {{ dropdown_item('View item', href='#item') }}
                {{ dropdown_item('Copy link') }}
                {{ dropdown_item('More information') }}
              {% endcall %}
            {% endset %}
            {{ datatable('composed-dropdowns', [
              {'key':'name', 'label':'Item', 'card_role':'title'},
              {'key':'actions', 'label':'Actions', 'sortable':false,
               'hideable':false, 'align':'end', 'card_role':'actions'}
            ], [{'id':'composed-item', 'label':'Example',
                 'cells':{'name':'Example', 'actions':actions}}],
              selectable=false, responsive_mode='toggle') }}
            </main><script src="/vendor/bootstrap/dist/js/bootstrap.bundle.min.js"></script>
            <script type="module">
              import DataTable from '/dist/js/datatable.js';
              DataTable.getOrCreateInstance(document.querySelector('.datatable'));
              document.body.dataset.datatableReady = 'true';
            </script></body></html>
        """)
        with tempfile.TemporaryDirectory(prefix="datatable-dropdown-", dir=ROOT / "site-dist") as temporary:
            fixture = Path(temporary) / "index.html"
            fixture.write_text(template.render(), encoding="utf-8")
            context = new_case_context(self.browser, CERTIFICATION_CASES[0])
            try:
                page = context.new_page()
                evidence = BrowserEvidence(page)
                page.goto(f"{self.base_url}/{fixture.relative_to(ROOT).as_posix()}", wait_until="networkidle")
                expect(page.locator('body')).to_have_attribute('data-datatable-ready', 'true')
                root = page.locator('#composed-dropdowns')
                for view in ('table', 'cards'):
                    with self.subTest(view=view):
                        if view == 'cards':
                            root.locator('label[for$="-view-cards"]').click()
                        source = root.locator('#composed-item' if view == 'table' else '[data-datatable-card-for="composed-item"]')
                        trigger = source.get_by_role('button', name='Actions', exact=True)
                        original_menu = source.locator('.dropdown-menu')
                        trigger.click()
                        menu = page.locator('.moo-ui[data-bs-theme] > .dropdown-menu.show')
                        expect(menu).to_have_count(1)
                        expect(menu).to_be_visible()
                        self.assertEqual(menu.evaluate('e => getComputedStyle(e).position'), 'fixed')
                        self.assertEqual(menu.get_attribute('data-datatable-row-action-owner'), 'composed-item')
                        self.assertTrue(menu.evaluate("""menu => {
                            return [...menu.querySelectorAll('.dropdown-item')].every(item => {
                                const r = item.getBoundingClientRect();
                                return item.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
                            });
                        }"""))
                        if view == 'table':
                            self.assertGreater(menu.bounding_box()['y'] + menu.bounding_box()['height'], root.locator('.datatable-frame').bounding_box()['y'] + root.locator('.datatable-frame').bounding_box()['height'])
                        trigger.press('Escape')
                        expect(trigger).to_have_attribute('aria-expanded', 'false')
                        expect(trigger).to_be_focused()
                        expect(original_menu).to_have_count(1)
                        trigger.click()
                        expect(menu).to_be_visible()
                        page.evaluate("""async () => {
                            const {default: DataTable} = await import('/dist/js/datatable.js');
                            DataTable.getInstance(document.querySelector('.datatable')).dispose();
                        }""")
                        expect(original_menu).to_have_count(1)
                        expect(original_menu).not_to_have_class(re.compile(r'\bshow\b'))
                        expect(trigger).to_have_attribute('aria-expanded', 'false')
                        self.assertEqual(page.locator('.moo-ui[data-bs-theme] > .dropdown-menu.show').count(), 0)
                        page.evaluate("""async () => {
                            const {default: DataTable} = await import('/dist/js/datatable.js');
                            DataTable.getOrCreateInstance(document.querySelector('.datatable'));
                        }""")
                evidence.assert_clean()
            finally:
                context.close()

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

    def test_searchbar_clips_closed_control_but_releases_open_filter_menu(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            searchbar = root.locator(".datatable-searchbar")
            filter_button = root.locator("[data-datatable-filter-menu-trigger]")
            filter_menu = root.locator(".datatable-search-filter-menu")

            self.assertEqual(
                searchbar.evaluate("element => getComputedStyle(element).overflow"),
                "hidden",
            )

            filter_button.click()
            expect(filter_menu).to_be_visible()
            self.assertEqual(
                searchbar.evaluate("element => getComputedStyle(element).overflow"),
                "visible",
            )

            filter_button.click()
            expect(filter_menu).to_be_hidden()
            self.assertEqual(
                searchbar.evaluate("element => getComputedStyle(element).overflow"),
                "hidden",
            )
            evidence.assert_clean()
        finally:
            context.close()

    def test_focused_search_keeps_search_icon_above_input_surface(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            search = root.locator("input[data-datatable-search]")
            icon = root.locator(".datatable-search-icon")

            search.click()
            layering = root.evaluate(
                """
                (datatable) => {
                  const input = datatable.querySelector(
                    'input[data-datatable-search]'
                  );
                  const icon = datatable.querySelector('.datatable-search-icon');
                  if (!input || !icon) {
                    return null;
                  }
                  const iconStyle = getComputedStyle(icon);
                  const inputStyle = getComputedStyle(input);
                  return {
                    iconZIndex: iconStyle.zIndex,
                    inputZIndex: inputStyle.zIndex,
                    iconOpacity: iconStyle.opacity,
                    iconVisibility: iconStyle.visibility,
                  };
                }
                """
            )

            self.assertIsNotNone(layering)
            self.assertGreater(
                int(layering["iconZIndex"]),
                int(layering["inputZIndex"]),
                layering,
            )
            self.assertEqual(layering["iconOpacity"], "1", layering)
            self.assertEqual(layering["iconVisibility"], "visible", layering)
            expect(icon).to_be_visible()
            evidence.assert_clean()
        finally:
            context.close()

    def test_selected_row_action_cell_matches_selected_row_surface(self) -> None:
        context, page, evidence = self.open_preview()
        try:
            root = page.locator(f"#{TABLE_ID}")
            row = root.locator("tbody > tr[data-datatable-row]").first
            row.locator("[data-datatable-select-row]").check()

            surfaces = root.evaluate(
                """
                (datatable) => {
                  const row = datatable.querySelector(
                    'tbody > tr[data-datatable-row].datatable-row-selected'
                  );
                  const action = row?.querySelector(
                    '[data-datatable-column="actions"]'
                  );
                  const regularCell = row?.querySelector(
                    'td:not([data-datatable-column="actions"])'
                  );
                  if (!row || !action || !regularCell) {
                    return null;
                  }
                  const actionStyle = getComputedStyle(action);
                  const regularCellStyle = getComputedStyle(regularCell);
                  const normalizeColor = (color) => {
                    const swatch = document.createElement("span");
                    swatch.style.backgroundColor = color;
                    document.body.append(swatch);
                    const normalized = getComputedStyle(swatch).backgroundColor;
                    swatch.remove();
                    return normalized;
                  };
                  return {
                    actionSurface: normalizeColor(
                      actionStyle.getPropertyValue(
                        "--moo-datatable-actions-cell-bg"
                      ).trim()
                    ),
                    regularSurface: normalizeColor(regularCellStyle.backgroundColor),
                    actionBackgroundImage: actionStyle.backgroundImage,
                  };
                }
                """
            )

            self.assertIsNotNone(surfaces)
            self.assertEqual(surfaces["actionSurface"], surfaces["regularSurface"])
            self.assertEqual(surfaces["actionBackgroundImage"], "none")
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
            menu = page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()

            result = page.evaluate(
                """
                () => {
                  const menu = document.querySelector(".moo-ui[data-bs-theme] > .dropdown-menu.show");
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
                    menuParentIsOwner: menu?.parentElement?.matches(".moo-ui[data-bs-theme]"),
                    menuExtendsPastCard: rect(menu).bottom > rect(card).bottom,
                    allItemsHit,
                  };
                }
                """
            )

            self.assertTrue(result["menuParentIsOwner"])
            self.assertTrue(result["menuExtendsPastCard"])
            self.assertTrue(result["allItemsHit"])
            action.press("Escape")
            expect(action).to_have_attribute("aria-expanded", "false")
            expect(page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")).to_have_count(0)
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
            menu = page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()
            expect(menu).to_contain_text("Open ticket")
            self.assertTrue(menu.evaluate("element => element.parentElement.matches('.moo-ui[data-bs-theme]')"))

            trigger.press("Escape")
            expect(trigger).to_have_attribute("aria-expanded", "false")
            expect(page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")).to_have_count(0)
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
            menu = page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")

            expect(trigger).to_have_attribute("aria-expanded", "false")
            trigger.click()
            expect(trigger).to_have_attribute("aria-expanded", "true")
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()
            expect(menu).to_contain_text("Open ticket")
            expect(menu).to_contain_text("Assign owner")
            expect(menu).to_contain_text("Copy link")
            self.assertTrue(menu.evaluate("element => element.parentElement.matches('.moo-ui[data-bs-theme]')"))
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
            expect(page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")).to_have_count(0)
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
            page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show").locator(
                '[data-datatable-sort-action="desc"]'
            ).click()

            expect(ticket_header).to_have_attribute("aria-sort", "descending")
            expect(rows).to_have_count(3)
            expect(rows.nth(0)).to_contain_text("TCK-3")
            expect(rows.nth(2)).to_contain_text("TCK-1")

            ticket_trigger.click()
            page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show").locator(
                '[data-datatable-sort-action="asc"]'
            ).click()

            expect(ticket_header).to_have_attribute("aria-sort", "ascending")
            expect(rows.nth(0)).to_contain_text("TCK-1")
            expect(rows.nth(2)).to_contain_text("TCK-3")

            status_header = root.locator('th[data-datatable-column="status"]')
            status_trigger = status_header.locator("[data-datatable-sort-key]")
            status_trigger.click()
            page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show").locator(
                '[data-datatable-sort-action="hide"]'
            ).click()
            self.assertTrue(
                status_header.evaluate(
                    "element => element.classList.contains('datatable-col-hidden')"
                )
            )

            subject_header = root.locator('th[data-datatable-column="subject"]')
            expect(subject_header).to_have_attribute("aria-sort", "none")
            evidence.assert_clean()
        finally:
            context.close()

    def test_certification_fixture_sort_menu_escapes_table_frame(self) -> None:
        context, page, evidence = self.open_certification_fixture()
        try:
            root = page.locator("#certification-datatable")
            ticket_header = root.locator('th[data-datatable-column="ticket"]')
            ticket_trigger = ticket_header.locator("[data-datatable-sort-key]")
            menu = page.locator(".moo-ui[data-bs-theme] > .dropdown-menu.show")
            frame = root.locator(".datatable-frame")

            # Keep the real overflow boundary, but make the fixture frame
            # short enough for the sort menu to cross it deterministically.
            frame.evaluate(
                "element => { element.style.height = '4rem'; element.style.minHeight = '0'; }"
            )

            ticket_trigger.click()
            expect(menu).to_have_count(1)
            expect(menu).to_be_visible()

            metrics = page.evaluate(
                """
                () => {
                  const menu = document.querySelector(".moo-ui[data-bs-theme] > .dropdown-menu.show");
                  const frame = document.querySelector("#certification-datatable .datatable-frame");
                  const rect = (element) => {
                    const box = element.getBoundingClientRect();
                    return {
                      top: box.top,
                      right: box.right,
                      bottom: box.bottom,
                      left: box.left,
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
                    menuParentIsOwner: menu?.parentElement?.matches(".moo-ui[data-bs-theme]"),
                    menuPosition: menu ? getComputedStyle(menu).position : "",
                    menuExtendsPastFrame:
                      menu && frame
                        ? rect(menu).bottom > rect(frame).bottom
                        : false,
                    allItemsHit,
                    frameOverflow: frame
                      ? getComputedStyle(frame).overflow
                      : "",
                  };
                }
                """
            )

            self.assertTrue(metrics["menuParentIsOwner"], metrics)
            self.assertEqual(metrics["menuPosition"], "fixed", metrics)
            self.assertTrue(metrics["menuExtendsPastFrame"], metrics)
            self.assertTrue(metrics["allItemsHit"], metrics)
            self.assertEqual(metrics["frameOverflow"], "hidden", metrics)

            ticket_trigger.press("Escape")
            expect(ticket_trigger).to_have_attribute("aria-expanded", "false")
            expect(menu).to_have_count(0)
            expect(ticket_header.locator(":scope > .dropdown .dropdown-menu")).to_have_count(1)
            expect(ticket_trigger).to_be_focused()

            ticket_trigger.click()
            expect(menu).to_be_visible()
            page.locator("html").click(position={"x": 1, "y": 1})
            expect(menu).to_have_count(0)
            expect(ticket_header.locator(":scope > .dropdown .dropdown-menu")).to_have_count(1)

            ticket_trigger.click()
            expect(menu).to_be_visible()
            page.evaluate("window.certificationDataTable.dispose()")
            expect(menu).to_have_count(0)
            expect(ticket_trigger).to_have_attribute("aria-expanded", "false")
            expect(ticket_header.locator(":scope > .dropdown .dropdown-menu")).to_have_count(1)
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
