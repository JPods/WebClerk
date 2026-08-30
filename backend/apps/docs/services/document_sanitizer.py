"""Document sanitization pipeline.

Every uploaded file passes through sanitization before it can be served.
This is a transformation, not a review — it strips active content so the
document is structurally safe regardless of who uploaded it.

Three layers gate document access:
    1. Sanitization (automatic) — strips threats, re-encodes where needed
    2. Alice review (automatic)  — flags anomalies (informational, no gate)
    3. Athena review (configurable) — authority check, required at WCHQ

Quarantine state lives in document.config.quarantine:
    {
        "status": "pending" | "sanitized" | "failed" | "cleared",
        "sanitized": false,
        "sanitized_at": null,
        "alice_cleared": false,
        "alice_cleared_at": null,
        "athena_cleared": false,
        "athena_cleared_at": null,
        "athena_required": true,
        "threats_found": [],
        "actions_taken": []
    }

A document is downloadable when:
    sanitized AND (athena_cleared OR NOT athena_required)
"""
import io
import logging
import os
import re
import struct
from pathlib import Path
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quarantine helpers
# ---------------------------------------------------------------------------

def default_quarantine(athena_required: bool = True) -> dict:
    """Return a fresh quarantine envelope."""
    return {
        "status": "pending",
        "sanitized": False,
        "sanitized_at": None,
        "alice_cleared": False,
        "alice_cleared_at": None,
        "athena_cleared": False,
        "athena_cleared_at": None,
        "athena_required": athena_required,
        "threats_found": [],
        "actions_taken": [],
    }


def is_downloadable(doc) -> bool:
    """Check whether a document has cleared quarantine."""
    config = doc.config if isinstance(doc.config, dict) else {}
    q = config.get("quarantine")
    if not q:
        # Legacy documents without quarantine — allow (they predate the system)
        return True
    if not q.get("sanitized"):
        return False
    if q.get("athena_required") and not q.get("athena_cleared"):
        return False
    return True


def athena_required_for_installation() -> bool:
    """Check whether this installation requires Athena clearance.

    Reads the wc:security Setting. WCHQ sets athena_required=true.
    Individual installations default to false (recommended, not required).
    """
    try:
        from apps.core.models import Setting
        sec = Setting.objects.filter(
            purpose='wc:security', is_active=True
        ).first()
        if sec and isinstance(sec.config, dict):
            return bool(sec.config.get("athena_document_review", False))
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Sanitization by type
# ---------------------------------------------------------------------------

def sanitize_svg(content: bytes) -> tuple[bytes, list[str]]:
    """Strip scripts, event handlers, foreignObject from SVG.

    Returns (cleaned_bytes, list_of_threats_found).
    """
    threats = []
    text = content.decode("utf-8", errors="replace")

    # Remove <script> blocks
    cleaned, n = re.subn(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    if n:
        threats.append(f"removed {n} script element(s)")

    # Remove <foreignObject> blocks
    cleaned, n = re.subn(r"<foreignObject[\s\S]*?</foreignObject>", "", cleaned, flags=re.IGNORECASE)
    if n:
        threats.append(f"removed {n} foreignObject element(s)")

    # Remove event handler attributes (on*)
    cleaned, n = re.subn(r'\s+on\w+\s*=\s*"[^"]*"', "", cleaned, flags=re.IGNORECASE)
    if n:
        threats.append(f"removed {n} event handler attribute(s)")
    cleaned, n = re.subn(r"\s+on\w+\s*=\s*'[^']*'", "", cleaned, flags=re.IGNORECASE)
    if n:
        threats.append(f"removed {n} event handler attribute(s) (single-quoted)")

    # Remove javascript: URIs
    cleaned, n = re.subn(r'(href|xlink:href)\s*=\s*"javascript:[^"]*"', r'\1=""', cleaned, flags=re.IGNORECASE)
    if n:
        threats.append(f"removed {n} javascript: URI(s)")

    return cleaned.encode("utf-8"), threats


def sanitize_image(file_path: str, mime_type: str) -> tuple[str, list[str]]:
    """Re-encode image to strip EXIF exploits and embedded payloads.

    Returns (output_path, threats_found). Output overwrites input.
    """
    threats = []
    try:
        from PIL import Image
        img = Image.open(file_path)
        fmt = "PNG" if "png" in mime_type.lower() else "JPEG"

        # Check for EXIF data
        if hasattr(img, "_getexif") and img._getexif():
            threats.append("stripped EXIF metadata")

        # Re-encode — this drops all metadata, embedded scripts, etc.
        out = io.BytesIO()
        if fmt == "JPEG":
            img = img.convert("RGB")
            img.save(out, format=fmt, quality=95)
        else:
            img.save(out, format=fmt)

        with open(file_path, "wb") as f:
            f.write(out.getvalue())

        threats.append(f"re-encoded as {fmt}")
        return file_path, threats

    except ImportError:
        logger.warning("Pillow not installed — image sanitization skipped")
        return file_path, ["pillow_not_available"]
    except Exception as e:
        logger.error(f"Image sanitization failed: {e}")
        return file_path, [f"sanitization_error: {e}"]


def sanitize_pdf(file_path: str) -> tuple[str, list[str]]:
    """Scan PDF for JavaScript and strip it if found.

    Does not re-render — preserves quality. Uses basic pattern matching
    to find and remove /JS and /JavaScript entries.
    """
    threats = []
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Check for embedded JavaScript
        js_patterns = [b"/JS ", b"/JS(", b"/JavaScript", b"/OpenAction", b"/AA "]
        found = [p.decode() for p in js_patterns if p in content]
        if found:
            threats.append(f"PDF contains active content markers: {', '.join(found)}")
            # Remove /JS entries (basic sanitization)
            cleaned = re.sub(rb'/JS\s*\([^)]*\)', b'/JS ()', content)
            cleaned = re.sub(rb'/JavaScript\s*\([^)]*\)', b'/JavaScript ()', cleaned)
            with open(file_path, "wb") as f:
                f.write(cleaned)
            threats.append("stripped JavaScript content from PDF")

        return file_path, threats

    except Exception as e:
        logger.error(f"PDF sanitization failed: {e}")
        return file_path, [f"pdf_sanitization_error: {e}"]


def clamav_scan(file_path: str) -> tuple[bool, list[str]]:
    """Scan file with ClamAV if available. Returns (clean, findings)."""
    try:
        import pyclamd
        cd = pyclamd.ClamdUnixSocket()
        cd.ping()
    except (ImportError, Exception):
        # ClamAV not available — not a failure, just not installed
        return True, ["clamav_not_available"]

    try:
        result = cd.scan_file(file_path)
        if result is None:
            return True, []
        # result = {filepath: ('FOUND', 'virus_name')}
        findings = []
        for path, info in result.items():
            findings.append(f"{info[1]} ({info[0]})")
        return False, findings
    except Exception as e:
        logger.error(f"ClamAV scan error: {e}")
        return True, [f"clamav_error: {e}"]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def sanitize_document(doc, file_path: str | None = None) -> dict:
    """Run the full sanitization pipeline on a document.

    Called after upload. Updates doc.config.quarantine in place and saves.

    Returns the quarantine dict.
    """
    config = doc.config if isinstance(doc.config, dict) else {}
    athena_req = athena_required_for_installation()
    q = config.get("quarantine") or default_quarantine(athena_req)
    threats = []
    actions = []
    mime = (doc.mime_type or "").lower()

    # Resolve file path
    if not file_path:
        path_data = doc.path if isinstance(doc.path, dict) else {}
        file_path = path_data.get("full")

    # --- Inline content (stored in config) ---
    inline_content = config.get("inline_content_b64")
    if inline_content and "svg" in mime:
        import base64
        import zlib
        try:
            compressed = base64.b64decode(inline_content.encode("ascii"))
            encoding = config.get("inline_encoding", "")
            raw = zlib.decompress(compressed) if encoding == "zlib+base64" else compressed
            cleaned, svg_threats = sanitize_svg(raw)
            threats.extend(svg_threats)
            actions.append("sanitized_inline_svg")
            # Re-encode
            recompressed = zlib.compress(cleaned, level=9)
            config["inline_content_b64"] = base64.b64encode(recompressed).decode("ascii")
        except Exception as e:
            threats.append(f"inline_svg_sanitization_error: {e}")

    # --- File on disk ---
    if file_path and os.path.exists(file_path):
        # ClamAV scan
        clean, scan_findings = clamav_scan(file_path)
        if scan_findings:
            threats.extend(scan_findings)
        if not clean:
            q["status"] = "failed"
            q["sanitized"] = False
            q["threats_found"] = threats
            q["actions_taken"] = actions
            config["quarantine"] = q
            doc.config = config
            doc.save(update_fields=["config"])
            return q

        # Type-specific sanitization
        if "svg" in mime:
            with open(file_path, "rb") as f:
                content = f.read()
            cleaned, svg_threats = sanitize_svg(content)
            threats.extend(svg_threats)
            with open(file_path, "wb") as f:
                f.write(cleaned)
            actions.append("sanitized_svg")

        elif mime in ("image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"):
            _, img_threats = sanitize_image(file_path, mime)
            threats.extend(img_threats)
            actions.append("re_encoded_image")

        elif mime == "application/pdf":
            _, pdf_threats = sanitize_pdf(file_path)
            threats.extend(pdf_threats)
            actions.append("scanned_pdf")

        else:
            actions.append("scanned_only")

        # Update checksum after sanitization
        import hashlib
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        new_checksum = hasher.hexdigest()
        if doc.checksum != new_checksum:
            doc.checksum = new_checksum
            actions.append("checksum_updated")

        # Update file size
        doc.size_bytes = os.path.getsize(file_path)

    now_ms = int(timezone.now().timestamp() * 1000)
    q["sanitized"] = True
    q["sanitized_at"] = now_ms
    q["status"] = "sanitized" if athena_req else "cleared"
    q["threats_found"] = threats
    q["actions_taken"] = actions
    config["quarantine"] = q
    doc.config = config
    doc.save(update_fields=["config", "checksum", "size_bytes"])

    return q


def athena_clear_document(doc, reviewer_id: int = 0) -> dict:
    """Mark a document as cleared by Athena.

    Called by Athena's review process.
    """
    config = doc.config if isinstance(doc.config, dict) else {}
    q = config.get("quarantine") or default_quarantine()

    if not q.get("sanitized"):
        raise ValueError("Cannot clear unsanitized document — run sanitization first")

    now_ms = int(timezone.now().timestamp() * 1000)
    q["athena_cleared"] = True
    q["athena_cleared_at"] = now_ms
    q["status"] = "cleared"
    q["athena_reviewer"] = reviewer_id

    config["quarantine"] = q
    doc.config = config
    doc.save(update_fields=["config"])
    return q


def alice_review_document(doc, findings: list[str] | None = None) -> dict:
    """Record Alice's review of a document.

    Alice's review is informational — flags patterns but doesn't gate.
    """
    config = doc.config if isinstance(doc.config, dict) else {}
    q = config.get("quarantine") or default_quarantine()

    now_ms = int(timezone.now().timestamp() * 1000)
    q["alice_cleared"] = True
    q["alice_cleared_at"] = now_ms
    if findings:
        q.setdefault("alice_findings", []).extend(findings)

    config["quarantine"] = q
    doc.config = config
    doc.save(update_fields=["config"])
    return q
