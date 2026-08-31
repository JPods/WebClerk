"""
Bundle file storage — payloads go to disk, never to the database.

Directory structure:
    DATA_DIR/bundles/{model_name}/{direction}/{bundle_id}.json

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
    "contact", "order", "invoice", "purchase", "payment",
    "product", "workorder", "journal", "report", "org",
    "action", "selectlist", "item",
})


def _bundle_dir(model_name: str, direction: str, status: str = "pending") -> Path:
    """Return the directory for this model+direction+status, creating it if needed.

    Structure: DATA_DIR/bundles/{model}/{direction}/{status}/
    Status is 'pending', 'processed', or 'rejected'.
    New bundles always land in pending/. Move to processed/ or rejected/ after handling.
    """
    folder = model_name if model_name in BUNDLE_MODELS else "general"
    subdir = DIRECTION_MAP.get(direction, "incoming")
    sub_status = status if status in ("pending", "processed", "rejected") else "pending"
    path = Path(settings.DATA_DIR) / "bundles" / folder / subdir / sub_status
    path.mkdir(parents=True, exist_ok=True)
    return path


def _move_bundle(bundle_id: int, model_name: str, direction: str, to_status: str) -> str | None:
    """Move a bundle file from pending/ to another status folder. Returns new relative path."""
    pending_dir = _bundle_dir(model_name, direction, "pending")
    pending_file = pending_dir / f"{bundle_id}.json"
    if not pending_file.exists():
        return None
    dest_dir = _bundle_dir(model_name, direction, to_status)
    dest_file = dest_dir / f"{bundle_id}.json"
    pending_file.rename(dest_file)
    return str(dest_file.relative_to(settings.DATA_DIR))


def mark_processed(bundle_id: int, model_name: str, direction: str) -> str | None:
    """Move a bundle file from pending/ to processed/. Returns new relative path."""
    return _move_bundle(bundle_id, model_name, direction, "processed")


def mark_rejected(bundle_id: int, model_name: str, direction: str) -> str | None:
    """Move a bundle file from pending/ to rejected/. Returns new relative path."""
    return _move_bundle(bundle_id, model_name, direction, "rejected")


def count_pending(model_name: str = "", direction: str = "") -> dict:
    """Count pending bundle files. Returns {model: {direction: count}}.

    If model_name given, counts only that model. If direction given, counts
    only that direction. Otherwise counts everything.
    """
    bundles_root = Path(settings.DATA_DIR) / "bundles"
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
    """Write payload to disk in pending/. Returns the relative path from DATA_DIR."""
    directory = _bundle_dir(model_name, direction, "pending")
    filepath = directory / f"{bundle_id}.json"
    filepath.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    # Return path relative to DATA_DIR for storage in config.payload_path
    return str(filepath.relative_to(settings.DATA_DIR))


def load_payload(bundle_id: int, model_name: str, direction: str) -> dict | list | None:
    """Read payload from disk. Checks pending/, then processed/, then rejected/."""
    for status in ("pending", "processed", "rejected"):
        directory = _bundle_dir(model_name, direction, status)
        filepath = directory / f"{bundle_id}.json"
        if filepath.exists():
            break
    else:
        return None
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load bundle payload %s: %s", filepath, e)
        return None


def load_payload_by_path(payload_path: str) -> dict | list | None:
    """Read payload using the relative path stored in config.payload_path."""
    filepath = Path(settings.DATA_DIR) / payload_path
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load bundle payload %s: %s", filepath, e)
        return None


def delete_payload(bundle_id: int, model_name: str, direction: str) -> bool:
    """Delete a payload file. Checks all status folders. Returns True if deleted."""
    for status in ("pending", "processed", "rejected"):
        directory = _bundle_dir(model_name, direction, status)
        filepath = directory / f"{bundle_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
    return False
