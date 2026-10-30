"""
Bundle file storage — payloads go to disk, never to the database.

Directory structure:
    WORK_DIR/bundles/{model_name}/{direction}/{bundle_id}.json

Direction mapping:
    push  → outgoing
    pull  → incoming
    sync  → incoming  (default for bidirectional)
    other → incoming

Usage:
    from apps.sync.services.bundle_storage import save_payload, load_payload

    path = save_payload(bundle_id=42, model_name="order", direction="pull", payload=data)
    data = load_payload(bundle_id=42, model_name="order", direction="pull")
"""
import json
import logging
from pathlib import Path

from django.conf import settings
from common.work_folders import work_folder, work_root

logger = logging.getLogger(__name__)

DIRECTION_MAP = {
    "push": "outgoing",
    "pull": "incoming",
    "sync": "incoming",
    "outbound": "outgoing",
    "inbound": "incoming",
}

# Models that have bundle folders. Others go to "general".
BUNDLE_MODELS = frozenset({
    "contact", "order", "invoice", "purchase", "cash",
    "product", "workorder", "journal", "report", "org",
    "action", "selectlist", "item",
})


# Where a bundle file sits is its state (Bill, 2026-10-29): pending/ until it is handled, then
# completed/, or defects/ while something in it still has to be resolved.
STATUSES = ("pending", "defects", "completed")


def _bundle_dir(model_name: str, direction: str, status: str = "pending") -> Path:
    """Return the directory for this model+direction+status, creating it if needed.

    Structure: WORK_DIR/bundles/{model}/{direction}/{status}/, status one of STATUSES.
    """
    if status not in STATUSES:
        raise ValueError(f"bundle status is one of {', '.join(STATUSES)}, not {status!r}")
    folder = model_name if model_name in BUNDLE_MODELS else "general"
    subdir = DIRECTION_MAP.get(direction, "incoming")
    return work_folder("bundles", folder, subdir, status)


def _find(bundle_id: int, model_name: str, direction: str) -> Path | None:
    for status in STATUSES:
        filepath = _bundle_dir(model_name, direction, status) / f"{bundle_id}.json"
        if filepath.exists():
            return filepath
    return None


def move(bundle_id: int, model_name: str, direction: str, to_status: str) -> str | None:
    """Move a bundle file to the to_status folder. Returns its new path relative to WORK_DIR."""
    current = _find(bundle_id, model_name, direction)
    if current is None:
        return None
    dest_file = _bundle_dir(model_name, direction, to_status) / f"{bundle_id}.json"
    if current != dest_file:
        current.rename(dest_file)
    return str(dest_file.relative_to(work_root()))


def count_pending(model_name: str = "", direction: str = "") -> dict:
    """Count pending bundle files. Returns {model: {direction: count}}.

    If model_name given, counts only that model. If direction given, counts
    only that direction. Otherwise counts everything.
    """
    bundles_root = work_folder("bundles")
    if not bundles_root.exists():
        return {}
    counts = {}
    models = [model_name] if model_name else [d.name for d in bundles_root.iterdir() if d.is_dir()]
    for m in models:
        model_dir = bundles_root / m
        if not model_dir.is_dir():
            continue
        directions = [direction] if direction else ["incoming", "outgoing"]
        for d in directions:
            mapped_d = DIRECTION_MAP.get(d, d)
            pending_dir = model_dir / mapped_d / "pending"
            if pending_dir.is_dir():
                n = len(list(pending_dir.glob("*.json")))
                if n > 0:
                    counts.setdefault(m, {})[mapped_d] = n
    return counts


def save_payload(bundle_id: int, model_name: str, direction: str, payload) -> str:
    """Write payload to disk in pending/. Returns the path relative to WORK_DIR."""
    directory = _bundle_dir(model_name, direction, "pending")
    filepath = directory / f"{bundle_id}.json"
    filepath.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    # Relative to WORK_DIR, for config.payload_path
    return str(filepath.relative_to(work_root()))


def load_payload(bundle_id: int, model_name: str, direction: str) -> dict | list | None:
    """Read payload from disk, whichever status folder holds it."""
    filepath = _find(bundle_id, model_name, direction)
    if filepath is None:
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load bundle payload %s: %s", filepath, e)
        return None


def load_payload_by_path(payload_path: str) -> dict | list | None:
    """Read payload using the relative path stored in config.payload_path."""
    root = work_root().resolve()
    filepath = (root / payload_path).resolve()
    if root not in filepath.parents:            # config is editable: never read outside WORK_DIR
        return None
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load bundle payload %s: %s", filepath, e)
        return None


def delete_payload(bundle_id: int, model_name: str, direction: str) -> bool:
    """Delete a payload file, whichever status folder holds it. Returns True if deleted."""
    filepath = _find(bundle_id, model_name, direction)
    if filepath is None:
        return False
    filepath.unlink()
    return True
