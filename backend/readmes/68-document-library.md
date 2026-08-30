# Document Library — File Upload, Local Storage, Cloud Transfer
**Created:** 2026-08-09
**Owner:** Alice (library management via Celery)

---

## What It Does

Users upload photos, videos, PDFs, and other files through WC3. Each file becomes a Document record — the single source of truth for that file's identity, location, and lifecycle. Files are stored locally first, then Alice transfers them to a secure cloud library via Celery tasks.

The user owns their data. The cloud library is storage, not a platform. Files can always be retrieved, moved, or deleted by the owner.

---

## The Flow

```
Upload → Checksum → Dedup check → Document record → Local storage
    ↓
Alice Celery pipeline:
    Virus scan → Thumbnail generation → Cloud transfer → Verify → Cleanup local
```

Flowchart: `readmes/flowcharts/wc3-document-library.dot`
```bash
dot -Tpdf readmes/flowcharts/wc3-document-library.dot -o readmes/flowcharts/wc3-document-library.pdf
```

---

## Upload

**Endpoint:** `POST /wcapi/upload/`

| Field | Required | What it does |
|-------|----------|-------------|
| `file` | Yes | The uploaded file (multipart) |
| `model_name` | No | Parent model: order, invoice, contact, item, action, project |
| `parent_id` | No | Parent record ID — links file to a business record |
| `purpose` | No | Why: attachment, photo, receipt, proof, spec_sheet, certificate |
| `description` | No | Human description |
| `address_*` | No | Street, city, state, postal_code, country — where taken/relevant |
| `geo_lat`, `geo_lng` | No | GPS coordinates (mobile uploads) |

**What happens immediately:**
1. SHA256 checksum computed
2. Dedup check — if checksum exists, return existing Document (no duplicate storage)
3. Document record created with `status=uploaded`
4. File stored locally:
   - Small files (< 5MB): inline in `config` as zlib+base64
   - Large files: filesystem at `.local/uploads/document/YYYY/MM/uuid.ext`
5. `path` JSONField set: `{storage: "local", key: "...", url: "/wcapi/document/{id}/"}`

**Response:** Document ID, path, checksum, is_duplicate flag, download URL

---

## Document Record — Key Fields

| Field | What it holds |
|-------|-------------|
| `name` | Original filename |
| `slug` | Stable identifier for API/URLs |
| `status` | uploaded → scanned → transferring → archived (or virus_detected) |
| `mime_type` | File MIME type (image/jpeg, video/mp4, application/pdf, etc.) |
| `size_bytes` | File size |
| `checksum` | SHA256 — identity and dedup key |
| `path` | JSONField: storage location (local, inline, cloud), key, url, remote_url |
| `confidential` | public / internal / restricted / confidential / secret |
| `config` | Inline content (small files), thumbnails, EXIF data, scan results |
| `metadata` | History, original_name, address, geo, purpose |
| `refs` | Parent linkage: `{parent: {model_name, parent_id}}` |

---

## Alice's Celery Tasks — Library Management

Alice owns the pipeline from upload to cloud. These are her responsibilities.

### Task Registry

| Task | Beat | What it does |
|------|------|-------------|
| `alice_library_scan` | Every 1 min | Virus scan new uploads; status → scanned or virus_detected |
| `alice_library_thumbnails` | Every 1 min | Generate 200×200 thumbnails for images/videos |
| `alice_library_transfer` | Async | Upload file to secure cloud library; set path.remote_url |
| `alice_library_verify` | Every 2 min | Checksum verify: local == remote; trigger cleanup on match |
| `alice_library_cleanup` | Async | Delete local copy after verified transfer; status → archived |
| `alice_library_monitor` | Every 5 min | Find stuck transfers (> 2 hours); retry or alert |
| `alice_library_dedup` | Every 5 min | Catch duplicates that slipped past upload-time check |

### Pipeline Rules

1. **No file moves to cloud without virus scan.** Infected files get `status=virus_detected` and stop.
2. **No local copy deleted without checksum verification.** `checksum(local) == checksum(remote)` or the transfer failed.
3. **Thumbnails are generated before transfer.** Users see previews immediately; thumbnails are small and stay local.
4. **Failed transfers retry 3 times, then alert.** Alice logs a FAULT file for Allie's nightly synthesis.
5. **Confidential files get extra handling.** `confidential=restricted` or higher: encrypted before transfer, access-logged on every download.

### Status Lifecycle

```
uploaded → scanned → transferring → archived
                ↘ virus_detected (terminal)
```

---

## Download

**Endpoint:** `GET /wcapi/document/<id>/`

- If file is local: serves directly with proper MIME type and Content-Disposition
- If file is in cloud: redirects to secure signed URL (time-limited)
- `count_accessed` incremented on every download
- Confidential files: access logged in `metadata.access`

---

## Local Storage Layout

```
.local/uploads/document/
    2026/
        08/
            a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
            b2c3d4e5-f6a7-8901-bcde-f12345678901.pdf
    thumbnails/
        a1b2c3d4-e5f6-7890-abcd-ef1234567890_thumb.png
```

Small files (< 5MB) stored inline in Document.config — no filesystem entry.

---

## Cloud Library

The cloud library is secure file storage — not a platform, not a service that owns the data. Requirements:

- **Encrypted at rest** — AES-256 or equivalent
- **Signed URLs for access** — time-limited, no permanent public links
- **Checksum verified** — SHA256 match on upload, periodic integrity checks
- **User-owned** — files deletable by owner at any time; no vendor lock-in
- **Audit trail** — every access logged with who, when, why

Cloud provider is configurable via Setting. Default: S3-compatible storage. The Document.path JSONField handles the abstraction:

```json
{
    "storage": "cloud",
    "key": "uploads/document/2026/08/uuid.jpg",
    "url": "/wcapi/document/456/",
    "remote_url": "https://library.example.com/...",
    "remote_checksum": "sha256:abc123..."
}
```

---

## Parent Linkage

Files attach to any WC3 model through `refs.parent`:

```json
{
    "parent": {
        "model_name": "order",
        "parent_id": 123
    }
}
```

Common attachments:
- **Order** — photos of custom specs, signed POs
- **Invoice** — proof of delivery, signed receipts
- **Contact** — profile photos, business cards, ID scans
- **Item** — product photos, spec sheets, certificates
- **Action** — task evidence, inspection photos, site photos
- **Project** — plans, drawings, progress photos

---

## Sovereignty

Files belong to the user, not WebClerk. This means:
- User can export all their files at any time (bulk download)
- User can delete files permanently (not just soft-delete)
- Cloud transfer is a service the user opted into, not a requirement
- Local-only mode works indefinitely — cloud is convenience, not dependency
- MyCarryOn portable identity can reference Document records via UUID

---

## Files

| File | What it is |
|------|-----------|
| `apps/docs/models/document.py` | Document model |
| `apps/docs/views_upload.py` | Upload/download/delete endpoints |
| `apps/docs/urls.py` | URL routing |
| `apps/docs/tasks.py` | Alice's Celery library management tasks (to be created) |
| `readmes/flowcharts/wc3-document-library.dot` | Flow diagram |
| `webclerk3_api/celery.py` | Celery configuration |
