# File Storage Protocol

## The Principle

The file path IS the metadata. No database lookup needed to find a file.
No collisions between tenants. The structure is:

```
/media/<org_id>/<model>/<record_id>/<filename>
```

Every file belongs to an org, a model, and a record. The path tells you
all three without querying the database.

## Directory Structure

```
/media/
  <org_id>/                         ← tenant isolation
    contacts/
      <contact_id>/
        photo_original.jpg          ← full resolution upload
        photo_512.jpg               ← lg — detail page
        photo_256.jpg               ← md — profile
        photo_128.jpg               ← sm — contact card, chat
        photo_64.jpg                ← tn — lists, badges, gantt
    items/
      <item_id>/
        primary_original.jpg
        primary_512.jpg
        primary_256.jpg
        primary_128.jpg
        primary_64.jpg
        gallery_001_original.jpg
        gallery_001_256.jpg
        gallery_001_128.jpg
        gallery_002_original.jpg
        ...
    orgs/
      logo_original.png
      logo_512.png
      logo_128.png
      logo_64.png
      banner_original.jpg
      banner_512.jpg
      icon_64.png                   ← favicon-sized
    documents/
      <document_id>/
        <original_filename>         ← preserve original name
    actions/
      <action_id>/
        <attachment_filename>
    invoices/
      <invoice_id>/
        <pdf_filename>
    orders/
      <order_id>/
        <attachment_filename>
```

## Naming Convention

Images: `<purpose>_<size>.<ext>`
- `photo_64.jpg`, `photo_128.jpg`, `photo_256.jpg`, `photo_512.jpg`, `photo_original.jpg`
- `logo_64.png`, `logo_128.png`, `logo_original.png`
- `primary_256.jpg`, `gallery_001_128.jpg`

Documents: preserve original filename.
- `invoice_2026-07-31.pdf`
- `spec_sheet_v2.pdf`

## Upload Flow

1. User uploads original file
2. Server validates: type, size, virus scan (if configured)
3. For images: Pillow generates all sizes (64, 128, 256, 512)
4. Files written to `/media/<org_id>/<model>/<record_id>/`
5. Paths saved to `record.metadata.images` using ImageSet schema
6. Old files replaced (not versioned — documents use Document model for versioning)

## Path Builder (Python)

```python
from pathlib import Path

MEDIA_ROOT = Path("/media")  # or settings.MEDIA_ROOT

def media_path(org_id: int, model: str, record_id: int, filename: str) -> Path:
    return MEDIA_ROOT / str(org_id) / model / str(record_id) / filename

def image_sizes(org_id: int, model: str, record_id: int, purpose: str, ext: str) -> dict:
    base = MEDIA_ROOT / str(org_id) / model / str(record_id)
    return {
        "tn": str(base / f"{purpose}_64.{ext}"),
        "sm": str(base / f"{purpose}_128.{ext}"),
        "md": str(base / f"{purpose}_256.{ext}"),
        "lg": str(base / f"{purpose}_512.{ext}"),
        "original": str(base / f"{purpose}_original.{ext}"),
    }
```

## Pydantic Schemas

Defined in `common/schemas/images.py`:

| Schema | Model | Fields |
|--------|-------|--------|
| `ImageSet` | Any | tn, sm, md, lg, original, alt |
| `ContactImages` | Contact | photo (ImageSet) |
| `OrgImages` | Org | logo, banner, icon (each ImageSet) |
| `ItemImages` | Item | primary (ImageSet), gallery (list of ImageSet) |

Stored in `record.metadata.images`.

## Security

- Files served via nginx `X-Accel-Redirect` — Django validates access, nginx serves the file
- Org isolation enforced at the path level — org A cannot access org B's files
- No direct `/media/` URL access in production — always through Django view
- Document model handles versioning and access control for business documents

## Alice's Role

Alice manages the file structure:
- On upload: validates path, generates sizes, updates metadata.images
- On cleanup: finds orphaned files (metadata.images path with no file on disk)
- On sync: includes image paths in bundle manifests
- On observation: tracks which images are accessed (popular items need
  pre-generated sizes; rarely viewed items can generate on demand)

## What NOT to Store in /media/

- Temporary files (use /tmp/)
- Build artifacts (use dist/)
- Logs (use /var/log/ or ~/Allie/logs/)
- Database dumps (use /backups/)
- Credentials (never on disk unencrypted)
