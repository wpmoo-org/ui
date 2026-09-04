#!/usr/bin/env python3
"""Run Moo UI test tiers and resolve CI tier selection.

The default feedback loop should be small on ordinary ``dev`` pushes, while
release, publish, and ``main`` events keep the full gate. This script is the
single place that maps tier names to commands and changed paths to the
smallest safe tier.
"""

from __future__ import annotations

import argparse
import ast
from fnmatch import fnmatch
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

TIERS = ("quick", "browser-smoke", "browser-full", "release")
TIER_ORDER = {tier: index for index, tier in enumerate(TIERS)}

QUICK_BASE_MODULES = [
    "tests.test_build",
    "tests.test_core_docs_boundary",
    "tests.test_catalog",
    "tests.test_catalog_js",
    "tests.test_code_examples",
    "tests.test_bootstrap_compatibility_runner",
    "tests.test_browser_harness",
    "tests.test_dev",
    "tests.test_design_gates",
    "tests.test_source_format",
    "tests.test_test_tiers",
]

BROWSER_SMOKE_MODULES = [
    "tests.test_catalog_browser",
    "tests.test_codepen_modal_browser",
    "tests.test_datepicker_browser",
    "tests.test_slider_browser",
    "tests.test_toast_browser",
    "tests.test_examples_forms_browser",
]

BROWSER_FULL_MODULES = [
    *BROWSER_SMOKE_MODULES,
    "tests.test_certification_browser",
    "tests.test_datatable_browser",
    "tests.test_conformance_runner.ConformanceRunnerTests",
    "tests.test_conformance_kit_packaging.PackagingTests."
    "test_extracted_artifact_is_self_sufficient",
    "tests.test_host_shell.HostShellTests.test_runner_passes_against_the_host_shell",
]

RELEASE_PATTERNS = [
    ".github/workflows/**",
    ".github/pull_request_template.md",
    "package.json",
    "package-lock.json",
    "certification.json",
    "conformance/**",
    "scripts/rehearse-rc.py",
    "scripts/build-certification-*",
    "scripts/package-conformance-kit.py",
    "scripts/verify_package_contents.py",
    "tests/test_package.py",
    "tests/test_rehearse_rc.py",
    "tests/test_certification_contract.py",
    "tests/test_certification_manifest.py",
]

BROWSER_FULL_PATTERNS = [
    "src/js/components/datatable.js",
    "tests/test_*_browser.py",
    "tests/test_certification_browser.py",
    "tests/test_datatable_browser.py",
    "tests/test_conformance_runner.py",
    "tests/test_conformance_kit_packaging.py",
    "tests/test_host_shell.py",
    "tests/helpers/browser_harness.py",
    "conformance/**",
]

BROWSER_SMOKE_PATTERNS = [
    "site/static/js/**",
    "src/js/components/combobox.js",
    "src/js/components/context-menu.js",
    "src/js/components/datepicker.js",
    "src/js/components/datatable.js",
    "src/js/components/slider.js",
    "src/js/components/toast.js",
    "tests/fixtures/certification/datepicker.html",
    "tests/fixtures/certification/slider.html",
    "tests/fixtures/certification/toast.html",
]

QUICK_PATTERNS = [
    "*.md",
    "docs/**",
    "site/src/**",
    "site/static/images/**",
    "src/components/**",
    "src/registry/**",
    "src/certification/evidence-inventory.json",
    "scss/**",
    "build.py",
    "dev.py",
    "tests/helpers/__init__.py",
    "tests/helpers/node_harness.py",
    "tests/test_*.py",
]

BROWSER_MARKERS = (
    "sync_playwright",
    "skip_if_browser_launch_is_sandboxed",
)


def python_executable() -> str:
    return sys.executable


def normalize_tier(value: str | None) -> str:
    if not value:
        return "auto"
    normalized = value.strip().lower().replace("_", "-")
    if normalized.startswith("test-"):
        normalized = normalized.removeprefix("test-")
    if normalized in {*TIERS, "auto"}:
        return normalized
    return "release"


def modules_for(tier: str, changed_paths: Iterable[str] | None = None) -> list[str]:
    normalized = normalize_tier(tier)
    if normalized == "quick":
        return unique([*QUICK_BASE_MODULES, *source_modules_for_paths(changed_paths or [])])
    if normalized == "browser-smoke":
        return list(BROWSER_SMOKE_MODULES)
    if normalized == "browser-full":
        return list(BROWSER_FULL_MODULES)
    if normalized == "release":
        return []
    raise ValueError(f"tier {tier!r} cannot be expanded without changed paths")


def commands_for(
    tier: str,
    changed_paths: Iterable[str] | None = None,
) -> list[list[str]]:
    normalized = normalize_tier(tier)
    python = python_executable()
    if normalized == "quick":
        return [[python, "-m", "unittest", "-v", "-f", *modules_for("quick", changed_paths)]]
    if normalized == "browser-smoke":
        return [[python, "-m", "unittest", "-v", *BROWSER_SMOKE_MODULES]]
    if normalized == "browser-full":
        return [[python, "-m", "unittest", "-v", *BROWSER_FULL_MODULES]]
    if normalized == "release":
        return [
            [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
            [python, "build.py"],
            ["npm", "pack", "--dry-run", "--json"],
            [python, "scripts/verify_package_contents.py"],
            [python, "scripts/rehearse-rc.py"],
        ]
    raise ValueError(f"tier {tier!r} cannot be run directly")


def needs_playwright(tier: str) -> bool:
    return normalize_tier(tier) in {"browser-smoke", "browser-full", "release"}


def _path_matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def classify_path(path: str) -> str:
    normalized = path.removeprefix("./")
    if _path_matches(normalized, RELEASE_PATTERNS):
        return "release"
    if _path_matches(normalized, BROWSER_FULL_PATTERNS):
        return "browser-full"
    if _path_matches(normalized, BROWSER_SMOKE_PATTERNS):
        return "browser-smoke"
    if _path_matches(normalized, QUICK_PATTERNS):
        return "quick"
    return "release"


def classify_paths(paths: Iterable[str]) -> str:
    tiers = [classify_path(path) for path in paths if path]
    if not tiers:
        return "release"
    return max(tiers, key=lambda tier: TIER_ORDER[tier])


def source_modules_for_paths(paths: Iterable[str]) -> list[str]:
    modules: list[str] = []
    for path in paths:
        module = source_module_for_path(path)
        if module:
            modules.append(module)
    return unique(modules)


def source_module_for_path(path: str) -> str | None:
    normalized = path.removeprefix("./")
    if _path_matches(normalized, RELEASE_PATTERNS + BROWSER_FULL_PATTERNS):
        return None
    if normalized.startswith("tests/test_") and normalized.endswith(".py"):
        module = "tests." + Path(normalized).stem
        return module if _test_module_exists(module) else None

    slug = component_slug_from_path(normalized)
    if not slug:
        return None
    module = f"tests.test_{slug.replace('-', '_')}"
    return module if _test_module_exists(module) else None


def component_slug_from_path(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) >= 3 and parts[:2] == ["src", "components"]:
        return parts[2].removesuffix(".html.jinja")
    if len(parts) >= 3 and parts[:2] == ["scss", "components"]:
        return parts[2].removeprefix("_").removesuffix(".scss")
    if len(parts) >= 4 and parts[:3] == ["src", "js", "components"]:
        return parts[3].removesuffix(".js")
    if len(parts) >= 5 and parts[:4] == ["site", "src", "pages", "components"]:
        return parts[4].removesuffix(".html.jinja")
    if len(parts) >= 4 and parts[:3] == ["tests", "fixtures", "certification"]:
        return parts[3].removesuffix(".html")
    return None


def _test_module_exists(module: str) -> bool:
    path = ROOT / Path(*module.split(".")).with_suffix(".py")
    return path.is_file()


def unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def changed_paths_from_git(base: str | None, head: str | None) -> list[str]:
    if not base or not head or set(base) == {"0"}:
        return []
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def resolve_tier(
    requested_tier: str | None,
    *,
    event_name: str | None,
    ref_name: str | None,
    changed_paths: Iterable[str],
) -> str:
    requested = normalize_tier(requested_tier)
    event = event_name or ""
    ref = ref_name or ""

    if requested != "auto":
        return requested
    if event == "pull_request":
        return "release"
    if ref == "main" or ref.startswith("refs/tags/") or ref.startswith("v"):
        return "release"
    if event == "push" and ref == "dev":
        return classify_paths(changed_paths)
    if event == "workflow_dispatch":
        return classify_paths(changed_paths)
    return "release"


def browser_launch_point_modules(selectors: Iterable[str]) -> list[str]:
    offenders: list[str] = []
    for selector in selectors:
        module_name = selector.split(".", 2)[:2]
        if len(module_name) < 2:
            continue
        relative = Path(*module_name).with_suffix(".py")
        path = ROOT / relative
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        if _has_runnable_browser_test_case(source):
            offenders.append(selector)
    return offenders


def _has_runnable_browser_test_case(source: str) -> bool:
    tree = ast.parse(source)
    mixins_with_browser_markers = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and _class_contains_browser_marker(node)
    }
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue
        bases = {_base_name(base) for base in node.bases}
        if "unittest.TestCase" in bases or "CatalogTestCase" in bases:
            if node.name.endswith("BrowserTests"):
                return True
            if any(base.endswith("BrowserMixin") for base in bases):
                return True
            if _class_contains_browser_marker(node):
                return True
            if bases.intersection(mixins_with_browser_markers):
                return True
    return False


def _class_contains_browser_marker(node: ast.ClassDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in BROWSER_MARKERS:
            return True
        if isinstance(child, ast.Attribute) and child.attr in BROWSER_MARKERS:
            return True
        if isinstance(child, ast.Constant) and child.value == "playwright.sync_api":
            return True
    return False


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def run_tier(
    tier: str,
    *,
    dry_run: bool = False,
    changed_paths: Iterable[str] | None = None,
) -> int:
    normalized = normalize_tier(tier)
    if normalized == "auto":
        raise SystemExit("run requires an explicit tier; use resolve first")

    commands = commands_for(normalized, changed_paths)
    if normalized == "release":
        validate_release_commands(commands)
    index = 0
    while index < len(commands):
        command = commands[index]
        if dry_run:
            print(" ".join(command))
            index += 1
            continue
        if command[:4] == ["npm", "pack", "--dry-run", "--json"]:
            verify = commands[index + 1]
            pack = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=npm_env(),
            )
            if pack.returncode != 0:
                sys.stderr.write(pack.stderr)
                return int(pack.returncode)
            verification = subprocess.run(
                verify,
                cwd=ROOT,
                input=pack.stdout,
                check=False,
                capture_output=True,
                text=True,
            )
            sys.stdout.write(verification.stdout)
            sys.stderr.write(verification.stderr)
            if verification.returncode != 0:
                return int(verification.returncode)
            index += 2
            continue
        result = subprocess.run(command, cwd=ROOT, check=False, env=npm_env())
        if result.returncode != 0:
            return int(result.returncode)
        index += 1
    return 0


def validate_release_commands(commands: list[list[str]]) -> None:
    for index, command in enumerate(commands):
        if not is_npm_pack_command(command):
            continue
        verifier = commands[index + 1] if index + 1 < len(commands) else []
        if not is_package_verifier_command(verifier):
            raise SystemExit(
                "release tier command plan must run "
                "scripts/verify_package_contents.py immediately after "
                "npm pack --dry-run --json"
            )


def is_npm_pack_command(command: list[str]) -> bool:
    return command == ["npm", "pack", "--dry-run", "--json"]


def is_package_verifier_command(command: list[str]) -> bool:
    return len(command) >= 2 and command[1:] == ["scripts/verify_package_contents.py"]


def npm_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("npm_config_cache", os.path.join("/tmp", "wpmoo-npm-cache"))
    return env


def write_github_output(path: str, tier: str) -> None:
    with open(path, "a", encoding="utf-8") as output:
        output.write(f"tier={tier}\n")
        output.write(f"needs_playwright={str(needs_playwright(tier)).lower()}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("tier", nargs="?", default="auto")
    resolve.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    resolve.add_argument("--ref-name", default=os.environ.get("GITHUB_REF_NAME", ""))
    resolve.add_argument("--base", default="")
    resolve.add_argument("--head", default=os.environ.get("GITHUB_SHA", ""))
    resolve.add_argument("--path", action="append", dest="paths", default=[])
    resolve.add_argument("--github-output", default="")

    run = subparsers.add_parser("run")
    run.add_argument("tier")
    run.add_argument("--base", default="")
    run.add_argument("--head", default=os.environ.get("GITHUB_SHA", ""))
    run.add_argument("--path", action="append", dest="paths", default=[])
    run.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "resolve":
        paths = args.paths or changed_paths_from_git(args.base, args.head)
        tier = resolve_tier(
            args.tier,
            event_name=args.event_name,
            ref_name=args.ref_name,
            changed_paths=paths,
        )
        if args.github_output:
            write_github_output(args.github_output, tier)
        print(tier)
        return 0

    if args.command == "run":
        paths = args.paths or changed_paths_from_git(args.base, args.head)
        return run_tier(args.tier, dry_run=args.dry_run, changed_paths=paths)

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
