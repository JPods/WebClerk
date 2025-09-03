#!/usr/bin/env bash
# Fails the build if README-like documentation files are added outside the canonical `readmes/` directory.
# Allowed exceptions:
#   - Root README.md (authoritative project entrypoint)
# Override (e.g. emergency hotfix) by setting DOC_GUARD_ALLOW_LEGACY=1
set -euo pipefail

if [[ "${DOC_GUARD_ALLOW_LEGACY:-0}" == "1" ]]; then
  echo "[doc-guard] Legacy docs allowed via DOC_GUARD_ALLOW_LEGACY=1; skipping checks." >&2
  exit 0
fi

violations=()

# 1. Detect any legacy documentation directory we expect removed
if [[ -d README_s ]]; then
  while IFS= read -r f; do
    violations+=("$f (legacy directory README_s should be removed)")
  done < <(find README_s -type f -name '*.md' -maxdepth 3 2>/dev/null || true)
fi

# 2. README* files anywhere other than root or readmes/
while IFS= read -r f; do
  base=$(basename "$f")
  # Allow root README.md only
  if [[ "$f" == "README.md" ]]; then
    continue
  fi
  # Allow files inside readmes/
  if [[ "$f" == readmes/* ]]; then
    continue
  fi
  violations+=("$f (README* docs must live in readmes/)")

done < <(git ls-files | grep -i '^README.*\.md$' || true)

# 3. Specific doc names that must only reside in readmes/
DOC_NAMES=(manage testing upgrade data-map debug envelope roadmap rules stats support reset)
for name in "${DOC_NAMES[@]}"; do
  while IFS= read -r f; do
    # Skip canonical location
    if [[ "$f" == readmes/$name.md ]]; then
      continue
    fi
    violations+=("$f ($name.md must be in readmes/)")
  done < <(git ls-files | grep -i "${name}\.md$" || true)

done

if [[ ${#violations[@]} -gt 0 ]]; then
  echo "❌ Documentation location guard failed. The following files violate the docs layout policy:" >&2
  printf ' - %s\n' "${violations[@]}" >&2
  echo >&2
  echo "Policy: All documentation readmes belong under readmes/ (single root README.md is allowed)." >&2
  echo "If this is a transitional commit you may bypass once with DOC_GUARD_ALLOW_LEGACY=1, but please migrate immediately." >&2
  exit 1
fi

echo "✅ Documentation layout guard passed." >&2
