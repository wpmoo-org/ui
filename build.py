#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import textwrap
import time
from html import escape
from pathlib import Path

import sass
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PAGES = SRC / "pages"
SCSS = ROOT / "scss"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
BOOTSTRAP = ROOT / "vendor/bootstrap"
LUCIDE_ICONS = SRC / "icons/lucide-icons.json"


def dedent_html(value: object) -> str:
    return textwrap.dedent(str(value)).strip()


def load_lucide_icons() -> dict[str, object]:
    return json.loads(LUCIDE_ICONS.read_text(encoding="utf-8"))


def render_lucide_icon(icon_set: dict[str, object], name: str, position: str) -> Markup:
    icons = icon_set["icons"]
    if not isinstance(icons, dict) or name not in icons:
        raise KeyError(f"Unknown Lucide icon: {name}")

    icon = icons[name]
    if not isinstance(icon, dict):
        raise TypeError(f"Invalid Lucide icon: {name}")

    left = icon.get("left", icon_set.get("left", 0))
    top = icon.get("top", icon_set.get("top", 0))
    width = icon.get("width", icon_set.get("width", 24))
    height = icon.get("height", icon_set.get("height", 24))
    body = icon["body"]
    return Markup(
        "\n".join(
            (
                "<svg",
                f'  data-icon="{escape(position)}"',
                f'  viewBox="{left} {top} {width} {height}"',
                '  fill="none"',
                '  stroke="currentColor"',
                '  stroke-width="2"',
                '  stroke-linecap="round"',
                '  stroke-linejoin="round"',
                '  aria-hidden="true"',
                ">",
                f"  {body}",
                "</svg>",
            )
        )
    )


def create_environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(SRC),
        autoescape=select_autoescape(("html", "jinja")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["dedent_html"] = dedent_html
    icon_set = load_lucide_icons()
    environment.globals["lucide_icon"] = lambda name, position: render_lucide_icon(
        icon_set,
        name,
        position,
    )
    return environment


def load_catalog() -> list[dict[str, str]]:
    catalog_file = SRC / "catalog.json"
    if not catalog_file.exists():
        return []
    return json.loads(catalog_file.read_text(encoding="utf-8"))


def compile_styles() -> None:
    css_dir = DIST / "assets/css"
    css_dir.mkdir(parents=True, exist_ok=True)
    include_paths = [str(SCSS), str(BOOTSTRAP / "scss")]
    for name in ("moo-ui", "catalog"):
        css = sass.compile(
            filename=str(SCSS / f"{name}.scss"),
            include_paths=include_paths,
            output_style="expanded",
        )
        (css_dir / f"{name}.css").write_text(css, encoding="utf-8")


def copy_assets() -> None:
    js_dir = DIST / "assets/js"
    js_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        BOOTSTRAP / "dist/js/bootstrap.bundle.min.js",
        js_dir / "bootstrap.bundle.min.js",
    )
    if STATIC.exists():
        shutil.copytree(STATIC, DIST / "assets", dirs_exist_ok=True)


def render_pages() -> None:
    environment = create_environment()
    catalog = load_catalog()
    for page in sorted(PAGES.rglob("*.html.jinja")):
        relative = page.relative_to(PAGES)
        output_relative = relative.with_suffix("")
        output_file = DIST / output_relative
        output_file.parent.mkdir(parents=True, exist_ok=True)
        depth = len(output_relative.parents) - 1
        root_path = "../" * depth
        current_slug = (
            output_relative.stem
            if output_relative.parent.name == "components"
            else "index"
        )
        template_name = page.relative_to(SRC).as_posix()
        rendered = environment.get_template(template_name).render(
            catalog=catalog,
            current_slug=current_slug,
            root_path=root_path,
        )
        output_file.write_text(rendered, encoding="utf-8")


def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    compile_styles()
    copy_assets()
    render_pages()


def source_snapshot() -> tuple[tuple[str, int], ...]:
    paths = [ROOT / "build.py"]
    for folder in (SRC, SCSS, STATIC):
        if folder.exists():
            paths.extend(path for path in folder.rglob("*") if path.is_file())
    return tuple(
        sorted((str(path), path.stat().st_mtime_ns) for path in paths)
    )


def watch() -> None:
    previous: tuple[tuple[str, int], ...] = ()
    while True:
        current = source_snapshot()
        if current != previous:
            build()
            print("Built Moo UI catalog.", flush=True)
            previous = current
        time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    if args.watch:
        watch()
    else:
        build()


if __name__ == "__main__":
    main()
