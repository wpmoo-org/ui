from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

from tests.helpers import npm_env


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DOCS_ROOT = ROOT.parent / "docs"
CERTIFICATION_ROOT = ROOT / "src/certification"
PUBLIC_COMPONENT_HOOK_SOURCES = (
    ROOT / "src/components",
    ROOT / "src/js/components",
    ROOT / "src/certification",
    ROOT / "site/src/pages/components",
    ROOT / "tests/fixtures/certification",
    ROOT / "conformance/fixtures",
)
BANNED_PUBLIC_MOO_COMPONENT_HOOK = re.compile(r"\bdata-moo-[\w-]+\b")
PUBLIC_MOO_COMPONENT_HOOK_ALLOWLIST = {
    "site/src/pages/components/index.html.jinja": {
        "data-moo-catalog-section",
        "data-moo-catalog-view",
    },
}
ACTIVE_RC3_PLAN_DOCS = (
    PROJECT_DOCS_ROOT / "plans/2026-08-17-chart-datepicker-slider-1-0-0-rc3.md",
)


class CertificationContractTests(unittest.TestCase):
    def _read_json(self, relative_path: str) -> dict | list:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_public_component_hooks_do_not_use_moo_prefixed_data_contracts(self) -> None:
        checked_extensions = {".css", ".html", ".jinja", ".js", ".json", ".md", ".py", ".scss"}
        violations: list[str] = []

        for source_root in PUBLIC_COMPONENT_HOOK_SOURCES:
            for path in source_root.rglob("*"):
                if not path.is_file() or path.suffix not in checked_extensions:
                    continue
                source = path.read_text(encoding="utf-8")
                relative = path.relative_to(ROOT).as_posix()
                allowed = PUBLIC_MOO_COMPONENT_HOOK_ALLOWLIST.get(relative, set())
                matches = sorted(
                    set(BANNED_PUBLIC_MOO_COMPONENT_HOOK.findall(source)) - allowed
                )
                if matches:
                    violations.append(f"{relative}: {', '.join(matches)}")

        self.assertEqual(
            violations,
            [],
            "Public component hooks must use component-owned data-* contracts.",
        )

    def test_active_rc3_plan_docs_match_current_public_component_contracts(self) -> None:
        if not PROJECT_DOCS_ROOT.is_dir():
            self.skipTest("UI project docs are not mounted in this checkout")

        stale_claims: list[str] = []
        banned_patterns = (
            "data-moo-chart",
            "data-moo-slider",
            "vanillajs-datepicker",
        )
        for path in ACTIVE_RC3_PLAN_DOCS:
            source = path.read_text(encoding="utf-8")
            relative = path.relative_to(PROJECT_DOCS_ROOT).as_posix()
            for pattern in banned_patterns:
                if pattern in source:
                    stale_claims.append(f"{relative}: {pattern}")

        self.assertEqual(
            stale_claims,
            [],
            "Active RC.3 plan docs must match the current public component contracts.",
        )

    def test_toast_public_wiring_hooks_are_recorded_in_component_contract(self) -> None:
        if not PROJECT_DOCS_ROOT.is_dir():
            self.skipTest("UI project docs are not mounted in this checkout")

        source = (PROJECT_DOCS_ROOT / "contracts/COMPONENTS.md").read_text(
            encoding="utf-8"
        )
        toast_section = source.split("## Toast Contract", 1)[1].split("\n## ", 1)[0]

        for hook in (
            "data-toast-target",
            'data-toast-template="toast"',
            "data-toast-variant",
            "data-toast-stack",
        ):
            with self.subTest(hook=hook):
                self.assertIn(hook, toast_section)

    def test_evidence_inventory_matches_the_live_component_registry(self) -> None:
        inventory = self._read_json("src/certification/evidence-inventory.json")
        registry = self._read_json("src/registry/components.json")
        inventory_slugs = {component["slug"] for component in inventory["components"]}
        registry_slugs = {component["slug"] for component in registry}

        self.assertEqual(len(inventory["components"]), 45)
        self.assertEqual(inventory_slugs, registry_slugs)
        self.assertEqual(
            {component["slug"] for component in inventory["plannedComponents"]},
            set(),
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

        self.assertEqual(tier_counts, {0: 24, 1: 6, 2: 5, 3: 10})

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

    def test_rc1_manual_acceptance_record_does_not_claim_pass_with_open_checklist(self) -> None:
        source = (
            CERTIFICATION_ROOT
            / "manual-acceptance/2026-08-06-rc1-manual-acceptance.md"
        ).read_text(encoding="utf-8")
        devices_section = source.split("## Test Devices", 1)[1].split("## URLs", 1)[0]
        checked_device_rows = re.findall(
            r"^- \[X\] (?P<device>[^\n]+)\n(?P<body>(?:  - .+\n)+)",
            devices_section,
            flags=re.MULTILINE,
        )

        self.assertTrue(checked_device_rows)
        for device, body in checked_device_rows:
            with self.subTest(device=device):
                self.assertRegex(
                    body,
                    r"Reviewed at \(UTC, ISO-8601\): \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                )
                self.assertNotRegex(body, r"iOS version: \d+\.\d+ \d+")
                if "- Result (passed/failed): passed" in body:
                    self.assertNotIn("- [ ]", source)

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
            "combobox": {"phase": "2B", "tier": 3},
            "alert-dialog": {"phase": "2B", "tier": 3},
            "menubar": {"phase": "2B", "tier": 3},
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

    def test_phase_three_evidence_tracks_t3_components(self) -> None:
        phase_three = self._read_json("src/certification/phase-3-evidence.json")
        manifest = self._read_json("certification.json")
        components = {
            component["slug"]: component for component in phase_three["components"]
        }
        expected_components = {
            "context-menu": {"phase": "3A", "tier": 3},
            "datatable": {
                "phase": "3B",
                "tier": 3,
                "manual_form": "src/certification/manual-acceptance/2026-08-03-datatable-phase-3b.md",
            },
        }

        self.assertEqual(phase_three["status"], "backfill")
        self.assertEqual(phase_three["releaseTarget"], "0.8.0")
        self.assertEqual(phase_three["releaseClaim"], "none")
        self.assertEqual(list(components), list(expected_components))
        for component_slug, expected in expected_components.items():
            with self.subTest(component=component_slug):
                component = components[component_slug]
                self.assertEqual(component["phase"], expected["phase"])
                self.assertEqual(component["tier"], expected["tier"])
                self.assertEqual(component["status"], "backfill-passed")
                self.assertIn("lifecycle", component["evidence"]["existing"])
                self.assertIn("real-device", component["evidence"]["manual"])
                self.assertIn("host-conformance", component["evidence"]["missing"])
                for evidence_path in component["automatedEvidence"]:
                    self.assertTrue((ROOT / evidence_path).is_file(), evidence_path)
                if expected.get("manual_form"):
                    self.assertTrue((ROOT / expected["manual_form"]).is_file())
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

    def test_core_attestation_is_built_from_the_real_tarball(self) -> None:
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
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
                    head_commit,
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

            schema = self._read_json("src/certification/attestation.schema.json")
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(attestation))
            self.assertEqual(errors, [], [error.message for error in errors])

            self.assertEqual(attestation["status"], "preview")
            self.assertEqual(attestation["scope"], "core")
            self.assertEqual(attestation["result"], "passed")
            self.assertEqual(attestation["sourceCommit"], head_commit)
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
            inventory = self._read_json(
                "src/certification/evidence-inventory.json"
            )
            self.assertEqual(
                [component["slug"] for component in attestation["components"]],
                [component["slug"] for component in inventory["components"]],
            )
            self.assertEqual(len(attestation["components"]), 45)
            for component in attestation["components"]:
                self.assertGreaterEqual(len(component["checks"]), 1)
            self.assertEqual(attestation["manualReviews"], [])
            self.assertEqual(attestation["realDevices"], [])
            self.assertEqual(attestation["waivers"], [])
            surfaces = {
                limitation["surface"] for limitation in attestation["limitations"]
            }
            self.assertIn("release", surfaces)
            self.assertIn("browsers", surfaces)

    def test_attestation_rejects_a_source_commit_not_at_the_checkout(self) -> None:
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        foreign_commit = "a" * 40 if head_commit != "a" * 40 else "b" * 40
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            # build-certification-attestation.py rejects a commit mismatch
            # before it ever opens --package as a tarball (it only checks
            # that the path exists), so a real npm pack here would just be
            # slower and less reliable for the same coverage.
            tarball = temporary_root / "placeholder.tgz"
            tarball.write_bytes(b"")
            build_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build-certification-attestation.py"),
                    "--package",
                    str(tarball),
                    "--output",
                    str(temporary_root / "attestation.json"),
                    "--source-commit",
                    foreign_commit,
                    "--browser-name",
                    "Chromium",
                    "--browser-version",
                    "test",
                    "--operating-system",
                    "test",
                    "--automated-evidence",
                    "https://github.com/wpmoo-org/ui/actions/runs/example",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(build_result.returncode, 0)
        self.assertIn("must match the checkout HEAD", build_result.stderr)

    def test_attestation_rejects_a_dirty_worktree(self) -> None:
        # The commit-mismatch test above locks half of the provenance
        # binding; this locks the other half. An untracked scratch file
        # outside the gitignored dist/ is enough to dirty
        # `git status --porcelain` without touching any tracked content
        # that would need restoring.
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        scratch_marker = ROOT / "_test_dirty_worktree_marker.tmp"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            tarball = temporary_root / "placeholder.tgz"
            tarball.write_bytes(b"")
            try:
                scratch_marker.write_text("dirtying the worktree for a test\n")
                build_result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts/build-certification-attestation.py"),
                        "--package",
                        str(tarball),
                        "--output",
                        str(temporary_root / "attestation.json"),
                        "--source-commit",
                        head_commit,
                        "--browser-name",
                        "Chromium",
                        "--browser-version",
                        "test",
                        "--operating-system",
                        "test",
                        "--automated-evidence",
                        "https://github.com/wpmoo-org/ui/actions/runs/example",
                    ],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            finally:
                scratch_marker.unlink(missing_ok=True)
        self.assertNotEqual(build_result.returncode, 0)
        self.assertIn("uncommitted changes", build_result.stderr)

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

    def test_api_freeze_document_matches_live_package_state(self) -> None:
        """Lock the 0.9.0 API freeze: any undocumented removal from the
        public surfaces must fail CI.  Additive exports/files introduced
        by later release candidates (e.g. 1.0.0-rc.3) are tolerated --
        exact equality for those is enforced by the rc.3 freeze test and
        ultimately by the Phase 6 package-surface gate."""
        freeze = self._read_json("src/certification/api-freeze-0.9.0.json")
        package = self._read_json("package.json")
        certification = self._read_json("certification.json")
        schema = self._read_json("src/certification/manifest.schema.json")

        # Frozen 0.9.0 package exports must be a subset of current exports.
        # Removals fail; additive RC.3 entries are allowed.
        live_exports = set(package["exports"].keys())
        frozen_exports = set(freeze["packageExports"])
        removed_exports = frozen_exports - live_exports
        self.assertFalse(
            removed_exports,
            f"0.9.0 frozen exports were removed from package.json: {removed_exports}",
        )

        # Frozen 0.9.0 package files must be a subset of current files.
        # Removals fail; additive RC.3 entries are allowed.
        live_files = set(package["files"])
        frozen_files = set(freeze["packageFiles"])
        removed_files = frozen_files - live_files
        self.assertFalse(
            removed_files,
            f"0.9.0 frozen files were removed from package.json: {removed_files}",
        )

        # Sass facade allow-list must match the real public declarations.
        # Extract variable names from the actual !default declarations in
        # the narrow public partial -- not from facade comments -- so any
        # widening of the public surface (e.g. re-importing the full
        # internal palette into _facade_public.scss) grows the extracted
        # set past the freeze document and fails for real.
        import re
        facade_public_source = (ROOT / "scss/settings/_facade_public.scss").read_text(encoding="utf-8")
        frozen_sass_vars = set(freeze["sassFacadeAllowList"])
        declared_vars = set(re.findall(r'^(\$[\w-]+)\s*:\s*[^;]*!default\s*;', facade_public_source, re.MULTILINE))
        self.assertEqual(frozen_sass_vars, declared_vars,
            "Sass facade allow-list diverged from the freeze document")

        # The facade itself may only import the narrow public partial;
        # importing the full internal palette would re-leak ~35 variables.
        facade_source = (ROOT / "scss/_facade-settings.scss").read_text(encoding="utf-8")
        # Strip comments first so the documented usage recipes in the
        # header are not mistaken for real imports.
        stripped_facade = re.sub(r"/\*.*?\*/", "", facade_source, flags=re.DOTALL)
        stripped_facade = "\n".join(
            line.split("//", 1)[0] for line in stripped_facade.splitlines()
        )
        facade_imports = set(re.findall(r'@import\s+"([^"]+)"\s*;', stripped_facade))
        self.assertEqual(facade_imports, {"settings/facade_public"},
            "facade-settings must import only the narrow public partial")

        # Certification manifest schema required fields must match
        live_required = set(schema["required"])
        frozen_required = set(freeze["certificationManifest"]["requiredFields"])
        self.assertEqual(live_required, frozen_required,
            "manifest.schema.json required fields diverged from the freeze document")

        # Bootstrap support must match certification.json
        self.assertEqual(
            freeze["bootstrapSupport"]["canonicalVersion"],
            certification["bootstrap"]["canonicalVersion"],
        )
        self.assertEqual(
            freeze["bootstrapSupport"]["targetRange"],
            certification["bootstrap"]["targetRange"],
        )
        self.assertEqual(
            freeze["bootstrapSupport"]["testedVersions"],
            certification["bootstrap"]["testedVersions"],
        )

    def test_rc3_api_freeze_declaration_is_well_formed(self) -> None:
        """Validate the 1.0.0-rc.3 freeze document structure, metadata,
        and exact package export/file equality against package.json."""
        freeze = self._read_json("src/certification/api-freeze-1.0.0-rc.3.json")
        package = self._read_json("package.json")
        certification = self._read_json("certification.json")
        schema = self._read_json("src/certification/manifest.schema.json")

        # Freeze document must declare version 1.0.0-rc.3
        self.assertEqual(freeze["freezeVersion"], "1.0.0-rc.3")

        # Sass facade allow-list must match the real public declarations.
        import re
        facade_public_source = (ROOT / "scss/settings/_facade_public.scss").read_text(encoding="utf-8")
        frozen_sass_vars = set(freeze["sassFacadeAllowList"])
        declared_vars = set(re.findall(r'^(\$[\w-]+)\s*:\s*[^;]*!default\s*;', facade_public_source, re.MULTILINE))
        self.assertEqual(frozen_sass_vars, declared_vars,
            "Sass facade allow-list diverged from the freeze document")

        # The facade itself may only import the narrow public partial.
        facade_source = (ROOT / "scss/_facade-settings.scss").read_text(encoding="utf-8")
        stripped_facade = re.sub(r"/\*.*?\*/", "", facade_source, flags=re.DOTALL)
        stripped_facade = "\n".join(
            line.split("//", 1)[0] for line in stripped_facade.splitlines()
        )
        facade_imports = set(re.findall(r'@import\s+"([^"]+)"\s*;', stripped_facade))
        self.assertEqual(facade_imports, {"settings/facade_public"},
            "facade-settings must import only the narrow public partial")

        # Certification manifest schema required fields must match
        live_required = set(schema["required"])
        frozen_required = set(freeze["certificationManifest"]["requiredFields"])
        self.assertEqual(live_required, frozen_required,
            "manifest.schema.json required fields diverged from the freeze document")

        # Bootstrap support must match certification.json
        self.assertEqual(
            freeze["bootstrapSupport"]["canonicalVersion"],
            certification["bootstrap"]["canonicalVersion"],
        )
        self.assertEqual(
            freeze["bootstrapSupport"]["targetRange"],
            certification["bootstrap"]["targetRange"],
        )
        self.assertEqual(
            freeze["bootstrapSupport"]["testedVersions"],
            certification["bootstrap"]["testedVersions"],
        )

        # RC.3 metadata fields
        self.assertEqual(certification["coreVersion"], "1.0.0-rc.3")
        self.assertEqual(certification["status"], "preview")
        self.assertEqual(certification["certifiedComponents"], [])

        # RC.3 ESM module records must be present in the freeze document
        frozen_modules = {m["module"] for m in freeze["esmModules"]}
        self.assertIn("chart.js", frozen_modules)
        self.assertIn("datepicker.js", frozen_modules)
        self.assertIn("slider.js", frozen_modules)

        # RC.3 package exports/files must include the three new entrypoints
        frozen_exports = set(freeze["packageExports"])
        self.assertEqual(
            frozen_exports,
            set(package["exports"]),
            "RC.3 package export freeze diverged from package.json",
        )
        self.assertIn("./chart.js", frozen_exports)
        self.assertIn("./chart.min.js", frozen_exports)
        self.assertIn("./datepicker.js", frozen_exports)
        self.assertIn("./datepicker.min.js", frozen_exports)
        self.assertIn("./slider.js", frozen_exports)

        frozen_files = set(freeze["packageFiles"])
        self.assertEqual(
            frozen_files,
            set(package["files"]),
            "RC.3 package file freeze diverged from package.json",
        )
        self.assertIn("dist/js/chart.js", frozen_files)
        self.assertIn("dist/js/chart.min.js", frozen_files)
        self.assertIn("dist/js/datepicker.js", frozen_files)
        self.assertIn("dist/js/datepicker.min.js", frozen_files)
        self.assertIn("dist/js/slider.js", frozen_files)
        self.assertIn("THIRD_PARTY_NOTICES.md", frozen_files)

        # RC.3 artifact variants must map minified to canonical
        artifact_variants = freeze.get("artifactVariants", {})
        self.assertIn("chart.min.js", artifact_variants)
        self.assertIn("datepicker.min.js", artifact_variants)
        self.assertEqual(artifact_variants["chart.min.js"]["canonical"], "chart.js")
        self.assertEqual(artifact_variants["datepicker.min.js"]["canonical"], "datepicker.js")

        # Datepicker is self-contained Moo UI ESM produced through esbuild; it
        # must not claim a third-party runtime or a bundled relationship.
        datepicker_record = next(
            m for m in freeze["esmModules"] if m["module"] == "datepicker.js"
        )
        self.assertFalse(datepicker_record.get("bundled", True))
        self.assertNotIn("runtime", datepicker_record)
        self.assertEqual(datepicker_record.get("buildTool"), "esbuild")

        # Chart.js stays bundled with its third-party runtime.
        chart_record = next(m for m in freeze["esmModules"] if m["module"] == "chart.js")
        self.assertTrue(chart_record.get("bundled", False))
        self.assertEqual(chart_record.get("runtime"), "chart.js@4.5.1")
        self.assertEqual(chart_record.get("getters"), ["chart", "element"])

        slider_record = next(m for m in freeze["esmModules"] if m["module"] == "slider.js")
        self.assertFalse(slider_record.get("bundled", True))
        self.assertEqual(slider_record.get("nativeElement"), 'input[type="range"]')
        self.assertEqual(
            slider_record.get("markup"),
            {
                "rootClass": "slider",
                "rootAttribute": "data-slider",
                "trackAttribute": "data-slider-track",
                "rangeAttribute": "data-slider-range",
                "inputAttribute": "data-slider-input",
                "outputAttribute": "data-slider-output",
            },
        )

    def test_rc3_freeze_test_docstring_matches_enforced_equality(self) -> None:
        docstring = self.test_rc3_api_freeze_declaration_is_well_formed.__doc__ or ""

        self.assertIn("exact package export/file equality", docstring)
        self.assertNotIn("deferred", docstring)


if __name__ == "__main__":
    unittest.main()
