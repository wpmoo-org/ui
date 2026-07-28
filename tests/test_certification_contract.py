from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CERTIFICATION_ROOT = ROOT / "src/certification"


class CertificationContractTests(unittest.TestCase):
    def _read_json(self, relative_path: str) -> dict | list:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_evidence_inventory_matches_the_live_component_registry(self) -> None:
        inventory = self._read_json("src/certification/evidence-inventory.json")
        registry = self._read_json("src/registry/components.json")
        inventory_slugs = {component["slug"] for component in inventory["components"]}
        registry_slugs = {component["slug"] for component in registry}

        self.assertEqual(len(inventory["components"]), 40)
        self.assertEqual(inventory_slugs, registry_slugs)
        self.assertEqual(
            {component["slug"] for component in inventory["plannedComponents"]},
            {"context-menu", "data-table"},
        )

    def test_every_evidence_profile_partitions_all_categories_once(self) -> None:
        inventory = self._read_json("src/certification/evidence-inventory.json")
        categories = set(inventory["categories"])
        tier_counts = Counter()

        for profile_name, profile in inventory["profiles"].items():
            with self.subTest(profile=profile_name):
                values = (
                    profile["existing"]
                    + profile["missing"]
                    + profile["not-applicable"]
                    + profile["manual"]
                )
                self.assertEqual(len(values), len(set(values)))
                self.assertEqual(set(values), categories)

        for component in inventory["components"]:
            profile = inventory["profiles"][component["profile"]]
            tier_counts[profile["tier"]] += 1
            for evidence_path in component["evidence"]:
                self.assertTrue((ROOT / evidence_path).is_file(), evidence_path)

        self.assertEqual(tier_counts, {0: 24, 1: 6, 2: 5, 3: 5})

    def test_pilot_evidence_keeps_release_claims_honest(self) -> None:
        pilot = self._read_json("src/certification/pilot-evidence.json")
        manifest = self._read_json("certification.json")
        components = {component["slug"]: component for component in pilot["components"]}

        self.assertEqual(pilot["status"], "preview")
        self.assertEqual(pilot["releaseClaim"], "none")
        self.assertEqual(
            list(components),
            ["badge", "accordion", "dialog", "combobox", "sidebar"],
        )
        self.assertEqual(components["badge"]["status"], "preview-passed")
        self.assertEqual(components["accordion"]["status"], "preview-passed")
        self.assertEqual(components["dialog"]["status"], "preview-passed")
        self.assertEqual(components["combobox"]["status"], "preview-passed")
        self.assertEqual(components["sidebar"]["status"], "preview-passed")
        for component_slug in components:
            for evidence_path in components[component_slug]["automatedEvidence"]:
                self.assertTrue((ROOT / evidence_path).is_file(), evidence_path)
        self.assertEqual(manifest["status"], "preview")
        self.assertEqual(manifest["certifiedComponents"], [])

    def test_phase_one_evidence_tracks_t0_backfill(self) -> None:
        phase_one = self._read_json("src/certification/phase-1-evidence.json")
        manifest = self._read_json("certification.json")
        components = {
            component["slug"]: component for component in phase_one["components"]
        }
        expected_phases = {
            "input": "1A",
            "textarea": "1A",
            "input-group": "1A",
            "select": "1A",
            "checkbox": "1A",
            "radio-group": "1A",
            "switch": "1A",
            "field": "1A",
            "button": "1B",
            "button-group": "1B",
            "card": "1B",
        }

        self.assertEqual(phase_one["status"], "backfill")
        self.assertEqual(phase_one["releaseTarget"], "0.6.0")
        self.assertEqual(phase_one["releaseClaim"], "none")
        self.assertEqual(list(components), list(expected_phases))
        for component_slug in components:
            with self.subTest(component=component_slug):
                self.assertEqual(
                    components[component_slug]["phase"],
                    expected_phases[component_slug],
                )
                self.assertEqual(components[component_slug]["status"], "backfill-passed")
                self.assertEqual(components[component_slug]["tier"], 0)
                self.assertIn(
                    "lifecycle",
                    components[component_slug]["evidence"]["not-applicable"],
                )
                for evidence_path in components[component_slug]["automatedEvidence"]:
                    self.assertTrue((ROOT / evidence_path).is_file(), evidence_path)
                for evidence_url in components[component_slug]["bootstrapEvidence"]:
                    parsed_url = urlparse(evidence_url)
                    self.assertEqual(parsed_url.scheme, "https", evidence_url)
                    self.assertIn(
                        parsed_url.netloc,
                        {"getbootstrap.com", "github.com"},
                        evidence_url,
                    )
        self.assertEqual(manifest["status"], "preview")
        self.assertEqual(manifest["certifiedComponents"], [])

    def test_preview_attestation_is_built_from_the_real_tarball(self) -> None:
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
            output = temporary_root / "attestation.json"
            build_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build-certification-attestation.py"),
                    "--package",
                    str(tarball),
                    "--output",
                    str(output),
                    "--source-commit",
                    "a" * 40,
                    "--browser-name",
                    "Chromium",
                    "--browser-version",
                    "test",
                    "--operating-system",
                    "test",
                    "--automated-evidence",
                    "https://github.com/wpmoo-org/ui/actions/runs/example",
                    "--created-at",
                    "2026-07-27T00:00:00Z",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(build_result.returncode, 0, build_result.stderr)
            attestation = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(attestation["status"], "preview")
            self.assertEqual(attestation["scope"], "phase-0-pilot")
            self.assertEqual(attestation["result"], "passed")
            self.assertEqual(attestation["sourceCommit"], "a" * 40)
            self.assertEqual(attestation["createdAt"], "2026-07-27T00:00:00Z")
            self.assertEqual(
                attestation["package"]["version"],
                self._read_json("package.json")["version"],
            )
            self.assertRegex(attestation["package"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(
                attestation["package"]["manifestSha256"],
                r"^[0-9a-f]{64}$",
            )
            self.assertEqual(
                [component["slug"] for component in attestation["components"]],
                ["badge", "accordion", "dialog", "combobox", "sidebar"],
            )
            self.assertEqual(attestation["manualReviews"], [])
            self.assertEqual(attestation["realDevices"], [])
            self.assertEqual(attestation["waivers"], [])
            self.assertIn("not a complete release certification", attestation["limitations"][0]["description"])

    def test_core_certification_sources_do_not_name_commercial_bridges(self) -> None:
        public_sources = [
            ROOT / "SUPPORT.md",
            ROOT / "certification.json",
            *CERTIFICATION_ROOT.glob("*.json"),
        ]
        forbidden_terms = ("wordpress", "odoo")

        for source_path in public_sources:
            content = source_path.read_text(encoding="utf-8").lower()
            with self.subTest(source=source_path.name):
                for term in forbidden_terms:
                    self.assertNotIn(term, content)


if __name__ == "__main__":
    unittest.main()
