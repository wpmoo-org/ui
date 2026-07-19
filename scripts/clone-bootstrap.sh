#!/usr/bin/env bash
# Restores the local, gitignored Bootstrap reference checkout under
# references/bootstrap/<version> that agent-brief.md requires alongside the
# vendored source for "Bootstrap has/lacks X" capability claims.
set -euo pipefail

VERSION="${1:-5.3.3}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$ROOT_DIR/references/bootstrap/$VERSION"

if [ -d "$TARGET_DIR" ]; then
  echo "references/bootstrap/$VERSION already exists, skipping clone."
  exit 0
fi

mkdir -p "$ROOT_DIR/references/bootstrap"
git clone --depth 1 --branch "v$VERSION" https://github.com/twbs/bootstrap.git "$TARGET_DIR"
