"""Schema and fault-injection tests for the certification manifest generator.

The manifest is the Core-only certification summary shipped with a release,
so the generator must produce documents that validate against
``src/certification/manifest.schema.json`` and must fail loudly whenever
the evidence it certifies cannot actually be produced — a silently
under-reporting manifest would be worse than no manifest.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tests.helpers import ROOT

SCRIPT = ROOT / "scripts" / "build-certification-manifest.py"
SCHEMA = ROOT / "src" / "certification" / "manifest.schema.json"
INVENTORY = ROOT / "src" / "certification" / "evidence-inventory.json"
PACK_TIMEOUT_SECONDS = 180
GENERATOR_TIMEOUT_SECONDS = 120


def pack_tarball(destination: Path) -> Path:
    completed = subprocess.run(
        ["npm", "pack", "--json", "--pack-destination", str(destination)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=PACK_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise AssertionError(f"npm pack failed: {completed.stderr}")
    payload = json.loads(completed.stdout)
    tarball = destination / payload[0]["filename"]
    if not tarball.is_file():
        raise AssertionError(f"npm pack produced no tarball at {tarball}")
    return tarball


def run_generator(*extra_args: str, **paths: str) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        str(SCRIPT),
        "--package",
        paths["package"],
        "--output",
        paths["output"],
    ]
    if "inventory" in paths:
        command += ["--inventory", paths["inventory"]]
    command += list(extra_args)
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=GENERATOR_TIMEOUT_SECONDS,
    )


class CertificationManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._scratch.cleanup)
        scratch = Path(cls._scratch.name)
        cls.tarball = pack_tarball(scratch)
        cls.output = scratch / "certification-manifest.json"
        completed = run_generator(package=str(cls.tarball), output=str(cls.output))
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        cls.manifest = json.loads(cls.output.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_generated_manifest_validates_against_the_schema(self) -> None:
        errors = list(
            Draft202012Validator(self.schema).iter_errors(self.manifest)
        )
        self.assertEqual(errors, [], [error.message for error in errors])

    def test_manifest_reflects_the_current_component_set(self) -> None:
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        expected = {
            (component["slug"], inventory["profiles"][component["profile"]]["tier"])
            for component in inventory["components"]
        }
        actual = {
            (component["slug"], component["tier"])
            for component in self.manifest["certifiedComponents"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(len(self.manifest["certifiedComponents"]), 42)
        self.assertEqual(self.manifest["status"], "preview")
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(self.manifest["coreVersion"], package["version"])

    def test_missing_evidence_fails_loudly(self) -> None:
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["components"][0]["evidence"].append(
            "tests/_manifest_fault_injection_missing.py"
        )
        with tempfile.TemporaryDirectory() as scratch:
            bad_inventory = Path(scratch) / "broken-inventory.json"
            bad_inventory.write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            completed = run_generator(
                package=str(self.tarball),
                output=str(Path(scratch) / "out.json"),
                inventory=str(bad_inventory),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("missing evidence", completed.stderr)

    def test_empty_evidence_fails_loudly(self) -> None:
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["components"][0]["evidence"] = []
        with tempfile.TemporaryDirectory() as scratch:
            bad_inventory = Path(scratch) / "broken-inventory.json"
            bad_inventory.write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            completed = run_generator(
                package=str(self.tarball),
                output=str(Path(scratch) / "out.json"),
                inventory=str(bad_inventory),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("has no evidence", completed.stderr)

    def test_evidence_escaping_the_repository_fails_loudly(self) -> None:
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["components"][0]["evidence"].append("../../../../etc/hosts")
        with tempfile.TemporaryDirectory() as scratch:
            bad_inventory = Path(scratch) / "broken-inventory.json"
            bad_inventory.write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            completed = run_generator(
                package=str(self.tarball),
                output=str(Path(scratch) / "out.json"),
                inventory=str(bad_inventory),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("escapes the repository", completed.stderr)

    def test_output_aliasing_the_package_fails_loudly(self) -> None:
        completed = run_generator(
            package=str(self.tarball),
            output=str(self.tarball),
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("must not name the package tarball", completed.stderr)
        self.assertTrue(self.tarball.is_file())

    def test_certified_status_requires_release_attestation_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            completed = run_generator(
                "--status",
                "certified",
                package=str(self.tarball),
                output=str(Path(scratch) / "out.json"),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--source-commit", completed.stderr)

    def test_package_hash_mismatch_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            completed = run_generator(
                "--expected-package-sha256",
                "0" * 64,
                package=str(self.tarball),
                output=str(Path(scratch) / "out.json"),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("package hash mismatch", completed.stderr)


if __name__ == "__main__":
    unittest.main()
