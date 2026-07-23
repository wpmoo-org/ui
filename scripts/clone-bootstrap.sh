#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
CANONICAL_SCRIPT="$ROOT_DIR/scripts/clone-bootstrap.sh"

if [ ! -x "$CANONICAL_SCRIPT" ]; then
  echo "Missing canonical Bootstrap reference helper: $CANONICAL_SCRIPT" >&2
  echo "Run from the odoo-dev workspace, not the standalone html package checkout." >&2
  exit 1
fi

exec "$CANONICAL_SCRIPT" "$@"
