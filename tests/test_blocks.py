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
                self.assertIn("moo-block-preview__frame", page)
                self.assertIn(f'src="previews/{slug}.html"', page)
                self.assertIn(f'href="previews/{slug}.html"', page)
                self.assertIn("Open standalone", page)

            source = (
                ROOT / f"src/pages/blocks/{slug}.html.jinja"
            ).read_text(encoding="utf-8")
            with self.subTest(slug=slug, contract="block-example macro"):
                self.assertIn(
                    '{% from "blocks/sidebar_shell.html.jinja" '
                    "import render_sidebar_shell %}",
                    source,
                )
                self.assertIn(
                    '{% from "includes/block-example.html.jinja" '
                    "import render_block_example %}",
                    source,
                )
                self.assertIn("render_sidebar_shell(", source)
                self.assertIn("render_block_example(", source)

            standalone = self.read_output(f"blocks/previews/{slug}.html")
            with self.subTest(slug=slug, contract="standalone preview"):
                self.assertNotIn('data-moo-shell="catalog"', standalone)
                self.assertIn('class="moo-block-standalone moo-ui"', standalone)
                self.assertIn('data-slot="sidebar-wrapper"', standalone)
                self.assertIn(f'data-variant="{variant}"', standalone)
                self.assertNotIn("moo-example__source", standalone)

            if slug in {"sidebar-floating", "sidebar-inset"}:
                with self.subTest(slug=slug, contract="portal demo copy"):
                    self.assertIn("Moo Portal", standalone)
                    self.assertIn("Portal Operations", standalone)
                    self.assertIn("Request Review", standalone)
                    self.assertIn("Workspace", standalone)
                    self.assertIn("Approvals", standalone)
                    self.assertIn("Customers", standalone)
                    self.assertIn("Reports", standalone)
                    self.assertIn("Preferences actions", standalone)
                    self.assertIn("Open preferences", standalone)
                    self.assertIn("Copy profile link", standalone)
                    self.assertIn("Manage notifications", standalone)
                    self.assertIn("Settings", standalone)
                    self.assertIn("Get Help", standalone)
                    self.assertIn("Search", standalone)
                    self.assertIn("Upgrade workspace", standalone)
                    self.assertIn("Billing", standalone)
                    self.assertIn("Notifications", standalone)
                    self.assertIn('data-bs-offset="0,4"', standalone)
                    self.assertNotIn("Customer Spaces", standalone)
                    self.assertNotIn("Client Onboarding", standalone)
                    self.assertNotIn("Invoice Review", standalone)
                    self.assertNotIn("Partner Access", standalone)
                    self.assertNotIn("Duplicate flow", standalone)
                    self.assertEqual(standalone.count('data-slot="sidebar-menu-action"'), 1)
                    self.assertIn("moo-sidebar-demo--portal-shell", standalone)
                    self.assertIn(
                        'class="sidebar-menu-item dropend sidebar-menu-item--account"',
                        standalone,
                    )
                    self.assertIn("sidebar-menu-button--account", standalone)
                    self.assertIn("sidebar-account-menu", standalone)
                    self.assertIn("sidebar-account-menu__item", standalone)
                    self.assertIn("sidebar-account-menu__header", standalone)
                    self.assertNotIn("Building Your Application", standalone)
                    self.assertNotIn("Data Fetching", standalone)
                    self.assertNotIn("Acme Inc", standalone)
                    self.assertNotIn("Evil Corp.", standalone)
                    self.assertIn(
                        "sidebar-inset__content d-flex flex-column gap-3 p-3 pt-0",
                        standalone,
                    )
                    self.assertIn('style="min-height: 0;"', standalone)
                    if slug == "sidebar-inset":
                        self.assertIn("moo-sidebar-demo--flat-inset", standalone)
                    else:
                        self.assertNotIn("moo-sidebar-demo--flat-inset", standalone)

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

    def test_catalog_sidebar_has_no_blocks_group(self) -> None:
        # The left catalog sidebar no longer lists Blocks at all; only shared
        # header/palette navigation does. Reading a page unrelated to either
        # block's own content (the Components index) isolates the shell: each
        # block name should come from the command-palette loop only, and
        # "blocks/index.html" should appear exactly three times: the compact
        # dropdown, the desktop header nav link, and the palette's hardcoded
        # Blocks entry.
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/index.html")

        self.assertEqual(page.count("Sidebar (Floating)"), 1)
        self.assertEqual(page.count("Sidebar (Inset)"), 1)
        self.assertEqual(page.count('href="../blocks/index.html"'), 3)
        self.assertNotIn('class="sidebar-group-label" data-slot="sidebar-group-label">Blocks<', page)

    def test_block_preview_iframes_are_scaled_programmatically(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        styles = self.read_output("assets/css/catalog.css")
        script = self.read_output("assets/js/preview.js")

        self.assertIn(".moo-block-preview__viewport", styles)
        self.assertIn(".moo-block-preview__frame", styles)
        self.assertIn(
            '.moo-sidebar-demo--flat-inset:has(.sidebar[data-variant="inset"]) .sidebar-inset',
            styles,
        )
        self.assertIn("box-shadow: none", styles)
        self.assertIn(
            '.moo-sidebar-demo--flat-inset .sidebar[data-side="left"] .sidebar-inner',
            styles,
        )
        self.assertIn(
            "border-inline-end: var(--bs-border-width) solid var(--moo-sidebar-border)",
            styles,
        )
        self.assertIn(".moo-sidebar-demo--portal-shell .sidebar-inset__header", styles)
        self.assertIn("data-moo-block-frame-shell", script)
        self.assertIn("ResizeObserver", script)
