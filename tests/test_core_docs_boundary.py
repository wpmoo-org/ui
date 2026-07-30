from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import build
from jinja2 import Environment, meta


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/boundary-baseline.json"
CORE_OUTPUTS = {
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
}
FORBIDDEN_CORE_SITE_REFERENCES = ("site/", "site/src", "site/scss")
CORE_SOURCE_ROOTS = ("src", "scss")
CORE_SOURCE_SUFFIXES = {".py", ".js", ".jinja", ".scss"}


def load_recorder():
    module_path = ROOT / "scripts/record-boundary-baseline.py"
    spec = importlib.util.spec_from_file_location(
        "record_boundary_baseline",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_source_boundary_offenders(root: Path) -> list[str]:
    jinja_environment = Environment()
    site_templates = {
        path.relative_to(root / "site/src").as_posix()
        for path in (root / "site/src").rglob("*.jinja")
        if path.is_file()
    }
    offenders: list[str] = []

    for root_name in CORE_SOURCE_ROOTS:
        source_root = root / root_name
        for path in sorted(source_root.rglob("*")):
            if not path.is_file() or path.suffix not in CORE_SOURCE_SUFFIXES:
                continue
            source = path.read_text(encoding="utf-8")
            matches = [
                needle
                for needle in FORBIDDEN_CORE_SITE_REFERENCES
                if needle in source
            ]
            if matches:
                offenders.append(
                    f"{path.relative_to(root).as_posix()}: {', '.join(matches)}"
                )
            if path.suffix == ".jinja":
                parsed = jinja_environment.parse(source)
                for template_name in sorted(
                    template
                    for template in meta.find_referenced_templates(parsed)
                    if isinstance(template, str)
                ):
                    if template_name in site_templates:
                        offenders.append(
                            f"{path.relative_to(root).as_posix()}: "
                            f"imports site template {template_name}"
                        )

    return offenders


class CoreDocsBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        result = subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise AssertionError(result.stderr)

    def test_core_outputs_match_recorded_hashes(self) -> None:
        self.assertEqual(set(self.fixture["coreOutputs"]), CORE_OUTPUTS)
        for relative_path, expected_hash in self.fixture["coreOutputs"].items():
            with self.subTest(relative_path=relative_path):
                output = ROOT / relative_path
                self.assertTrue(output.is_file(), relative_path)
                self.assertEqual(sha256(output), expected_hash)

    def test_package_and_site_outputs_are_separate(self) -> None:
        package_dist = ROOT / "dist"
        site_dist = ROOT / "site-dist"
        package_files = {
            path.relative_to(package_dist).as_posix()
            for path in package_dist.rglob("*")
            if path.is_file()
        }
        expected_package_files = {
            "assets/css/moo-ui.css",
            "assets/css/moo-ui.min.css",
            "assets/css/moo.css",
            "assets/css/moo.min.css",
            "js/combobox.js",
            "js/sidebar.js",
        }
        expected_site_files = {
            "index.html",
            "favicon.svg",
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "site.webmanifest",
            "llms.txt",
            "sitemap.xml",
            "robots.txt",
            "assets/css/catalog.css",
            "assets/js/bootstrap.bundle.min.js",
            "components/button/index.html",
            "blocks/sidebar-floating/index.html",
            "utils/scroll-fade/index.html",
        }

        self.assertEqual(package_files, expected_package_files)
        for relative_path in sorted(expected_site_files):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((site_dist / relative_path).is_file())

    def test_npm_pack_files_match_recorded_baseline(self) -> None:
        result = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        packed_files = sorted(entry["path"] for entry in payload[0]["files"])
        self.assertEqual(packed_files, self.fixture["npmPackFiles"])

    def test_package_metadata_matches_recorded_baseline(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        expected = self.fixture["package"]

        self.assertEqual(package["version"], "0.7.0")
        self.assertEqual(sorted(package["files"]), expected["files"])
        self.assertEqual(package["exports"], expected["exports"])
        self.assertEqual(package["sideEffects"], expected["sideEffects"])
        self.assertEqual(
            package["peerDependencies"],
            expected["peerDependencies"],
        )

    def test_site_public_assets_are_site_owned(self) -> None:
        metadata_files = (
            "favicon.svg",
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "site.webmanifest",
            "llms.txt",
        )

        for name in metadata_files:
            with self.subTest(name=name):
                self.assertFalse((ROOT / name).exists())
                self.assertTrue((ROOT / "site/public" / name).is_file())

    def test_site_static_assets_are_not_package_owned(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        protected_paths = {
            "site/static",
            "static",
            "site",
            "site-dist",
            "dist/assets/images",
        }

        self.assertFalse((ROOT / "static").exists())
        self.assertTrue((ROOT / "site/static").is_dir())
        self.assertTrue(protected_paths.isdisjoint(package["files"]))

    def test_site_templates_are_under_site_src(self) -> None:
        self.assertFalse((ROOT / "src/pages").exists())
        self.assertTrue((ROOT / "site/src/pages").is_dir())
        self.assertTrue((ROOT / "site/src/layouts").is_dir())
        self.assertTrue((ROOT / "site/src/shell").is_dir())
        self.assertTrue((ROOT / "site/src/blocks").is_dir())
        self.assertTrue((ROOT / "site/src/includes").is_dir())
        self.assertTrue((ROOT / "site/src/registry").is_dir())

    def test_catalog_assets_are_site_owned(self) -> None:
        self.assertFalse((ROOT / "scss/catalog.scss").exists())
        self.assertFalse((ROOT / "scss/catalog").exists())
        self.assertFalse((ROOT / "src/js/catalog").exists())
        self.assertTrue((ROOT / "site/scss/catalog.scss").is_file())
        self.assertTrue((ROOT / "site/scss/catalog").is_dir())
        self.assertTrue((ROOT / "site/src/js/catalog").is_dir())

    def test_catalog_sass_settings_are_site_owned(self) -> None:
        self.assertFalse((ROOT / "scss/settings/_catalog.scss").exists())
        self.assertTrue((ROOT / "site/scss/catalog/_settings.scss").is_file())

    def test_cloudflare_root_config_targets_site_dist_without_script_changes(
        self,
    ) -> None:
        wrangler = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(wrangler["assets"]["directory"], "site-dist")
        self.assertEqual(package["scripts"]["deploy"], "wrangler deploy")
        self.assertEqual(package["scripts"]["preview"], "wrangler dev")
        self.assertFalse((ROOT / "site/wrangler.jsonc").exists())

    def test_core_sass_include_paths_respect_ownership(self) -> None:
        style_include_paths = getattr(build, "style_include_paths", None)

        self.assertIsNotNone(style_include_paths)
        self.assertEqual(
            style_include_paths(build.SCSS / "moo-ui.scss"),
            [str(build.SCSS), str(build.BOOTSTRAP / "scss")],
        )
        self.assertEqual(
            style_include_paths(build.SCSS / "moo-core.scss"),
            [str(build.SCSS), str(build.BOOTSTRAP / "scss")],
        )
        self.assertEqual(
            style_include_paths(build.SITE_SCSS / "catalog.scss"),
            [str(build.SCSS), str(build.SITE_SCSS), str(build.BOOTSTRAP / "scss")],
        )

    def test_site_templates_are_in_source_snapshot(self) -> None:
        snapshot_paths = {path for path, _ in build.source_snapshot()}
        template = ROOT / "site/src/pages/index.html.jinja"

        self.assertIn(str(template), snapshot_paths)

    def test_source_snapshot_covers_required_dev_server_watch_roots(self) -> None:
        snapshot_paths = {path for path, _ in build.source_snapshot()}
        required_paths = (
            ROOT / "build.py",
            ROOT / "site/public/llms.txt",
            ROOT / "site/src/pages/index.html.jinja",
            ROOT / "site/scss/catalog.scss",
            ROOT / "site/static/images/components/sidebar.webp",
            ROOT / "src/components/input.html.jinja",
            ROOT / "src/js/components/combobox.js",
            ROOT / "src/icons/lucide-icons.json",
            ROOT / "src/registry/components.json",
            ROOT / "scss/_primary_variables.scss",
        )

        for path in required_paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertIn(str(path), snapshot_paths)

    def test_core_source_does_not_import_site_source(self) -> None:
        self.assertEqual(core_source_boundary_offenders(ROOT), [])

    def test_core_jinja_source_cannot_logically_import_site_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            core_template = root / "src/components/probe.html.jinja"
            site_template = root / "site/src/includes/example.html.jinja"
            core_template.parent.mkdir(parents=True)
            site_template.parent.mkdir(parents=True)
            core_template.write_text(
                '{% from "includes/example.html.jinja" import render_example %}\n',
                encoding="utf-8",
            )
            site_template.write_text(
                "{% macro render_example() %}{% endmacro %}\n",
                encoding="utf-8",
            )

            offenders = core_source_boundary_offenders(root)

        self.assertEqual(
            offenders,
            [
                "src/components/probe.html.jinja: "
                "imports site template includes/example.html.jinja"
            ],
        )

    def test_certification_fixtures_use_core_dist_paths(self) -> None:
        stylesheet_href = "/dist/assets/css/moo-ui.css"

        for path in sorted((ROOT / "tests/fixtures/certification").glob("*.html")):
            fixture = path.read_text(encoding="utf-8")
            if ".css" not in fixture:
                continue
            with self.subTest(path=path.name):
                self.assertIn(stylesheet_href, fixture)
                self.assertNotIn("/site-dist/", fixture)

    def test_site_pages_load_core_artifacts_from_public_asset_urls(self) -> None:
        assets = (
            "assets/css/moo-ui.css",
            "assets/css/catalog.css",
            "assets/js/bootstrap.bundle.min.js",
            "assets/js/catalog/index.js",
        )
        site_dist = ROOT / "site-dist"
        site_pages = sorted(site_dist.rglob("*.html"))

        self.assertTrue(site_pages, "site-dist must contain generated HTML pages")

        for path in site_pages:
            relative_path = path.relative_to(site_dist)
            prefix = "../" * len(relative_path.parent.parts)
            page = path.read_text(encoding="utf-8")

            for asset in assets:
                with self.subTest(page=relative_path.as_posix(), asset=asset):
                    self.assertIn(f'"{prefix}{asset}?', page)

    def test_public_asset_prose_uses_site_static_source_path(self) -> None:
        source_paths = (
            ROOT / "README.md",
            ROOT / "ASSET_LICENSE.md",
            ROOT / "THIRD_PARTY_NOTICES.md",
            ROOT / "site/src/pages/license.html.jinja",
        )

        for path in source_paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                source = path.read_text(encoding="utf-8")
                self.assertIn("site/static/images/", source)
                self.assertNotIn(
                    "static/images/",
                    source.replace("site/static/images/", ""),
                )

    def test_recorder_reproduces_stable_baseline_sections(self) -> None:
        recorder = load_recorder()
        payload = recorder.record_boundary_baseline(ROOT)

        for section in ("package", "npmPackFiles", "coreOutputs"):
            with self.subTest(section=section):
                self.assertEqual(payload[section], self.fixture[section])


if __name__ == "__main__":
    unittest.main()
