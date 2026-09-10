"""
Catalog File Import Service — images and documents from the catalog library.

The catalog library shares FILES (images, documents), never pricing.

DynamicCatalogs normalizes catalog files and assigns UUIDs. It gives the
UUID back to the manufacturer/distributor to use in their price lists.
Pricing flows DIRECTLY between mfg/dstb and each retailer — DynamicCatalogs
does not see, store, or broker pricing. Different retailers have different
price points for the same product; the catalog library is agnostic to that.

The UUID is the handshake: mfg part 12048 = UUID abc-123. Every retailer
who carries that product uses the same UUID for catalog files. Their
pricing agreement with the mfg is separate and private.

Two file categories:
  Images    — product photos, lifestyle shots → resize to tn/md/hires .jpg
  Documents — QA manuals, SDS, install videos, spec sheets → store original

Two import paths:
  1. Local source — raw files from source_path, process and push up to WC_HQ
                    (first converter pays, all subsequent retailers benefit)
  2. Library download — pull pre-processed files from DynamicCatalogs by uuid

Allie/Andi sets source locations via Connection.config.catalog_config.
Alice collaborates with Alice WC_HQ, Allie/Andi, and Claude to process.

Connection.config.catalog_config structure:
  {
    "source_path": "/path/to/raw/files",
    "match_by": "sku" | "ida" | "filename",
    "filename_pattern": "{sku}.jpg",
    "subdirs": {"tn": "TN"},
    "default_alt": "Product image for {name}",
    "file_types": ["image", "document"]
  }

Connection with purpose='catalog_library':
  config.base_url → hosted site serving files by uuid
  URL pattern: {base_url}/{uuid}/images/{size}.jpg
               {base_url}/{uuid}/documents/{filename}

Image sizes (standard):
  tn    — 90px max .jpg
  md    — 256px .jpg
  hires — original resolution .jpg
"""

import io
import logging
import re
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger("alice.image_import")

MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", "media"))

SIZES = {
    "tn": 90,
    "md": 256,
}


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".mp4", ".mov", ".avi", ".doc", ".docx", ".xls", ".xlsx"}


def process_source_files(
    connection_id: int,
    file_type: str = "image",
    dry_run: bool = False,
) -> dict:
    """Process catalog files from a Connection's catalog_config source_path.

    For images: resize to tn/md/hires .jpg, store in image library.
    For documents: store original in document library, linked by item uuid.

    Catalog library shares files, never pricing. Pricing flows through
    distribution agreements per-retailer.

    Returns summary dict: {processed, skipped, errors, items}.
    """
    from apps.sync.models import Connection
    from apps.products.models import Item

    conn = Connection.objects.get(pk=connection_id)
    catalog_config = (conn.config or {}).get("catalog_config", {})
    # Backward compat: fall back to image_config
    if not catalog_config:
        catalog_config = (conn.config or {}).get("image_config", {})

    source_path = Path(catalog_config.get("source_path", ""))
    if not source_path.exists():
        return {"error": f"source_path does not exist: {source_path}"}

    match_by = catalog_config.get("match_by", "sku")
    filename_pattern = catalog_config.get("filename_pattern", "{sku}.jpg")
    subdirs = catalog_config.get("subdirs", {})
    default_alt = catalog_config.get("default_alt", "")

    # Collect source files — filter by type
    valid_exts = IMAGE_EXTENSIONS if file_type == "image" else DOCUMENT_EXTENSIONS
    raw_files = _collect_source_files(source_path, subdirs, valid_exts)

    results = {
        "processed": 0,
        "skipped": 0,
        "errors": [],
        "items": [],
        "dry_run": dry_run,
    }

    for raw_file in raw_files:
        try:
            # Extract the match key from filename
            match_key = _extract_match_key(raw_file, filename_pattern)
            if not match_key:
                results["skipped"] += 1
                continue

            # Find the item
            item = _find_item(match_key, match_by)
            if not item:
                results["errors"].append(f"No item for {match_by}={match_key}")
                continue

            if dry_run:
                results["items"].append({
                    "sku": item.sku,
                    "ida": item.ida,
                    "match_key": match_key,
                    "source_file": str(raw_file),
                })
                results["processed"] += 1
                continue

            file_bytes = raw_file.read_bytes()

            if file_type == "image":
                # Check for existing TN in subdirs
                tn_subdir = subdirs.get("tn")
                tn_bytes = None
                if tn_subdir:
                    tn_path = source_path / tn_subdir / raw_file.name
                    if tn_path.exists():
                        tn_bytes = tn_path.read_bytes()

                alt_text = default_alt.format(
                    name=item.name, sku=item.sku
                ) if default_alt else item.name

                image_set = _process_and_store_image(
                    item=item,
                    hires_bytes=file_bytes,
                    tn_bytes=tn_bytes,
                    alt_text=alt_text,
                )
                _update_item_images(item, image_set)
                results["items"].append({
                    "sku": item.sku,
                    "ida": item.ida,
                    "type": "image",
                    "sizes": list(image_set.keys()),
                })

            else:
                # Document — store original, link to item
                doc_path = _store_document(item, file_bytes, raw_file.name)
                _update_item_documents(item, raw_file.name, str(doc_path))
                results["items"].append({
                    "sku": item.sku,
                    "ida": item.ida,
                    "type": "document",
                    "filename": raw_file.name,
                })

            results["processed"] += 1

        except Exception as e:
            results["errors"].append(f"{raw_file.name}: {e}")

    logger.info(
        "Catalog %s import from %s: %d processed, %d skipped, %d errors",
        file_type, conn.name, results["processed"],
        results["skipped"], len(results["errors"]),
    )
    return results


# Keep backward compat name
process_source_images = process_source_files


def download_from_library(
    connection_id: int,
    item_ids: Optional[list] = None,
    file_type: str = "image",
    dry_run: bool = False,
) -> dict:
    """Download catalog files from a remote catalog library (DynamicCatalogs/WC_HQ).

    The catalog library serves files at:
      {base_url}/{uuid}/images/{size}.jpg     (images)
      {base_url}/{uuid}/documents/{filename}  (documents)

    The library shares FILES only — never pricing. Pricing flows through
    distribution agreements per-retailer. Different retailers may have
    different price points for the same product; the catalog library
    is agnostic to that.

    Alice WC_HQ provides each local Alice with the base_url as an
    alternative path for catalog files.

    Args:
        connection_id: Connection with purpose='catalog_library'
        item_ids: Optional list of item PKs to limit scope (None = all items)
        file_type: 'image' or 'document'
        dry_run: If True, check availability without downloading
    """
    from apps.sync.models import Connection
    from apps.products.models import Item

    conn = Connection.objects.get(pk=connection_id)
    base_url = (conn.config or {}).get("base_url", "").rstrip("/")
    if not base_url:
        return {"error": "Connection has no base_url in config"}

    qs = Item.objects.filter(is_active=True).exclude(ida="")
    if item_ids:
        qs = qs.filter(pk__in=item_ids)

    results = {
        "downloaded": 0,
        "already_local": 0,
        "not_available": 0,
        "errors": [],
        "items": [],
        "dry_run": dry_run,
    }

    for item in qs.iterator():
        try:
            item_result = _download_item_images(
                item=item,
                base_url=base_url,
                conn_name=conn.name,
                dry_run=dry_run,
            )
            results["items"].append(item_result)

            if item_result.get("status") == "downloaded":
                results["downloaded"] += 1
            elif item_result.get("status") == "local":
                results["already_local"] += 1
            else:
                results["not_available"] += 1

        except Exception as e:
            results["errors"].append(f"{item.sku}: {e}")

    logger.info(
        "Library download from %s: %d downloaded, %d local, %d unavailable, %d errors",
        conn.name, results["downloaded"], results["already_local"],
        results["not_available"], len(results["errors"]),
    )
    return results


# ── Internal helpers ──────────────────────────────────────────────────


def _collect_source_files(source_path: Path, subdirs: dict, valid_exts: set) -> list:
    """Collect files from source_path matching valid extensions, excluding known subdirs."""
    skip_dirs = {v for v in subdirs.values() if v}
    files = []
    for f in sorted(source_path.iterdir()):
        if f.is_file() and f.suffix.lower() in valid_exts:
            files.append(f)
        elif f.is_dir() and f.name in skip_dirs:
            continue  # known subdir, skip
    return files


def _extract_match_key(filepath: Path, pattern: str) -> Optional[str]:
    """Extract the match key (sku, ida, etc.) from a filename using the pattern.

    Pattern uses {sku}, {ida}, or {id} as placeholders.
    Example: "{sku}.jpg" matches "HW-DRL-001.jpg" → "HW-DRL-001"
    """
    # Convert pattern to regex: "{sku}" → "(?P<key>.+)"
    regex_str = re.escape(pattern)
    for placeholder in [r"\{sku\}", r"\{ida\}", r"\{id\}"]:
        regex_str = regex_str.replace(placeholder, r"(?P<key>.+)")

    match = re.match(regex_str, filepath.name, re.IGNORECASE)
    if match:
        return match.group("key")

    # Fallback: stem as key
    return filepath.stem


def _find_item(match_key: str, match_by: str):
    """Find an Item by sku, ida, or pk."""
    from apps.products.models import Item

    if match_by == "sku":
        return Item.objects.filter(sku=match_key, is_active=True).first()
    elif match_by == "ida":
        return Item.objects.filter(ida=match_key, is_active=True).first()
    elif match_by == "filename":
        # Try sku first, then ida
        item = Item.objects.filter(sku=match_key, is_active=True).first()
        if not item:
            item = Item.objects.filter(ida=match_key, is_active=True).first()
        return item
    return None


def _process_and_store_image(
    item,
    hires_bytes: bytes,
    tn_bytes: Optional[bytes] = None,
    alt_text: str = "",
) -> dict:
    """Resize and store images in the library. Returns ImageSet-compatible dict."""
    try:
        from PIL import Image
    except ImportError:
        logger.error("Pillow not installed — cannot process images")
        return {}

    from .resolve_image import get_image_root

    root = get_image_root()
    model_name = "item"
    ida = item.ida or f"pk{item.pk}"
    dir_path = root / model_name / ida
    dir_path.mkdir(parents=True, exist_ok=True)

    result = {"alt": alt_text}

    # Save hires — convert to RGB .jpg
    img = Image.open(io.BytesIO(hires_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    hires_path = dir_path / "hires.jpg"
    img.save(str(hires_path), "JPEG", quality=90, optimize=True)
    result["hires"] = str(hires_path.relative_to(MEDIA_ROOT))

    # Generate md (256px)
    md_img = img.copy()
    md_img.thumbnail((256, 256), Image.LANCZOS)
    md_path = dir_path / "md.jpg"
    md_img.save(str(md_path), "JPEG", quality=85, optimize=True)
    result["md"] = str(md_path.relative_to(MEDIA_ROOT))

    # Generate tn (90px) — use supplier TN if provided
    if tn_bytes:
        tn_img = Image.open(io.BytesIO(tn_bytes))
        if tn_img.mode in ("RGBA", "P", "LA"):
            tn_img = tn_img.convert("RGB")
        tn_img.thumbnail((90, 90), Image.LANCZOS)
    else:
        tn_img = img.copy()
        tn_img.thumbnail((90, 90), Image.LANCZOS)

    tn_path = dir_path / "tn.jpg"
    tn_img.save(str(tn_path), "JPEG", quality=85, optimize=True)
    result["tn"] = str(tn_path.relative_to(MEDIA_ROOT))

    return result


def _update_item_images(item, image_set: dict):
    """Update item.metadata.images with the new ImageSet."""
    metadata = item.metadata or {}
    metadata["images"] = {
        "primary": image_set,
        "gallery": [],
    }
    # Also set the resolve_image cache
    metadata.setdefault("_image_cache", {})
    metadata["_image_cache"] = {
        "source": "local",
        "tn": bool(image_set.get("tn")),
        "md": bool(image_set.get("md")),
        "hires": bool(image_set.get("hires")),
    }
    from apps.products.models import Item
    Item.objects.filter(pk=item.pk).update(metadata=metadata)


def _store_document(item, file_bytes: bytes, filename: str) -> Path:
    """Store a document file in the catalog library. Returns relative path."""
    from .resolve_image import get_image_root

    ida = item.ida or f"pk{item.pk}"
    root = get_image_root()
    dir_path = root / "item" / ida / "documents"
    dir_path.mkdir(parents=True, exist_ok=True)

    doc_path = dir_path / filename
    doc_path.write_bytes(file_bytes)
    return doc_path.relative_to(MEDIA_ROOT)


def _update_item_documents(item, filename: str, rel_path: str):
    """Add a document reference to item.metadata.documents list."""
    metadata = item.metadata or {}
    docs = metadata.get("documents", [])

    # Don't duplicate
    existing = [d for d in docs if d.get("filename") == filename]
    if not existing:
        docs.append({
            "filename": filename,
            "path": rel_path,
            "type": _classify_document(filename),
        })
        metadata["documents"] = docs
        from apps.products.models import Item
        Item.objects.filter(pk=item.pk).update(metadata=metadata)


def _classify_document(filename: str) -> str:
    """Classify a document by its extension."""
    ext = Path(filename).suffix.lower()
    return {
        ".pdf": "spec_sheet",
        ".mp4": "video",
        ".mov": "video",
        ".avi": "video",
        ".doc": "manual",
        ".docx": "manual",
        ".xls": "data_sheet",
        ".xlsx": "data_sheet",
    }.get(ext, "other")


def _download_item_images(
    item,
    base_url: str,
    conn_name: str,
    dry_run: bool = False,
) -> dict:
    """Download all 3 sizes for one item from a remote catalog library."""
    import requests as req
    from .resolve_image import get_image_root

    ida = item.ida or f"pk{item.pk}"
    root = get_image_root()
    dir_path = root / "item" / ida

    result = {"sku": item.sku, "ida": ida, "sizes": {}}

    # Library URL pattern: {base_url}/{uuid}/images/{size}.jpg
    any_downloaded = False
    for size in ("tn", "md", "hires"):
        local_path = dir_path / f"{size}.jpg"
        if local_path.exists():
            result["sizes"][size] = "local"
            continue

        url = f"{base_url}/{ida}/images/{size}.jpg"
        try:
            resp = req.head(url, timeout=5) if dry_run else req.get(url, timeout=10)
            if resp.status_code == 200:
                if dry_run:
                    result["sizes"][size] = "available"
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(resp.content)
                    result["sizes"][size] = "downloaded"
                    any_downloaded = True
            else:
                result["sizes"][size] = "not_found"
        except Exception as e:
            result["sizes"][size] = f"error: {e}"

    if any_downloaded:
        image_set = {}
        for size in ("tn", "md", "hires"):
            path = dir_path / f"{size}.jpg"
            if path.exists():
                image_set[size] = str(path.relative_to(MEDIA_ROOT))
        image_set["alt"] = item.name
        _update_item_images(item, image_set)
        result["status"] = "downloaded"
    elif all(v == "local" for v in result["sizes"].values()):
        result["status"] = "local"
    else:
        result["status"] = "not_available"

    return result
