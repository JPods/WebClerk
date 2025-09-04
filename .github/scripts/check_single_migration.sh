#!/usr/bin/env bash
set -euo pipefail

APPS_DIR="apps"
ALLOW=${ALLOW_MULTIPLE_MIGRATIONS:-0}

violations=0
while IFS= read -r app; do
  count=$(find "$app/migrations" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]*.py' 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$count" -gt 1 ]]; then
    echo "::error file=$app::App '$app' has $count migration files (policy allows only a single 0001_initial)." >&2
    violations=$((violations+1))
  fi
done < <(find "$APPS_DIR" -maxdepth 1 -mindepth 1 -type d -print)

if [[ "$violations" -gt 0 && "$ALLOW" != "1" ]]; then
  echo "Found $violations apps violating single-migration policy." >&2
  exit 1
fi

echo "Migration guard passed (single 0001_initial per app)."
