from __future__ import annotations

import subprocess
import sys
import unittest
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from tests.helpers import ROOT, SITE_DIST


VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
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
}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    parent: "Element | None" = None
    children: list["Element"] = field(default_factory=list)


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, {name: value or "" for name, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def elements(node: Element) -> list[Element]:
    result = [node]
    for child in node.children:
        result.extend(elements(child))
    return result


def has_class(node: Element, class_name: str) -> bool:
    return class_name in node.attrs.get("class", "").split()


def is_resolved_owner(node: Element) -> bool:
    return (
        has_class(node, "moo-ui")
        and node.attrs.get("data-bs-theme") in {"light", "dark"}
    )


class DocumentRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise AssertionError(result.stderr)

    def parse_page(self, relative_path: str) -> tuple[str, Element]:
        source = (SITE_DIST / relative_path).read_text(encoding="utf-8")
        parser = DocumentParser()
        parser.feed(source)
        return source, parser.root

    def parse_source(self, relative_path: str) -> tuple[str, Element]:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        parser = DocumentParser()
        parser.feed(source)
        return source, parser.root

    def assert_document_owner(self, source: str, root: Element) -> tuple[Element, Element]:
        nodes = elements(root)
        html = next(node for node in nodes if node.tag == "html")
        body = next(node for node in nodes if node.tag == "body")

        self.assertEqual(html.attrs.get("lang"), "en")
        self.assertEqual(html.attrs.get("dir"), "ltr")
        self.assertNotIn("data-bs-theme", html.attrs)
        self.assertNotIn("data-bs-theme", body.attrs)

        owners = [node for node in body.children if is_resolved_owner(node)]
        self.assertEqual(len(owners), 1)
        owner = owners[0]
        self.assertIs(body.children[0], owner)
        self.assertNotIn("dir", owner.attrs)
        self.assertTrue(owner.children)

        state_script = owner.children[0]
        self.assertEqual(state_script.tag, "script")
        self.assertNotIn("src", state_script.attrs)
        self.assertNotIn("defer", state_script.attrs)
        self.assertIn(
            "const owner = ownerDocument?.currentScript?.parentElement",
            source,
        )

        skip_links = [
            node
            for node in elements(owner)
            if node.tag == "a" and node.attrs.get("href") == "#main-content"
        ]
        self.assertEqual(len(skip_links), 1)

        runtime_scripts = [
            node
            for node in body.children
            if node.tag == "script"
            and (
                "assets/js/bootstrap.bundle.min.js?" in node.attrs.get("src", "")
                or "assets/js/catalog/index.js?" in node.attrs.get("src", "")
            )
        ]
        self.assertEqual(len(runtime_scripts), 2)
        self.assertEqual(body.children[-2:], runtime_scripts)
        self.assertLess(source.index("</div>"), source.index(runtime_scripts[0].attrs["src"]))
        return body, owner

    def test_catalog_document_places_owner_and_sidebar_state_at_owner_starts(self) -> None:
        source, root = self.parse_page("introduction/index.html")
        body, owner = self.assert_document_owner(source, root)

        canonical = (ROOT / "src/js/state.js").read_text(encoding="utf-8")
        owner_start = source.index('data-moo-document-owner="true"')
        owner_script = source.index("<script>", owner_start)
        owner_end = source.index("</script>", owner_script)
        self.assertEqual(source[owner_script + len("<script>") : owner_end], canonical)

        wrapper = next(
            node for node in elements(owner)
            if node.attrs.get("data-sidebar-key") == "catalog-shell"
        )
        self.assertEqual(wrapper.children[0].tag, "script")
        self.assertNotIn("src", wrapper.children[0].attrs)
        wrapper_start = source.index('data-sidebar-key="catalog-shell"')
        wrapper_script = source.index("<script>", wrapper_start)
        wrapper_end = source.index("</script>", wrapper_script)
        self.assertEqual(source[wrapper_script + len("<script>") : wrapper_end], canonical)
        self.assertLess(wrapper_end, source.index('id="catalog-sidebar"'))

        catalog = next(node for node in elements(owner) if has_class(node, "moo-catalog"))
        catalog_state = next(
            node
            for node in elements(owner)
            if node.tag == "script"
            and "assets/js/catalog-state.js?" in node.attrs.get("src", "")
        )
        self.assertIs(catalog_state.parent, owner)
        self.assertLess(owner.children.index(catalog), owner.children.index(catalog_state))
        self.assertLess(source.index('id="catalog-settings"'), source.index(catalog_state.attrs["src"]))
        self.assertLess(source.index(catalog_state.attrs["src"]), source.index('assets/js/bootstrap.bundle.min.js?'))
        self.assertIs(body.children[0], owner)

    def test_direct_base_page_uses_the_same_single_document_owner(self) -> None:
        source, root = self.parse_page("acceptance/rc2/index.html")
        _body, owner = self.assert_document_owner(source, root)
        self.assertNotIn("moo-catalog", owner.attrs.get("class", ""))

    def test_block_preview_does_not_create_a_nested_resolved_owner(self) -> None:
        source, root = self.parse_page("blocks/previews/sidebar-floating/index.html")
        _body, owner = self.assert_document_owner(source, root)

        owners = [node for node in elements(owner) if is_resolved_owner(node)]
        self.assertEqual(owners, [owner])
        preview_main = next(
            node
            for node in elements(owner)
            if node.tag == "main" and has_class(node, "moo-block-standalone")
        )
        self.assertFalse(has_class(preview_main, "moo-ui"))

    def test_raw_certification_fixture_uses_a_body_first_resolved_owner(self) -> None:
        fixture_directory = ROOT / "tests/fixtures/certification"
        fixture_paths = sorted(fixture_directory.glob("*.html*"))
        self.assertTrue(fixture_paths)

        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.name):
                _source, root = self.parse_source(str(fixture_path.relative_to(ROOT)))
                nodes = elements(root)
                html = next(node for node in nodes if node.tag == "html")
                body = next(node for node in nodes if node.tag == "body")

                self.assertNotIn("data-bs-theme", html.attrs)
                self.assertNotIn("data-bs-theme", body.attrs)
                owners = [node for node in body.children if is_resolved_owner(node)]
                self.assertEqual(len(owners), 1)
                self.assertIs(body.children[0], owners[0])

    def test_conformance_fixture_keeps_host_content_outside_its_embedded_owner(self) -> None:
        fixture_directory = ROOT / "conformance/fixtures"
        fixture_paths = sorted(fixture_directory.glob("*.html"))
        self.assertTrue(fixture_paths)

        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.name):
                _source, root = self.parse_source(str(fixture_path.relative_to(ROOT)))
                nodes = elements(root)
                html = next(node for node in nodes if node.tag == "html")
                body = next(node for node in nodes if node.tag == "body")
                if fixture_path.name == "document-owner-state.html":
                    owners = [node for node in body.children if is_resolved_owner(node)]
                    self.assertEqual(len(owners), 1)
                    self.assertIs(body.children[0], owners[0])
                    host = next(
                        node for node in nodes if "data-conformance-host" in node.attrs
                    )
                    self.assertIs(host.parent, body)
                    self.assertGreater(
                        body.children.index(host), body.children.index(owners[0])
                    )
                    continue
                host = next(
                    node for node in nodes if "data-conformance-host" in node.attrs
                )

                self.assertNotIn("data-bs-theme", html.attrs)
                self.assertNotIn("data-bs-theme", body.attrs)
                owners = [node for node in body.children if is_resolved_owner(node)]
                self.assertEqual(len(owners), 1)
                self.assertIs(host.parent, body)
                self.assertIs(owners[0].parent, body)
                self.assertLess(body.children.index(host), body.children.index(owners[0]))
