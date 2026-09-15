# Alice Dedup — Duplicate Detection and Extraction

**Created:** 2026-08-10
**Service:** `apps/ai_assistant/services/dedup_service.py`
**Connection:** `conn-alice-dedup` (id=52, internal)
**Celery task:** `dedup_scan_task` — weekly Wednesday 3:30 AM UTC

---

## How It Works

Alice scans records for duplicates. Duplicates are hard-deleted from the
database and stored in a bundle file. The user works through the bundle
until it's empty.

```
Alice scans → finds duplicates → hard deletes from DB
    → writes bundle file (sync/dedup/pending/)
    → user reviews in indented list (like BOM)
    → copy field / remove / done
    → bundle file deleted when empty
```

---

## Matching Strategies

| Model | Strategy | Match Key | Confidence |
|-------|----------|-----------|------------|
| OrgBase | `name_zip` | First 8 chars of name + first 5 chars of zip | medium |
| OrgBase | `email` | Exact email match | high |
| OrgBase | `phone` | Last 7 digits of phone | medium |
| Contact | `name_email` | Same name (case-insensitive) + same email | medium |
| Contact | `email` | Exact email match | high |
| Contact | `phone` | Last 7 digits of phone | medium |
| Item | `sku` | Exact SKU match | high |
| Item | `name_vendor` | Same name + same vendor | medium |
| Item | `upc` | Exact UPC match | high |

Retained record = highest `health_rating`, then lowest pk (oldest).

---

## User Operations

Displayed as an indented list (BOM pattern):

```
Acme Corporation (retained — id=123)          [done]
    Acme Corp (dup — id=456)                  [copy field] [remove]
    ACME CORPORATION (dup — id=789)           [copy field] [remove]
```

### copy_field(bundle_id, duplicate_id, field_name)

Click a field on an indented duplicate row. That value overwrites the
same field on the retained record. One field at a time. Logged in
`bundle.response.field_copies[]`.

### remove_from_bundle(bundle_id, duplicate_id)

Hard delete from the database AND from the bundle file. Gone. Junk does
not grow better with age. If no duplicates remain, the bundle file is
deleted and the bundle record is marked success.

### mark_done(bundle_id)

User is finished reviewing. Bundle file deleted. Bundle record marked
success. Nothing archived — the user worked through every entry.

---

## Escalation to Claude

Complex cases are escalated automatically via Action records on the
Alice-Claude escalation channel (conn-alice-claude, id=32):

- More than 5 duplicates in one group
- A duplicate has higher `health_rating` than the retained record
- Duplicates have linked transactions

Claude reviews and recommends a merge strategy. The user still decides.

---

## File Layout

```
sync/dedup/
    pending/          ← active bundle files (JSON)
```

No `processed/` folder. Files are deleted when the user finishes, not
moved. Bundle records in the database are the audit trail.

---

## Bundle File Format

```json
{
  "model": "orgbase",
  "strategy": "name_zip",
  "match_key": "acme co|53711",
  "confidence": "medium",
  "dt_extracted": "2026-08-10T22:00:00+00:00",
  "retained": {
    "id": 123,
    "data": { ...full record... }
  },
  "duplicates": [
    { "id": 456, "data": { ...full record... } },
    { "id": 789, "data": { ...full record... } }
  ]
}
```

As the user removes duplicates, they are deleted from this file. When
the last duplicate is removed, the file is deleted.

---

## Adding New Models

Add to `MATCH_STRATEGIES` in `dedup_service.py` and to `_resolve_bundle.model_map`:

```python
MATCH_STRATEGIES['newmodel'] = [
    ('field_name', ['field__rule'], 'Description'),
]
```

Rules: `__exact`, `__lower`, `__8` (first N chars), `__digits_last_7`.

---

## Connection Record

| Field | Value |
|-------|-------|
| ida | `conn-alice-dedup` |
| id | 52 |
| type | internal |
| status | active |
| from_agent | alice |
| to_agent | claude_code |
| operations | copy_field, remove_from_bundle, mark_done |
| ui_pattern | indented_list |
| hard_delete | true |
| bundle_is_archive | true (until user works through it) |
