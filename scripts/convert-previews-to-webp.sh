#!/usr/bin/env bash
# Mirrors every PNG under the private assets source tree into a WebP at the
# same relative path under static/images/. build.py's preview lookups
# resolve .webp first, so publishing a new or updated preview is just:
# drop the PNG under the source tree (in the same relative subfolder you
# want it to land in) and re-run this script — no code changes required
# unless the directory layout itself changes.
#
# Original PNGs live outside this repo, in the private parent checkout at
# projects/ui/assets/ (sibling to this html submodule, not
# projects/ui/html/assets) — only the converted, optimized WebP ships in
# the public wpmoo-org/ui repo. Override SOURCE_DIR to point elsewhere.
#
# High-quality lossy, not lossless: the preview art has a sketchy
# paper-texture/shading style (see docs/design/component-preview-images.md),
# not flat line art, and that texture is exactly what lossless struggles to
# compress. -q 90 -alpha_q 100 checked visually clean on every sample (no
# banding or edge ringing) while cutting file size 40-85% versus lossless,
# depending on how much texture a given illustration has.
#
# cwebp is deterministic for a given input + these flags (verified: two
# runs on the same PNG produce byte-identical output), so re-running this
# script never dirties git for unchanged images on its own. The mtime skip
# below is purely to avoid re-encoding hundreds of untouched files on every
# run; set FORCE=1 to bypass it and reconvert everything.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_ROOT="$ROOT_DIR/static/images"
SOURCE_ROOT="${SOURCE_DIR:-$ROOT_DIR/../assets}"
FORCE="${FORCE:-0}"

if ! command -v cwebp >/dev/null 2>&1; then
  echo "cwebp not found. Install it with: brew install webp" >&2
  exit 1
fi

if [ ! -d "$SOURCE_ROOT" ]; then
  echo "Source directory not found: $SOURCE_ROOT" >&2
  echo "Set SOURCE_DIR to point at the original PNGs, or create that path." >&2
  exit 1
fi

converted=0
skipped=0
while IFS= read -r -d '' png; do
  rel="${png#"$SOURCE_ROOT"/}"
  webp="$DEST_ROOT/${rel%.[Pp][Nn][Gg]}.webp"
  if [ "$FORCE" != "1" ] && [ -e "$webp" ] && [ "$webp" -nt "$png" ]; then
    skipped=$((skipped + 1))
    continue
  fi
  mkdir -p "$(dirname "$webp")"
  cwebp -quiet -q 90 -alpha_q 100 -m 6 "$png" -o "$webp"
  converted=$((converted + 1))
done < <(find "$SOURCE_ROOT" -type f \( -iname "*.png" \) -print0)

echo "Converted $converted, skipped $skipped up-to-date PNG(s) from $SOURCE_ROOT to $DEST_ROOT"
