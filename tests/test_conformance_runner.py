import json
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

from tests.helpers.browser_harness import serve_directory
from tests.helpers.browser_harness import skip_if_browser_launch_is_sandboxed

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "conformance" / "fixtures"
RUNNER = ROOT / "conformance" / "runner" / "run.py"
CONTRACT_PATH = ROOT / "conformance" / "contract" / "conformance-contract.json"
REPORT_SCHEMA_PATH = ROOT / "conformance" / "contract" / "report.schema.json"
RUN_TIMEOUT_SECONDS = 600


def load_runner_module():
    spec = importlib.util.spec_from_file_location("conformance_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke_runner(base_url, report_out):
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--base-url",
            base_url,
            "--report-out",
            str(report_out),
        ],
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_SECONDS,
    )


def failed_assertion_summary(report):
    failures = []
    for fixture in report["fixtures"]:
        for category in fixture["categories"]:
            for assertion in category["assertions"]:
                if assertion["status"] != "fail":
                    continue
                reason = assertion.get("reason", "no reason reported")
                failures.append(
                    f"{fixture['name']}::{category['id']}::{assertion['id']}: "
                    f"{reason}"
                )
    return "\n".join(failures)


class ConformanceRunnerCliTests(unittest.TestCase):
    def test_runner_requires_base_url(self):
        process = subprocess.run(
            [sys.executable, str(RUNNER)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(process.returncode, 2)

    def test_runner_writes_report_when_browser_close_loses_driver(self):
        runner = load_runner_module()
        report = {
            "summary": {
                "assertionsPassed": 1,
                "assertionsFailed": 0,
                "assertionsSkipped": 0,
                "result": "pass",
            }
        }

        class PlaywrightManager:
            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, traceback):
                return None

        class Browser:
            def close(self):
                raise Exception("Connection closed while reading from the driver")

        with tempfile.TemporaryDirectory(prefix="moo-close-report-") as scratch:
            report_path = Path(scratch) / "report.json"
            with mock.patch.object(
                runner, "sync_playwright", return_value=PlaywrightManager()
            ), mock.patch.object(
                runner, "launch_browser", return_value=Browser()
            ), mock.patch.object(
                runner, "run_contract", return_value=report
            ):
                status = runner.main(
                    [
                        "--base-url",
                        "http://127.0.0.1:1",
                        "--contract",
                        str(CONTRACT_PATH),
                        "--report-out",
                        str(report_path),
                    ]
                )

            self.assertEqual(status, 0)
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8")),
                report,
            )


class ConformanceRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        skip_if_browser_launch_is_sandboxed()
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.server = serve_directory(FIXTURES_DIR)
        cls.base_url = cls.server.__enter__()
        try:
            cls.report_dir = tempfile.TemporaryDirectory(prefix="moo-conformance-")
            cls.report_path = Path(cls.report_dir.name) / "pass-report.json"
            cls.process = invoke_runner(cls.base_url, cls.report_path)
            cls.report = json.loads(cls.report_path.read_text(encoding="utf-8"))
        except Exception:
            cls.server.__exit__(None, None, None)
            raise

    @classmethod
    def tearDownClass(cls):
        cls.report_dir.cleanup()
        cls.server.__exit__(None, None, None)

    def test_canonical_fixtures_pass_with_exit_code_zero(self):
        self.assertEqual(
            self.process.returncode,
            0,
            "runner stderr:\n"
            f"{self.process.stderr}\n"
            "failed assertions:\n"
            f"{failed_assertion_summary(self.report)}",
        )
        summary = self.report["summary"]
        self.assertEqual(summary["result"], "pass")
        self.assertEqual(summary["assertionsFailed"], 0)
        self.assertGreater(summary["assertionsPassed"], 0)
        self.assertEqual(summary["assertionsSkipped"], 0)

    def test_report_conforms_to_report_schema(self):
        schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(self.report),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual(
            [error.message for error in errors],
            [],
            "runner output does not conform to report.schema.json",
        )

    def test_host_metadata_is_detected(self):
        host = self.report["host"]
        self.assertEqual(host["baseUrl"], self.base_url)
        self.assertEqual(host["servedBootstrapVersion"], "5.3.3")
        self.assertEqual(host["cssRecipeDetected"], "scoped")
        self.assertEqual(self.report["contractVersion"], self.contract["schemaVersion"])

    def test_every_contract_assertion_is_reported_for_its_fixtures(self):
        reported = {
            (fixture["name"], assertion["id"]): assertion
            for fixture in self.report["fixtures"]
            for category in fixture["categories"]
            for assertion in category["assertions"]
        }
        for category in self.contract["categories"]:
            for assertion in category["assertions"]:
                for fixture_name in assertion["fixtures"]:
                    key = (fixture_name, assertion["id"])
                    self.assertIn(key, reported, f"missing {key} in the report")
                    self.assertIn(
                        reported[key]["status"], {"pass", "fail", "skipped"}
                    )

    def test_inert_check_uses_visibility_not_dom_presence(self):
        """Claude's Task 4 note: the listbox is always in the DOM and hidden
        by CSS, so the openedMarker check must be a visibility check."""
        moo_esm = next(
            fixture
            for fixture in self.report["fixtures"]
            if fixture["name"] == "moo-esm"
        )
        assertion = next(
            assertion
            for category in moo_esm["categories"]
            for assertion in category["assertions"]
            if assertion["id"] == "inert-before-init"
        )
        self.assertEqual(assertion["status"], "pass")
        pre_init = assertion["evidence"]["preInit"]
        self.assertGreaterEqual(pre_init["markerCount"], 1)
        self.assertFalse(pre_init["markerVisible"])
        self.assertNotEqual(pre_init["ariaExpanded"], "true")
        self.assertTrue(assertion["evidence"]["opensAfterInit"])

    def test_fault_injection_breaks_the_scoping_category(self):
        with tempfile.TemporaryDirectory(prefix="moo-fault-") as broken_dir:
            broken_fixtures = Path(broken_dir) / "fixtures"
            shutil.copytree(FIXTURES_DIR, broken_fixtures)
            target = broken_fixtures / "static-primitives.html"
            original = target.read_text(encoding="utf-8")
            broken = original.replace('class="moo-ui p-4"', 'class="moo-ui-off p-4"')
            self.assertNotEqual(broken, original)
            target.write_text(broken, encoding="utf-8")

            with serve_directory(broken_fixtures) as broken_url:
                report_path = Path(broken_dir) / "fault-report.json"
                process = invoke_runner(broken_url, report_path)
                report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(
            process.returncode,
            1,
            f"runner stderr:\n{process.stderr}",
        )
        self.assertEqual(report["summary"]["result"], "fail")
        self.assertGreater(report["summary"]["assertionsFailed"], 0)

        static = next(
            fixture
            for fixture in report["fixtures"]
            if fixture["name"] == "static-primitives"
        )
        by_category = {category["id"]: category for category in static["categories"]}
        self.assertEqual(by_category["scoping"]["status"], "fail")
        self.assertEqual(by_category["css-reset"]["status"], "fail")
        self.assertEqual(by_category["asset-order"]["status"], "fail")
        # Out-of-scope host content is still untouched by the broken scope.
        untouched = next(
            assertion
            for assertion in by_category["scoping"]["assertions"]
            if assertion["id"] == "out-of-scope-untouched"
        )
        self.assertEqual(untouched["status"], "pass")
        # Untouched fixtures must still pass fully.
        forms = next(
            fixture for fixture in report["fixtures"] if fixture["name"] == "forms"
        )
        for category in forms["categories"]:
            self.assertEqual(
                category["status"],
                "pass",
                f"forms category {category['id']} regressed under fault injection",
            )


if __name__ == "__main__":
    unittest.main()
