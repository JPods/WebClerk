#!/usr/bin/env python3
"""
Sync OpenAPI spec between YAML and JSON files.

Usage:
  - Run from repo root: bin/python tools/openapi_sync.py

Behavior:
  - Reads openapi.yaml if present; otherwise tries to parse openapi.json as YAML.
  - Writes both openapi.yaml (pretty YAML) and openapi.json (pretty JSON).
  - Preserves content; does not modify fields beyond formatting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except Exception as e:  # pragma: no cover
    print("ERROR: PyYAML is required. Install with 'pip install pyyaml'", file=sys.stderr)
    raise


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "openapi.json"
YAML_PATH = ROOT / "openapi.yaml"


def _sniff_is_json(text: str) -> bool:
    text = text.lstrip()
    return text.startswith("{") or text.startswith("[")


def load_spec() -> dict:
    # Prefer YAML when present (canonical source)
    if YAML_PATH.exists():
        with YAML_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # Fallback: read JSON, which may actually contain YAML
    if JSON_PATH.exists():
        text = JSON_PATH.read_text(encoding="utf-8")
        if _sniff_is_json(text):
            return json.loads(text)
        return yaml.safe_load(text)

    raise FileNotFoundError("No openapi.yaml or openapi.json found at repo root")


def write_yaml(spec: dict) -> None:
    # Use block style and keep keys order where possible
    with YAML_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)


def write_json(spec: dict) -> None:
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    spec = load_spec()
    # Light sanity check
    for key in ("openapi", "info", "paths"):
        if key not in spec:
            print(f"WARNING: spec missing top-level key '{key}'", file=sys.stderr)
    write_yaml(spec)
    write_json(spec)
    print(f"Wrote {YAML_PATH.relative_to(ROOT)} and {JSON_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
