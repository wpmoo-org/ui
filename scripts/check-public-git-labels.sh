#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage:
  check-public-git-labels.sh commit-msg <message-file>
  check-public-git-labels.sh ref-name <git-ref-or-branch-name>
USAGE
}

mode="${1:-}"
target="${2:-}"

if [[ -z "$mode" || -z "$target" ]]; then
  usage
  exit 2
fi

forbidden_pattern='(^|[^[:alnum:]])(anthropic|chatgpt|claude|codex|copilot|cursor|deepseek|gemini|gpt|hermes|openai|openhands|opencode|windsurf)([^[:alnum:]]|$)'
forbidden_names='anthropic, chatgpt, claude, codex, copilot, cursor, deepseek, gemini, gpt, hermes, openai, openhands, opencode, windsurf'

reject() {
  local surface="$1"
  cat >&2 <<EOF
Public git ${surface} contains an agent, tool, or model name.

Forbidden names: ${forbidden_names}

Use neutral product wording instead. This keeps public history focused on the
change itself and prevents branch names from leaking into generated merge
commit titles.
EOF
  exit 1
}

case "$mode" in
  commit-msg)
    if [[ ! -f "$target" ]]; then
      echo "Commit message file not found: $target" >&2
      exit 2
    fi
    message_without_comments="$(sed '/^[[:space:]]*#/d' "$target")"
    if printf '%s\n' "$message_without_comments" | LC_ALL=C grep -Eiq "$forbidden_pattern"; then
      reject "message"
    fi
    ;;
  ref-name)
    if printf '%s\n' "$target" | LC_ALL=C grep -Eiq "$forbidden_pattern"; then
      reject "ref name"
    fi
    ;;
  *)
    usage
    exit 2
    ;;
esac
