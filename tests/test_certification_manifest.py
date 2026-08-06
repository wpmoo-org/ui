"""Schema and fault-injection tests for the certification manifest generator.

The manifest is the Core-only certification summary shipped with a release,
so the generator must produce documents that validate against
``src/certification/manifest.schema.json`` and must fail loudly whenever
the evidence it certifies cannot actually be produced — a silently
under-reporting manifest would be worse than no manifest.
"""

from __future__ import annotations

import hashlib
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

    def test_certified_status_requires_an_attestation_file_not_just_a_uri(self) -> None:
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as scratch:
            completed = run_generator(
                "--status",
                "certified",
                "--source-commit",
                head_commit,
                "--attestation",
                "https://github.com/wpmoo-org/ui/releases/download/v1.0.0/attestation.json",
                package=str(self.tarball),
                output=str(Path(scratch) / "out.json"),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--attestation-file", completed.stderr)

    def test_certified_status_rejects_a_mismatched_attestation(self) -> None:
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as scratch:
            scratch_path = Path(scratch)
            forged = scratch_path / "attestation.json"
            forged.write_text(
                json.dumps(
                    {
                        "sourceCommit": "a" * 40,  # does not match head_commit
                        "coreVersion": "0.0.0",
                        "result": "passed",
                        "package": {"sha256": "b" * 64},
                    }
                ),
                encoding="utf-8",
            )
            completed = run_generator(
                "--status",
                "certified",
                "--source-commit",
                head_commit,
                "--attestation",
                "https://example.invalid/attestation.json",
                "--attestation-file",
                str(forged),
                package=str(self.tarball),
                output=str(scratch_path / "out.json"),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not conform to attestation.schema.json", completed.stderr)

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

    def test_certified_status_rejects_a_real_preview_attestation(self) -> None:
        # scripts/build-certification-attestation.py only ever emits
        # status="preview" by design (it explicitly rejects non-preview
        # manifest input) - a real, correctly-generated, passing attestation
        # must still be refused as certified backing, because it never
        # claimed to be one.
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as scratch:
            scratch_path = Path(scratch)
            attestation_path = scratch_path / "attestation.json"
            attestation_completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build-certification-attestation.py"),
                    "--package",
                    str(self.tarball),
                    "--output",
                    str(attestation_path),
                    "--source-commit",
                    head_commit,
                    "--browser-name",
                    "test-harness",
                    "--browser-version",
                    "n/a",
                    "--operating-system",
                    "test",
                    "--automated-evidence",
                    "urn:test:manifest-certified-status",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=GENERATOR_TIMEOUT_SECONDS,
            )
            self.assertEqual(
                attestation_completed.returncode, 0, attestation_completed.stderr
            )
            attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
            self.assertEqual(attestation["status"], "preview")

            completed = run_generator(
                "--status",
                "certified",
                "--source-commit",
                head_commit,
                "--attestation",
                "https://github.com/wpmoo-org/ui/releases/download/v1.0.0/attestation.json",
                "--attestation-file",
                str(attestation_path),
                package=str(self.tarball),
                output=str(scratch_path / "out.json"),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("not 'certified'", completed.stderr)

    def test_certified_status_accepts_a_matching_certified_attestation(self) -> None:
        # No tool in this repo produces status="certified" yet - that
        # requires the human/manual-acceptance evidence Phase 6 doesn't
        # generate. This constructs a schema-valid certified attestation
        # by hand to test the manifest generator's own validation in
        # isolation from that still-missing upstream generator.
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        package_sha256 = hashlib.sha256(self.tarball.read_bytes()).hexdigest()
        core_version = json.loads(
            (ROOT / "package.json").read_text(encoding="utf-8")
        )["version"]
        certified_attestation_document = {
            "schemaVersion": "0.1",
            "status": "certified",
            "scope": "core",
            "coreVersion": core_version,
            "sourceCommit": head_commit,
            "createdAt": "2026-08-06T00:00:00Z",
            "result": "passed",
            "package": {
                "name": "@wpmoo/ui",
                "version": core_version,
                "filename": self.tarball.name,
                "sha256": package_sha256,
                "manifestSha256": "0" * 64,
            },
            "bootstrap": [
                {"lane": "canonical", "version": "5.3.3", "result": "passed"}
            ],
            "browsers": [
                {
                    "name": "Chromium",
                    "version": "test",
                    "operatingSystem": "test",
                    "mode": "automated",
                    "result": "passed",
                }
            ],
            "components": [],
            "automatedRuns": [
                {
                    "name": "test-harness",
                    "result": "passed",
                    "evidence": "urn:test:manifest-certified-status",
                }
            ],
            "manualReviews": [],
            "realDevices": [],
            "waivers": [],
            "limitations": [],
        }
        with tempfile.TemporaryDirectory() as scratch:
            scratch_path = Path(scratch)
            attestation_path = scratch_path / "attestation.json"
            attestation_path.write_text(
                json.dumps(certified_attestation_document), encoding="utf-8"
            )

            output_path = scratch_path / "out.json"
            completed = run_generator(
                "--status",
                "certified",
                "--source-commit",
                head_commit,
                "--attestation",
                "https://github.com/wpmoo-org/ui/releases/download/v1.0.0/attestation.json",
                "--attestation-file",
                str(attestation_path),
                package=str(self.tarball),
                output=str(output_path),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            manifest = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["status"], "certified")
        self.assertEqual(manifest["sourceCommit"], head_commit)
        errors = list(
            Draft202012Validator(
                json.loads(SCHEMA.read_text(encoding="utf-8"))
            ).iter_errors(manifest)
        )
        self.assertEqual(errors, [], [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()
