from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-test-tier.py"


def load_tier_runner():
    spec = importlib.util.spec_from_file_location("run_test_tier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestTierRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_tier_runner()

    def test_quick_includes_static_source_and_boundary_contracts(self) -> None:
        modules = self.runner.modules_for("quick")

        self.assertIn("tests.test_build", modules)
        self.assertIn("tests.test_catalog", modules)
        self.assertIn("tests.test_catalog_js", modules)
        self.assertIn("tests.test_code_examples", modules)
        self.assertIn("tests.test_core_docs_boundary", modules)
        self.assertIn("tests.test_test_tiers", modules)
        self.assertNotIn("tests.test_datepicker", modules)
        self.assertNotIn("tests.test_slider", modules)

    def test_quick_adds_changed_component_source_modules(self) -> None:
        modules = self.runner.modules_for(
            "quick",
            changed_paths=[
                "src/components/datepicker.html.jinja",
                "scss/components/_slider.scss",
            ],
        )

        self.assertIn("tests.test_datepicker", modules)
        self.assertIn("tests.test_slider", modules)

    def test_quick_modules_do_not_contain_browser_launch_points(self) -> None:
        offenders = self.runner.browser_launch_point_modules(
            self.runner.modules_for("quick")
        )

        self.assertEqual(offenders, [])

    def test_browser_wrapper_modules_are_detected_as_launch_points(self) -> None:
        offenders = self.runner.browser_launch_point_modules(
            ["tests.test_slider_browser"]
        )

        self.assertEqual(offenders, ["tests.test_slider_browser"])

    def test_browser_tiers_include_smoke_and_full_surfaces(self) -> None:
        self.assertEqual(
            self.runner.modules_for("browser-smoke"),
            [
                "tests.test_catalog_browser",
                "tests.test_codepen_modal_browser",
                "tests.test_datepicker_browser",
                "tests.test_slider_browser",
                "tests.test_toast_browser",
                "tests.test_examples_forms_browser",
            ],
        )
        self.assertIn(
            "tests.test_certification_browser",
            self.runner.modules_for("browser-full"),
        )
        self.assertIn(
            "tests.test_datatable_browser",
            self.runner.modules_for("browser-full"),
        )
        self.assertIn(
            "tests.test_conformance_runner.ConformanceRunnerTests",
            self.runner.modules_for("browser-full"),
        )

    def test_changed_paths_classify_to_smallest_safe_tier(self) -> None:
        cases = [
            (["README.md"], "quick"),
            (["tests/test_core_docs_boundary.py"], "quick"),
            (["site/static/js/codepen-demo.js"], "browser-smoke"),
            (["src/js/components/slider.js"], "browser-smoke"),
            (["src/js/components/datatable.js"], "browser-full"),
            (["tests/test_catalog_browser.py"], "browser-full"),
            (["conformance/runner/run.py"], "release"),
            (["package.json"], "release"),
            ([".github/workflows/ui-ci.yml"], "release"),
            (["unrecognized/generated-output.txt"], "release"),
        ]

        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assertEqual(self.runner.classify_paths(paths), expected)

    def test_event_matrix_keeps_dev_pushes_small_and_release_events_full(self) -> None:
        self.assertEqual(
            self.runner.resolve_tier(
                "auto",
                event_name="push",
                ref_name="dev",
                changed_paths=["README.md"],
            ),
            "quick",
        )
        self.assertEqual(
            self.runner.resolve_tier(
                "auto",
                event_name="pull_request",
                ref_name="refs/pull/1/merge",
                changed_paths=["README.md"],
            ),
            "release",
        )
        self.assertEqual(
            self.runner.resolve_tier(
                "auto",
                event_name="push",
                ref_name="main",
                changed_paths=["README.md"],
            ),
            "release",
        )
        self.assertEqual(
            self.runner.resolve_tier(
                "surprise",
                event_name="workflow_dispatch",
                ref_name="dev",
                changed_paths=["README.md"],
            ),
            "release",
        )

    def test_release_commands_keep_full_boundary_and_rehearsal_steps(self) -> None:
        commands = self.runner.commands_for("release")
        command_text = [" ".join(command) for command in commands]

        self.assertIn(
            f"{self.runner.python_executable()} -m unittest discover -s tests -v",
            command_text,
        )
        self.assertIn(f"{self.runner.python_executable()} build.py", command_text)
        self.assertIn("npm pack --dry-run --json", command_text)
        self.assertIn(
            f"{self.runner.python_executable()} scripts/verify_package_contents.py",
            command_text,
        )
        self.assertIn(
            f"{self.runner.python_executable()} scripts/rehearse-rc.py",
            command_text,
        )

    def test_release_runner_fails_closed_when_npm_pack_loses_verifier(self) -> None:
        python = self.runner.python_executable()
        original_commands_for = self.runner.commands_for
        self.runner.commands_for = lambda _tier, _paths=None: [
            [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
            ["npm", "pack", "--dry-run", "--json"],
            [python, "scripts/rehearse-rc.py"],
        ]
        try:
            with self.assertRaises(SystemExit) as raised:
                self.runner.run_tier("release", dry_run=True)
        finally:
            self.runner.commands_for = original_commands_for

        self.assertIn("verify_package_contents.py", str(raised.exception))

    def test_only_browser_and_release_tiers_need_playwright(self) -> None:
        self.assertFalse(self.runner.needs_playwright("quick"))
        self.assertTrue(self.runner.needs_playwright("browser-smoke"))
        self.assertTrue(self.runner.needs_playwright("browser-full"))
        self.assertTrue(self.runner.needs_playwright("release"))

    def test_ci_selects_tier_and_skips_playwright_for_quick(self) -> None:
        workflow = (ROOT / ".github/workflows/ui-ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Select test tier", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("scripts/run-test-tier.py resolve", workflow)
        self.assertIn("steps.test-tier.outputs.needs_playwright == 'true'", workflow)
        self.assertIn("scripts/run-test-tier.py run", workflow)


if __name__ == "__main__":
    unittest.main()
