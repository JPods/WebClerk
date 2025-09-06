#!/usr/bin/env bash
# Disable all Git hooks locally by redirecting core.hooksPath to an empty directory.
# Safe, reversible, and does not modify repository files.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "${REPO_ROOT:-}" ] && echo "Not a git repo" >&2 && exit 1
DISABLED_DIR="$REPO_ROOT/.git/hooks.disabled"
mkdir -p "$DISABLED_DIR"

git config core.hooksPath "$DISABLED_DIR"

CURRENT=$(git config core.hooksPath || echo "")
echo "Git hooks disabled. core.hooksPath=$CURRENT"
