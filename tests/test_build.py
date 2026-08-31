from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import build
from tests.helpers import PACKAGE_DIST, ROOT, SITE_DIST, CatalogTestCase


class BuildTests(CatalogTestCase):
    def require_full_build(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_theme_builder_first_paint_payload_times_out_cleanly(self) -> None:
        original_run = build.subprocess.run

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(
                cmd=args[0] if args else kwargs.get("args"),
                timeout=kwargs.get("timeout"),
            )

        try:
            build.subprocess.run = fake_run
            with self.assertRaisesRegex(
                RuntimeError,
                "Theme Builder first-paint payload generation timed out",
            ):
                build.theme_builder_first_paint_payload()
        finally:
            build.subprocess.run = original_run

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
            "moo-ui.js",
            "moo-ui.min.js",
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
            self.assertTrue((PACKAGE_DIST / "js/moo-ui.js").is_file())
            self.assertTrue((PACKAGE_DIST / "js/moo-ui.min.js").is_file())
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

    def test_public_esm_outputs_have_no_bare_imports_or_cdn_urls(self) -> None:
        """Public Chart/Datepicker outputs must be self-contained.

        Chart.js bundles its runtime; Datepicker is self-contained Moo UI ESM.
        In both cases the shipped output must never contain a bare third-party
        specifier or a CDN runtime URL."""
        self.require_full_build()
        for module_name in (
            "moo-ui.js",
            "moo-ui.min.js",
            "chart.js",
            "chart.min.js",
            "datepicker.js",
            "datepicker.min.js",
        ):
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

    def test_public_npm_js_outputs_carry_moo_ui_license_banner(self) -> None:
        self.require_full_build()
        for module_name in (
            "combobox.js",
            "sidebar.js",
            "context-menu.js",
            "datatable.js",
            "slider.js",
            "moo-ui.js",
            "moo-ui.min.js",
            "chart.js",
            "chart.min.js",
            "datepicker.js",
            "datepicker.min.js",
        ):
            with self.subTest(module=module_name):
                expected_banner = (
                    "/*!\n"
                    f" * Moo UI {module_name} v1.0.0-rc.3 (https://ui.wpmoo.org/)\n"
                    " * Copyright 2026 WPMoo (https://wpmoo.org)\n"
                    " * Licensed under MIT (https://github.com/wpmoo-org/ui/blob/main/LICENSE)\n"
                    " */\n"
                )
                content = (PACKAGE_DIST / f"js/{module_name}").read_text(
                    encoding="utf-8"
                )
                self.assertTrue(content.startswith(expected_banner))
                self.assertEqual(content.count(expected_banner), 1)

    def test_bundled_module_comments_are_path_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "chart.js"
            output.write_text(
                "\n".join(
                    (
                        "var helper = true;",
                        "// ../../../../projects/ui/html/node_modules/chart.js/dist/chart.js",
                        "// /tmp/ui-html/node_modules/@kurkle/color/dist/color.esm.js",
                        "// src/js/components/chart.js",
                    )
                ),
                encoding="utf-8",
            )

            build._normalize_esbuild_module_comments(output)

            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                [
                    "var helper = true;",
                    "// node_modules/chart.js/dist/chart.js",
                    "// node_modules/@kurkle/color/dist/color.esm.js",
                    "// src/js/components/chart.js",
                ],
            )

    def test_slider_has_no_minified_variant(self) -> None:
        """Slider is a plain ESM module; no minified variant should exist."""
        self.require_full_build()
        self.assertTrue((PACKAGE_DIST / "js/slider.js").is_file())
        self.assertFalse((PACKAGE_DIST / "js/slider.min.js").exists())

    def test_canonical_and_minified_bundles_have_equivalent_exports(self) -> None:
        """Canonical and minified bundles must expose the same public API.

        Uses Node.js dynamic import() to compare sorted Object.keys(module)
        for each pair, ensuring runtime-level equivalence rather than
        regex-based text matching."""
        self.require_full_build()
        for base_name in ("moo-ui", "chart", "datepicker"):
            canonical_path = PACKAGE_DIST / f"js/{base_name}.js"
            minified_path = PACKAGE_DIST / f"js/{base_name}.min.js"

            with self.subTest(module=base_name):
                self.assertTrue(canonical_path.is_file())
                self.assertTrue(minified_path.is_file())

                node_script = (
                    f"const c = await import('{canonical_path}');"
                    f"const m = await import('{minified_path}');"
                    "const ck = Object.keys(c).sort();"
                    "const mk = Object.keys(m).sort();"
                    "if (JSON.stringify(ck) !== JSON.stringify(mk)) {"
                    "  console.error('CANONICAL:', JSON.stringify(ck));"
                    "  console.error('MINIFIED:', JSON.stringify(mk));"
                    "  process.exit(1);"
                    "}"
                    "console.log(JSON.stringify(ck));"
                )
                result = subprocess.run(
                    ["node", "--input-type=module", "-e", node_script],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"{base_name}: canonical and minified export keys differ:\n"
                    f"stdout: {result.stdout}\nstderr: {result.stderr}",
                )

    def test_no_sourcemap_files_are_generated(self) -> None:
        """The locked esbuild configuration must not produce .map files."""
        self.require_full_build()
        map_files = list((PACKAGE_DIST / "js").glob("*.map"))
        self.assertEqual(
            map_files, [],
            f"Unexpected sourcemap files in dist/js/: {[f.name for f in map_files]}",
        )

    def test_dist_reader_self_provision_does_not_delete_shared_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shared_package_dist = Path(temp_dir) / "dist"
            shared_site_dist = Path(temp_dir) / "site-dist"
            shared_package_dist.mkdir()
            shared_site_dist.mkdir()

            original_rmtree = shutil.rmtree

            def guarded_rmtree(path, *args, **kwargs):
                if Path(path) in {shared_package_dist, shared_site_dist}:
                    raise AssertionError(f"deleted shared output path: {path}")
                return original_rmtree(path, *args, **kwargs)

            def fake_run_build(_self):
                return subprocess.CompletedProcess(["build.py"], 0, "", "")

            with (
                mock.patch("tests.test_build.PACKAGE_DIST", shared_package_dist),
                mock.patch("tests.test_build.SITE_DIST", shared_site_dist),
                mock.patch("tests.test_build.shutil.rmtree", guarded_rmtree),
                mock.patch("tests.test_build.subprocess.run") as run,
                mock.patch.object(BuildTests, "run_build", fake_run_build),
            ):
                run.return_value = subprocess.CompletedProcess(
                    ["python", "-m", "unittest"],
                    0,
                    "",
                    "",
                )
                self.test_dist_reader_tests_self_provision_from_empty_outputs()

    def _copy_isolated_build_checkout(self, destination: Path) -> None:
        root = ROOT.resolve()

        def ignore_build_outputs(directory: str, names: list[str]) -> set[str]:
            ignored = {
                ".git",
                ".pytest_cache",
                ".venv",
                "__pycache__",
                "node_modules",
            }.intersection(names)
            if Path(directory).resolve() == root:
                ignored.update({"dist", "site-dist"}.intersection(names))
            return ignored

        shutil.copytree(
            ROOT,
            destination,
            ignore=ignore_build_outputs,
        )
        node_modules = ROOT / "node_modules"
        if node_modules.is_dir():
            (destination / "node_modules").symlink_to(
                node_modules,
                target_is_directory=True,
            )

    def test_dist_reader_tests_self_provision_from_empty_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="moo-ui-build-test-") as temp_dir:
            isolated_root = Path(temp_dir) / "html"
            self._copy_isolated_build_checkout(isolated_root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "tests.test_build.BuildTests.test_public_esm_outputs_have_no_bare_imports_or_cdn_urls",
                    "tests.test_build.BuildTests.test_canonical_and_minified_bundles_have_equivalent_exports",
                    "tests.test_build.BuildTests.test_no_sourcemap_files_are_generated",
                    "tests.test_build.BuildTests.test_slider_has_no_minified_variant",
                ],
                cwd=isolated_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
