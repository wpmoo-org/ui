from __future__ import annotations

import ast
import copy
import json
import re
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "src/registry/layouts.json"
EVIDENCE = ROOT / "src/certification/layout-evidence.json"
REQUIRED_ROOT_KEYS = {"schemaVersion", "manualReleaseGates", "layouts"}
REQUIRED_LAYOUT_KEYS = {
    "contractVersion",
    "status",
    "source",
    "componentExports",
    "fixtureUrls",
    "tests",
    "matrix",
    "sourceCommit",
    "acceptedAt",
}
REQUIRED_MATRIX_KEYS = {"shellModes", "viewports", "directions", "themes", "zoom"}
GENERATED_FIXTURE_STEMS = {
    "layout-page-base": "layout-page",
    "layout-page-sm": "layout-page",
    "layout-page-md": "layout-page",
    "layout-page-lg": "layout-page",
    "layout-page-xxl": "layout-page",
    "layout-page-fluid": "layout-page",
    "layout-app-contained": "layout-app",
    "layout-app-right": "layout-app",
    "layout-app-none": "layout-app",
}
STATUS_VALUES = {"preview", "ready"}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
TEST_REFERENCE_PATTERN = re.compile(
    r"^(?P<module>tests(?:\.[A-Za-z_]\w*)+)"
    r"(?::(?P<class>[A-Za-z_]\w*)"
    r"(?:\.(?P<method>[A-Za-z_]\w*))?)?$"
)


def _fixture_source(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return None
    path = parsed.path.strip("/")
    prefix = "tests/fixtures/certification/"
    if not path.startswith(prefix):
        return None
    relative_path = path.removeprefix(prefix)
    name = Path(relative_path).name
    if name == "index.html":
        name = Path(relative_path).parent.name
    elif name.endswith(".html"):
        name = name.removesuffix(".html")
    name = GENERATED_FIXTURE_STEMS.get(name, name)
    return ROOT / prefix / f"{name}.html.jinja"


def _test_source(reference: str) -> tuple[Path, str | None, str | None] | None:
    match = TEST_REFERENCE_PATTERN.fullmatch(reference)
    if match is None:
        return None
    module_path = match.group("module").split(".")
    return (
        ROOT / Path(*module_path).with_suffix(".py"),
        match.group("class"),
        match.group("method"),
    )


def _test_reference_exists(reference: str) -> bool:
    parsed = _test_source(reference)
    if parsed is None:
        return False
    source, class_name, method_name = parsed
    if not source.is_file():
        return False
    if class_name is None:
        return True

    try:
        tree = ast.parse(source.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False

    test_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if test_class is None:
        return False
    if method_name is None:
        return True
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
        for node in test_class.body
    )


def _is_rfc3339_timestamp(value: object) -> bool:
    if not isinstance(value, str) or RFC3339_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def evidence_errors(payload: object, registry: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["evidence root must be an object"]
    if set(payload) != REQUIRED_ROOT_KEYS:
        errors.append(
            "evidence root keys must be exactly schemaVersion, manualReleaseGates, and layouts"
        )
    if payload.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    manual_release_gates = payload.get("manualReleaseGates")
    if not isinstance(manual_release_gates, list) or not all(
        isinstance(value, str) for value in manual_release_gates
    ):
        errors.append("manualReleaseGates must be a string array")
    layouts = payload.get("layouts")
    if not isinstance(layouts, dict):
        return errors + ["layouts must be an object"]

    registry_by_slug = {entry["slug"]: entry for entry in registry}
    if set(layouts) != set(registry_by_slug):
        errors.append("evidence layouts must match the layout registry exactly")

    for slug, evidence in layouts.items():
        if not isinstance(evidence, dict):
            errors.append(f"{slug}: evidence must be an object")
            continue
        if set(evidence) != REQUIRED_LAYOUT_KEYS:
            errors.append(f"{slug}: evidence keys are incomplete or unknown")
        expected = registry_by_slug.get(slug)
        if expected is not None and evidence.get("source") != expected["source"]:
            errors.append(f"{slug}: evidence source does not match registry source")
        if evidence.get("contractVersion") != 1:
            errors.append(f"{slug}: contractVersion must be 1")
        status = evidence.get("status")
        if status not in STATUS_VALUES:
            errors.append(f"{slug}: status must be preview or ready")

        component_exports = evidence.get("componentExports")
        if not isinstance(component_exports, list) or not all(
            isinstance(value, str) for value in component_exports
        ):
            errors.append(f"{slug}: componentExports must be a string array")
        elif slug == "page" and component_exports:
            errors.append("page: componentExports must be empty")
        elif slug == "app" and component_exports != [
            "sidebar",
            "sidebar_header",
            "sidebar_content",
            "sidebar_footer",
        ]:
            errors.append("app: componentExports must record the Sidebar anatomy")

        arrays = {
            field: evidence.get(field)
            for field in ("fixtureUrls", "tests")
        }
        matrix = evidence.get("matrix")
        if not isinstance(matrix, dict) or set(matrix) != REQUIRED_MATRIX_KEYS:
            errors.append(f"{slug}: matrix keys are incomplete or unknown")
            matrix = {}
        for field, values in {**arrays, **matrix}.items():
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                errors.append(f"{slug}: {field} must be a string array")

        if status == "preview":
            if evidence.get("sourceCommit") is not None:
                errors.append(f"{slug}: preview sourceCommit must be null")
            if evidence.get("acceptedAt") is not None:
                errors.append(f"{slug}: preview acceptedAt must be null")
        elif status == "ready":
            if not all(arrays[field] for field in arrays):
                errors.append(f"{slug}: ready evidence requires fixture URLs and tests")
            if not all(matrix.get(field) for field in REQUIRED_MATRIX_KEYS):
                errors.append(f"{slug}: ready evidence requires the full matrix")
            if not isinstance(evidence.get("sourceCommit"), str) or not SHA_PATTERN.fullmatch(
                evidence["sourceCommit"]
            ):
                errors.append(f"{slug}: ready sourceCommit must be a lowercase full SHA")
            accepted_at = evidence.get("acceptedAt")
            if not _is_rfc3339_timestamp(accepted_at):
                errors.append(f"{slug}: ready acceptedAt must be an RFC 3339 timestamp")

        for reference in arrays["tests"] if isinstance(arrays["tests"], list) else []:
            if not _test_reference_exists(reference):
                errors.append(f"{slug}: test reference does not exist: {reference}")
        for url in arrays["fixtureUrls"] if isinstance(arrays["fixtureUrls"], list) else []:
            source = _fixture_source(url)
            if source is None or not source.is_file():
                errors.append(f"{slug}: fixture reference does not exist: {url}")

    return errors


class LayoutEvidenceTests(unittest.TestCase):
    def _read_json(self, path: Path) -> object:
        self.assertTrue(path.is_file(), f"Missing required contract file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.registry = self._read_json(REGISTRY)
        self.evidence = self._read_json(EVIDENCE)

    def test_preview_evidence_has_the_exact_structural_shape(self) -> None:
        self.assertEqual(evidence_errors(self.evidence, self.registry), [])
        for slug, entry in self.evidence["layouts"].items():
            with self.subTest(slug=slug):
                self.assertEqual(entry["status"], "preview")
                self.assertIsNone(entry["sourceCommit"])
                self.assertIsNone(entry["acceptedAt"])

    def test_invalid_status_and_unknown_keys_are_rejected(self) -> None:
        invalid = copy.deepcopy(self.evidence)
        invalid["unexpected"] = True
        invalid["layouts"]["page"]["status"] = "accepted"
        invalid["layouts"]["page"]["unknown"] = True

        errors = evidence_errors(invalid, self.registry)
        self.assertTrue(any("root keys" in error for error in errors))
        self.assertTrue(any("status must be preview or ready" in error for error in errors))
        self.assertTrue(any("keys are incomplete or unknown" in error for error in errors))

    def test_ready_status_requires_complete_immutable_evidence(self) -> None:
        invalid = copy.deepcopy(self.evidence)
        page = invalid["layouts"]["page"]
        page["status"] = "ready"
        page["fixtureUrls"] = []
        page["tests"] = []
        page["matrix"] = {field: [] for field in REQUIRED_MATRIX_KEYS}

        errors = evidence_errors(invalid, self.registry)
        self.assertTrue(any("ready evidence requires fixture URLs and tests" in error for error in errors))
        self.assertTrue(any("ready evidence requires the full matrix" in error for error in errors))
        self.assertTrue(any("ready sourceCommit" in error for error in errors))
        self.assertTrue(any("ready acceptedAt" in error for error in errors))

    def test_mismatched_sources_and_missing_references_are_rejected(self) -> None:
        invalid = copy.deepcopy(self.evidence)
        page = invalid["layouts"]["page"]
        page["source"] = "src/layouts/not-page.html.jinja"
        page["tests"] = ["tests.test_evidence:DefinitelyMissing"]
        page["fixtureUrls"] = ["/tests/fixtures/certification/layout-missing/"]

        errors = evidence_errors(invalid, self.registry)
        self.assertTrue(any("source does not match" in error for error in errors))
        self.assertTrue(any("test reference does not exist" in error for error in errors))
        self.assertTrue(any("fixture reference does not exist" in error for error in errors))

    def test_ready_timestamp_requires_rfc3339_timezone_and_valid_calendar_values(self) -> None:
        invalid = copy.deepcopy(self.evidence)
        page = invalid["layouts"]["page"]
        page["status"] = "ready"
        page["sourceCommit"] = "a" * 40
        page["matrix"] = {
            field: ["covered"]
            for field in ("shellModes", "viewports", "directions", "themes", "zoom")
        }
        page["acceptedAt"] = "not-a-timestampT"

        errors = evidence_errors(invalid, self.registry)
        self.assertTrue(any("ready acceptedAt" in error for error in errors))

        for accepted_at in (
            "2026-09-13T12:34:56Z",
            "2026-09-13T12:34:56.123+02:00",
        ):
            with self.subTest(accepted_at=accepted_at):
                page["acceptedAt"] = accepted_at
                errors = evidence_errors(invalid, self.registry)
                self.assertFalse(any("ready acceptedAt" in error for error in errors))

        for accepted_at in (
            "2026-09-13T12:34:56",
            "2026-02-30T12:34:56Z",
            "2026-09-13T12:34:56+0200",
        ):
            with self.subTest(accepted_at=accepted_at):
                page["acceptedAt"] = accepted_at
                errors = evidence_errors(invalid, self.registry)
                self.assertTrue(any("ready acceptedAt" in error for error in errors))

    def test_test_references_resolve_to_real_unittest_targets(self) -> None:
        invalid = copy.deepcopy(self.evidence)
        page = invalid["layouts"]["page"]
        page["tests"] = [
            "tests.test_layout_evidence:LayoutEvidenceTests.test_preview_evidence_has_the_exact_structural_shape",
            "tests.test_layout_evidence:DefinitelyMissing",
        ]

        errors = evidence_errors(invalid, self.registry)
        self.assertTrue(any("DefinitelyMissing" in error for error in errors))
        self.assertFalse(any("test_preview_evidence" in error for error in errors))

        page["tests"] = [
            "tests.test_layout_evidence:LayoutEvidenceTests.test_preview_evidence_has_the_exact_structural_shape"
        ]
        errors = evidence_errors(invalid, self.registry)
        self.assertFalse(any("test reference does not exist" in error for error in errors))

        page["tests"] = ["tests.test_layout_evidence.py"]
        errors = evidence_errors(invalid, self.registry)
        self.assertTrue(any("test reference does not exist" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
