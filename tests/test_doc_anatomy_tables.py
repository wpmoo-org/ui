from __future__ import annotations

import re
from html.parser import HTMLParser

from tests.helpers import DIST, CatalogTestCase


DOC_ANATOMY_PAGES = (
    "components/chart.html",
    "components/datatable.html",
    "components/datepicker.html",
    "components/sidebar.html",
    "components/slider.html",
)

ANATOMY_GROUPS_BY_PAGE = {
    "components/chart.html": (
        ("chart-anatomy-root", "Root", ["chart-root", "chart-id"]),
        (
            "chart-anatomy-contract",
            "Data Contract",
            ["chart-type", "chart-data", "chart-options"],
        ),
        ("chart-anatomy-render-target", "Render Target", ["chart-canvas"]),
    ),
    "components/datatable.html": (
        ("datatable-anatomy-root", "Root", ["root"]),
        (
            "datatable-anatomy-toolbar",
            "Toolbar",
            ["toolbar", "search", "facet", "responsive-toggle"],
        ),
        (
            "datatable-anatomy-table-surface",
            "Table Surface",
            ["frame", "responsive-scroll", "column", "row", "select-row", "sort-value"],
        ),
        ("datatable-anatomy-cards", "Cards", ["responsive-cards", "cards"]),
        (
            "datatable-anatomy-state-actions",
            "State & Actions",
            ["empty", "results-summary", "select-all", "bulk-actions"],
        ),
        ("datatable-anatomy-pagination", "Pagination", ["pagination"]),
    ),
    "components/datepicker.html": (
        (
            "datepicker-anatomy-roots",
            "Roots",
            ["datepicker-root", "datepicker-range-root"],
        ),
        ("datepicker-anatomy-trigger", "Trigger", ["datepicker-trigger"]),
        (
            "datepicker-anatomy-popover",
            "Popover",
            ["datepicker-popover", "datepicker-calendar"],
        ),
    ),
    "components/sidebar.html": (
        (
            "sidebar-anatomy-shell",
            "Shell",
            [
                "sidebar-wrapper-class",
                "sidebar-wrapper-slot",
                "sidebar-class",
                "sidebar-slot",
            ],
        ),
        (
            "sidebar-anatomy-controls",
            "Controls",
            ["sidebar-trigger", "sidebar-rail"],
        ),
        (
            "sidebar-anatomy-navigation",
            "Navigation",
            ["sidebar-content", "sidebar-menu-button", "sidebar-submenu"],
        ),
        ("sidebar-anatomy-content", "Content", ["sidebar-inset"]),
    ),
    "components/slider.html": (
        ("slider-anatomy-root", "Root", ["slider-root"]),
        (
            "slider-anatomy-track",
            "Track",
            ["slider-track", "slider-fill", "slider-input"],
        ),
        ("slider-anatomy-output", "Output", ["slider-output"]),
    ),
}


class AnatomyTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict[str, str | None]]] = []
        self.tables: list[dict[str, object]] = []
        self.current_table: dict[str, object] | None = None
        self.current_header: list[str] | None = None
        self.current_row_group: dict[str, object] | None = None
        self.in_thead = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self.stack.append((tag, attributes))
        if tag == "thead":
            self.in_thead += 1
        if tag == "table":
            responsive_class = ""
            for ancestor_tag, ancestor_attrs in reversed(self.stack[:-1]):
                if ancestor_tag != "div":
                    continue
                class_name = ancestor_attrs.get("class") or ""
                if "table-responsive" in class_name.split():
                    responsive_class = class_name
                    break
            self.current_table = {
                "class": attributes.get("class") or "",
                "headers": [],
                "responsive_class": responsive_class,
                "row_ids": [],
                "row_group_ids": [],
                "row_group_labels": [],
            }
        if (
            tag == "tr"
            and self.current_table is not None
            and not self.in_thead
            and attributes.get("id")
        ):
            class_name = attributes.get("class") or ""
            if "moo-table-section-row" in class_name.split():
                self.current_row_group = {"id": attributes["id"], "text": []}
            else:
                row_ids = self.current_table["row_ids"]
                assert isinstance(row_ids, list)
                row_ids.append(attributes["id"])
        if tag == "th" and self.current_table is not None and self.in_thead:
            self.current_header = []

    def handle_data(self, data: str) -> None:
        if self.current_header is not None:
            self.current_header.append(data)
        if self.current_row_group is not None:
            text = self.current_row_group["text"]
            assert isinstance(text, list)
            text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "th" and self.current_header is not None and self.current_table:
            header = " ".join("".join(self.current_header).split())
            headers = self.current_table["headers"]
            assert isinstance(headers, list)
            headers.append(header)
            self.current_header = None
        if tag == "tr" and self.current_row_group is not None and self.current_table:
            group_id = self.current_row_group["id"]
            group_text = self.current_row_group["text"]
            assert isinstance(group_id, str)
            assert isinstance(group_text, list)
            group_ids = self.current_table["row_group_ids"]
            group_labels = self.current_table["row_group_labels"]
            assert isinstance(group_ids, list)
            assert isinstance(group_labels, list)
            group_ids.append(group_id)
            group_labels.append(" ".join("".join(group_text).split()))
            self.current_row_group = None
        if tag == "table" and self.current_table is not None:
            self.tables.append(self.current_table)
            self.current_table = None
        if tag == "thead":
            self.in_thead -= 1
        if self.stack:
            self.stack.pop()


class DocAnatomyTableTests(CatalogTestCase):
    def selector_purpose_tables(self, page: str) -> list[dict[str, object]]:
        parser = AnatomyTableParser()
        parser.feed(self.read_output(page))
        return [
            table
            for table in parser.tables
            if table["headers"] == ["Selector", "Purpose"]
        ]

    def test_selector_purpose_anatomy_tables_use_scroll_fade_viewports(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for page in DOC_ANATOMY_PAGES:
            with self.subTest(page=page):
                tables = self.selector_purpose_tables(page)
                self.assertEqual(len(tables), 1)
                [table] = tables
                table_class = str(table["class"]).split()
                responsive_class = str(table["responsive_class"]).split()
                self.assertIn("moo-doc-anatomy-table", table_class)
                self.assertIn("moo-doc-anatomy-table--grouped", table_class)
                self.assertIn("scroll-fade-x", responsive_class)
                self.assertIn("no-scrollbar", responsive_class)

    def test_anatomy_tables_group_hooks_by_role(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for page, groups in ANATOMY_GROUPS_BY_PAGE.items():
            with self.subTest(page=page):
                tables = self.selector_purpose_tables(page)
                self.assertEqual(len(tables), 1)
                [table] = tables
                self.assertEqual(
                    table["row_group_ids"],
                    [group_id for group_id, _label, _row_ids in groups],
                )
                self.assertEqual(
                    table["row_group_labels"],
                    [label for _group_id, label, _row_ids in groups],
                )
                expected_row_ids = [
                    row_id
                    for _group_id, _label, row_ids in groups
                    for row_id in row_ids
                ]
                self.assertEqual(table["row_ids"], expected_row_ids)

    def test_selector_purpose_anatomy_tables_size_selector_column_to_content(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/catalog.css").read_text(encoding="utf-8")
        selector_rule = re.search(
            r"(?:^|\n)\.moo-doc-anatomy-table "
            r":is\(th,\s*td\):first-child(?:,\s*[^{}]+)?\s*\{(?P<body>[^}]+)\}",
            css,
        )
        self.assertIsNotNone(selector_rule)
        assert selector_rule is not None
        rule_body = selector_rule.group("body")
        self.assertRegex(rule_body, r"width:\s*1%;")
        self.assertRegex(rule_body, r"padding-inline-end:\s*1\.25rem;")
        self.assertRegex(rule_body, r"white-space:\s*nowrap;")
        self.assertNotRegex(rule_body, r"(?:width|min-width):\s*22rem;")

    def test_long_compound_selectors_can_render_as_meaningful_parts(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/slider.html")
        row_start = page.index('id="slider-input"')
        row = page[row_start : page.index("</tr>", row_start)]

        self.assertIn('class="moo-doc-selector-stack"', row)
        self.assertIn('<code>input[type="range"]</code>', row)
        self.assertIn("<code>.form-range</code>", row)
        self.assertIn("<code>[data-slider-input]</code>", row)
        self.assertNotIn('input[type="range"].form-range[data-slider-input]', row)

    def test_sidebar_shell_anatomy_documents_class_and_slot_hooks_separately(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/sidebar.html")

        expected_selectors = {
            "sidebar-wrapper-class": "<code>.sidebar-wrapper</code>",
            "sidebar-wrapper-slot": '<code>[data-slot="sidebar-wrapper"]</code>',
            "sidebar-class": "<code>.sidebar</code>",
            "sidebar-slot": '<code>[data-slot="sidebar"]</code>',
        }
        for row_id, selector in expected_selectors.items():
            with self.subTest(row=row_id):
                row_marker = f'id="{row_id}"'
                row_start = page.find(row_marker)
                self.assertNotEqual(-1, row_start, f"Missing row {row_id}")
                row = page[row_start : page.index("</tr>", row_start)]
                self.assertIn(selector, row)
                self.assertNotIn(".sidebar-wrapper[data-slot", row)
                self.assertNotIn(".sidebar[data-slot", row)
