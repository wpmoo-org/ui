#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Moo UI certification fixtures against a specific Bootstrap "
            "5.3.x package without mutating the source checkout."
        )
    )
    parser.add_argument("--version", required=True, help="Bootstrap version, e.g. 5.3.0")
    parser.add_argument("--lane", required=True, help="Human-readable lane name")
    parser.add_argument("--output", type=Path, help="JSON report path")
    parser.add_argument(
        "--repo",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Moo UI repository root; defaults to this script's parent checkout",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Run package install and build only; useful for sandboxed workers.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary checkout for debugging failed lanes.",
    )
    return parser.parse_args()


def default_output_path(lane: str, version: str) -> Path:
    return (
        Path(tempfile.gettempdir())
        / "moo-ui-bootstrap-compatibility"
        / f"{lane}-{version}.json"
    )


def run(command: list[str], cwd: Path, env: dict[str, str]) -> dict[str, object]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "durationSeconds": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def copy_tracked_tree(source: Path, destination: Path) -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=source,
        check=True,
        capture_output=True,
    )
    for raw_name in result.stdout.split(b"\0"):
        if not raw_name:
            continue
        relative = Path(raw_name.decode("utf-8"))
        source_path = source / relative
        destination_path = destination / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def install_bootstrap(
    version: str,
    project_root: Path,
    env: dict[str, str],
) -> dict[str, object]:
    package_dir = project_root / ".bootstrap-packages"
    package_dir.mkdir()
    pack = run(
        [
            "npm",
            "pack",
            f"bootstrap@{version}",
            "--json",
            "--pack-destination",
            str(package_dir),
        ],
        cwd=project_root,
        env=env,
    )
    if pack["returncode"] != 0:
        return {"pack": pack}

    payload = json.loads(str(pack["stdout"]))
    tarball = package_dir / payload[0]["filename"]
    vendor_bootstrap = project_root / "vendor/bootstrap"
    if vendor_bootstrap.exists():
        shutil.rmtree(vendor_bootstrap)
    vendor_bootstrap.parent.mkdir(parents=True, exist_ok=True)
    unpack_root = project_root / ".bootstrap-unpacked"
    unpack_root.mkdir()
    with tarfile.open(tarball, mode="r:gz") as archive:
        archive.extractall(unpack_root)
    shutil.move(str(unpack_root / "package"), vendor_bootstrap)
    return {
        "pack": pack,
        "tarball": str(tarball),
        "packageVersion": payload[0]["version"],
        "packageFilename": payload[0]["filename"],
    }


def write_report(report: dict[str, object], output: Path) -> None:
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    output = (
        args.output.resolve()
        if args.output is not None
        else default_output_path(args.lane, args.version)
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    base_env = os.environ.copy()
    base_env.setdefault("npm_config_cache", "/private/tmp/wpmoo-npm-cache")
    base_env["MOO_UI_BOOTSTRAP_EXPECTED_VERSION"] = args.version

    report: dict[str, object] = {
        "lane": args.lane,
        "bootstrapVersion": args.version,
        "sourceRepo": str(repo),
        "python": sys.executable,
        "steps": [],
    }

    temp_manager = tempfile.TemporaryDirectory(
        prefix=f"moo-ui-bootstrap-{args.version}-"
    )
    temp_root = Path(temp_manager.name)
    report["tempRoot"] = str(temp_root)
    try:
        project_root = temp_root / "html"
        project_root.mkdir()
        copy_tracked_tree(repo, project_root)

        node_modules = repo / "node_modules"
        if node_modules.exists():
            os.symlink(node_modules, project_root / "node_modules")

        install = install_bootstrap(args.version, project_root, base_env)
        report["bootstrapInstall"] = install
        pack = install.get("pack")
        if isinstance(pack, dict):
            report["steps"].append(pack)
            if pack.get("returncode") != 0:
                report["result"] = "failed"
                write_report(report, output)
                return 1

        bundle = project_root / "vendor/bootstrap/dist/js/bootstrap.bundle.min.js"
        bundle_text = bundle.read_text(encoding="utf-8", errors="replace")
        report["bundleContainsExpectedVersion"] = (
            f"Bootstrap v{args.version}" in bundle_text
        )

        build = run([sys.executable, "build.py"], project_root, base_env)
        report["steps"].append(build)
        if build["returncode"] != 0:
            report["result"] = "failed"
            write_report(report, output)
            return 1

        if args.skip_browser:
            report["result"] = "passed"
            report["browserSkipped"] = True
            write_report(report, output)
            return 0

        browser_tests = run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*_browser.py",
                "-v",
            ],
            project_root,
            base_env,
        )
        report["steps"].append(browser_tests)
        report["result"] = "passed" if browser_tests["returncode"] == 0 else "failed"
        write_report(report, output)
        return int(browser_tests["returncode"])
    finally:
        if args.keep_temp:
            temp_manager.cleanup = lambda: None  # type: ignore[method-assign]
        temp_manager.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
