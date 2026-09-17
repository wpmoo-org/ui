from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = ROOT / "scripts/verify_release_tarball.py"
MANIFEST_LIMIT = 1 * 1024 * 1024
ARTIFACT_LIMIT = 10 * 1024 * 1024
AGGREGATE_LIMIT = 32 * 1024 * 1024
BASE_PAYLOADS = {
    "dist/assets/css/moo.css": b"moo css\n",
    "dist/assets/css/moo-ui.css": b"moo ui css\n",
    "dist/js/theme-prepaint.js": b"(() => {})();\n",
}
BASE_EXPORTS = {
    "dist/assets/css/moo.css": "./moo.css",
    "dist/assets/css/moo-ui.css": "./moo-ui.css",
    "dist/js/theme-prepaint.js": "./theme-prepaint.js",
}


class ReleaseTarballTests(unittest.TestCase):
    def _manifest(
        self,
        payloads: dict[str, bytes] | None = None,
        *,
        artifacts: list[dict[str, str]] | None = None,
        padding: str = "",
    ) -> dict[str, object]:
        payloads = payloads or BASE_PAYLOADS
        if artifacts is None:
            artifacts = [
                {
                    "export": BASE_EXPORTS[path],
                    "path": path,
                    "sha256": hashlib.sha256(payloads[path]).hexdigest(),
                }
                for path in BASE_PAYLOADS
            ]
        manifest: dict[str, object] = {
            "schemaVersion": 1,
            "package": {"name": "@wpmoo/ui", "version": "1.0.0-rc.8"},
            "artifacts": artifacts,
        }
        if padding:
            manifest["padding"] = padding
        return manifest

    def _add_member(
        self,
        archive: tarfile.TarFile,
        name: str,
        data: bytes = b"",
        *,
        member_type: bytes = tarfile.REGTYPE,
        linkname: str = "",
        pax_headers: dict[str, str] | None = None,
    ) -> None:
        member = tarfile.TarInfo(name)
        member.type = member_type
        member.mode = 0o644
        member.mtime = 0
        member.linkname = linkname
        member.pax_headers = pax_headers or {}
        if member_type == tarfile.REGTYPE:
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        else:
            archive.addfile(member)

    def _write_candidate(
        self,
        directory: Path,
        *,
        payloads: dict[str, bytes] | None = None,
        manifest: dict[str, object] | None = None,
        package: dict[str, str] | None = None,
        extra_members: list[dict[str, object]] | None = None,
    ) -> Path:
        payloads = payloads or BASE_PAYLOADS
        manifest = manifest or self._manifest(payloads)
        package = package or {"name": "@wpmoo/ui", "version": "1.0.0-rc.8"}
        tarball = directory / "candidate.tgz"
        with tarfile.open(tarball, mode="w:gz") as archive:
            self._add_member(
                archive,
                "package/package.json",
                json.dumps(package, sort_keys=True).encode("utf-8"),
            )
            self._add_member(
                archive,
                "package/dist/release-manifest.json",
                (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8"),
            )
            for entry in manifest.get("artifacts", []):
                path = entry.get("path")
                if isinstance(path, str) and path in payloads:
                    self._add_member(archive, f"package/{path}", payloads[path])
            for extra in extra_members or []:
                self._add_member(
                    archive,
                    str(extra["name"]),
                    bytes(extra.get("data", b"")),
                    member_type=extra.get("member_type", tarfile.REGTYPE),
                    linkname=str(extra.get("linkname", "")),
                    pax_headers=extra.get("pax_headers"),
                )
        return tarball

    def _run(self, tarball: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VERIFY_SCRIPT), "--tarball", str(tarball)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def _assert_rejected(self, tarball: Path, pattern: str) -> None:
        result = self._run(tarball)
        output = f"{result.stdout}\n{result.stderr}".lower()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertRegex(output, pattern)

    def test_valid_candidate_verifies_against_raw_packed_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(Path(temporary_directory))
            result = self._run(tarball)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_package_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(
                Path(temporary_directory),
                package={"name": "@wpmoo/not-ui", "version": "1.0.0-rc.8"},
            )
            self._assert_rejected(tarball, r"package|name|identity")

    def test_rejects_package_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(
                Path(temporary_directory),
                package={"name": "@wpmoo/ui", "version": "1.0.0-rc.7"},
            )
            self._assert_rejected(tarball, r"package|version|identity")

    def test_rejects_manifest_hash_mismatch(self) -> None:
        artifacts = [
            {
                "export": BASE_EXPORTS[path],
                "path": path,
                "sha256": "0" * 64,
            }
            if path == "dist/assets/css/moo.css"
            else {
                "export": BASE_EXPORTS[path],
                "path": path,
                "sha256": hashlib.sha256(BASE_PAYLOADS[path]).hexdigest(),
            }
            for path in BASE_PAYLOADS
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(
                Path(temporary_directory),
                manifest=self._manifest(artifacts=artifacts),
            )
            self._assert_rejected(tarball, r"sha256|hash|digest")

    def test_rejects_manifest_paths_that_are_not_canonical(self) -> None:
        cases = {
            "absolute": "/dist/assets/css/moo.css",
            "unc": "//server/share/moo.css",
            "backslash": "dist\\assets\\css\\moo.css",
            "empty-segment": "dist//assets/css/moo.css",
            "dot-segment": "dist/assets/./css/moo.css",
            "dot-dot-segment": "dist/assets/../css/moo.css",
        }
        for label, path in cases.items():
            with self.subTest(path=label), tempfile.TemporaryDirectory() as temporary_directory:
                artifacts = [
                    {
                        "export": BASE_EXPORTS[canonical_path],
                        "path": path if canonical_path == "dist/assets/css/moo.css" else canonical_path,
                        "sha256": hashlib.sha256(BASE_PAYLOADS[canonical_path]).hexdigest(),
                    }
                    for canonical_path in BASE_PAYLOADS
                ]
                tarball = self._write_candidate(
                    Path(temporary_directory),
                    manifest=self._manifest(artifacts=artifacts),
                )
                self._assert_rejected(tarball, r"path|canonical|absolute|segment|manifest")

    def test_rejects_duplicate_and_normalized_duplicate_manifest_paths(self) -> None:
        duplicate = [
            {
                "export": BASE_EXPORTS[path],
                "path": path,
                "sha256": hashlib.sha256(BASE_PAYLOADS[path]).hexdigest(),
            }
            for path in BASE_PAYLOADS
        ]
        duplicate.append({**duplicate[0], "export": "./duplicate.css"})
        normalized = [
            {
                "export": "./moo.css",
                "path": "dist/assets/css/../css/moo.css",
                "sha256": hashlib.sha256(BASE_PAYLOADS["dist/assets/css/moo.css"]).hexdigest(),
            },
            *duplicate[1:3],
        ]
        for label, artifacts in (("duplicate", duplicate), ("normalized", normalized)):
            with self.subTest(path=label), tempfile.TemporaryDirectory() as temporary_directory:
                tarball = self._write_candidate(
                    Path(temporary_directory),
                    manifest=self._manifest(artifacts=artifacts),
                )
                self._assert_rejected(tarball, r"duplicate|unique|canonical|path|artifact")

    def test_rejects_non_package_and_non_regular_archive_members(self) -> None:
        cases = {
            "outside": {"name": "outside.txt", "data": b"x"},
            "absolute": {"name": "/package/escape", "data": b"x"},
            "unc": {"name": "//server/share", "data": b"x"},
            "empty-segment": {"name": "package//extra", "data": b"x"},
            "dot-segment": {"name": "package/./extra", "data": b"x"},
            "dot-dot-segment": {"name": "package/../extra", "data": b"x"},
            "symlink": {
                "name": "package/link",
                "member_type": tarfile.SYMTYPE,
                "linkname": "package/dist/js/theme-prepaint.js",
            },
            "hard-link": {
                "name": "package/hard-link",
                "member_type": tarfile.LNKTYPE,
                "linkname": "package/dist/js/theme-prepaint.js",
            },
            "fifo": {"name": "package/fifo", "member_type": tarfile.FIFOTYPE},
            "character-device": {
                "name": "package/character-device",
                "member_type": tarfile.CHRTYPE,
            },
        }
        for label, extra in cases.items():
            with self.subTest(member=label), tempfile.TemporaryDirectory() as temporary_directory:
                tarball = self._write_candidate(
                    Path(temporary_directory),
                    extra_members=[extra],
                )
                self._assert_rejected(tarball, r"package|path|regular|link|member|archive")

    def test_rejects_pax_name_link_and_nul_metadata(self) -> None:
        cases = {
            "pax-path": {
                "name": "package/pax-name",
                "data": b"x",
                "pax_headers": {"path": "package/../escape"},
            },
            "pax-link": {
                "name": "package/pax-link",
                "data": b"x",
                "pax_headers": {"linkpath": "package/dist/js/theme-prepaint.js"},
            },
            "pax-nul": {
                "name": "package/pax-nul",
                "data": b"x",
                "pax_headers": {"path": "package/invalid\x00name"},
            },
        }
        for label, extra in cases.items():
            with self.subTest(member=label), tempfile.TemporaryDirectory() as temporary_directory:
                tarball = self._write_candidate(
                    Path(temporary_directory),
                    extra_members=[extra],
                )
                self._assert_rejected(tarball, r"pax|link|nul|path|archive")

    def test_rejects_oversized_manifest_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(
                Path(temporary_directory),
                manifest=self._manifest(padding="x" * (MANIFEST_LIMIT + 1)),
            )
            self._assert_rejected(tarball, r"size|manifest|limit|large")

    def test_rejects_oversized_artifact_before_reading_bytes(self) -> None:
        payloads = {
            **BASE_PAYLOADS,
            "dist/assets/css/moo.css": b"x" * (ARTIFACT_LIMIT + 1),
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(
                Path(temporary_directory),
                payloads=payloads,
                manifest=self._manifest(payloads),
            )
            self._assert_rejected(tarball, r"size|artifact|limit|large")

    def test_rejects_oversized_aggregate_regular_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            tarball = self._write_candidate(
                Path(temporary_directory),
                extra_members=[
                    {
                        "name": "package/aggregate.bin",
                        "data": b"x" * (AGGREGATE_LIMIT + 1),
                    }
                ],
            )
            self._assert_rejected(tarball, r"size|aggregate|payload|limit|large")


if __name__ == "__main__":
    unittest.main()
