# Database Maintenance Guide

<!-- TOC START -->

## Table of Contents

- [Database Maintenance Guide](#database-maintenance-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [N+1 Query Prevention](#n1-query-prevention)
    - [The Problem: Lazy FK Loading in BaseModel](#the-problem-lazy-fk-loading-in-basemodel)
    - [The Fix: Use attname for Change Tracking](#the-fix-use-attname-for-change-tracking)
    - [ViewSet select\_related Policy](#viewset-select_related-policy)
    - [How to Detect N+1 Issues](#how-to-detect-n1-issues)
  - [Remote Database Latency](#remote-database-latency)
  - [Serializer Payload Size](#serializer-payload-size)
  - [Index Maintenance](#index-maintenance)
  - [Audit Tools](#audit-tools)
  - [Checklist for New Models with ForeignKeys](#checklist-for-new-models-with-foreignkeys)

<!-- TOC END -->

## Overview

This project uses a **remote PostgreSQL database** (hosted externally). Every unnecessary query adds real network round-trip latency (~10–50ms per query depending on conditions). Performance issues that would be invisible with a local database become very noticeable at scale.

This document captures lessons learned and policies for keeping database interactions fast.

---

## N+1 Query Prevention

### The Problem: Lazy FK Loading in BaseModel

`BaseModel` (in `common/models.py`) implements change tracking via `_capture_original_state()`, which snapshots every field value when a model instance is created. The original implementation used `f.name` to access field values:

```python
# BAD — triggers lazy load for every ForeignKey field
for f in self._meta.fields:
    self._original_state[f.name] = getattr(self, f.name)
    # e.g. getattr(self, 'contact') → fires SELECT on core_contact table
```

For ForeignKey fields, `f.name` (e.g. `contact`) resolves the **related object**, triggering a separate `SELECT` query per FK per row. With a remote database, this means:

- 16 customers × 2 FK fields × ~30ms per query = **~1 second just for change tracking**
- Worse: this happens inside `__init__`, so it fires on every queryset evaluation

### The Fix: Use attname for Change Tracking

The fix uses `f.attname` which accesses the raw database column value (e.g. `contact_id` integer) without triggering a lazy load:

```python
# GOOD — reads raw column value, no extra queries
for f in self._meta.fields:
    self._original_state[f.attname] = getattr(self, f.attname)
    # e.g. getattr(self, 'contact_id') → reads int from instance dict
```

**Files affected by this fix:**
- `common/models.py` — `_capture_original_state()` and `_compute_changed_fields()`
- `apps/core/models/action.py` — inline changed-fields computation in `save()`

### ViewSet select_related Policy

Even with the `attname` fix, any code that accesses FK objects (e.g. in serializers or templates) will trigger lazy loads. **Always use `select_related`** for FK fields in ViewSet querysets:

```python
# GOOD
class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.select_related(
        'contact', 'terms_fk'
    ).filter(is_active=True, is_deleted=False)

# BAD — will N+1 if serializer or any code touches the FK objects
class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.filter(is_active=True, is_deleted=False)
```

### How to Detect N+1 Issues

1. **Django Debug Toolbar** — shows query count and duplicates per request
2. **django-silk** — profiling middleware for API endpoints
3. **Manual logging** — add to settings temporarily:
   ```python
   LOGGING = {
       'loggers': {
           'django.db.backends': {
               'level': 'DEBUG',
               'handlers': ['console'],
           },
       },
   }
   ```
4. **Shell test** — quick check for a specific queryset:
   ```python
   from django.test.utils import override_settings
   from django.db import connection, reset_queries

   reset_queries()
   list(Customer.objects.filter(is_active=True, is_deleted=False))
   print(f"Queries: {len(connection.queries)}")
   # Should be 1 for a simple list. If > 1, you have N+1.
   ```

---

## Remote Database Latency

The production/dev database is remote (not localhost). Key implications:

| Operation | Local DB | Remote DB |
|-----------|----------|-----------|
| Single query | ~0.5ms | ~10–50ms |
| N+1 (16 rows × 2 FKs) | ~16ms (unnoticeable) | ~960ms–1600ms |
| N+1 (100 rows × 3 FKs) | ~150ms | ~9–15 seconds |

**Rules of thumb:**
- Keep query count per request **under 10** for list endpoints
- Use `select_related()` for ForeignKey fields (single JOIN, same query)
- Use `prefetch_related()` for reverse FK / M2M relationships (1 extra query total)
- Use `.only()` or `.defer()` to exclude large JSON fields from list views if they aren't needed

---

## Serializer Payload Size

`OrgBase` has 12 JSONB aspect fields (`contacts`, `addresses`, `financial`, etc.). For list views, consider whether all of these need to be in the response.

If payload size becomes an issue, create a lightweight list serializer:

```python
class CustomerListSerializer(serializers.ModelSerializer):
    company = serializers.CharField(source="display_name")

    class Meta:
        model = Customer
        fields = ["id", "company", "status", "phone", "email", "address_full"]
```

And use `get_serializer_class()` in the ViewSet to switch based on action:

```python
def get_serializer_class(self):
    if self.action == 'list':
        return CustomerListSerializer
    return CustomerSerializer
```

---

## Index Maintenance

Current indexes on `OrgBase`:

| Index | Type | Fields |
|-------|------|--------|
| `org_contacts_gin` | GIN | `contacts` (JSONB) |
| `org_rel_gin` | GIN | `relations` (JSONB) |
| `org_financial_gin` | GIN | `financial` (JSONB) |
| `org_domains_gin` | GIN | `domains` (JSONB) |
| B-tree | Standard | `org_type`, `display_name`, `status` |

When adding new query patterns, verify they use existing indexes:

```sql
EXPLAIN ANALYZE SELECT * FROM orgs_orgbase WHERE org_type = 'customer' AND is_active = true;
```

Consider a composite index if a filter combination is used frequently:

```python
class Meta:
    indexes = [
        models.Index(fields=['org_type', 'is_active', 'is_deleted'], name='org_type_active_idx'),
    ]
```

---

## Audit Tools

A payload audit script is available at `tools/audit_customer_payload.py`. It measures:

- Total customer count
- Serialization time
- Total and per-record payload size
- Per-field size breakdown (identifies bloated JSON fields)
- Aggregate field sizes across all records

Run it:

```bash
cd webClerk3 && python tools/audit_customer_payload.py
```

---

## Checklist for New Models with ForeignKeys

When adding a new model or FK field:

- [ ] Verify `_capture_original_state` uses `f.attname` (already fixed globally)
- [ ] Add `select_related()` to any ViewSet queryset that touches the model
- [ ] If the model has reverse FKs accessed in serializers, add `prefetch_related()`
- [ ] For list endpoints, consider a lightweight serializer excluding large JSON fields
- [ ] Test with `reset_queries()` / `connection.queries` to verify query count
- [ ] If the model will have > 100 rows, verify the endpoint responds in < 1 second
