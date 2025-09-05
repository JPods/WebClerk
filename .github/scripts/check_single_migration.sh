#!/usr/bin/env bash
set -euo pipefail

# Configuration
APPS_DIR="apps"
ALLOW=${ALLOW_MULTIPLE_MIGRATIONS:-0}
# Space-separated list of branches where the policy is enforced strictly
PROTECTED_BRANCHES=${PROTECTED_BRANCHES:-"main bill_dev"}

current_branch() {
  # For PRs, use base branch; for pushes, use ref name; otherwise empty
  if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]] && [[ -n "${GITHUB_BASE_REF:-}" ]]; then
    echo "${GITHUB_BASE_REF}"
  elif [[ -n "${GITHUB_REF_NAME:-}" ]]; then
    echo "${GITHUB_REF_NAME}"
  else
    # Try git for local runs
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo ""
  fi
}

is_protected_branch() {
  local br="$1"
  for p in ${PROTECTED_BRANCHES}; do
    if [[ "$br" == "$p" ]]; then return 0; fi
  done
  return 1
}

BRANCH=$(current_branch)

if [[ "$ALLOW" == "1" ]]; then
  echo "ALLOW_MULTIPLE_MIGRATIONS=1 set; skipping enforcement (informational only)."
  exit 0
fi

if ! is_protected_branch "$BRANCH"; then
  echo "Non-protected branch '$BRANCH' detected; migration guard in warn-only mode."
  MODE=warn
else
  MODE=fail
fi

violations=0
while IFS= read -r app; do
  count=$(find "$app/migrations" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]*.py' 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$count" -gt 1 ]]; then
    if [[ "$MODE" == "fail" ]]; then
      echo "::error file=$app::App '$app' has $count migration files (policy allows only a single 0001_initial)." >&2
    else
      echo "::warning file=$app::App '$app' has $count migration files (policy allows only a single 0001_initial)." >&2
    fi
    violations=$((violations+1))
  fi
done < <(find "$APPS_DIR" -maxdepth 1 -mindepth 1 -type d -print)

if [[ "$violations" -gt 0 && "$MODE" == "fail" ]]; then
  echo "Found $violations apps violating single-migration policy on protected branch '$BRANCH'." >&2
  exit 1
fi

echo "Migration guard passed (single 0001_initial per app) on branch '${BRANCH:-unknown}'."
