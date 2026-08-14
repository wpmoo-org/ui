#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_root="$(cd "$root_dir/../../.." && pwd)"
checker="$workspace_root/scripts/ui/git-label-guard.sh"
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

assert_pass commit-msg "fix(docs): use canonical reference checkouts"
assert_pass commit-msg $'docs(agent): update bridge docs\n\n# codex in a comment is ignored'
assert_pass commit-msg "chore: update generated baselines"
assert_pass commit-msg "feat(ui): add manual acceptance portal"
assert_pass commit-msg "fix(docs)!: rename public package path"
assert_fail commit-msg "Use canonical reference checkouts"
assert_fail commit-msg "Polish rc2 catalog acceptance pass"
assert_fail commit-msg "Fix combobox and datatable keyboard overlays"
assert_fail commit-msg "fix docs: missing conventional separator"
assert_fail commit-msg "fix(): empty scope"
assert_fail commit-msg "Codex release followup"
assert_fail commit-msg $'Update release workflow\n\nReviewed by Claude'

assert_ref_pass "refs/heads/fix/release-workflow"
assert_ref_fail "refs/heads/codex/fix-release-workflow"
assert_ref_fail "claude/polish-alert"
