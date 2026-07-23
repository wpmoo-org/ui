#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
checker="$root_dir/scripts/check-public-git-labels.sh"
message_file="$(mktemp)"
trap 'rm -f "$message_file"' EXIT

assert_pass() {
  printf '%s\n' "$2" > "$message_file"
  "$checker" "$1" "$message_file" >/dev/null
}

assert_fail() {
  printf '%s\n' "$2" > "$message_file"
  if "$checker" "$1" "$message_file" >/dev/null 2>&1; then
    echo "Expected failure for: $2" >&2
    exit 1
  fi
}

assert_ref_pass() {
  "$checker" ref-name "$1" >/dev/null
}

assert_ref_fail() {
  if "$checker" ref-name "$1" >/dev/null 2>&1; then
    echo "Expected ref failure for: $1" >&2
    exit 1
  fi
}

assert_pass commit-msg "Use canonical reference checkouts"
assert_pass commit-msg $'Update agent bridge docs\n\n# codex in a comment is ignored'
assert_fail commit-msg "Codex release followup"
assert_fail commit-msg $'Update release workflow\n\nReviewed by Claude'

assert_ref_pass "refs/heads/fix/release-workflow"
assert_ref_fail "refs/heads/codex/fix-release-workflow"
assert_ref_fail "claude/polish-alert"
