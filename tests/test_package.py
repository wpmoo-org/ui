import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from tests.helpers import npm_env


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIST = ROOT / "dist"
EXPECTED_PACKAGE_FILES = {
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
    "dist/js/context-menu.js",
    "dist/js/datatable.js",
    "dist/js/slider.js",
    "dist/js/chart.js",
    "dist/js/chart.min.js",
    "dist/js/datepicker.js",
    "dist/js/datepicker.min.js",
    "scss/_facade-settings.scss",
    "scss/settings/_facade_public.scss",
    "certification.json",
    "README.md",
    "LICENSE",
    "ASSET_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
}
EXPECTED_PACKAGE_EXPORTS = {
    "./moo-ui.css": "./dist/assets/css/moo-ui.css",
    "./moo-ui.min.css": "./dist/assets/css/moo-ui.min.css",
    "./moo.css": "./dist/assets/css/moo.css",
    "./moo.min.css": "./dist/assets/css/moo.min.css",
    "./combobox.js": "./dist/js/combobox.js",
    "./sidebar.js": "./dist/js/sidebar.js",
    "./context-menu.js": "./dist/js/context-menu.js",
    "./datatable.js": "./dist/js/datatable.js",
    "./slider.js": "./dist/js/slider.js",
    "./chart.js": "./dist/js/chart.js",
    "./chart.min.js": "./dist/js/chart.min.js",
    "./datepicker.js": "./dist/js/datepicker.js",
    "./datepicker.min.js": "./dist/js/datepicker.min.js",
    "./scss/facade-settings": "./scss/_facade-settings.scss",
    "./certification.json": "./certification.json",
    "./package.json": "./package.json",
}
EXPECTED_PACKAGE_OUTPUT_FILES = {
    path
    for path in EXPECTED_PACKAGE_FILES
    if path.startswith("dist/")
}


class PackageMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [sys.executable, "build.py", "--core"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=npm_env(),
        )
        if result.returncode:
            raise AssertionError(result.stderr)

    def _read_package(self, relative_path: str = "package.json") -> dict:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_root_package_publishes_canonical_wpmoo_scope(self) -> None:
        package = self._read_package()

        self.assertEqual(package["name"], "@wpmoo/ui")
        self.assertEqual(package["license"], "MIT")
        self.assertFalse(package.get("private", True))
        self.assertEqual(package["repository"]["url"], "git+https://github.com/wpmoo-org/ui.git")
        self.assertEqual(package["scripts"]["build"], ".venv/bin/python build.py")
        self.assertEqual(package["scripts"]["dev"], ".venv/bin/python dev.py")
        self.assertNotIn("workspaces", package)

    def test_root_package_exports_built_css_without_protected_images(self) -> None:
        package = self._read_package()
        files = package["files"]

        self.assertEqual(set(files), EXPECTED_PACKAGE_FILES)
        self.assertEqual(package["exports"], EXPECTED_PACKAGE_EXPORTS)
        self.assertIn("dist/assets/css/moo-ui.css", files)
        self.assertIn("dist/assets/css/moo-ui.min.css", files)
        self.assertIn("dist/assets/css/moo.css", files)
        self.assertIn("dist/assets/css/moo.min.css", files)
        self.assertNotIn("dist/assets/css/moo-core.css", files)
        self.assertNotIn("dist/assets/js/bootstrap.bundle.min.js", files)
        self.assertNotIn("dist/assets/js/bootstrap.bundle.min.js.map", files)
        self.assertNotIn("dist", files)
        self.assertNotIn("static", files)
        self.assertNotIn("dist/assets/images", files)
        self.assertNotIn("static/images", files)
        self.assertEqual(package["peerDependencies"]["bootstrap"], ">=5.3.0 <5.4")
        self.assertTrue(package["peerDependenciesMeta"]["bootstrap"]["optional"])
        self.assertEqual(
            package["exports"]["./moo-ui.css"],
            "./dist/assets/css/moo-ui.css",
        )
        self.assertEqual(
            package["exports"]["./moo-ui.min.css"],
            "./dist/assets/css/moo-ui.min.css",
        )
        self.assertEqual(
            package["exports"]["./moo.css"],
            "./dist/assets/css/moo.css",
        )
        self.assertEqual(
            package["exports"]["./moo.min.css"],
            "./dist/assets/css/moo.min.css",
        )
        self.assertEqual(package["type"], "module")
        self.assertEqual(package["exports"]["./combobox.js"], "./dist/js/combobox.js")
        self.assertEqual(package["exports"]["./sidebar.js"], "./dist/js/sidebar.js")
        self.assertEqual(package["exports"]["./context-menu.js"], "./dist/js/context-menu.js")
        self.assertEqual(package["exports"]["./datatable.js"], "./dist/js/datatable.js")
        self.assertIn("dist/js/combobox.js", files)
        self.assertIn("dist/js/sidebar.js", files)
        self.assertIn("dist/js/context-menu.js", files)
        self.assertIn("dist/js/datatable.js", files)
        self.assertEqual(package["sideEffects"], ["dist/assets/css/*.css"])
        self.assertEqual(
            package["exports"]["./certification.json"],
            "./certification.json",
        )
        self.assertIn("certification.json", files)
        self.assertNotIn("src/certification", files)
        self.assertNotIn("./moo-core.css", package["exports"])
        self.assertNotIn("./bootstrap.bundle.min.js", package["exports"])

    def test_package_dist_contains_only_published_outputs(self) -> None:
        package_files = {
            path.relative_to(ROOT).as_posix()
            for path in PACKAGE_DIST.rglob("*")
            if path.is_file()
        }

        self.assertEqual(package_files, EXPECTED_PACKAGE_OUTPUT_FILES)

    def test_certification_preview_matches_package_metadata(self) -> None:
        package = self._read_package()
        certification = self._read_package("certification.json")
        schema = self._read_package("src/certification/manifest.schema.json")

        self.assertEqual(certification["schemaVersion"], "0.1")
        self.assertEqual(certification["status"], "preview")
        self.assertEqual(certification["coreVersion"], package["version"])
        self.assertEqual(
            certification["bootstrap"]["targetRange"],
            package["peerDependencies"]["bootstrap"],
        )
        self.assertEqual(
            certification["bootstrap"]["verifiedRange"],
            package["peerDependencies"]["bootstrap"],
        )
        self.assertEqual(
            certification["bootstrap"]["testedVersions"],
            ["5.3.0", "5.3.3", "5.3.8"],
        )
        self.assertEqual(certification["certifiedComponents"], [])
        self.assertFalse(
            certification["browserPolicy"]["exactEvidenceInAttestation"]
        )
        self.assertNotIn("sourceCommit", certification)
        self.assertNotIn("attestation", certification)
        self.assertEqual(
            set(certification["publicEntrypoints"]["css"])
            | set(certification["publicEntrypoints"]["esm"])
            | set(certification["publicEntrypoints"]["sass"]),
            set(package["exports"]) - {"./certification.json", "./package.json"},
        )
        self.assertEqual(
            schema["properties"]["status"]["enum"],
            ["preview", "certified"],
        )

    def test_public_component_module_surface_is_explicit(self) -> None:
        directory = ROOT / "src/js/components"
        modules = {
            path.relative_to(directory).as_posix()
            for path in directory.rglob("*.js")
        }
        self.assertEqual(
            modules,
            {
                "combobox.js",
                "sidebar.js",
                "context-menu.js",
                "datatable.js",
                "slider.js",
                "chart.js",
                "datepicker.js",
            },
        )

    def test_npm_pack_contains_only_the_approved_files(self) -> None:
        result = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=npm_env(),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        packed_files = {entry["path"] for entry in payload[0]["files"]}
        self.assertEqual(packed_files, EXPECTED_PACKAGE_FILES | {"package.json"})

    def test_published_notices_references_are_version_pinned_urls(self) -> None:
        package = self._read_package()
        expected_url = (
            f"https://github.com/wpmoo-org/ui/blob/v{package['version']}/"
            "THIRD_PARTY_NOTICES.md"
        )
        moving_branch_pattern = (
            r"https://github\.com/wpmoo-org/ui/blob/"
            r"(?:main|dev|release/[^/]+)/THIRD_PARTY_NOTICES\.md"
        )

        for package_file in ("README.md", "ASSET_LICENSE.md"):
            with self.subTest(package_file=package_file):
                document = (ROOT / package_file).read_text(encoding="utf-8")

                self.assertIn(expected_url, document)
                self.assertNotIn("`THIRD_PARTY_NOTICES.md`", document)
                self.assertNotRegex(document, moving_branch_pattern)

    def test_package_manifest_validator_accepts_approved_tarball_files(self) -> None:
        payload = [
            {
                "files": [
                    {"path": path}
                    for path in sorted(EXPECTED_PACKAGE_FILES | {"package.json"})
                ]
            }
        ]
        result = subprocess.run(
            [sys.executable, "scripts/verify_package_contents.py"],
            cwd=ROOT,
            input=json.dumps(payload),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_package_manifest_validator_runs_pack_when_no_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            bad_cache = Path(temporary_directory) / "not-a-directory"
            bad_cache.write_text("", encoding="utf-8")
            env = os.environ.copy()
            env["npm_config_cache"] = str(bad_cache)
            result = subprocess.run(
                [sys.executable, "scripts/verify_package_contents.py"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Package manifest matches the approved package boundary.",
            result.stdout,
        )

    def test_package_manifest_validator_rejects_missing_dist_output(self) -> None:
        payload = [
            {
                "files": [
                    {"path": path}
                    for path in sorted(
                        (EXPECTED_PACKAGE_FILES | {"package.json"})
                        - {"dist/assets/css/moo-ui.css"}
                    )
                ]
            }
        ]
        result = subprocess.run(
            [sys.executable, "scripts/verify_package_contents.py"],
            cwd=ROOT,
            input=json.dumps(payload),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dist/assets/css/moo-ui.css", result.stderr)

    def test_package_manifest_validator_rejects_site_dist_output(self) -> None:
        payload = [
            {
                "files": [
                    {"path": path}
                    for path in sorted(
                        EXPECTED_PACKAGE_FILES
                        | {"package.json", "site-dist/index.html"}
                    )
                ]
            }
        ]
        result = subprocess.run(
            [sys.executable, "scripts/verify_package_contents.py"],
            cwd=ROOT,
            input=json.dumps(payload),
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("site-dist/index.html", result.stderr)

    def test_real_tarball_resolves_from_a_clean_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            pack_result = subprocess.run(
                [
                    "npm",
                    "pack",
                    "--json",
                    "--pack-destination",
                    str(temporary_root),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=npm_env(),
            )

            self.assertEqual(pack_result.returncode, 0, pack_result.stderr)
            pack_payload = json.loads(pack_result.stdout)
            tarball = temporary_root / pack_payload[0]["filename"]
            self.assertTrue(tarball.is_file())

            unpack_root = temporary_root / "unpacked"
            with tarfile.open(tarball, mode="r:gz") as archive:
                self.assertTrue(
                    all(
                        member.name == "package"
                        or member.name.startswith("package/")
                        for member in archive.getmembers()
                    )
                )
                archive.extractall(unpack_root)

            consumer_root = temporary_root / "consumer"
            installed_package = consumer_root / "node_modules/@wpmoo/ui"
            installed_package.parent.mkdir(parents=True)
            shutil.move(unpack_root / "package", installed_package)

            installed_metadata = json.loads(
                (installed_package / "package.json").read_text(encoding="utf-8")
            )
            source_metadata = self._read_package()
            self.assertEqual(installed_metadata["name"], "@wpmoo/ui")
            self.assertEqual(installed_metadata["version"], source_metadata["version"])
            self.assertEqual(installed_metadata["exports"], EXPECTED_PACKAGE_EXPORTS)
            installed_certification = json.loads(
                (installed_package / "certification.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                installed_certification["coreVersion"],
                installed_metadata["version"],
            )

            consumer_check = consumer_root / "verify-package.mjs"
            consumer_check.write_text(
                """
import Combobox from "@wpmoo/ui/combobox.js";
import Sidebar from "@wpmoo/ui/sidebar.js";
import ContextMenu from "@wpmoo/ui/context-menu.js";
import DataTable from "@wpmoo/ui/datatable.js";

if (
  Combobox.name !== "Combobox" ||
  Sidebar.name !== "Sidebar" ||
  ContextMenu.name !== "ContextMenu" ||
  DataTable.name !== "DataTable"
) {
  throw new Error("Unexpected public ESM default export");
}

for (const specifier of [
  "@wpmoo/ui/moo-ui.css",
  "@wpmoo/ui/moo-ui.min.css",
  "@wpmoo/ui/moo.css",
  "@wpmoo/ui/moo.min.css",
  "@wpmoo/ui/certification.json",
]) {
  const resolved = import.meta.resolve(specifier);
  if (!resolved.startsWith("file:")) {
    throw new Error(`Package export did not resolve locally: ${specifier}`);
  }
}
""".lstrip(),
                encoding="utf-8",
            )
            consumer_result = subprocess.run(
                ["node", consumer_check.name],
                cwd=consumer_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(consumer_result.returncode, 0, consumer_result.stderr)

    def test_sass_facade_compiles_from_a_clean_consumer(self) -> None:
        """Phase 0C discipline: test the facade from a clean consumer
        fixture without source-tree shortcuts. Mirrors the tarball-install
        pattern from test_real_tarball_resolves_from_a_clean_consumer."""
        import sass

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            pack_result = subprocess.run(
                ["npm", "pack", "--json", "--pack-destination", str(temporary_root)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=npm_env(),
            )
            self.assertEqual(pack_result.returncode, 0, pack_result.stderr)
            pack_payload = json.loads(pack_result.stdout)
            tarball = temporary_root / pack_payload[0]["filename"]
            self.assertTrue(tarball.is_file())

            # Unpack into a consumer node_modules layout
            unpack_root = temporary_root / "unpacked"
            with tarfile.open(tarball, mode="r:gz") as archive:
                archive.extractall(unpack_root)
            consumer_root = temporary_root / "consumer"
            installed_package = consumer_root / "node_modules/@wpmoo/ui"
            installed_package.parent.mkdir(parents=True)
            shutil.move(unpack_root / "package", installed_package)

            # Install bootstrap@5.3.3 alongside
            bootstrap_pkg = consumer_root / "node_modules/bootstrap/scss"
            bootstrap_pkg.mkdir(parents=True)
            vendor_bootstrap_scss = ROOT / "vendor/bootstrap/scss"
            for item in vendor_bootstrap_scss.iterdir():
                dest = bootstrap_pkg / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                elif item.is_dir():
                    shutil.copytree(item, dest)

            # --- Assertion 1: zero overrides compiles ---
            scss_dir = consumer_root / "scss"
            scss_dir.mkdir(exist_ok=True)
            (scss_dir / "defaults.scss").write_text(
                '@import "@wpmoo/ui/scss/facade-settings";\n'
                "@import \"bootstrap/scss/functions\";\n"
                "@import \"bootstrap/scss/variables\";\n"
                "@import \"bootstrap/scss/variables-dark\";\n"
                "@import \"bootstrap/scss/maps\";\n"
                "@import \"bootstrap/scss/mixins\";\n"
                "@import \"bootstrap/scss/root\";\n",
                encoding="utf-8",
            )
            css_defaults = sass.compile(
                filename=str(scss_dir / "defaults.scss"),
                include_paths=[str(consumer_root / "node_modules")],
                output_style="expanded",
            )
            self.assertIn("--bs-body-color:", css_defaults)

            # --- Assertion 2: overriding $primary changes the output ---
            (scss_dir / "override.scss").write_text(
                '@import "@wpmoo/ui/scss/facade-settings";\n'
                "$primary: #3b82f6;\n"
                '@import "bootstrap/scss/functions";\n'
                '@import "bootstrap/scss/variables";\n'
                '@import "bootstrap/scss/maps";\n'
                '@import "bootstrap/scss/mixins";\n'
                '@import "bootstrap/scss/root";\n',
                encoding="utf-8",
            )
            css_override = sass.compile(
                filename=str(scss_dir / "override.scss"),
                include_paths=[str(consumer_root / "node_modules")],
                output_style="expanded",
            )
            self.assertIn("#3b82f6", css_override)
            self.assertNotIn(css_defaults, css_override)

            # --- Assertion 3: no internal partial paths leaked ---
            for output in (css_defaults, css_override):
                self.assertNotIn("settings/", output)
                self.assertNotIn("_palette", output)
                self.assertNotIn("_components", output)
                self.assertNotIn("_forms", output)

            # --- Assertion 4: non-allow-listed variables must not leak ---
            # The facade may only expose the frozen 15-variable allow-list.
            # Referencing an internal declaration ($white from the palette,
            # $moo-destructive derived token) after the facade import must
            # fail with Sass's own undefined-variable error. If the facade
            # ever re-imports the full internal settings partial, these
            # compilations succeed and this assertion fails for real.
            for leaked_variable in ("$white", "$moo-destructive"):
                with self.subTest(leaked_variable=leaked_variable):
                    (scss_dir / "leak.scss").write_text(
                        '@import "@wpmoo/ui/scss/facade-settings";\n'
                        f".leak-test {{ color: {leaked_variable}; }}\n",
                        encoding="utf-8",
                    )
                    with self.assertRaises(sass.CompileError) as leak_context:
                        sass.compile(
                            filename=str(scss_dir / "leak.scss"),
                            include_paths=[str(consumer_root / "node_modules")],
                            output_style="expanded",
                        )
                    self.assertIn(
                        "Undefined variable", str(leak_context.exception)
                    )

    def test_component_module_imports_have_no_document_side_effect(self) -> None:
        for module_name in (
            "combobox.js",
            "sidebar.js",
            "context-menu.js",
            "datatable.js",
        ):
            with self.subTest(module_name=module_name):
                result = subprocess.run(
                    [
                        "node",
                        "--input-type=module",
                        "--eval",
                        f'import("./src/js/components/{module_name}")',
                    ],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(result.returncode, 0, result.stderr)

    def test_publish_workflow_requires_a_matching_existing_tag_ref(self) -> None:
        workflow = (ROOT / ".github/workflows/npm-publish.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("release_ref:", workflow)
        self.assertIn("tag/version guard", workflow)
        self.assertIn("ref: ${{ github.ref }}", workflow)
        self.assertNotIn("ref: ${{ inputs.release_ref || github.ref }}", workflow)
        self.assertIn('tag="${RELEASE_REF:-${GITHUB_REF_NAME}}"', workflow)
        self.assertIn('git show-ref --verify --quiet "refs/tags/${tag}"', workflow)
        self.assertIn('${GITHUB_REF_TYPE}" != "tag', workflow)
        self.assertIn('${tag}" != "v${version}', workflow)
        self.assertIn('source_commit="$(git rev-parse HEAD)"', workflow)
        self.assertIn('release_commit="$(git rev-list -n 1 "${tag}")"', workflow)
        self.assertIn(
            'git merge-base --is-ancestor "${release_commit}" origin/main',
            workflow,
        )
        self.assertIn(
            'git merge-base --is-ancestor "${source_commit}" origin/main',
            workflow,
        )
        self.assertIn(
            'Workflow source commit ${source_commit} is not in origin/main history.',
            workflow,
        )

    def test_publish_workflow_never_tags_a_prerelease_as_npm_latest(self) -> None:
        workflow = (ROOT / ".github/workflows/npm-publish.yml").read_text(
            encoding="utf-8"
        )

        # A version like "1.0.0-rc.1" must publish under a dist-tag other
        # than npm's default "latest" - otherwise a plain `npm install
        # @wpmoo/ui` would resolve to a release candidate instead of the
        # last stable release the moment an RC tag is pushed. Extract the
        # exact routing snippet and actually execute it for a stable and a
        # prerelease version, asserting on its real GITHUB_OUTPUT writes -
        # a text/position check could still pass a logic bug (e.g. an
        # inverted comparison) that happens to keep the right literal
        # strings in the right branches.
        marker = 'if [[ "${version}" == *-* ]]; then'
        self.assertIn(marker, workflow)
        start = workflow.index(marker)
        end = workflow.index("\n          fi\n", start) + len("\n          fi\n")
        routing_snippet = workflow[start:end]

        for version, expected_npm_tag, expected_prerelease in (
            ("1.0.0-rc.1", "rc", "true"),
            ("1.0.0", "latest", "false"),
        ):
            with self.subTest(version=version):
                with tempfile.TemporaryDirectory() as scratch:
                    output_path = Path(scratch) / "github_output"
                    output_path.write_text("", encoding="utf-8")
                    completed = subprocess.run(
                        ["bash", "-c", routing_snippet],
                        env={
                            **os.environ,
                            "version": version,
                            "GITHUB_OUTPUT": str(output_path),
                        },
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    outputs = output_path.read_text(encoding="utf-8")
                    self.assertEqual(
                        outputs,
                        f"npm_tag={expected_npm_tag}\n"
                        f"prerelease={expected_prerelease}\n",
                    )

        self.assertIn(
            'npm publish --access public --provenance --tag '
            '"${{ steps.package.outputs.npm_tag }}"',
            workflow,
        )
        self.assertNotIn("npm publish --access public --provenance\n", workflow)
        # The GitHub release itself must also be marked prerelease, not
        # presented as a normal stable release.
        self.assertIn(
            'if [ "${{ steps.package.outputs.prerelease }}" = "true" ]; then',
            workflow,
        )
        self.assertIn("release_args+=(--prerelease)", workflow)

    def test_release_tag_workflow_creates_lightweight_tags(self) -> None:
        workflow = (ROOT / ".github/workflows/release-tag.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('git tag "${tag}"', workflow)
        self.assertNotIn("git tag -a", workflow)

    def test_ci_runs_for_main_and_dev_pushes(self) -> None:
        workflow = (ROOT / ".github/workflows/ui-ci.yml").read_text(
            encoding="utf-8"
        )
        push_block = workflow.split("  push:\n", 1)[1].split(
            "  workflow_dispatch:",
            1,
        )[0]

        self.assertIn("      - main", push_block)
        self.assertIn("      - dev", push_block)

    def test_ci_keeps_ui_tests_name_and_verifies_both_output_boundaries(self) -> None:
        workflow = (ROOT / ".github/workflows/ui-ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("  ui-tests:\n    name: ui-tests", workflow)
        self.assertIn('.venv/bin/python -m unittest discover -s tests -v', workflow)
        self.assertIn('.venv/bin/python build.py', workflow)
        self.assertIn(
            'npm pack --dry-run --json | .venv/bin/python '
            'scripts/verify_package_contents.py',
            workflow,
        )

    def test_alias_package_is_not_part_of_root_install(self) -> None:
        self.assertFalse((ROOT / "pnpm-workspace.yaml").exists())


if __name__ == "__main__":
    unittest.main()
