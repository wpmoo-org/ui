from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from build import create_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the independent TOC example.")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    parser.add_argument("--direction", choices=("ltr", "rtl"), default="ltr")
    parser.add_argument("--nested", action="store_true")
    parser.add_argument("--short", action="store_true")
    parser.add_argument("--long-labels", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    template = create_environment().from_string(
        (directory / "index.html.jinja").read_text(encoding="utf-8")
    )
    rendered = template.render(**vars(args))
    normalized = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"
    (directory / "index.html").write_text(normalized, encoding="utf-8")


if __name__ == "__main__":
    main()
