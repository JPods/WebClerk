#!/usr/bin/env bash
# Re-enable Git hooks by pointing core.hooksPath to the repo hooks directory or unsetting it.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "${REPO_ROOT:-}" ] && echo "Not a git repo" >&2 && exit 1

# If repo provides a custom hooks path, set it here; otherwise unset.
DEFAULT_PATH=".git/hooks"

# Unset to revert to default .git/hooks
if git config --global --get core.hooksPath >/dev/null 2>&1; then
  echo "Note: You have a global core.hooksPath configured; leaving it unchanged."
fi

git config --unset core.hooksPath || true

echo "Git hooks enabled (using default .git/hooks)."
