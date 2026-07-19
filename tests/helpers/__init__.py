from __future__ import annotations

import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
ICONS = ROOT / "src/icons/lucide-icons.json"
STATIC = ROOT / "static"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COLOR_TYPE_RGBA = 6


def lucide_body(name: str) -> str:
    return json.loads(ICONS.read_text(encoding="utf-8"))["icons"][name]["body"]


def read_png_ihdr(path: Path) -> tuple[int, int, int]:
    """Return (width, height, color_type) parsed from a PNG's IHDR chunk."""
    data = path.read_bytes()
    if data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file")
    width, height, _bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type


def is_valid_webp(path: Path) -> bool:
    """Check a file has a well-formed RIFF/WEBP header (any codec chunk)."""
    header = path.read_bytes()[:12]
    return header[:4] == b"RIFF" and header[8:12] == b"WEBP"


class CatalogTestCase(unittest.TestCase):
    def run_build(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def read_output(self, relative_path: str) -> str:
        return (DIST / relative_path).read_text(encoding="utf-8")
