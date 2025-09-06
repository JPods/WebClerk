#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_BIN="${PY_BIN:-}"
if [[ -z "$PY_BIN" ]]; then
	if [[ -x "$ROOT_DIR/bin/python" ]]; then
		PY_BIN="$ROOT_DIR/bin/python"
	else
		PY_BIN="python3"
	fi
fi

cd "$ROOT_DIR"
$PY_BIN manage.py migrate --noinput
exec $PY_BIN manage.py runserver 0.0.0.0:8000

