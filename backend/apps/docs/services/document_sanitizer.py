"""Uploaded documents: quarantine, check, then release (Bill, 2026-11-22: "they are to be
put in quarantine until checked. Then moved to a permanent location").

Quarantine is a place, not only a flag. An upload is written under
DATA_DIR/quarantine/document/ and its record says path.storage = 'quarantine'. It moves to
permanent storage (uploads/document/YYYY/MM/, path.storage = 'local') only when:

    1. a check that applies to its type has actually run and passed, and
    2. Athena has cleared it, where the installation requires that (WCHQ does).

The checks are plain code, the same answer every time:
    - a virus scan (ClamAV), when the scanner is running;
    - executables are refused by their first bytes, whatever they are named;
    - images are re-encoded (what is not an image fails); SVG has scripts removed;
    - a PDF must be a PDF, and one that carries JavaScript, a launch action or an
      embedded file is refused.

A scanner that is not running is not a pass. Images and SVG are made safe by their own
check; every other type waits in quarantine (status 'pending') until a scan can run.
`manage.py quarantine --recheck` runs the checks again on what is waiting.

State lives in document.config.quarantine:
    status: pending (waiting for a check) | failed (refused) |
            sanitized (checked, waiting for Athena) | cleared (released)
"""
import io
import logging
import os
import re

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
        "virus_scan": "",
        "reason": "",
        "released_at": None,
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
    path = doc.path if isinstance(doc.path, dict) else {}
    return path.get("storage") != "quarantine"


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


class CheckFailed(Exception):
    """The file is refused. The message is the reason shown on the document."""


EXECUTABLE_STARTS = (
    (b"MZ", "Windows executable"), (b"\x7fELF", "Linux executable"),
    (b"\xcf\xfa\xed\xfe", "macOS executable"), (b"\xce\xfa\xed\xfe", "macOS executable"),
    (b"\xca\xfe\xba\xbe", "macOS or Java executable"), (b"#!", "script with an interpreter line"),
)
# PDF features that run code or carry other files. /OpenAction and /AA are noted, not
# refused: ordinary PDFs use them to open at a page.
PDF_REFUSED = (b"/JS", b"/JavaScript", b"/Launch", b"/EmbeddedFile")
PDF_NOTED = (b"/OpenAction", b"/AA")
IMAGE_TYPES = {"image/jpeg": "JPEG", "image/jpg": "JPEG", "image/png": "PNG",
               "image/gif": "GIF", "image/webp": "WEBP"}


def refuse_executable(file_path: str) -> None:
    with open(file_path, "rb") as f:
        head = f.read(8)
    for start, what in EXECUTABLE_STARTS:
        if head.startswith(start):
            raise CheckFailed(f"the file is a {what}")


def sanitize_image(file_path: str, mime_type: str) -> list[str]:
    """Re-encode the image in place, which drops metadata and anything hidden after the
    picture. A file that will not open as its stated kind of image is refused."""
    from PIL import Image
    fmt = IMAGE_TYPES[mime_type]
    notes = []
    try:
        img = Image.open(file_path)
        if (img.format or "").upper() != fmt:
            raise CheckFailed(f"the file says {mime_type} but holds {img.format or 'no image'}")
        if img.getexif():
            notes.append("stripped EXIF metadata")
        out = io.BytesIO()
        if fmt == "JPEG":
            img.convert("RGB").save(out, format=fmt, quality=95)
        else:
            img.save(out, format=fmt)
    except CheckFailed:
        raise
    except Exception as e:
        raise CheckFailed(f"the file is not a readable {fmt} image ({type(e).__name__})") from e
    with open(file_path, "wb") as f:
        f.write(out.getvalue())
    notes.append(f"re-encoded as {fmt}")
    return notes


def check_pdf(file_path: str) -> list[str]:
    """A PDF must be a PDF and must not carry code or other files. Nothing is rewritten:
    cutting pieces out of a PDF by pattern does not make it safe and can break it.
    Limit: markers inside compressed object streams are not seen; the virus scan covers
    those when it runs."""
    with open(file_path, "rb") as f:
        content = f.read()
    if b"%PDF-" not in content[:1024]:
        raise CheckFailed("the file says PDF but does not begin as one")
    found = [m.decode() for m in PDF_REFUSED if re.search(re.escape(m) + rb"(?![A-Za-z])", content)]
    if found:
        raise CheckFailed(f"the PDF carries active content: {', '.join(found)}")
    return [f"PDF has {m.decode()} (allowed)" for m in PDF_NOTED
            if re.search(re.escape(m) + rb"(?![A-Za-z])", content)]


def clamav_scan(file_path: str) -> tuple[str, list[str]]:
    """Scan with ClamAV. Returns ('clean' | 'infected' | 'not_run', findings).
    'not_run' is never treated as clean by the caller."""
    from django.conf import settings
    try:
        import pyclamd
        cd = pyclamd.ClamdUnixSocket(settings.CLAMD_SOCKET)
        cd.ping()
    except Exception as e:
        return "not_run", [f"virus scanner not reachable at {settings.CLAMD_SOCKET} ({type(e).__name__})"]
    try:
        result = cd.scan_file(file_path)
    except Exception as e:
        logger.error(f"ClamAV scan error: {e}")
        return "not_run", [f"virus scan error: {e}"]
    if result is None:
        return "clean", []
    found = [f"{info[1]} ({info[0]})" for info in result.values() if info[0] == "FOUND"]
    if found:
        return "infected", found
    # The scanner answered but could not read the file: that is not a scan.
    return "not_run", [f"virus scanner could not read the file: {info[1]}" for info in result.values()]


def check_file(file_path: str, mime: str) -> tuple[str, list[str], list[str], str]:
    """Run every check that applies. Returns (verdict, findings, actions, virus_scan):
    verdict 'pass' (a check ran and passed), 'fail' (refused), or 'unchecked' (nothing
    that applies to this type could run)."""
    findings, actions = [], []
    scan, scan_findings = clamav_scan(file_path)
    findings.extend(scan_findings)
    if scan == "infected":
        return "fail", findings, actions, scan
    try:
        refuse_executable(file_path)
        type_checked = True
        if "svg" in mime:
            with open(file_path, "rb") as f:
                cleaned, svg_notes = sanitize_svg(f.read())
            with open(file_path, "wb") as f:
                f.write(cleaned)
            findings.extend(svg_notes)
            actions.append("sanitized_svg")
        elif mime in IMAGE_TYPES:
            findings.extend(sanitize_image(file_path, mime))
            actions.append("re_encoded_image")
        elif mime == "application/pdf":
            findings.extend(check_pdf(file_path))
            actions.append("checked_pdf")
            type_checked = False        # the PDF check has a stated limit: it needs the scan too
        else:
            type_checked = False
    except CheckFailed as e:
        findings.append(str(e))
        return "fail", findings, actions, scan
    if scan == "clean":
        actions.append("virus_scanned")
    return ("pass" if scan == "clean" or type_checked else "unchecked"), findings, actions, scan


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def release(doc) -> str:
    """Move a checked document's file out of quarantine into permanent storage and point
    the record at it. Returns the new key. Does nothing if it is already released."""
    from django.conf import settings
    from apps.docs.views.upload_view import _build_storage_path
    path = dict(doc.path) if isinstance(doc.path, dict) else {}
    if path.get("storage") != "quarantine":
        return path.get("key", "")
    old = os.path.join(str(settings.DATA_DIR), path["key"])
    key = _build_storage_path(path["key"])["key"]
    new = os.path.join(str(settings.DATA_DIR), key)
    os.makedirs(os.path.dirname(new), exist_ok=True)
    os.replace(old, new)
    doc.path = {**path, "storage": "local", "key": key}
    return key


def sanitize_document(doc, file_path: str | None = None) -> dict:
    """Check a quarantined document; release it if it passes and no Athena clearance is
    owed. Safe to run again on a document that is still waiting. Returns the quarantine dict."""
    config = doc.config if isinstance(doc.config, dict) else {}
    athena_req = athena_required_for_installation()
    q = {**default_quarantine(athena_req), **(config.get("quarantine") or {})}
    q["athena_required"] = athena_req
    mime = (doc.mime_type or "").lower()
    now_ms = int(timezone.now().timestamp() * 1000)

    if not file_path:
        from apps.docs.views.upload_view import document_file
        file_path = document_file(doc)

    # A drawing held in the record itself, not on disk
    inline_content = config.get("inline_content_b64")
    inline_notes = []
    if inline_content and "svg" in mime:
        import base64
        import zlib
        compressed = base64.b64decode(inline_content.encode("ascii"))
        raw = zlib.decompress(compressed) if config.get("inline_encoding") == "zlib+base64" else compressed
        cleaned, inline_notes = sanitize_svg(raw)
        config["inline_content_b64"] = base64.b64encode(zlib.compress(cleaned, level=9)).decode("ascii")

    if file_path and os.path.exists(file_path):
        verdict, findings, actions, scan = check_file(file_path, mime)
    elif inline_content and "svg" in mime:
        verdict, findings, actions, scan = "pass", [], ["sanitized_inline_svg"], "not_run"
    else:
        verdict, findings, actions, scan = "fail", ["the uploaded file is not in quarantine"], [], "not_run"
    findings = inline_notes + findings

    q.update(threats_found=findings, actions_taken=actions, virus_scan=scan)
    if verdict == "fail":
        q.update(status="failed", sanitized=False, reason=findings[-1])
    elif verdict == "unchecked":
        q.update(status="pending", sanitized=False,
                 reason="waiting for a virus scan: no check for this type of file could run")
    else:
        if file_path and os.path.exists(file_path):
            import hashlib
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            if doc.checksum != hasher.hexdigest():
                doc.checksum = hasher.hexdigest()
                actions.append("checksum_updated")
            doc.size_bytes = os.path.getsize(file_path)
        q.update(sanitized=True, sanitized_at=now_ms, reason="")
        if q["athena_required"] and not q.get("athena_cleared"):
            q["status"] = "sanitized"
        else:
            release(doc)
            q.update(status="cleared", released_at=now_ms)

    meta = doc.metadata if isinstance(doc.metadata, dict) else {}
    meta["virus"] = {**(meta.get("virus") or {}),
                     "status": {"clean": "clean", "infected": "infected"}.get(scan, "skipped"),
                     "scanner": "clamav" if scan != "not_run" else "",
                     "scanned_at": now_ms if scan != "not_run" else 0,
                     "threat": findings[0] if scan == "infected" else None,
                     "quarantined": q["status"] != "cleared"}
    doc.metadata = meta
    config["quarantine"] = q
    doc.config = config
    doc.save(update_fields=["config", "metadata", "path", "checksum", "size_bytes"])
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
    q["released_at"] = now_ms
    q["athena_reviewer"] = reviewer_id
    release(doc)
    meta = doc.metadata if isinstance(doc.metadata, dict) else {}
    if isinstance(meta.get("virus"), dict):
        meta["virus"]["quarantined"] = False
        doc.metadata = meta

    config["quarantine"] = q
    doc.config = config
    doc.save(update_fields=["config", "metadata", "path"])
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
