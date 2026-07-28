import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PACKAGE_FILES = {
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
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
    "./certification.json": "./certification.json",
    "./package.json": "./package.json",
}


class PackageMetadataTests(unittest.TestCase):
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
        self.assertIn("dist/js/combobox.js", files)
        self.assertIn("dist/js/sidebar.js", files)
        self.assertEqual(package["sideEffects"], ["dist/assets/css/*.css"])
        self.assertEqual(
            package["exports"]["./certification.json"],
            "./certification.json",
        )
        self.assertIn("certification.json", files)
        self.assertNotIn("src/certification", files)
        self.assertNotIn("./moo-core.css", package["exports"])
        self.assertNotIn("./bootstrap.bundle.min.js", package["exports"])

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
        self.assertEqual(modules, {"combobox.js", "sidebar.js"})

    def test_npm_pack_contains_only_the_approved_files(self) -> None:
        result = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        packed_files = {entry["path"] for entry in payload[0]["files"]}
        self.assertEqual(packed_files, EXPECTED_PACKAGE_FILES | {"package.json"})

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

if (Combobox.name !== "Combobox" || Sidebar.name !== "Sidebar") {
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

    def test_component_module_imports_have_no_document_side_effect(self) -> None:
        for module_name in ("combobox.js", "sidebar.js"):
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
        self.assertIn("ref: ${{ inputs.release_ref || github.ref }}", workflow)
        self.assertIn('tag="${RELEASE_REF:-${GITHUB_REF_NAME}}"', workflow)
        self.assertIn('git show-ref --verify --quiet "refs/tags/${tag}"', workflow)
        self.assertIn('${GITHUB_REF_TYPE}" != "tag', workflow)
        self.assertIn('${tag}" != "v${version}', workflow)
        self.assertIn('source_commit="$(git rev-parse HEAD)"', workflow)
        self.assertIn(
            'git merge-base --is-ancestor "${source_commit}" origin/main',
            workflow,
        )

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

    def test_alias_package_is_not_part_of_root_install(self) -> None:
        self.assertFalse((ROOT / "pnpm-workspace.yaml").exists())


if __name__ == "__main__":
    unittest.main()
