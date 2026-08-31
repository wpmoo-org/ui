from __future__ import annotations

import json

from tests.helpers import ROOT, CatalogTestCase


class BlocksTests(CatalogTestCase):
    def test_blocks_json_entries_are_ready(self) -> None:
        blocks = json.loads(
            (ROOT / "site/src/registry/blocks.json").read_text(encoding="utf-8")
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
                self.assertIn(f'src="../../blocks/previews/{slug}/"', page)
                self.assertIn(f'href="../../blocks/previews/{slug}/"', page)

            source = (
                ROOT / f"site/src/pages/blocks/{slug}.html.jinja"
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
                with self.subTest(slug=slug, contract="portal demo structure"):
                    self.assertIn("Moo Portal", standalone)
                    self.assertIn("Portal Operations", standalone)
                    self.assertIn('data-slot="sidebar-menu-badge"', standalone)
                    self.assertIn('aria-label="Preferences actions"', standalone)
                    self.assertIn('data-bs-offset="0,4"', standalone)
                    self.assertIn('class="sidebar-menu-item dropend"', standalone)
                    self.assertEqual(standalone.count('data-slot="sidebar-menu-action"'), 1)
                    self.assertGreaterEqual(standalone.count('data-slot="sidebar-menu-sub"'), 3)
                    self.assertIn("moo-sidebar-demo--portal-shell", standalone)
                    self.assertIn(
                        'class="sidebar-menu-item dropend sidebar-menu-item--account"',
                        standalone,
                    )
                    self.assertIn("sidebar-menu-button--account", standalone)
                    self.assertIn("sidebar-account-menu", standalone)
                    self.assertIn("sidebar-account-menu__item", standalone)
                    self.assertIn("sidebar-account-menu__header", standalone)
                    self.assertGreaterEqual(standalone.count("sidebar-account-menu__item"), 4)
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
                self.assertIn(f'href="../blocks/{slug}/"', index)
                self.assertIn(label, index)
        # Blocks cards mirror the Components index showcase-card layout with
        # real block preview art and the whole card as a stretched-link.
        self.assertRegex(index, r'class="[^"]*\bmoo-catalog__showcase-card\b')
        self.assertEqual(
            index.count("moo-catalog__showcase-preview"), 2
        )
        self.assertIn(
            'src="../assets/images/blocks/sidebar-floating.webp"',
            index,
        )
        self.assertIn(
            'src="../assets/images/blocks/sidebar-inset.webp"',
            index,
        )
        self.assertRegex(index, r'class="[^"]*\bstretched-link\b')

    def test_navbar_and_command_palette_list_both_blocks_by_name(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        self.assertIn('href="blocks/"', home)
        for slug, label in (
            ("sidebar-floating", "Sidebar (Floating)"),
            ("sidebar-inset", "Sidebar (Inset)"),
        ):
            with self.subTest(slug=slug):
                self.assertIn(f'href="blocks/{slug}/"', home)
                self.assertIn(label, home)

    def test_catalog_sidebar_has_no_blocks_group(self) -> None:
        # Blocks is a link inside the sidebar's "Catalog" group, not its own
        # labelled group -- the navbar carries no page links at all now (it's
        # header chrome only: sidebar toggle, search, theme, GitHub), so
        # "../blocks/" should appear exactly twice: the sidebar link and the
        # command palette's hardcoded Blocks entry. Reading a page unrelated
        # to either block's own content (the Components index) isolates the
        # shell from that assertion.
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/index.html")

        self.assertEqual(page.count("Sidebar (Floating)"), 1)
        self.assertEqual(page.count("Sidebar (Inset)"), 1)
        self.assertEqual(page.count('href="../blocks/"'), 2)
        self.assertNotIn('class="sidebar-group-label" data-slot="sidebar-group-label">Blocks<', page)

    def test_block_preview_iframes_are_scaled_programmatically(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        styles = self.read_output("assets/css/catalog.css")
        script = self.read_output("assets/js/catalog/block-frame.js")

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

    def test_block_preview_loading_placeholder_and_reveal_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("blocks/sidebar-floating.html")
        styles = self.read_output("assets/css/catalog.css")
        script = self.read_output("assets/js/catalog/block-frame.js")

        # The loading placeholder markup must ship with the block frame.
        self.assertIn("moo-block-preview__loading", page)
        self.assertIn("data-moo-block-frame-loading", page)
        self.assertIn("Loading preview", page)

        # The reveal state must be wired: CSS fades the placeholder out on
        # .is-loaded, and the script toggles that class.
        self.assertIn(".moo-block-preview__viewport.is-loaded", styles)
        self.assertIn("moo-block-preview__loading", styles)
        self.assertIn("is-loaded", script)
        self.assertIn("revealFrame", script)

        # Variant switching must bring the placeholder back for the new src.
        self.assertIn("classList.remove(\"is-loaded\")", script)

        # The cached-load shortcut must not reveal a still-lazy about:blank
        # frame; the guard must check the document URL, not only readyState.
        self.assertIn('href !== "about:blank"', script)

        # The load listener must reveal and resize the frame together.
        self.assertIn("listen(frame, \"load\"", script)
