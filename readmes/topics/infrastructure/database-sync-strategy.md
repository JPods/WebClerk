# Database Sync Strategy — Keeping Remote & Local Current

Date: 2026-02-18
Status: Implemented (write-through proxy); Plan (incremental sync phases 1–3)
Owner: Bill

---

## Table of Contents

- [Purpose](#purpose)
- [Current State](#current-state)
- [Identity Model: id + uuid](#identity-model-id--uuid)
- [Change Detection: What Existing Django Gives Us](#change-detection-what-existing-django-gives-us)
- [Sync Direction & Conflict Rules](#sync-direction--conflict-rules)
- [Incremental Sync Design](#incremental-sync-design)
  - [Phase 1 — Timestamp-Based Delta Pull](#phase-1--timestamp-based-delta-pull)
  - [Phase 2 — Bidirectional Merge](#phase-2--bidirectional-merge)
  - [Phase 3 — Event-Driven Notification](#phase-3--event-driven-notification)
- [Implementation Using Django Behaviors](#implementation-using-django-behaviors)
  - [CoreModel.save() — Built-in Change Tracking](#coremodelsave--built-in-change-tracking)
  - [Version Field — Optimistic Concurrency](#version-field--optimistic-concurrency)
  - [Django Signals — post_save for Sync Journaling](#django-signals--post_save-for-sync-journaling)
  - [Management Commands — Extending sync_model](#management-commands--extending-sync_model)
- [Record Matching Algorithm](#record-matching-algorithm)
- [Sync Journal Model](#sync-journal-model)
- [Workflow Scenarios](#workflow-scenarios)
  - [Developer refreshes local from remote](#developer-refreshes-local-from-remote)
  - [Developer pushes local changes to remote](#developer-pushes-local-changes-to-remote)
  - [Two developers edit the same record](#two-developers-edit-the-same-record)
  - [New record created on local, synced to remote](#new-record-created-on-local-synced-to-remote)
- [Sync Metadata in JSONB Envelope](#sync-metadata-in-jsonb-envelope)
- [Write-Through Proxy — Read Local, Save Remote](#write-through-proxy--read-local-save-remote)
  - [How It Works](#how-it-works-1)
  - [Request Flow — New Record (create)](#request-flow--new-record-create)
  - [Request Flow — Existing Record (update)](#request-flow--existing-record-update)
  - [The Response Bundle](#the-response-bundle)
  - [Offline / Remote-Unreachable Behavior](#offline--remote-unreachable-behavior)
  - [What This Eliminates](#what-this-eliminates)
  - [What sync_model Becomes](#what-sync_model-becomes)
  - [Implementation Sketch](#implementation-sketch)
- [FK Dependency Order](#fk-dependency-order)
- [Safety & Guardrails](#safety--guardrails)
- [Open Questions](#open-questions)
- [Related Documentation](#related-documentation)

---

## Purpose

Define how the remote (shared/production) and local (developer) copies of
the PostgreSQL database stay current with each other using:

1. **Existing Django behaviors** — `CoreModel.save()`, `dt_modified`,
   `version`, signals, and management commands.
2. **The id/uuid identity rule** — `id` is unique within a single database;
   `uuid` is unique across databases. When both match between databases,
   the record is the same entity and the latest copy is an update, not a
   new record.
3. **A defined, repeatable process** for bidirectional sync that avoids
   data loss, detects conflicts, and leverages infrastructure already in
   place.

---

## Current State

| Capability | Status | Location |
|---|---|---|
| Full-table copy (sync_model) | Implemented | `apps/core/management/commands/sync_model.py` |
| id + uuid + ida on every model | Implemented | `common/models.py → CoreModel` |
| dt_modified updated on every save | Implemented | `CoreModel.save()` |
| version bump on every update | Implemented | `CoreModel.save()` |
| PK/UUID match → update logic | Implemented | `sync_model.py` conflict handler |
| Incremental (delta) sync | **Not yet** | — |
| Sync journal (change log) | **Not yet** | — |
| Bidirectional merge with conflict UI | **Not yet** | — |
| Write-through proxy (read local, save remote) | **Not yet** | — |

The existing `sync_model` command copies all rows for one model at a time.
It handles PK/UUID matching to update-in-place versus insert-new. But it
always does a **full pass** — it is not incremental and not suitable for
ongoing replication between actively used databases.

---

## Identity Model: id + uuid

Every record in the system inherits from `CoreModel`:

```
┌──────────────────────────────────────────────────────────────┐
│ CoreModel                                                     │
├──────────────────────────────────────────────────────────────┤
│ id       BigAutoField   PK, auto-increment, unique per DB    │
│ uuid     UUIDField      unique across ALL databases           │
│ ida      CharField(40)  soft id from external systems         │
│ dt_created   BigInteger   epoch ms, set once on insert        │
│ dt_modified  BigInteger   epoch ms, updated on every save     │
│ version      PositiveInt  bumped on every update              │
└──────────────────────────────────────────────────────────────┘
```

### The Matching Rule

Given a record on Database A and a record on Database B:

| id match? | uuid match? | Interpretation | Action |
|---|---|---|---|
| Yes | Yes | Same record, same entity | **Update** — take the one with later `dt_modified` |
| Yes | No | PK collision, different entities | **Conflict** — reassign PK on the incoming record |
| No | Yes | Same entity, different PKs | **Update** — align to target's PK, take later `dt_modified` |
| No | No | Completely different records | **Insert** — new record on the target |

The uuid is the **authoritative cross-database identity**. The id (PK) is
a database-local convenience. When syncing, uuid determines "is this the
same entity?" and dt_modified determines "whose version is newer?"

---

## Change Detection: What Existing Django Gives Us

Django and CoreModel already provide the building blocks for incremental
sync without adding external tools:

### 1. `dt_modified` — Last-Change Timestamp

`CoreModel.save()` sets `dt_modified = int(timezone.now().timestamp() * 1000)`
on every save. This is an epoch-millisecond integer stored as a
`BigIntegerField` with a database index.

**Sync use:** Query `Model.objects.filter(dt_modified__gt=last_sync_ts)` to
get only records changed since the last sync.

### 2. `version` — Optimistic Concurrency Counter

Incremented on every update (not on insert). If Remote has version 5 and
Local has version 3 for the same uuid, Remote is newer.

**Sync use:** When both sides changed the same record, compare versions.
Higher version wins in a last-writer-wins strategy. If versions diverge
from a common ancestor, flag as a true conflict.

### 3. `dt_created` — Insert Timestamp

Set once on first save. Never changes. Useful for distinguishing "new
record since last sync" from "updated record since last sync."

**Sync use:** `dt_created > last_sync_ts` means the record was created
after the last sync — guaranteed insert, not update.

### 4. Django Signals — `post_save` / `post_delete`

Django fires `post_save` after every `Model.save()` call. A signal handler
can write a lightweight journal entry recording which model, which uuid,
and what operation (create/update/delete) occurred.

**Sync use:** A sync journal table captures every mutation. The sync
command reads the journal instead of scanning all records.

### 5. Django Management Commands

The existing `sync_model` command already handles dual-database
connections, serialization, FK trigger management, and sequence resets.
Incremental sync extends this infrastructure rather than replacing it.

---

## Sync Direction & Conflict Rules

### Single Source of Truth

In the current workflow, **Remote is the authoritative database**. Local
databases are developer sandboxes. This establishes a clear priority:

```
Remote (shared)       ←── authoritative
  │
  ├── Local-A (dev)   ←── sandbox, may diverge
  ├── Local-B (dev)   ←── sandbox, may diverge
  └── Local-C (dev)   ←── sandbox, may diverge
```

### Conflict Resolution Hierarchy

1. **Remote → Local (pull):** Remote always wins. Local changes to the
   same record are overwritten. This is the safe default for refreshing a
   dev environment.

2. **Local → Remote (push):** Local wins only if the remote record has
   **not** been modified since the local copy was last synced. If Remote
   was also modified, flag as conflict.

3. **Bidirectional merge:** Compare `dt_modified` on both sides. If only
   one side changed, take that side. If both changed, apply per-field merge
   or flag for manual resolution.

---

## Incremental Sync Design

### Phase 1 — Timestamp-Based Delta Pull

**Goal:** Pull only records that changed on Remote since the last sync,
instead of copying entire tables.

```
sync_model contact --direction to-local --since last
                                         ↑
                              reads last_sync_ts from SyncState table
```

**How it works:**

1. Read `last_sync_ts` for this model from a local `SyncState` table.
2. Query source: `Model.objects.using(source).filter(dt_modified__gt=last_sync_ts)`
3. For each record, apply the [Record Matching Algorithm](#record-matching-algorithm).
4. Update `last_sync_ts` to `max(dt_modified)` of the synced batch.

**Django behaviors used:**
- `dt_modified` index for efficient range queries
- `CoreModel.save()` guarantees dt_modified is always current
- Existing `sync_model` dual-database connection infrastructure

### Phase 2 — Bidirectional Merge

**Goal:** Allow local changes to be pushed to Remote while also pulling
Remote changes, with conflict detection.

```
sync_model contact --direction merge
```

**How it works:**

1. Collect local changes since last sync: `dt_modified > last_sync_ts` on Local.
2. Collect remote changes since last sync: `dt_modified > last_sync_ts` on Remote.
3. Partition into three sets:
   - **Remote-only changes** → apply to Local (update or insert)
   - **Local-only changes** → apply to Remote (update or insert)
   - **Both changed (same uuid)** → conflict resolution
4. For conflicts, compare `version` numbers:
   - If versions are sequential (one is clearly newer), take the newer one.
   - If versions diverged (both incremented independently), flag for manual
     review and write to conflict log.

**Django behaviors used:**
- `version` field for conflict detection
- `uuid` for cross-database identity matching
- `post_save` signal (Phase 3) or dt_modified scan

### Phase 3 — Event-Driven Notification

**Goal:** Instead of polling or scanning, know immediately when a record
changes on either side.

**How it works:**

1. A `post_save` signal handler writes to a `SyncJournal` table on every
   save (see [Sync Journal Model](#sync-journal-model)).
2. The sync command reads the journal instead of scanning `dt_modified`
   across all records.
3. After successful sync, journal entries are marked as processed.

**Django behaviors used:**
- `django.db.models.signals.post_save`
- `django.db.models.signals.post_delete`
- Standard ORM for journal read/write

---

## Implementation Using Django Behaviors

### CoreModel.save() — Built-in Change Tracking

No changes needed. The existing `save()` already provides everything for
Phase 1:

```python
def save(self, *args, **kwargs):
    now_ms = int(timezone.now().timestamp() * 1000)
    if not self.pk:
        self.dt_created = now_ms       # ← insert detection
    else:
        self.version = (self.version or 0) + 1  # ← conflict detection
    self.dt_modified = now_ms          # ← change detection
    super().save(*args, **kwargs)
```

### Version Field — Optimistic Concurrency

Already implemented. The `assert_version()` and `optimistic_save()` helpers
on CoreModel can guard against stale overwrites during push-to-remote:

```python
# Before pushing a local record to remote:
remote_record.assert_version(local_record.version - 1)
# If remote was also modified, this raises VersionConflictError
```

### Django Signals — post_save for Sync Journaling

New for Phase 3. Register a lightweight signal handler:

```python
# common/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from common.models import CoreModel

@receiver(post_save)
def log_sync_journal(sender, instance, created, **kwargs):
    """Record every mutation for incremental sync."""
    if not isinstance(instance, CoreModel):
        return
    if getattr(instance, '_sync_in_progress', False):
        return  # don't journal changes made BY the sync process

    from apps.core.models import SyncJournal  # deferred import
    SyncJournal.objects.create(
        model_label=instance._meta.label,
        record_uuid=instance.uuid,
        record_pk=instance.pk,
        operation='create' if created else 'update',
        dt_modified=instance.dt_modified,
    )

@receiver(post_delete)
def log_sync_delete(sender, instance, **kwargs):
    if not isinstance(instance, CoreModel):
        return
    if getattr(instance, '_sync_in_progress', False):
        return

    from apps.core.models import SyncJournal
    SyncJournal.objects.create(
        model_label=instance._meta.label,
        record_uuid=instance.uuid,
        record_pk=instance.pk,
        operation='delete',
        dt_modified=int(timezone.now().timestamp() * 1000),
    )
```

### Management Commands — Extending sync_model

Add `--since` flag to the existing `sync_model` command:

| New Flag | Behavior |
|---|---|
| `--since last` | Use stored `last_sync_ts` for this model |
| `--since <epoch_ms>` | Use explicit timestamp |
| `--since 0` | Full sync (current behavior) |
| `--direction merge` | Bidirectional merge (Phase 2) |

---

## Record Matching Algorithm

For each incoming record from the source database:

```
┌─────────────────────────────────────────────────────────┐
│ 1. Look up by uuid in target                            │
│    ├── Found? ─────────────────────────────────────────┐│
│    │   Compare dt_modified                             ││
│    │   ├── Source newer → UPDATE target fields          ││
│    │   ├── Target newer → SKIP (target is current)     ││
│    │   └── Equal → SKIP (no change)                    ││
│    │                                                   ││
│    └── Not found? ─────────────────────────────────────┘│
│        ├── PK available in target? ────────────────────┐│
│        │   Yes → PK collision! Reassign PK, INSERT     ││
│        │   No  → INSERT with original PK               ││
│        └───────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

In code (extending the existing sync_model conflict handler):

```python
def _match_and_apply(source_obj, model, tgt_alias):
    """Match a source record to the target database and apply the change."""
    uuid_val = source_obj.uuid
    dt_src = source_obj.dt_modified

    # Step 1: Try to find by uuid (authoritative cross-DB identity)
    try:
        existing = model.objects.using(tgt_alias).get(uuid=uuid_val)
    except model.DoesNotExist:
        existing = None

    if existing:
        # Same entity exists on target — is source newer?
        if dt_src > existing.dt_modified:
            # Update all fields except id and uuid
            for field in model._meta.fields:
                if field.name in ('id', 'uuid'):
                    continue
                setattr(existing, field.name, getattr(source_obj, field.name))
            existing._sync_in_progress = True
            existing.save(using=tgt_alias)
            return 'updated'
        else:
            return 'skipped'  # target is already current or newer
    else:
        # New entity — check if PK is free
        pk_free = not model.objects.using(tgt_alias).filter(pk=source_obj.pk).exists()
        if pk_free:
            source_obj._sync_in_progress = True
            source_obj.save(using=tgt_alias)
            return 'inserted'
        else:
            # PK collision — different entity occupies this PK
            source_obj.pk = None  # let auto-increment assign a new PK
            source_obj._sync_in_progress = True
            source_obj.save(using=tgt_alias)
            return 'inserted_new_pk'
```

---

## Sync Journal Model

A lightweight table for Phase 3 that records every mutation:

```python
# apps/core/models/sync_journal.py

class SyncJournal(models.Model):
    """Append-only log of record mutations for incremental sync."""
    id = models.BigAutoField(primary_key=True)
    model_label = models.CharField(max_length=100, db_index=True)  # e.g. "core.Contact"
    record_uuid = models.UUIDField(null=True, db_index=True)
    record_pk = models.BigIntegerField(null=True)
    operation = models.CharField(max_length=10)  # create, update, delete
    dt_modified = models.BigIntegerField()  # epoch ms from the record
    dt_journaled = models.BigIntegerField()  # epoch ms when this entry was written
    is_processed = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'core_sync_journal'
        indexes = [
            models.Index(fields=['model_label', 'is_processed']),
            models.Index(fields=['record_uuid', 'model_label']),
        ]
```

A companion table tracks the "high-water mark" per model per direction:

```python
class SyncState(models.Model):
    """Tracks the last successful sync timestamp per model and direction."""
    model_label = models.CharField(max_length=100)
    direction = models.CharField(max_length=20)  # to-local, to-remote, merge
    last_sync_ts = models.BigIntegerField(default=0)  # epoch ms
    last_sync_dt = models.DateTimeField(auto_now=True)
    rows_synced = models.IntegerField(default=0)

    class Meta:
        db_table = 'core_sync_state'
        unique_together = [('model_label', 'direction')]
```

---

## Workflow Scenarios

### Developer refreshes local from remote

```bash
# Pull only what changed since last sync (Phase 1)
python manage.py sync_model contact --direction to-local --since last

# Or pull everything (existing full-copy behavior)
python manage.py sync_model contact --direction to-local
```

Records matched by uuid are updated if Remote is newer. Records not found
locally are inserted. Local-only records (not on Remote) are **preserved** —
this is non-destructive.

### Developer pushes local changes to remote

```bash
# Push local changes since last sync
python manage.py sync_model contact --direction to-remote --since last
```

For each local change:
1. Look up by uuid on Remote.
2. If Remote version == Local version - 1 → safe to update.
3. If Remote version diverged → flag as conflict.

### Two developers edit the same record

Developer A and Developer B both modify Contact uuid=`abc-123`:

```
Remote:  version=5, dt_modified=1708300000000  (baseline)

Dev A:   version=6, dt_modified=1708301000000  (edited name)
Dev B:   version=6, dt_modified=1708302000000  (edited phone)
```

When Dev A pushes first: Remote becomes version=6.
When Dev B pushes: Remote version is now 6, but Dev B's base was version=5.
Version mismatch → **conflict**. Options:
- Auto-merge: Dev A changed name, Dev B changed phone → merge both.
- Manual: write to conflict log for review if same fields touched.

### New record created on local, synced to remote

```bash
# New contact created locally (id=999, uuid=new-uuid-here)
python manage.py sync_model contact --direction to-remote --since last
```

1. uuid lookup on Remote → not found.
2. PK 999 check on Remote → likely free (or reassign if taken).
3. Insert with original PK (or new PK if collision).
4. Record now exists on both databases with the same uuid.

---

## Sync Metadata in JSONB Envelope

The existing `metadata` JSONB field on BaseModel includes a `history`
key. Extend it to track sync state per record:

```json
{
  "metadata": {
    "history": {
      "synced": {
        "dt": 1708300000000,
        "direction": "to-remote",
        "source_db": "LOCAL@localhost",
        "target_db": "REMOTE@76.13.185.210"
      }
    }
  }
}
```

This allows any record to answer: "When was I last synced, and in which
direction?" without querying the SyncJournal.

---

## Write-Through Proxy — Read Local, Save Remote

An alternative to periodic sync: make the local database serve all
**reads** while routing all **writes** through the remote database. The
remote saves the record, returns a response bundle, and the local database
stores the bundle so both databases stay current in real time — no
separate sync step needed for normal operations.

### How It Works

```
                          ┌─────────────────────┐
  Browser ──GET──────────►│ Local WC3 API       │──► Local DB  (fast read)
                          │                     │
  Browser ──POST/PUT─────►│ Local WC3 API       │
                          │  (write-through)    │
                          │      │              │
                          │      ▼              │
                          │  POST wcapi/save ───┼──► Remote WC3 API
                          │                     │         │
                          │                     │    Remote DB saves
                          │                     │    CoreModel.save()
                          │                     │    assigns id, uuid,
                          │                     │    dt_modified, version
                          │                     │         │
                          │  ◄── response bundle┼────────┘
                          │      │              │
                          │  Local DB stores    │
                          │  bundle (insert or  │
                          │  update by uuid)    │
                          │      │              │
                          │  ◄── 200 + payload ─┼──► Browser
                          └─────────────────────┘
```

**Key principle:** Remote is the single source of truth for writes. Local
never creates authoritative records — it stores copies returned by remote.
This means the remote's `CoreModel.save()` assigns all identity fields
(id, uuid, dt_modified, version), and local receives those exact values.

### Request Flow — New Record (create)

1. Browser sends `POST /wcapi/orders/` to Local WC3 API.
2. Local API does **not** save to local DB yet.
3. Local API forwards the payload to Remote: `POST <remote_host>/wcapi/orders/`.
4. Remote `CoreModel.save()` runs:
   - Assigns `id` (auto-increment on remote)
   - Generates `uuid` if not provided
   - Sets `dt_created` and `dt_modified`
   - Sets `version = 1`
5. Remote returns 201 with the full serialized record (the **response bundle**).
6. Local API receives the bundle and inserts the record into local DB
   using the remote-assigned id, uuid, and all field values.
7. Local API returns the response to the browser (same payload, same status).

**Result:** Both databases have the identical record with the same id,
uuid, version, and timestamps. No sync needed.

### Request Flow — Existing Record (update)

1. Browser sends `PUT /wcapi/orders/42/` to Local WC3 API.
2. Local API forwards to Remote: `PUT <remote_host>/wcapi/orders/42/`.
3. Remote loads the existing record, applies changes, and `CoreModel.save()` runs:
   - Increments `version`
   - Updates `dt_modified`
4. Remote returns 200 with the updated record bundle.
5. Local API matches the record by uuid in local DB and updates all fields.
6. Local API returns the response to the browser.

**Result:** Both databases have version N+1 with the same dt_modified.

### The Response Bundle

The response bundle is the standard WCAPI serialized record — the same
JSON shape the browser would receive from a direct API call. It includes:

| Field | Why It Matters |
|---|---|
| `id` | Remote-assigned PK — local stores the same value |
| `uuid` | Cross-database identity — local matches on this |
| `dt_created` | Remote-assigned on insert — local stores the same |
| `dt_modified` | Remote-assigned on every save — guarantees alignment |
| `version` | Remote-incremented — local stores the same |
| All data fields | Local stores exactly what remote has |

**Extended bundle (optional):** When a save triggers side effects on
remote (e.g., saving an OrderLine recalculates Order totals, creates
Pending inventory records), the bundle can include an `_related` key
with the cascaded records:

```json
{
  "id": 42,
  "uuid": "abc-123",
  "version": 6,
  "dt_modified": 1708300000000,
  "line_items": [...],
  "_related": {
    "order": { "id": 10, "uuid": "def-456", "sell_total": 1500.00, "version": 12 },
    "pending": [{ "id": 99, "uuid": "ghi-789", "purpose": "inventory_qty_change" }]
  }
}
```

Local stores the `_related` records in their respective tables, keeping
the entire object graph in sync from a single round-trip.

### Offline / Remote-Unreachable Behavior

When the remote database is unreachable, the write-through proxy has
two options:

| Strategy | Behavior | Trade-off |
|---|---|---|
| **Fail-fast** | Return 503 to browser; user retries later | Simple, no stale risk |
| **Queue-and-replay** | Save to local pending queue; replay when remote returns | Better UX, needs conflict check on replay |

The **queue-and-replay** strategy aligns with the existing
[pending-records pattern](../api/pending-records-offline-updates.md):

1. Local saves the mutation as a pending record (keyed by uuid + operation).
2. Browser receives a 202 Accepted with `pending: true` status.
3. A background worker (Celery) or the next request polls remote availability.
4. When remote returns, replay pending writes in order.
5. Store each response bundle in local DB and clear the pending entry.
6. If remote rejects a replayed write (version conflict), flag for user review.

### What This Eliminates

| Concern from batch sync | Write-through status |
|---|---|
| Sync conflicts (both sides edited) | **Eliminated** — writes always go to remote first |
| Stale local data after save | **Eliminated** — local stores the remote response immediately |
| PK collisions between databases | **Eliminated** — remote assigns all PKs, local copies them |
| dt_modified drift | **Eliminated** — local stores remote's exact timestamp |
| Version divergence | **Eliminated** — local stores remote's exact version |
| Need for periodic sync of active data | **Eliminated** — every write keeps both current |

### What sync_model Becomes

With write-through in place, `sync_model` shifts from a day-to-day tool
to a **recovery and seeding tool:**

| Use Case | Tool |
|---|---|
| Normal create/update | Write-through proxy (automatic) |
| Initial local DB setup | `sync_model --direction to-local` (one-time seed) |
| Recovery after local DB loss | `sync_model --direction to-local` (full restore) |
| Backfill after adding a new model | `sync_model <model> --direction to-local` |
| Data that changed while local was offline | `sync_model --since last` (catch up) |
| Bulk migration or data repair | `sync_model` or `pg_dump/pg_restore` |

### Implementation Sketch

> **Status: IMPLEMENTED** (2026-02-18)
>
> The write-through proxy is implemented using Django's multi-database ORM
> (direct Postgres-to-Postgres), **not** HTTP forwarding. This avoids
> needing a running remote Django server for auth forwarding.

#### Configuration

```bash
# .env
DB_MODE=write-through          # remote | local | write-through
WRITE_THROUGH_TIMEOUT=30       # seconds
```

`settings.py` reads `DB_MODE` and configures:
- `DATABASES['default']` → local Postgres (reads)
- `DATABASES['_wt_remote']` → remote Postgres (writes)
- `WRITE_THROUGH_ENABLED = True`
- `WRITE_THROUGH_REMOTE_ALIAS = '_wt_remote'`

#### Core Module — `common/write_through.py`

```
is_write_through()            → bool (checks settings.WRITE_THROUGH_ENABLED)
get_remote_alias()            → str  ('_wt_remote')
forward_and_store(request, model_cls, payload)
                              → (dict, status_code)
                              Saves to remote via ORM, syncs result to local
forward_transaction_and_store(request, model_key, record_data, lines_data, options)
                              → (dict, status_code)
                              Transaction header+lines save on remote, sync to local
_apply_fields(obj, payload)   → applies WCAPI field envelope format
_serialize_record(obj)        → model_to_dict + non-editable fields
_store_bundle_locally(model_cls, remote_obj, bundle)
                              → uuid-match then update, bypasses CoreModel.save()
_reset_local_sequence(model_cls) → setval(pg_get_serial_sequence, MAX+1)
```

Key design decisions:
- Uses `models.Model.save()` (not `CoreModel.save()`) when storing bundles
  locally, so remote's exact `version`, `dt_modified`, `id` are preserved.
- Sets `_sync_in_progress = True` to suppress post_save signals.
- Temporarily swaps `DATABASES['default']` for transaction saves (the
  `save_transaction_with_lines` service doesn't accept `using=`).

#### Wired Save Views

| View | File | Approach |
|---|---|---|
| `SaveWcapiView` | `apps/core/views/save_view.py` | Intercepts before create/update block, calls `forward_and_store()` |
| `WCAPITransactionSaveView` | `apps/transactions/views/wcapi.py` | Intercepts before `save_transaction_with_lines()`, calls `forward_transaction_and_store()` |
| `WCAPISaveView` | `apps/transactions/views/wcapi.py` | Intercepts before `core_save_item()`, calls `forward_and_store()` |

All intercepts are gated by `if is_write_through():` — when `DB_MODE` is
not `write-through`, all views behave exactly as before.

---

## FK Dependency Order

When syncing multiple tables, parent tables must be synced before children
to maintain referential integrity. The recommended order:

```
1. core.Setting          (no FKs)
2. orgs.OrgBase          (no FKs)
3. core.Contact          (FK → OrgBase)
4. products.Item         (FK → OrgBase via vendor)
5. products.Warehouse    (no FKs)
6. orders.Order          (FK → Contact, OrgBase)
7. orders.OrderLine      (FK → Order, Item)
8. invoices.Invoice      (FK → Contact, OrgBase, Order)
9. invoices.InvoiceLine  (FK → Invoice, Item)
10. payments.Payment     (FK → Invoice, Contact)
```

A convenience wrapper script:

```bash
#!/bin/bash
# sync_all.sh — Sync all tables in FK dependency order
DIRECTION=${1:-to-local}
SINCE=${2:-last}

MODELS=(setting org contact item warehouse order orderline invoice invoiceline payment)

for model in "${MODELS[@]}"; do
  echo "▸ Syncing $model ($DIRECTION, since=$SINCE)..."
  python manage.py sync_model "$model" --direction "$DIRECTION" --since "$SINCE" --no-confirm
done
```

---

## Safety & Guardrails

| Safeguard | Description |
|---|---|
| **Dry-run first** | `--dry-run` shows what would change without touching data |
| **Audit log** | Every sync appended to `logs/sync_model.log` |
| **Conflict log** | PK/UUID mismatches and version conflicts written to audit |
| **Non-destructive** | No TRUNCATE or DELETE — only insert/update |
| **Signal suppression** | `_sync_in_progress = True` prevents sync from triggering re-journaling |
| **FK trigger disable** | Triggers disabled during sync, re-enabled in `finally` block |
| **Backup recommendation** | Run `pg_dump` before first bidirectional merge on production |
| **Version check** | `assert_version()` prevents stale overwrites during push |

---

## Open Questions

1. **Delete propagation:** Should a soft-delete (`is_active=False`) on one
   database propagate to the other? Or only hard deletes?
   → Recommendation: Propagate `is_active` changes as normal field updates.
   Hard deletes propagate only via SyncJournal delete entries.

2. **Bulk operations:** When `sync_model` disables triggers, `post_save`
   signals don't fire. Should the sync command write journal entries
   directly instead of relying on signals?
   → Recommendation: Yes — the sync command should mark all synced records
   as processed in the journal and not rely on signal-based journaling
   during sync operations.

3. **UUID generation policy:** UUIDs are not auto-generated on save (by
   design). When should they be populated?
   → Recommendation: Generate uuid on insert via `CoreModel.save()` when
   `self.uuid is None`, or via a post-migration data fix as done previously.

4. **Multi-tenant scope:** Is sync always between exactly two databases
   (one remote, one local), or could there be multiple remotes?
   → Current assumption: One remote, N locals. The SyncState table's
   `direction` field could be extended to include a database identifier
   if multi-remote becomes necessary.

5. **Frequency:** How often should incremental sync run?
   → Options: On-demand (developer runs command), scheduled (cron every N
   minutes), or continuous (Phase 3 event-driven with Celery worker).

6. **Write-through scope:** Should all WCAPI viewsets use write-through,
   or only selected models (e.g., transactions yes, settings no)?
   → Recommendation: Start with transaction models (Order, OrderLine,
   Invoice, InvoiceLine, Payment) where data freshness matters most.
   Extend to all models once the pattern is proven.

7. **Response bundle depth:** Should the bundle include `_related`
   cascaded records, or keep it to the single saved record?
   → Recommendation: Start with single-record bundles. Add `_related`
   when a use case requires it (e.g., OrderLine save updates Order totals).

8. **Authentication forwarding:** How does the local API authenticate
   with the remote API when forwarding writes?
   → Options: Service-to-service token, forwarded user JWT, or API key.

---

## Related Documentation

- [sync-model.md](sync-model.md) — Current full-table sync_model command
- [dev-db-strategy.md](dev-db-strategy.md) — SQLite vs Postgres dual-lane approach
- [data-cleanup.md](data-cleanup.md) — UUID population and orphan fix history
- [../../React2025/readmes/data-set-identification.md](../../../React2025/readmes/data-set-identification.md) — DB_MODE, DATA_SET_ID, SystemInfoView
- [../../React2025/readmes/topics/offline-optimistic-updates.md](../../../React2025/readmes/topics/offline-optimistic-updates.md) — Frontend offline/optimistic strategy
- [../api/pending-records-offline-updates.md](../api/pending-records-offline-updates.md) — Backend pending record handling
- [../../React2025/readmes/django-model-fields.md](../../../React2025/readmes/django-model-fields.md) — Full field reference for all models
