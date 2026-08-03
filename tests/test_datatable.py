from __future__ import annotations

import re
from html.parser import HTMLParser

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/datatable.html.jinja"
RELEASE_REVIEW_BLOCK = ROOT / "site/src/blocks/datatable_release_review.html.jinja"
DOCUMENTATION_PAGE = ROOT / "site/src/pages/components/datatable.html.jinja"
CERTIFICATION_FIXTURE = ROOT / "tests/fixtures/certification/datatable.html"
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
