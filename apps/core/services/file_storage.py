"""
File storage service — enforces the storage protocol.

Path structure: /media/<org_id>/<model>/<record_id>/<filename>
Image sizes: tn(64), sm(128), md(256), lg(512), original

Used by:
  - Upload views (image + document uploads)
  - Alice (nightly cleanup, orphan detection)
  - Sync bundles (file manifests)
"""

import os
import logging
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger("core.file_storage")

MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", "media"))

IMAGE_SIZES = {
    "tn": 64,
    "sm": 128,
    "md": 256,
    "lg": 512,
}


def media_path(org_id: int, model: str, record_id: int, filename: str = "") -> Path:
    """Build the canonical media path for a record's file."""
    p = MEDIA_ROOT / str(org_id) / model / str(record_id)
    if filename:
        p = p / filename
    return p


def ensure_dir(org_id: int, model: str, record_id: int) -> Path:
    """Create the directory if it doesn't exist. Return the path."""
    p = media_path(org_id, model, record_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def image_set_paths(org_id: int, model: str, record_id: int, purpose: str, ext: str) -> dict:
    """Return a dict of size_key → relative path for all image sizes."""
    base = Path(str(org_id)) / model / str(record_id)
    result = {}
    for key in IMAGE_SIZES:
        result[key] = str(base / f"{purpose}_{IMAGE_SIZES[key]}.{ext}")
    result["original"] = str(base / f"{purpose}_original.{ext}")
    return result


def save_image(
    file_data: bytes,
    org_id: int,
    model: str,
    record_id: int,
    purpose: str = "photo",
    ext: str = "jpg",
) -> dict:
    """Save an image and generate all sizes. Returns ImageSet-compatible dict.

    Args:
        file_data: Raw image bytes
        org_id: Organization ID (tenant)
        model: Model name (contacts, items, orgs)
        record_id: Record ID
        purpose: Image purpose (photo, logo, primary, etc.)
        ext: File extension

    Returns:
        Dict with tn, sm, md, lg, original paths (relative to MEDIA_ROOT)
    """
    try:
        from PIL import Image
        import io
    except ImportError:
        logger.error("Pillow not installed — cannot process images")
        return {}

    directory = ensure_dir(org_id, model, record_id)
    paths = image_set_paths(org_id, model, record_id, purpose, ext)

    # Save original
    original_path = MEDIA_ROOT / paths["original"]
    original_path.write_bytes(file_data)

    # Generate resized versions
    try:
        img = Image.open(io.BytesIO(file_data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        for key, size in IMAGE_SIZES.items():
            resized = img.copy()
            resized.thumbnail((size, size), Image.LANCZOS)
            out_path = MEDIA_ROOT / paths[key]
            resized.save(str(out_path), quality=85, optimize=True)

    except Exception as e:
        logger.error("Image resize failed for %s/%s/%s: %s", model, record_id, purpose, e)

    logger.info("Saved image: org=%s model=%s id=%s purpose=%s sizes=%d",
                org_id, model, record_id, purpose, len(paths))

    return paths


def save_document(
    file_data: bytes,
    org_id: int,
    model: str,
    record_id: int,
    filename: str,
) -> str:
    """Save a document file. Returns relative path."""
    directory = ensure_dir(org_id, model, record_id)
    rel_path = Path(str(org_id)) / model / str(record_id) / filename
    full_path = MEDIA_ROOT / rel_path
    full_path.write_bytes(file_data)
    logger.info("Saved document: %s", rel_path)
    return str(rel_path)


def find_orphans(org_id: int, model: str) -> list:
    """Find files on disk that aren't referenced in any record's metadata.images.

    Returns list of file paths that have no matching metadata reference.
    Alice runs this nightly.
    """
    from django.apps import apps

    model_dir = MEDIA_ROOT / str(org_id) / model
    if not model_dir.exists():
        return []

    # Collect all files on disk
    disk_files = set()
    for dirpath, _, filenames in os.walk(model_dir):
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), str(MEDIA_ROOT))
            disk_files.add(rel)

    if not disk_files:
        return []

    # Collect all referenced paths from metadata.images
    referenced = set()
    try:
        # Try to find the Django model for this model name
        model_map = {
            "contacts": ("core", "Contact"),
            "items": ("products", "Item"),
            "orgs": ("orgs", "Organization"),
        }
        app_label, model_cls_name = model_map.get(model, (None, None))
        if not app_label:
            return list(disk_files)

        ModelCls = apps.get_model(app_label, model_cls_name)
        for record in ModelCls.objects.filter(is_active=True).only("metadata"):
            images = (record.metadata or {}).get("images", {})
            _collect_paths(images, referenced)
    except Exception as e:
        logger.error("Orphan scan failed for %s: %s", model, e)
        return []

    orphans = disk_files - referenced
    if orphans:
        logger.warning("Found %d orphaned files in %s/%s", len(orphans), org_id, model)

    return sorted(orphans)


def _collect_paths(obj, paths: set):
    """Recursively collect all string paths from an image metadata structure."""
    if isinstance(obj, str) and obj:
        paths.add(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_paths(v, paths)
    elif isinstance(obj, list):
        for v in obj:
            _collect_paths(v, paths)
