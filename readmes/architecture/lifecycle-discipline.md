# Lifecycle Discipline — When to Use What

Three mechanisms exist for running logic when a record changes. Each has a specific purpose. Using the wrong one creates bugs that surface only under specific save paths.

## The Three Mechanisms

### 1. `save()` override — Self-consistency

Use for: ensuring the record itself is internally consistent before it hits the database.

```python
def save(self, *args, **kwargs):
    self.slug = slugify(self.name)        # derived from own fields
    self.row_version += 1                  # optimistic concurrency
    super().save(*args, **kwargs)
```

**Rule:** `save()` only touches `self`. Never queries other models. Never creates other records. Never sends notifications. If it does, those side effects will fire on every save — including migrations, data fixes, and bulk imports.

**Examples that belong here:**
- Normalizing field values (slugify, uppercase, strip whitespace)
- Computing derived fields from own data (profit = revenue - cost)
- Validating constraints that `clean()` should catch
- Incrementing version counters

**Examples that do NOT belong here:**
- Creating Pending records → use post_save_hook or signal
- Updating related records → use signal
- Sending emails → use signal + Celery task
- GL journal entries → use signal or explicit service call

### 2. `pre_save_hook` / `post_save_hook` — API-driven side effects

Use for: side effects that should only happen when a record is saved through the wcapi save endpoint (user action, not system action).

```python
def post_save_hook(self, data, is_update=False, context=None):
    # Only fires on wcapi save — not on migration, signal, or management command
    if not is_update:
        create_default_contacts_for_customer(self)
    return "Customer created with default contacts"
```

**Rule:** Hooks fire ONLY through the wcapi save path (`save_view.py`). They do NOT fire on `Model.objects.create()`, `bulk_create()`, management commands, or signal-driven saves. This is their strength — they represent user-initiated side effects.

**Examples that belong here:**
- Creating related records on first save (default contacts for a new customer)
- Queueing a Pending record for async processing
- Logging an Alice observation about a user action
- Denormalizing display fields into refs.links

**Examples that do NOT belong here:**
- Anything that must happen regardless of save path → use signal
- Self-consistency → use save() override

### 3. Django Signals (`post_save`, `pre_save`) — System-wide side effects

Use for: side effects that must happen on EVERY save, regardless of how the save was triggered.

```python
@receiver(post_save, sender=Invoice)
def invoice_post_save(sender, instance, created, **kwargs):
    if instance.status == 'released':
        journalize_invoice(instance)     # GL entries must always happen
```

**Rule:** Signals fire on every save — API, management command, migration, test. Use them only for operations that must be universally consistent.

**Examples that belong here:**
- Audit logging (every save, every path)
- GL journal entries on status transitions
- Inventory quantity updates on transaction line changes
- Aggregate counter updates (dashboard totals)
- Schema compliance validation on Setting saves

**Examples that do NOT belong here:**
- User notifications (not every save is user-initiated)
- Default record creation (fires during migrations/imports)
- Expensive operations without guards (will slow down bulk imports)

## Decision Matrix

| Question | → Use |
|----------|-------|
| Does it only touch `self` fields? | `save()` override |
| Should it ONLY happen on user-initiated saves? | `post_save_hook` |
| Must it happen on EVERY save regardless of path? | Django signal |
| Is it expensive and can be deferred? | Signal → queue Pending → async process |
| Does it involve another model's data? | Signal or hook, never `save()` |

## Guard Pattern for Signals

Signals that create records must guard against re-entry and bulk operations:

```python
@receiver(post_save, sender=InvoiceLine)
def update_invoice_totals(sender, instance, **kwargs):
    if getattr(instance, '_skip_totals', False):
        return  # bulk operation sets this flag
    recalculate_totals(instance.invoice_id)
```

The `_pending_created` flag pattern (used in `convert_order_to_invoice.py`) is the standard for suppressing signals during conversion operations.

## Current State

| Model | save() | hook | signal | Notes |
|-------|--------|------|--------|-------|
| Contact | slug, role sync | — | audit | correct |
| Setting | config guard | — | schema compliance | correct |
| Action | dt_start from project | — | audit, refs | correct |
| Invoice/Order/etc | — | denormalize links | audit, totals, GL | correct |
| Address | normalize | — | — | missing audit signal? |
| Phone | — | normalize | — | normalize should be in save() |
| GlAccount | ensure defaults | — | — | correct |

**Phone.pre_save_hook** normalizing phone numbers is in the wrong place — it should be in `save()` since normalization is self-consistency, not an API-side effect. Fix when touching phone code.
