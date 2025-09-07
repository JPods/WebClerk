# Readme Documentation Sync Pipeline


<!-- TOC START -->

## Table of Contents

- [Readme Documentation Sync Pipeline](#readme-documentation-sync-pipeline)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Data Model Mapping](#data-model-mapping)
  - [Management Command Usage](#management-command-usage)
    - [Core Options](#core-options)
    - [Examples](#examples)
  - [Slug Generation Logic](#slug-generation-logic)
  - [Exported Index Structure](#exported-index-structure)
  - [React Client Access](#react-client-access)
  - [Typical Lifecycle](#typical-lifecycle)
  - [Integration Recommendations](#integration-recommendations)
  - [Edge Cases & Notes](#edge-cases-notes)
  - [Future Extensions (Roadmap)](#future-extensions-roadmap)
  - [Troubleshooting](#troubleshooting)
  - [Minimal Internal API Contract](#minimal-internal-api-contract)
  - [At A Glance (Cheat Sheet)](#at-a-glance-cheat-sheet)

<!-- TOC END -->

This document explains how markdown files in the repository are ingested into `Document` rows (model_name = `readme`), exposed via API endpoints, and exported as a lightweight JSON index for client (React) consumption.

---

## Overview

Source markdown lives primarily under the `readmes/` directory (and any additional roots you specify). A custom Django management command `sync_readmes` scans these folders, normalizes and imports each markdown file into the `Document` model, generating a stable `slug` for React routing.

Key features:

- Idempotent: Uses SHA256 checksum & body comparison to skip unchanged files unless forced.
- Collision-safe slugs: Auto-resolves duplicates by appending numeric suffixes during a single scan.
- Filtering: Include-only glob patterns (`--pattern`) and modification time gating (`--modified-since`).
- Size management: Skip or truncate oversized files (`--max-bytes`, `--truncate`).
- Empty file handling: Optionally persist empty markdown (`--allow-empty`).
- Deletion detection: Remove `Document` rows when source files disappear (`--delete-missing`).
- Dry runs: Preview create/update/delete actions (`--dry-run`).
- Lightweight search index: Optional JSON index export with top-level headings (`--export-index`).

---
## Data Model Mapping

Each markdown file becomes a `Document` with:

- `slug`: Derived from filename (and parent folder if name is generic like `README.md`).
- `name`: First H1 line (or stem if absent).
- `description`: Auto-filled reference to source path.
- `body`: Entire markdown content (possibly truncated if configured).
- `model_name`: Always `readme` for these ingested docs.
- `data` JSON extras:
  - `category`: `readme`
  - `source_path`: Repository-relative path
  - `checksum`: SHA256 of the original full file contents
  - `bytes`: Raw file size in bytes
  - `truncated`: Boolean (true if truncated due to `--max-bytes` + `--truncate`)
  - `headings`: Up to 50 extracted H1/H2 headings (skips deeper levels) for client-side indexing

---
## Management Command Usage

Invoke from project root:

```bash
python manage.py sync_readmes [options]
```

### Core Options

| Option | Description |
| ------ | ----------- |
| `--root <dir>` | Add an additional scan root (repeatable). Defaults to `readmes`. |
| `--delete-missing` | Delete `readme` documents whose source file is gone. |
| `--dry-run` | Show actions without persisting changes. |
| `--force` | Update body & metadata even if checksum & content unchanged. |
| `--pattern <glob>` | Include-only glob (repeatable). If any given, non-matching files ignored. |
| `--modified-since <ts>` | Only process files modified at/after timestamp (epoch ms or `YYYY-MM-DDTHH:MM:SSZ`). |
| `--max-bytes N` | If >0, skip (or truncate) files larger than N bytes. |
| `--truncate` | With `--max-bytes`, ingest truncated slice instead of skipping. |
| `--allow-empty` | Ingest empty markdown files (otherwise skipped). |
| `--export-index` | Emit a JSON index (array of records) capturing slug/title/path/headings. |
| `--index-path <file>` | Path for the index file (default `docs_index.json`). |

### Examples

Only update changed files (standard run):

```bash
python manage.py sync_readmes
```

Dry run with pattern filter:

```bash
python manage.py sync_readmes --pattern "readmes/api/*.md" --dry-run
```

Process only updates after a given time (UTC ISO8601):

```bash
python manage.py sync_readmes --modified-since 2025-09-05T12:00:00Z
```

Epoch ms variant:

```bash
python manage.py sync_readmes --modified-since 1725537600000
```

Truncate very large files to first 50 KB and export index:

```bash
python manage.py sync_readmes --max-bytes 51200 --truncate --export-index
```

Include an additional root and delete removed docs:

```bash
python manage.py sync_readmes --root docs --delete-missing
```

Force refresh all metadata even if unchanged:

```bash
python manage.py sync_readmes --force
```

---
## Slug Generation Logic

1. Start with slugified filename stem.
2. If stem is `readme`, prepend parent directory name (e.g. `integration-readme`).
3. Trim to 230 chars (leaves space for collision suffix).
4. On in-scan collision, append `-2`, `-3`, etc. while keeping under length limit.

---



## Exported Index Structure

When `--export-index` is supplied, a JSON file is produced (default `docs_index.json`):

```json
[
  {
    "slug": "item-model",
    "title": "Item Model",
    "path": "readmes/item-model.md",
    "bytes": 1234,
    "headings": ["Item Model", "Fields", "Relationships"]
  }
]
```

Intended uses:

- Fast client-side slug -> title lookup (navigation menus)
- Pre-search scaffolding (fuzzy or prefix search over headings)
- Change detection (compare previous export in CI)

---



## React Client Access

Two API endpoints (DRF views):

- `GET /api/docs/readmes/` – list of readme documents (lightweight serializer)
- `GET /api/docs/readmes/<slug>/` – detail (full body)

Future enhancements (optional):

- ETag / Last-Modified headers using checksum & updated timestamp
- `/api/docs/readmes/search?q=` backed by the JSON index (or DB search)
- HTML pre-render / caching layer

---



## Typical Lifecycle

1. Author edits markdown under `readmes/` (or other configured root).
2. Run `python manage.py sync_readmes` (manually, in reset script, or CI pipeline).
3. Updated/created/deleted docs reflected in DB. API immediately serves new content by slug.
4. Optional: Exported index shipped with build artifact for instant client bootstrapping.

---



## Integration Recommendations

- Add to dev reset script (e.g. after migrations) so local environments always have docs loaded.
- Add a CI job that runs with `--dry-run --delete-missing --export-index` and fails if unexpected destructive changes occur (diff index against previous commit).
- Cache the exported index in CDN for ultra-fast unauthenticated navigation if docs are public.

---



## Edge Cases & Notes

- Empty files skipped unless `--allow-empty`.
- Files beyond size threshold skipped unless `--truncate`, in which case the truncated flag is recorded.
- Collisions only resolved within a single run; if two distinct files later converge on same slug after rename, stale doc may persist until one is removed or `--delete-missing` is used.
- Heading extraction intentionally limited to H1/H2 to keep index small.
- Checksum based on full original file (not truncated slice) so detecting true content change still works even if stored body is truncated.

---



## Future Extensions (Roadmap)

- Search endpoint leveraging Postgres full text or in-memory index build from exported JSON.
- Markdown to HTML pre-render & sanitized snippet extraction.
- Differential index output (additions / removals) for PR visualizations.
- Multi-language / versioned doc support via additional metadata fields (`lang`, `version`).
- Permission tiers using `security_level` for internal vs external docs.

---



## Troubleshooting

| Symptom | Possible Cause | Resolution |
| ------- | -------------- | ---------- |
| Command shows 0 discovered | Wrong root path | Pass `--root` or ensure directory exists. |
| Unexpected deletions | Used `--delete-missing` with missing root | Re-run without option or add correct root. |
| Slug mismatch with expected | Collision or generic README path logic | Check actual file path; adjust filename for desired slug. |
| Large file skipped | Exceeded `--max-bytes` without `--truncate` | Add `--truncate` or raise threshold. |
| Index missing headings | File has only deeper headings (H3+) | Add an H1/H2 or extend extractor logic. |

---



## Minimal Internal API Contract

List endpoint returns objects with: `slug`, `name`, `description`.

Detail endpoint returns above plus: `body`, `data` (with `headings`, `checksum`, etc.).

---



## At A Glance (Cheat Sheet)



- Sync everything: `python manage.py sync_readmes`
- Export index: `python manage.py sync_readmes --export-index`
- Focus subset: `python manage.py sync_readmes --pattern "readmes/api/*.md"`
- Refresh all metadata: `python manage.py sync_readmes --force`
- Clean up removed docs: `python manage.py sync_readmes --delete-missing`
- Large-file safe import: `python manage.py sync_readmes --max-bytes 65536 --truncate`

---
Maintainer: (add owner/contact)
