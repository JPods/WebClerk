# Envelope Security Constraints

**Established:** 2026-09-02
**Applies to:** Every BaseModel record — all six JSON envelopes

## Principle

Documents go through `Document.path`. Everything else is bounded text.
Reject oversized payloads before processing. Binary content is forbidden
outside the document path. Every list has a count limit. Every string has
a length limit. Every dict has a key count limit. Every merge has a depth limit.

Guards exist at **both** layers:
- **Frontend** — validates before sending (character counters, field limits, type checks)
- **Backend** — hard enforcement that rejects and returns clear errors

The frontend is a courtesy. The backend is the law.

## HTTP Gate (settings.py)

| Setting | Value | Purpose |
|---------|-------|---------|
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 2 MB | Reject oversized requests before Django parses |
| `DATA_UPLOAD_MAX_NUMBER_FIELDS` | 200 | Prevent field-count abuse |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | 5 MB | Files go through Document.path |

## Binary / Base64 Rejection

Documents go through `Document.path` — the only field on the only model that
may contain binary content. All other fields on all other models reject
base64 and data URIs.

Detection (`looks_like_binary()` in `envelopes.py`):
- Data URI pattern: `data:*;base64,`
- Base64 pattern: 40+ base64 chars in the first 200 chars
- Only triggers on strings >= 500 chars (short strings are never flagged)

Enforcement:
- **Schema layer**: `MetadataBase` string validators reject binary in `explanation`, `publish`, `priority`, `security`
- **Runtime layer**: `_check_binary_content()` in `save_field_assignment.py` checks every string value before assignment; only `document.path` is exempt

## userdefined Constraints

| # | Constraint | Limit |
|---|-----------|-------|
| 1 | Max key count | 20 pairs |
| 2 | Key name length | 64 chars |
| 3 | Value length | 255 chars (strings) |
| 4 | Flat scalars only | `str`, `int`, `float`, `bool`, `None` |
| 5 | No dot-path nesting | `prefs.userdefined.key` OK; `prefs.userdefined.key.nested` rejected |

Enforced at:
- `envelopes.py` — `validate_userdefined()` with `@field_validator` on MetadataBase + RecordPrefsBase
- `save_field_assignment.py` — `_store_unknown_field()` pre-write checks + dot-path guard in `assign_fields()`

## Tags

| Constraint | Limit |
|-----------|-------|
| Max count | 50 tags per record |
| Tag length | 64 chars per tag |

Enforced: `RecordPrefsBase._validate_tags()`

## Comments

| Constraint | Limit |
|-----------|-------|
| Text length | 1,000 chars per entry |
| by/source/ts length | 255 chars |
| Entries per channel | 500 (public, process, foreign each) |

Enforced: `CommentEntry._cap_text()`, `CommentChannels._cap_channel_count()`

## Saved Searches

| Constraint | Limit |
|-----------|-------|
| Searches per record | 25 |
| Filter keys per search | 10 |
| Search fields per search | 20 |
| Name/model_name length | 255 chars |

Enforced: `RecordPrefsBase._validate_search_count()`, `SavedSearch._cap_filters()`, `SavedSearch._cap_search_fields()`

## Audit Trail

| Constraint | Limit |
|-----------|-------|
| Max entries | 500 per record |
| Detail dict size | 2,048 bytes per entry |
| Action string | 255 chars |

Enforced: `MetadataBase._cap_audit_trail()`, `AuditEntry._cap_details_size()`

## Lists (erosions, small_stings, temp)

| List | Max count |
|------|----------|
| erosions | 50 |
| small_stings | 100 |
| temp | 50 |

Enforced: `MetadataBase._cap_erosions()`, `_cap_small_stings()`, `_cap_temp()`

## Saved Addresses (CartPrefsMixin)

| Constraint | Limit |
|-----------|-------|
| Max addresses | 10 |

Enforced: `CartPrefsMixin._cap_addresses()`

## Notifications (Rep/Employee/Cart)

| Constraint | Limit |
|-----------|-------|
| Max keys | 20 per notifications dict |

Enforced: `_cap_notifications()` on RepPrefsMixin, EmployeePrefsMixin, CartPrefsMixin

## Metadata String Fields

| Field | Max length |
|-------|-----------|
| explanation, publish, priority, security | 10,000 chars |

These also reject binary/base64 content.

Enforced: `MetadataBase._cap_metadata_strings()`

## JSON Depth Limits

| Where | Max depth | Mechanism |
|-------|----------|-----------|
| `deep_merge_dict()` in save_field_assignment.py | 8 levels | Checks both recursion depth and incoming value depth |
| `_deep_merge()` in json_ops.py | 8 levels | Same dual check |
| `deep_merge_dict()` in save_view.py | 8 levels | Same (imported by write_through.py) |
| `apply_json_op()` path depth | 8 segments | Rejects paths with > 8 dot-separated segments |
| Dot-path in `assign_fields()` | 8 segments | Same check before handing to json_ops |

## Envelope Size Limits (models.py — pre-existing)

| Envelope | Max size |
|----------|---------|
| metadata | 128 KB |
| prefs | 96 KB |
| config | 64 KB |
| refs | 64 KB |
| actions | 32 KB |

Warning at 75% of limit. These are checked at `BaseModel.save()` time.

## Frontend Responsibilities

The backend rejects violations with HTTP 400 and clear error messages. The
frontend should prevent users from hitting these limits:

- **Character counters** on comment text, tag input, search name fields
- **Count indicators** showing "3 of 20 custom fields used"
- **Tag input** that refuses tags > 64 chars or > 50 total
- **Address list** that hides "add" button after 10 entries
- **Saved search list** that warns at 25
- **File upload** routed exclusively through Document.path — never inline base64

## Files

| File | What it does |
|------|-------------|
| `webclerk3_api/settings.py` | HTTP payload size gates |
| `common/schemas/envelopes.py` | All Pydantic validators + `looks_like_binary()` + constants |
| `apps/core/services/save_field_assignment.py` | Runtime save gate — userdefined, binary, depth, dot-path |
| `apps/core/services/json_ops.py` | Path depth + merge depth limits |
| `apps/core/views/save_view.py` | `deep_merge_dict` depth limit (also used by write_through.py) |
| `apps/core/services/save_envelope.py` | Pydantic validation bridge — calls schema validators after field assignment |
