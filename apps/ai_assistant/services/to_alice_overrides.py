from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from apps.core.models import Setting


TO_ALICE_PATTERN = re.compile(r"<!--\s*To_Alice:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL)
CSV_KEYS = {"list_display", "detail_order"}


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def _parse_payload(payload: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for part in payload.split(";"):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in CSV_KEYS:
            parsed[key] = _split_csv(value)
        else:
            parsed[key] = value
    return parsed


def _load_report_comment_overrides(repo_root: Path) -> list[dict[str, Any]]:
    latest_report = repo_root / "readmes" / "topics" / "ai" / "reports" / "alice-schema-watch-latest.md"
    if not latest_report.exists():
        return []

    try:
        text = latest_report.read_text(encoding="utf-8")
    except OSError:
        return []

    rows: list[dict[str, Any]] = []
    for match in TO_ALICE_PATTERN.finditer(text):
        payload = _parse_payload(match.group(1))
        if payload:
            rows.append({
                "source": "report_comment",
                "payload": payload,
            })
    return rows


def _load_pending_note_overrides() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    notes = Setting.objects.filter(
        purpose="alice_pending",
        role="config_suggestion",
        is_active=True,
    ).order_by("dt_created")

    for note in notes:
        payload = dict(note.config or {})
        if note.parent_model and "model" not in payload:
            payload["model"] = note.parent_model
        if note.name and "name" not in payload:
            payload["name"] = note.name
        rows.append({
            "source": "pending_note",
            "setting_id": note.pk,
            "payload": payload,
        })
    return rows


def load_validated_to_alice_overrides(
    repo_root: Path,
    model_fields: dict[str, dict[str, list[str]]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Load To_Alice overrides from report comments and active config notes.

    Returns (override_map, audit) where override_map is keyed by canonical model
    name and contains only validated, non-alias field names.
    """
    audit: dict[str, list[dict[str, Any]]] = {
        "applied": [],
        "ignored": [],
    }
    override_map: dict[str, dict[str, Any]] = {}

    raw_rows = _load_report_comment_overrides(repo_root) + _load_pending_note_overrides()

    for row in raw_rows:
        payload = row.get("payload", {})
        model_name = str(payload.get("model", "")).strip().lower()
        if not model_name or model_name not in model_fields:
            audit["ignored"].append({
                "source": row.get("source"),
                "reason": "unknown_model",
                "model": model_name,
                "payload": payload,
            })
            continue

        scalars = list(model_fields[model_name].get("scalar_fields", []))
        jsonb = list(model_fields[model_name].get("jsonb_fields", []))
        scalar_set = set(scalars)
        detail_set = scalar_set | set(jsonb)

        requested_list = _split_csv(payload.get("list_display"))
        requested_detail = _split_csv(payload.get("detail_order"))

        invalid_list = [field for field in requested_list if field not in scalar_set]
        invalid_detail = [field for field in requested_detail if field not in detail_set]

        valid_list: list[str] = []
        for field in requested_list:
            if field in scalar_set and field not in valid_list:
                valid_list.append(field)
        if len(valid_list) > 8:
            valid_list = valid_list[:8]

        scalar_prefix: list[str] = []
        jsonb_prefix: list[str] = []
        for field in requested_detail:
            if field in scalar_set and field not in scalar_prefix:
                scalar_prefix.append(field)
            elif field in jsonb and field not in jsonb_prefix:
                jsonb_prefix.append(field)

        detail_order = []
        if scalar_prefix or jsonb_prefix:
            remaining_scalars = [field for field in scalars if field not in scalar_prefix]
            remaining_jsonb = [field for field in jsonb if field not in jsonb_prefix]
            detail_order = scalar_prefix + remaining_scalars + jsonb_prefix + remaining_jsonb

        if not valid_list and not detail_order:
            audit["ignored"].append({
                "source": row.get("source"),
                "reason": "no_valid_fields",
                "model": model_name,
                "invalid_list_display": invalid_list,
                "invalid_detail_order": invalid_detail,
                "payload": payload,
            })
            continue

        existing = override_map.get(model_name, {})
        merged = dict(existing)
        if valid_list:
            merged["list_display"] = valid_list
        if detail_order:
            merged["detail_order"] = detail_order
        merged.setdefault("sources", []).append(row.get("source"))
        merged.setdefault("rationale", payload.get("rationale", ""))
        override_map[model_name] = merged

        audit["applied"].append({
            "source": row.get("source"),
            "model": model_name,
            "list_display": valid_list,
            "detail_order": detail_order,
            "invalid_list_display": invalid_list,
            "invalid_detail_order": invalid_detail,
        })

    return override_map, audit