from __future__ import annotations

import json

from tests.helpers import ROOT, CatalogTestCase


class BlocksTests(CatalogTestCase):
    def test_blocks_json_entries_are_ready(self) -> None:
        blocks = json.loads(
            (ROOT / "src/blocks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            blocks,
            [
                {
                    "slug": "sidebar-floating",
                    "label": "Sidebar (Floating)",
                    "status": "ready",
                },
                {
                    "slug": "sidebar-inset",
                    "label": "Sidebar (Inset)",
                    "status": "ready",
                },
            ],
        )

    def test_block_pages_build_and_compose_through_render_block_example(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        for slug, variant in (
            ("sidebar-floating", "floating"),
            ("sidebar-inset", "inset"),
        ):
            page = self.read_output(f"blocks/{slug}.html")
            with self.subTest(slug=slug):
                self.assertIn('data-moo-shell="catalog"', page)
                self.assertIn(f'data-example="{slug}"', page)
                self.assertIn("moo-example__surface", page)
                self.assertIn(f'data-variant="{variant}"', page)

            source = (
                ROOT / f"src/pages/blocks/{slug}.html.jinja"
            ).read_text(encoding="utf-8")
            with self.subTest(slug=slug, contract="block-example macro"):
                self.assertIn(
                    '{% from "includes/block-example.html.jinja" '
                    "import render_block_example %}",
                    source,
                )
                self.assertIn("render_block_example(", source)

    def test_blocks_index_page_lists_both_blocks(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("blocks/index.html")

        self.assertIn('data-moo-shell="catalog"', index)
        for slug, label in (
            ("sidebar-floating", "Sidebar (Floating)"),
            ("sidebar-inset", "Sidebar (Inset)"),
        ):
            with self.subTest(slug=slug):
                self.assertIn(f'href="../blocks/{slug}.html"', index)
                self.assertIn(label, index)
        # Blocks cards mirror the Components index showcase-card layout: a
        # preview image (falling back to the shared placeholder until real
        # block art exists) with the whole card as a stretched-link.
        self.assertRegex(index, r'class="[^"]*\bmoo-catalog__showcase-card\b')
        self.assertEqual(
            index.count("moo-catalog__showcase-preview"), 2
        )
        self.assertIn('src="../assets/images/placeholder.webp"', index)
        self.assertRegex(index, r'class="[^"]*\bstretched-link\b')

    def test_navbar_and_command_palette_list_both_blocks_by_name(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        self.assertIn('href="blocks/index.html"', home)
        for slug, label in (
            ("sidebar-floating", "Sidebar (Floating)"),
            ("sidebar-inset", "Sidebar (Inset)"),
        ):
            with self.subTest(slug=slug):
                self.assertIn(f'href="blocks/{slug}.html"', home)
                self.assertIn(label, home)

    def test_catalog_sidebar_links_to_the_blocks_index_only(self) -> None:
        # The left catalog sidebar must not enumerate every block by name;
        # only the command palette does. Reading a page unrelated to either
        # block's own content (the Components index) isolates the shared
        # shell: one occurrence of each block name should come from the
        # command-palette loop only, and "blocks/index.html" should appear
        # exactly three times: the header nav Blocks link, the sidebar's
        # single Blocks link, and the palette's hardcoded Blocks entry.
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/index.html")

        self.assertEqual(page.count("Sidebar (Floating)"), 1)
        self.assertEqual(page.count("Sidebar (Inset)"), 1)
        self.assertEqual(page.count('href="../blocks/index.html"'), 3)
