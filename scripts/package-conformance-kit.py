#!/usr/bin/env python3
"""Package the Generic Host Conformance Kit as a deterministic archive.

Produces a byte-identical ``.tar.gz`` (and a ``.sha256`` sidecar) for the
same repository content, regardless of when or where it is built: file
order is sorted, mtimes/owners/modes are fixed, and gzip embeds no name
or timestamp.  The archive carries the distributable kit only — contract,
fixtures, runner, and example host shell — laid out under a versioned
prefix that preserves the repository-relative ``conformance/`` paths, so
an extracted copy is directly runnable (``conformance/host-shell/serve.py``
plus ``conformance/runner/run.py``).  Evidence snapshots under
``conformance/reports/`` are repository evidence, not kit content, and
are excluded.  Symbolic links are rejected so the archive can never
carry content from outside the repository.

Usage:
    python scripts/package-conformance-kit.py [--version 1.0] [--out-dir dist/conformance-kit]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT_DIR = ROOT / "conformance"
INCLUDED_DIRS = ("contract", "fixtures", "runner", "host-shell")
EXCLUDED_PARTS = {"__pycache__", ".DS_Store"}
FIXED_MTIME = 0
FIXED_MODE = 0o644


def kit_files() -> list:
    files = []
    for dir_name in INCLUDED_DIRS:
        base = KIT_DIR / dir_name
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError(
                    f"conformance kit must not contain symlinks: {path}"
                )
            if not path.is_file():
                continue
            if any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
                continue
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(KIT_DIR).as_posix())


def build_archive(version: str) -> bytes:
    prefix = f"moo-ui-conformance-kit-{version}"
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for path in kit_files():
            data = path.read_bytes()
            info = tarfile.TarInfo(
                name=f"{prefix}/conformance/{path.relative_to(KIT_DIR).as_posix()}"
            )
            info.size = len(data)
            info.mtime = FIXED_MTIME
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = FIXED_MODE
            tar.addfile(info, io.BytesIO(data))
    gz_buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=gz_buffer, mtime=0) as gz:
        gz.write(tar_buffer.getvalue())
    return gz_buffer.getvalue()


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic packaging of the conformance kit."
    )
    parser.add_argument("--version", default="1.0")
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "dist" / "conformance-kit"),
    )
    args = parser.parse_args(argv)

    archive = build_archive(args.version)
    digest = hashlib.sha256(archive).hexdigest()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"moo-ui-conformance-kit-{args.version}.tar.gz"
    archive_path = out_dir / archive_name
    archive_path.write_bytes(archive)
    (out_dir / f"{archive_name}.sha256").write_text(
        f"{digest}  {archive_name}\n", encoding="utf-8"
    )
    print(f"{digest}  {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
