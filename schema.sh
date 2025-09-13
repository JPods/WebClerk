#!/usr/bin/env bash
# Generate OpenAPI schema and sync YAML -> JSON in one step
# Usage: ./schema.sh

set -euo pipefail
cd "$(dirname "$0")"

# Activate venv if available
if [ -f "bin/activate" ]; then
  # shellcheck disable=SC1091
  source bin/activate
fi

# Pick python interpreter
PY=python
if [ -x "bin/python" ]; then
  PY="bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

# Generate OpenAPI YAML via drf-spectacular (adjust path if needed)
$PY manage.py spectacular --file openapi.yaml

# Sync YAML -> JSON
$PY tools/openapi_sync.py

echo "Schema generation and sync complete: openapi.yaml + openapi.json"
