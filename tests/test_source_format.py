from __future__ import annotations

import re

from tests.helpers import ROOT, CatalogTestCase


EDITORCONFIG = ROOT / ".editorconfig"
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "dist",
    "external",
    "node_modules",
    "references",
    "third-party",
    "third_party",
    "vendor",
}
EXCLUDED_FILES = {"src/icons/lucide-icons.json"}
SOURCE_NAMES = {".editorconfig", ".gitignore", "LICENSE"}
SOURCE_SUFFIXES = {
    ".css",
    ".html",
    ".jinja",
    ".js",
    ".json",
    ".md",
    ".py",
    ".scss",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def owned_source_files():
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file():
            continue
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.as_posix() in EXCLUDED_FILES:
            continue
        if path.name in SOURCE_NAMES or path.suffix in SOURCE_SUFFIXES:
            yield path


def editorconfig_sections(source: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    for name, body in re.findall(
        r"(?ms)^\[([^]]+)]\s*$\n(.*?)(?=^\[|\Z)",
        source,
    ):
        sections[name] = {
            key.strip(): value.strip()
            for key, value in re.findall(r"(?m)^([^#;=]+?)\s*=\s*(.*?)\s*$", body)
        }
    return sections


class SourceFormatTests(CatalogTestCase):
    def test_editorconfig_declares_the_owned_source_contract(self) -> None:
        self.assertTrue(EDITORCONFIG.is_file(), "Missing UI repo .editorconfig")
        source = EDITORCONFIG.read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^root\s*=\s*true\s*$")

        sections = editorconfig_sections(source)
        self.assertEqual(
            sections.get("*"),
            {
                "charset": "utf-8",
                "end_of_line": "lf",
                "insert_final_newline": "true",
                "trim_trailing_whitespace": "true",
                "indent_style": "space",
                "indent_size": "2",
            },
        )
        self.assertEqual(
            sections.get("*.py"),
            {
                "indent_style": "space",
                "indent_size": "4",
            },
        )

        unset_settings = {
            key: "unset"
            for key in (
                "charset",
                "end_of_line",
                "insert_final_newline",
                "trim_trailing_whitespace",
                "indent_style",
                "indent_size",
            )
        }
        self.assertEqual(sections.get("{dist,vendor}/**"), unset_settings)
        self.assertEqual(
            sections.get("src/icons/lucide-icons.json"),
            unset_settings,
        )

    def test_owned_sources_have_canonical_whitespace(self) -> None:
        offenders: list[str] = []
        for path in owned_source_files():
            relative = path.relative_to(ROOT)
            source = path.read_bytes()
            if b"\r" in source:
                offenders.append(f"{relative}: must use LF line endings")
            if source and not source.endswith(b"\n"):
                offenders.append(f"{relative}: missing final newline")

            for lineno, line in enumerate(source.split(b"\n"), start=1):
                if line.endswith((b" ", b"\t")):
                    offenders.append(f"{relative}:{lineno}: trailing whitespace")
                indentation = line[: len(line) - len(line.lstrip(b" \t"))]
                if b"\t" in indentation:
                    offenders.append(f"{relative}:{lineno}: tab indentation")

        self.assertEqual(offenders, [])
