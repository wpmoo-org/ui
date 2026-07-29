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
            "accordion": "1C",
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
            "typography": "1B",
            "kbd": "1B",
            "avatar": "1B",
            "navigation": "1B",
            "separator": "1B",
            "skeleton": "1B",
            "close-button": "1B",
            "breadcrumb": "1B",
            "pagination": "1B",
            "progress": "1B",
            "table": "1B",
            "spinner": "1B",
            "dropdown-menu": "1C",
            "alert": "1C",
            "tabs": "1C",
            "collapsible": "1C",
            "toggle-group": "1C",
        }
        # 1A/1B are Tier 0 form/display primitives where lifecycle never
        # applies (no init/dispose Bootstrap plugin involved). 1C backfills
        # Tier 1 Bootstrap Data API / native-state components: most compose
        # a Bootstrap JS plugin, so lifecycle evidence is real but deferred
        # to the Phase 2 overlay backfill ("missing", not "not-applicable");
        # a later native-state 1C component (Toggle Group) owns no JS plugin,
        # so it stays not-applicable like every Tier 0 component.
        expected_tiers = {slug: 0 for slug in expected_phases}
        for slug in ("accordion", "dropdown-menu", "alert", "tabs", "collapsible", "toggle-group"):
            expected_tiers[slug] = 1
        lifecycle_not_applicable = {
            slug for slug in expected_phases if expected_phases[slug] != "1C"
        }
        lifecycle_not_applicable.add("toggle-group")
        # Accordion was the Phase 0E T1 pilot and already carries full
        # lifecycle evidence (unlike the other 1C components, where it is
        # real but deferred to Phase 2), so it is neither not-applicable
        # nor missing here.
        lifecycle_existing = {"accordion"}

        self.assertEqual(phase_one["status"], "backfill")
        self.assertEqual(phase_one["releaseTarget"], "0.6.0")
        self.assertEqual(phase_one["releaseClaim"], "none")
        self.assertEqual(
            phase_one["bootstrapCompatibility"]["evidence"],
            "src/certification/bootstrap-compatibility.json",
        )
        self.assertEqual(phase_one["bootstrapCompatibility"]["status"], "passed")
        self.assertEqual(list(components), list(expected_phases))
        for component_slug in components:
            with self.subTest(component=component_slug):
                self.assertEqual(
                    components[component_slug]["phase"],
                    expected_phases[component_slug],
                )
                self.assertEqual(components[component_slug]["status"], "backfill-passed")
                self.assertEqual(
                    components[component_slug]["tier"],
                    expected_tiers[component_slug],
                )
                if component_slug in lifecycle_existing:
                    self.assertIn(
                        "lifecycle",
                        components[component_slug]["evidence"]["existing"],
                    )
                elif component_slug in lifecycle_not_applicable:
                    self.assertIn(
                        "lifecycle",
                        components[component_slug]["evidence"]["not-applicable"],
                    )
                else:
                    self.assertIn(
                        "lifecycle",
                        components[component_slug]["evidence"]["missing"],
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

    def test_phase_two_evidence_tracks_t2_t3_backfill(self) -> None:
        phase_two = self._read_json("src/certification/phase-2-evidence.json")
        manifest = self._read_json("certification.json")
        components = {
            component["slug"]: component for component in phase_two["components"]
        }
        expected_components = {
            "tooltip": {"phase": "2A", "tier": 2},
            "popover": {"phase": "2A", "tier": 2},
            "dialog": {"phase": "2A", "tier": 2},
            "toast": {"phase": "2A", "tier": 2},
            "sheet": {"phase": "2A", "tier": 2},
            "sidebar": {"phase": "2B", "tier": 3},
            "form": {"phase": "2B", "tier": 3, "lifecycle": "not-applicable"},
        }

        self.assertEqual(phase_two["status"], "backfill")
        self.assertEqual(phase_two["releaseTarget"], "0.7.0")
        self.assertEqual(phase_two["releaseClaim"], "none")
        self.assertEqual(list(components), list(expected_components))
        for component_slug, expected in expected_components.items():
            with self.subTest(component=component_slug):
                component = components[component_slug]
                self.assertEqual(component["phase"], expected["phase"])
                self.assertEqual(component["tier"], expected["tier"])
                self.assertEqual(component["status"], "backfill-passed")
                if expected.get("lifecycle") == "not-applicable":
                    self.assertIn(
                        "lifecycle",
                        component["evidence"]["not-applicable"],
                    )
                else:
                    self.assertIn("lifecycle", component["evidence"]["existing"])
                self.assertIn("real-device", component["evidence"]["manual"])
                self.assertIn("host-conformance", component["evidence"]["missing"])
                for evidence_path in component["automatedEvidence"]:
                    self.assertTrue((ROOT / evidence_path).is_file(), evidence_path)
                for evidence_url in component["bootstrapEvidence"]:
                    parsed_url = urlparse(evidence_url)
                    self.assertEqual(parsed_url.scheme, "https", evidence_url)
                    self.assertIn(
                        parsed_url.netloc,
                        {"getbootstrap.com", "github.com"},
                        evidence_url,
                    )
        self.assertEqual(manifest["status"], "preview")
        self.assertEqual(manifest["certifiedComponents"], [])

    def test_bootstrap_compatibility_evidence_backs_manifest_range(self) -> None:
        compatibility = self._read_json("src/certification/bootstrap-compatibility.json")
        manifest = self._read_json("certification.json")
        package = self._read_json("package.json")
        lanes = compatibility["lanes"]
        lane_versions = [lane["version"] for lane in lanes]

        self.assertEqual(compatibility["status"], "passed")
        self.assertEqual(compatibility["phase"], "1D")
        self.assertEqual(compatibility["releaseTarget"], "0.6.0")
        self.assertTrue((ROOT / compatibility["runner"]).is_file())
        self.assertEqual(
            compatibility["verifiedRange"],
            package["peerDependencies"]["bootstrap"],
        )
        self.assertEqual(
            manifest["bootstrap"]["targetRange"],
            package["peerDependencies"]["bootstrap"],
        )
        self.assertEqual(
            manifest["bootstrap"]["verifiedRange"],
            compatibility["verifiedRange"],
        )
        self.assertEqual(manifest["bootstrap"]["testedVersions"], lane_versions)
        self.assertEqual(
            [lane["name"] for lane in lanes],
            ["minimum", "canonical", "latest-5.3.x"],
        )
        self.assertEqual(lane_versions, ["5.3.0", "5.3.3", "5.3.8"])
        self.assertEqual(compatibility["latestResolvedVersion"], "5.3.8")
        self.assertEqual(
            compatibility["browserCases"],
            ["desktop-light-ltr", "mobile-dark-rtl"],
        )
        for lane in lanes:
            with self.subTest(lane=lane["name"]):
                self.assertEqual(lane["source"], f"npm:bootstrap@{lane['version']}")
                self.assertEqual(lane["build"], "passed")
                self.assertEqual(lane["browserCertification"], "passed")

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
