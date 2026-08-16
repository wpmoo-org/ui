from __future__ import annotations

import re
from html.parser import HTMLParser

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/datatable.html.jinja"
RELEASE_REVIEW_BLOCK = ROOT / "site/src/blocks/datatable_release_review.html.jinja"
DOCUMENTATION_PAGE = ROOT / "site/src/pages/components/datatable.html.jinja"
CERTIFICATION_FIXTURE = ROOT / "tests/fixtures/certification/datatable.html"
DATATABLE_JS = ROOT / "src/js/components/datatable.js"
DATATABLE_SCSS = ROOT / "scss/components/_datatable.scss"
TABLE_SCSS = ROOT / "scss/components/_table.scss"
MACHINE_PATH_ROOTS = (
    ROOT / "src",
    ROOT / "site/src",
    ROOT / "tests/fixtures",
)


class _Node:
    def __init__(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag = tag
        self.attrs = dict(attrs)
        self.children: list[_Node] = []
        self.text = ""

    def find_all(
        self,
        *,
        tag: str | None = None,
        class_name: str | None = None,
        attrs: set[str] | None = None,
    ) -> list[_Node]:
        matches: list[_Node] = []
        for child in self.children:
            classes = set((child.attrs.get("class") or "").split())
            if (tag is None or child.tag == tag) and (
                class_name is None or class_name in classes
            ) and (attrs is None or attrs <= child.attrs.keys()):
                matches.append(child)
            matches.extend(child.find_all(tag=tag, class_name=class_name, attrs=attrs))
        return matches

    def find_one(
        self,
        *,
        tag: str | None = None,
        class_name: str | None = None,
        attrs: set[str] | None = None,
    ) -> _Node | None:
        return next(
            iter(self.find_all(tag=tag, class_name=class_name, attrs=attrs)),
            None,
        )

    def text_content(self) -> str:
        return self.text + "".join(child.text_content() for child in self.children)


class _HtmlTreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", [])
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, attrs)
        self._stack[-1].children.append(node)
        if tag not in {
            "area",
            "base",
            "br",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].text += data


def _parse_html(source: str) -> _Node:
    parser = _HtmlTreeParser()
    parser.feed(source)
    parser.close()
    return parser.root


class DataTableTests(CatalogTestCase):
    def render_release_review(self, responsive_mode: str = "toggle") -> str:
        self.assertTrue(COMPONENT.is_file(), "Data Table macro is not implemented")
        self.assertTrue(
            RELEASE_REVIEW_BLOCK.is_file(),
            "Release review block is not implemented",
        )
        template = create_environment().from_string(
            '{% from "blocks/datatable_release_review.html.jinja" import render_release_review_table %}'
            f'{{{{ render_release_review_table('
            f'id="test-datatable", responsive_mode="{responsive_mode}") }}}}'
        )
        return template.render()

    def test_datatable_namespace_has_no_legacy_machine_identifiers(self) -> None:
        paths = (
            COMPONENT,
            RELEASE_REVIEW_BLOCK,
            DOCUMENTATION_PAGE,
            CERTIFICATION_FIXTURE,
        )
        legacy_tokens = ("data-table", "data_table")

        for root in MACHINE_PATH_ROOTS:
            for path in root.rglob("*"):
                with self.subTest(path=path):
                    path_text = path.relative_to(ROOT).as_posix().lower()
                    self.assertFalse(
                        any(token in path_text for token in legacy_tokens)
                    )

        for path in paths:
            self.assertFalse(
                any(token in path.name.lower() for token in legacy_tokens),
                path,
            )
            source = path.read_text(encoding="utf-8").lower()
            for token in legacy_tokens:
                with self.subTest(path=path, token=token):
                    self.assertNotIn(token, source)

    def test_public_docs_do_not_expose_template_parameters(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/datatable/index.html")
        for forbidden in (
            "responsive_mode=",
            "card_role=",
            "hideable=false",
        ):
            with self.subTest(forbidden=forbidden):
                if forbidden in page:
                    raise AssertionError(
                        f"Data Table public docs expose template parameter: {forbidden}"
                    )

    def test_release_review_visibility_menu_keeps_identity_columns_fixed(self) -> None:
        output = self.render_release_review()

        self.assertEqual(
            re.findall(r'data-datatable-column-toggle="([^"]+)"', output),
            ["status", "priority", "area"],
        )

    def test_release_review_toggle_and_card_selection_use_shared_frame_controls(
        self,
    ) -> None:
        tree = _parse_html(self.render_release_review())
        root = tree.find_one(class_name="datatable")
        self.assertIsNotNone(root)
        assert root is not None

        toolbar = root.find_one(class_name="datatable-toolbar")
        self.assertIsNotNone(toolbar)
        assert toolbar is not None
        self.assertEqual(len(toolbar.find_all(class_name="datatable-view-toggle")), 1)
        self.assertEqual(len(root.find_all(class_name="datatable-view-toggle")), 1)

        card_frame = root.find_one(class_name="datatable-card-frame")
        self.assertIsNotNone(card_frame)
        assert card_frame is not None
        self.assertEqual(len(card_frame.find_all(class_name="datatable-frame-header")), 1)
        card_headers = card_frame.find_all(class_name="datatable-card-header")
        self.assertTrue(card_headers)
        self.assertEqual(card_frame.find_all(tag="th"), [])
        self.assertEqual(card_frame.find_all(tag="thead"), [])
        for header in card_headers:
            self.assertEqual(
                header.find_all(attrs={"data-datatable-select-all"}),
                [],
            )
        shared_header = card_frame.find_one(class_name="datatable-frame-header")
        self.assertIsNotNone(shared_header)
        assert shared_header is not None
        select_all_inputs = shared_header.find_all(
            tag="input", attrs={"data-datatable-select-all"}
        )
        self.assertEqual(len(select_all_inputs), 1)
        self.assertEqual(
            len(card_frame.find_all(tag="input", attrs={"data-datatable-select-all"})),
            1,
        )

    def test_release_review_empty_state_exposes_clear_filters_hook(self) -> None:
        tree = _parse_html(self.render_release_review())
        root = tree.find_one(class_name="datatable")
        self.assertIsNotNone(root)
        assert root is not None

        empty = root.find_one(class_name="datatable-empty")
        self.assertIsNotNone(empty)
        assert empty is not None
        self.assertIn("data-datatable-empty", empty.attrs)
        self.assertIn("hidden", empty.attrs)
        reset = empty.find_one(tag="button")
        self.assertIsNotNone(reset)
        assert reset is not None
        self.assertIn("data-datatable-empty-reset", reset.attrs)
        self.assertIn("Clear filters", reset.text_content())

        # JS owns the runtime hidden state of both frames; this test only locks
        # the static hooks that JS needs to control table/card visibility.
        self.assertIsNotNone(root.find_one(class_name="datatable-frame"))
        self.assertIsNotNone(root.find_one(class_name="datatable-card-frame"))

    def test_bulk_clear_tooltip_uses_sanitizer_safe_kbd_markup(self) -> None:
        tree = _parse_html(self.render_release_review())
        clear_button = tree.find_one(
            tag="button", attrs={"data-datatable-bulk-clear"}
        )
        self.assertIsNotNone(clear_button)
        assert clear_button is not None

        self.assertIn(
            "Clear selection <kbd>Escape</kbd>",
            clear_button.attrs.get("data-bs-title"),
        )
        self.assertEqual(clear_button.attrs.get("data-bs-html"), "true")
        self.assertEqual(clear_button.attrs.get("aria-label"), "Clear selection")

    def test_certification_fixture_exposes_empty_state_hook(self) -> None:
        tree = _parse_html(CERTIFICATION_FIXTURE.read_text(encoding="utf-8"))
        root = tree.find_one(class_name="datatable")
        self.assertIsNotNone(root)
        assert root is not None

        empty = root.find_one(class_name="datatable-empty")
        self.assertIsNotNone(empty)
        assert empty is not None
        self.assertIn("data-datatable-empty", empty.attrs)
        self.assertIn("hidden", empty.attrs)
        self.assertIsNotNone(
            empty.find_one(tag="button", attrs={"data-datatable-empty-reset"})
        )
        self.assertIsNotNone(root.find_one(class_name="datatable-frame"))
        self.assertIsNotNone(root.find_one(class_name="datatable-card-frame"))

    def test_certification_fixture_exposes_search_filter_picker(self) -> None:
        tree = _parse_html(CERTIFICATION_FIXTURE.read_text(encoding="utf-8"))
        root = tree.find_one(class_name="datatable")
        self.assertIsNotNone(root)
        assert root is not None

        search_filter = root.find_one(class_name="datatable-search-filter")
        self.assertIsNotNone(search_filter)
        assert search_filter is not None
        self.assertIsNotNone(search_filter.find_one(class_name="datatable-searchbar"))
        self.assertIsNotNone(
            search_filter.find_one(tag="input", attrs={"data-datatable-search"})
        )
        self.assertIsNotNone(
            search_filter.find_one(
                tag="button", attrs={"data-datatable-filter-menu-trigger"}
            )
        )

        picker = search_filter.find_one(class_name="datatable-search-filter-menu")
        self.assertIsNotNone(picker)
        assert picker is not None
        self.assertIn("Filter by", picker.text_content())
        status_group = picker.find_one(
            tag="button", attrs={"data-datatable-filter-group"}
        )
        self.assertIsNotNone(status_group)
        assert status_group is not None
        self.assertEqual(status_group.attrs.get("data-datatable-filter-group"), "status")
        self.assertIsNotNone(
            picker.find_one(
                tag="span", attrs={"data-datatable-filter-group-summary"}
            )
        )

        status_options = [
            option
            for option in picker.find_all(
                tag="button", attrs={"data-datatable-filter-option"}
            )
            if option.attrs.get("data-datatable-filter-option-key") == "status"
        ]
        self.assertEqual(
            [option.attrs.get("data-datatable-filter-option") for option in status_options],
            ["open", "resolved"],
        )
        self.assertEqual(
            picker.find_all(tag="button", attrs={"data-datatable-filter-clear"}),
            [],
        )
        toolbar_filters = root.find_one(class_name="datatable-toolbar-filters")
        self.assertIsNotNone(toolbar_filters)
        assert toolbar_filters is not None
        status_facet = next(
            (
                facet
                for facet in toolbar_filters.find_all(class_name="datatable-facet")
                if facet.attrs.get("data-datatable-facet") == "status"
            ),
            None,
        )
        self.assertIsNotNone(status_facet)
        assert status_facet is not None
        self.assertIn("hidden", status_facet.attrs)
        self.assertIsNotNone(
            status_facet.find_one(attrs={"data-datatable-facet-summary"})
        )
        self.assertEqual(
            [
                option.attrs.get("data-datatable-facet-option")
                for option in status_facet.find_all(
                    tag="button", attrs={"data-datatable-facet-option"}
                )
            ],
            ["open", "resolved"],
        )
        self.assertIsNotNone(
            toolbar_filters.find_one(tag="button", attrs={"data-datatable-reset"})
        )

    def test_certification_fixture_exposes_table_and_card_views(self) -> None:
        tree = _parse_html(CERTIFICATION_FIXTURE.read_text(encoding="utf-8"))
        root = tree.find_one(class_name="datatable")
        self.assertIsNotNone(root)
        assert root is not None

        toolbar = root.find_one(class_name="datatable-toolbar")
        self.assertIsNotNone(toolbar)
        assert toolbar is not None
        self.assertEqual(len(toolbar.find_all(class_name="datatable-view-toggle")), 1)
        self.assertEqual(len(root.find_all(class_name="datatable-view-toggle")), 1)

        card_frame = root.find_one(class_name="datatable-card-frame")
        self.assertIsNotNone(card_frame)
        assert card_frame is not None
        self.assertEqual(card_frame.find_all(tag="th"), [])
        self.assertEqual(card_frame.find_all(tag="thead"), [])
        self.assertIsNotNone(card_frame.find_one(class_name="datatable-frame-header"))
        self.assertEqual(
            len(card_frame.find_all(tag="input", attrs={"data-datatable-select-all"})),
            1,
        )

        cards = card_frame.find_all(attrs={"data-datatable-card"})
        self.assertEqual(len(cards), 3)
        self.assertEqual(
            [card.attrs.get("data-datatable-card-for") for card in cards],
            ["cert-row-1", "cert-row-2", "cert-row-3"],
        )
        self.assertIn("Login redirect loops", cards[0].text_content())
        self.assertIn("TCK-1", cards[0].text_content())
        self.assertIsNotNone(cards[0].find_one(class_name="table-row-actions"))

    def test_certification_fixture_exposes_row_action_menu(self) -> None:
        tree = _parse_html(CERTIFICATION_FIXTURE.read_text(encoding="utf-8"))
        root = tree.find_one(class_name="datatable")
        self.assertIsNotNone(root)
        assert root is not None

        action_headers = [
            header
            for header in root.find_all(tag="th", attrs={"data-datatable-column"})
            if header.attrs.get("data-datatable-column") == "actions"
        ]
        self.assertEqual(len(action_headers), 1)
        action_header = action_headers[0]
        self.assertNotIn("Actions", action_header.text)
        action_header_labels = action_header.find_all(
            tag="span", class_name="visually-hidden"
        )
        self.assertEqual(
            [label.text_content().strip() for label in action_header_labels],
            ["Row actions"],
        )

        actions = root.find_all(class_name="table-row-actions")
        self.assertGreaterEqual(len(actions), 1)
        first_action = actions[0]
        trigger = first_action.find_one(tag="button", attrs={"data-bs-toggle"})
        self.assertIsNotNone(trigger)
        assert trigger is not None
        self.assertEqual(trigger.attrs.get("data-bs-toggle"), "dropdown")
        self.assertEqual(trigger.attrs.get("aria-label"), "Open ticket actions")
        self.assertIsNotNone(first_action.find_one(class_name="dropdown-menu"))
        self.assertIn("Open ticket", first_action.text_content())
        self.assertIn("Assign owner", first_action.text_content())
        self.assertIn("Copy link", first_action.text_content())

    def test_row_action_dropdowns_flip_inside_preview_viewports(self) -> None:
        source = DATATABLE_JS.read_text(encoding="utf-8")

        self.assertIn('strategy: "fixed"', source)
        self.assertIn('fallbackPlacements: ["top-end", "top-start", "bottom-end", "bottom-start"]', source)
        self.assertIn('boundary: "viewport"', source)
        self.assertIn("padding: 8", source)

    def test_row_action_dropdowns_escape_scroll_frame_without_changing_frame_overflow(self) -> None:
        source = DATATABLE_JS.read_text(encoding="utf-8")
        browser_source = (ROOT / "tests" / "test_datatable_browser.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("this._reparentedRowMenus = new Map();", source)
        self.assertIn("this._reparentedRowMenuByTrigger = new WeakMap();", source)
        self.assertIn('trigger?.closest?.(".table-row-actions")', source)
        self.assertIn("this._reparentedRowMenuByTrigger.set(trigger, menu);", source)
        self.assertIn("this._reparentedRowMenuByTrigger.get(trigger)", source)
        self.assertIn("this._reparentedRowMenuByTrigger.delete(trigger);", source)
        self.assertIn("this._document.body.appendChild(menu);", source)
        self.assertIn("this._restoreRowActionMenuForTrigger(event.target);", source)
        self.assertIn("this._restoreRowActionMenus();", source)
        self.assertIn('page.locator("body > .dropdown-menu.show")', browser_source)
        self.assertNotIn(
            'root.locator(".datatable-card .dropdown-menu.show")',
            browser_source,
        )

    def test_row_action_dropdowns_export_owner_metadata_when_reparented(self) -> None:
        source = DATATABLE_JS.read_text(encoding="utf-8")

        self.assertIn("_rowActionOwnerIdForTrigger(trigger)", source)
        self.assertIn('trigger?.closest?.("tr[data-datatable-row]")?.id', source)
        self.assertIn(
            'trigger?.closest?.("[data-datatable-card]")'
            '?.getAttribute("data-datatable-card-for")',
            source,
        )
        self.assertIn(
            'menu.setAttribute("data-datatable-row-action-owner", ownerId)',
            source,
        )
        self.assertIn(
            'menu.setAttribute("data-datatable-row-action-trigger", trigger.id)',
            source,
        )
        self.assertIn(
            'menu.removeAttribute("data-datatable-row-action-owner")',
            source,
        )
        self.assertIn(
            'menu.removeAttribute("data-datatable-row-action-trigger")',
            source,
        )

    def test_card_row_action_dropdowns_share_the_fixed_popper_config(self) -> None:
        source = DATATABLE_JS.read_text(encoding="utf-8")

        self.assertIn(
            '[data-datatable-card] .table-row-actions [data-bs-toggle=\\"dropdown\\"]"',
            source,
        )
        self.assertIn("_rowActionTriggers()", source)
        # Both init and dispose must select triggers through the same shared
        # method, so table and card views can never drift out of sync again.
        self.assertEqual(
            source.count("this._rowActionTriggers()"),
            2,
        )

    def test_dispose_cleans_up_open_row_action_dropdowns(self) -> None:
        source = DATATABLE_JS.read_text(encoding="utf-8")
        dispose_body = source.split("dispose() {", 1)[1].split("\n  }\n", 1)[0]

        self.assertIn("this._disposeRowActionDropdowns();", dispose_body)
        method_body = source.split("_disposeRowActionDropdowns() {", 1)[1].split(
            "\n  }\n", 1
        )[0]
        self.assertIn("Dropdown.getInstance(trigger)", method_body)
        self.assertIn("instance.hide();", method_body)
        self.assertIn("instance.dispose();", method_body)

    def test_datatable_frame_keeps_row_menu_out_of_overflow_rules(self) -> None:
        source = DATATABLE_SCSS.read_text(encoding="utf-8")
        table_source = TABLE_SCSS.read_text(encoding="utf-8")
        card_frame_rule = source.split(".datatable-card-frame:has(.datatable-card .dropdown-menu.show)", 1)[1].split("}", 1)[0]

        self.assertNotIn(".datatable-frame:has(.table-row-actions .dropdown-menu.show)", source)
        self.assertNotIn(".datatable-frame .table-responsive:has(.table-row-actions .dropdown-menu.show)", source)
        self.assertIn('.table-responsive:not(.scroll-fade-x):has(.table-row-actions > [aria-expanded="true"])', table_source)
        self.assertNotIn('.table-responsive:has(.table-row-actions > [aria-expanded="true"])', table_source)
        self.assertIn("position: relative;", card_frame_rule)
        self.assertIn("z-index: $zindex-dropdown;", card_frame_rule)
        self.assertIn("overflow: visible;", card_frame_rule)

    def test_datatable_sticky_action_cell_uses_soft_fade_background(self) -> None:
        source = DATATABLE_SCSS.read_text(encoding="utf-8")

        self.assertIn("--moo-datatable-actions-cell-fade-width", source)
        self.assertIn(".datatable-frame [data-datatable-column=\"actions\"]", source)
        self.assertIn("linear-gradient(", source)
        self.assertIn("transparent 0", source)
        self.assertIn("var(--bs-body-bg) var(--moo-datatable-actions-cell-fade-width)", source)
        self.assertIn('[dir="rtl"] .datatable-frame [data-datatable-column="actions"]', source)

    def test_datatable_bulk_actions_bottom_offset_is_consumer_overridable(self) -> None:
        source = DATATABLE_SCSS.read_text(encoding="utf-8")

        self.assertIn("--moo-datatable-bulk-actions-bottom", source)
        self.assertIn("inset-block-end: var(--moo-datatable-bulk-actions-bottom);", source)
        self.assertNotIn("inset-block-end: 1rem;", source)

    def test_datatable_view_toggle_paints_focus_ring_on_visible_label(self) -> None:
        source = DATATABLE_SCSS.read_text(encoding="utf-8")

        self.assertIn(".datatable-view-toggle .btn-check:focus-visible + .datatable-view-option", source)
        self.assertIn("border-color: var(--moo-ring);", source)
        self.assertIn("box-shadow: 0 0 0 #{$moo-form-focus-ring-width}", source)
        self.assertIn("z-index: 3;", source)

    def test_documentation_page_contains_the_rendered_release_review_showcase(
        self,
    ) -> None:
        self.assertTrue(DOCUMENTATION_PAGE.is_file())
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        page = self.read_output("components/datatable.html")
        self.assertIn('data-example="release-review-queue"', page)
        self.assertIn('https://ui.wpmoo.org/components/datatable/', page)
        self.assertIn("datatable--responsive-toggle", page)
        self.assertIn("datatable-view-toggle", page)
        self.assertIn('data-datatable-empty', page)
