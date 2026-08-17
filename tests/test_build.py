from __future__ import annotations

import shutil
import subprocess
import sys

from tests.helpers import PACKAGE_DIST, ROOT, SITE_DIST, CatalogTestCase


class BuildTests(CatalogTestCase):
    def test_build_creates_static_entrypoints(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((SITE_DIST / "index.html").is_file())
        for css_name in ("moo-ui.css", "moo-ui.min.css", "moo.css", "moo.min.css"):
            with self.subTest(css_name=css_name):
                self.assertTrue((PACKAGE_DIST / f"assets/css/{css_name}").is_file())
                self.assertTrue((SITE_DIST / f"assets/css/{css_name}").is_file())
                self.assertEqual(
                    (PACKAGE_DIST / f"assets/css/{css_name}").read_bytes(),
                    (SITE_DIST / f"assets/css/{css_name}").read_bytes(),
                )
        self.assertTrue((SITE_DIST / "assets/css/catalog.css").is_file())
        self.assertFalse((PACKAGE_DIST / "assets/css/catalog.css").exists())
        self.assertFalse((PACKAGE_DIST / "assets/css/moo-core.css").exists())
        self.assertFalse((SITE_DIST / "assets/css/moo-core.css").exists())
        self.assertTrue(
            (SITE_DIST / "assets/js/bootstrap.bundle.min.js").is_file()
        )
        self.assertTrue(
            (SITE_DIST / "assets/js/bootstrap.bundle.min.js.map").is_file()
        )
        for module_name in (
            "combobox.js",
            "sidebar.js",
            "context-menu.js",
            "datatable.js",
            "slider.js",
            "chart.js",
            "chart.min.js",
            "datepicker.js",
            "datepicker.min.js",
        ):
            site_component_module = SITE_DIST / f"assets/js/components/{module_name}"
            site_legacy_module = SITE_DIST / f"js/{module_name}"
            package_module = PACKAGE_DIST / f"js/{module_name}"

            self.assertTrue(site_component_module.is_file())
            self.assertTrue(site_legacy_module.is_file())
            self.assertTrue((PACKAGE_DIST / f"js/{module_name}").is_file())
            self.assertEqual(
                site_component_module.read_bytes(),
                package_module.read_bytes(),
            )
            self.assertEqual(
                site_legacy_module.read_bytes(),
                package_module.read_bytes(),
            )
        index = (SITE_DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script type="module" src="assets/js/catalog/index.js?', index)
        self.assertTrue((SITE_DIST / "llms.txt").is_file())
        self.assertTrue((SITE_DIST / "sitemap.xml").is_file())
        self.assertTrue((SITE_DIST / "robots.txt").is_file())

    def test_build_writes_canonical_sitemap(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        sitemap = (SITE_DIST / "sitemap.xml").read_text(encoding="utf-8")
        robots = (SITE_DIST / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/components/button/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/blocks/sidebar-floating/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/utils/scroll-fade/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/llms.txt</loc>",
            sitemap,
        )
        self.assertNotIn(".html", sitemap)
        self.assertNotIn("/blocks/previews/", sitemap)
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertIn(
            "Sitemap: https://ui.wpmoo.org/sitemap.xml",
            robots,
        )

    def test_core_mode_builds_only_package_outputs(self) -> None:
        if SITE_DIST.exists():
            shutil.rmtree(SITE_DIST)

        try:
            result = subprocess.run(
                [sys.executable, "build.py", "--core"],
                cwd=PACKAGE_DIST.parent,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((PACKAGE_DIST / "assets/css/moo-ui.css").is_file())
            self.assertTrue((PACKAGE_DIST / "assets/css/moo.css").is_file())
            self.assertTrue((PACKAGE_DIST / "js/combobox.js").is_file())
            self.assertFalse(SITE_DIST.exists())
        finally:
            self.run_build()

    def test_site_mode_requires_existing_package_outputs(self) -> None:
        if PACKAGE_DIST.exists():
            shutil.rmtree(PACKAGE_DIST)
        if SITE_DIST.exists():
            shutil.rmtree(SITE_DIST)

        try:
            result = subprocess.run(
                [sys.executable, "build.py", "--site"],
                cwd=PACKAGE_DIST.parent,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Required Core outputs are missing", result.stderr)
            self.assertIn("build.py --core", result.stderr)
            self.assertFalse(SITE_DIST.exists())
        finally:
            self.run_build()

    def test_site_mode_copies_public_component_js_from_package_dist(self) -> None:
        core_result = subprocess.run(
            [sys.executable, "build.py", "--core"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(core_result.returncode, 0, core_result.stderr)

        package_module = PACKAGE_DIST / "js/combobox.js"
        source_module = ROOT / "src/js/components/combobox.js"
        sentinel_module = (
            package_module.read_bytes()
            + b"\n// package-dist-sentinel-for-site-build\n"
        )
        package_module.write_bytes(sentinel_module)

        try:
            site_result = subprocess.run(
                [sys.executable, "build.py", "--site"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(site_result.returncode, 0, site_result.stderr)
            for site_module in (
                SITE_DIST / "assets/js/components/combobox.js",
                SITE_DIST / "js/combobox.js",
            ):
                with self.subTest(site_module=site_module.relative_to(SITE_DIST)):
                    self.assertTrue(site_module.is_file())
                    self.assertEqual(site_module.read_bytes(), sentinel_module)
                    self.assertNotEqual(site_module.read_bytes(), source_module.read_bytes())
            self.assertTrue((SITE_DIST / "assets/js/catalog/index.js").is_file())
        finally:
            self.run_build()

    def test_build_uses_one_shared_catalog_shell(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        self.assertEqual(index.count('data-moo-shell="catalog"'), 1)
        self.assertEqual(index.count("<header"), 1)
        self.assertEqual(index.count("<footer"), 0)
        self.assertIn('href="components/button/"', index)
        self.assertIn('href="components/card/"', index)
        self.assertIn('id="main-content"', index)
        self.assertIn('href="#main-content"', index)
        self.assertIn('id="main-content" tabindex="-1"', index)

        introduction = self.read_output("introduction.html")
        self.assertEqual(introduction.count("<footer"), 0)

    def test_bundled_modules_have_no_bare_imports_or_cdn_urls(self) -> None:
        """Bundled Chart/Datepicker outputs must be self-contained."""
        for module_name in ("chart.js", "chart.min.js", "datepicker.js", "datepicker.min.js"):
            module_path = PACKAGE_DIST / "js" / module_name
            with self.subTest(module=module_name):
                self.assertTrue(module_path.is_file())
                content = module_path.read_text(encoding="utf-8")
                # No bare third-party imports
                self.assertNotIn('from "chart.js', content)
                self.assertNotIn('from "vanillajs-datepicker', content)
                self.assertNotIn("from 'chart.js", content)
                self.assertNotIn("from 'vanillajs-datepicker", content)
                # No CDN URLs
                self.assertNotIn("cdn.jsdelivr.net", content)
                self.assertNotIn("unpkg.com", content)
                self.assertNotIn("cdnjs.cloudflare.com", content)

    def test_slider_has_no_minified_variant(self) -> None:
        """Slider is a plain ESM module; no minified variant should exist."""
        self.assertTrue((PACKAGE_DIST / "js/slider.js").is_file())
        self.assertFalse((PACKAGE_DIST / "js/slider.min.js").exists())

    def test_canonical_and_minified_bundles_have_equivalent_exports(self) -> None:
        """Canonical and minified bundles must expose the same public API."""
        import re

        for base_name in ("chart", "datepicker"):
            canonical = (PACKAGE_DIST / f"js/{base_name}.js").read_text(encoding="utf-8")
            minified = (PACKAGE_DIST / f"js/{base_name}.min.js").read_text(encoding="utf-8")

            with self.subTest(module=base_name):
                # Extract export statements (handle both spaced and minified formats)
                canonical_exports = set(re.findall(r'export\s*{([^}]+)}', canonical))
                minified_exports = set(re.findall(r'export\s*{([^}]+)}', minified))

                # Both should have the same export structure
                self.assertEqual(len(canonical_exports), len(minified_exports),
                    f"{base_name}: canonical and minified have different export counts")

                # Check for default export presence
                canonical_has_default = "as default" in canonical
                minified_has_default = "as default" in minified
                self.assertEqual(canonical_has_default, minified_has_default,
                    f"{base_name}: canonical and minified differ in default export")
