# Database Views in WebClerk3

**Created:** 2026-08-18
**Status:** Active

## What They Are

PostgreSQL VIEWs are named queries that look like tables but compute their results on read. They have no storage — they run the underlying SELECT each time. DataBrowser can query them alongside Django models.

## Why Views, Not Models

Django models map 1:1 to tables. When you need cross-model data (touches + actions merged into an agenda), you have two choices:

1. **Django unmanaged model** — wraps the VIEW in a Django class. Adds complexity: model file, registry entry, migrations that create fake model state. The ORM doesn't know it's read-only.

2. **Direct VIEW query** — PostgreSQL VIEW handles the aggregation. DataBrowser queries it via raw SQL with standard pagination, sorting, filtering. No Django model. No added complexity.

**We chose option 2.** The VIEW is the model. PostgreSQL is the engine. DataBrowser is the UI.

## How It Works

### Creating a VIEW

VIEWs are created via Django migrations using `RunSQL`:

```python
# apps/communications/migrations/0016_create_agenda_view.py
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "CREATE OR REPLACE VIEW agenda AS SELECT ... UNION ALL SELECT ...",
            "DROP VIEW IF EXISTS agenda;"
        ),
    ]
```

### VIEW Registration

VIEWs are registered in a Setting record so DataBrowser knows about them:

```json
{
  "ida": "wc-views",
  "purpose": "wc:system",
  "config": {
    "views": {
      "agenda": {
        "label": "Agenda",
        "description": "Pending touches + open actions sorted by due date",
        "columns": ["icon", "title", "status", "purpose", "dt_due", "impact", "detail_text"],
        "default_sort": "dt_due",
        "source_model_field": "source_model",
        "source_id_field": "source_id",
        "read_only": true
      }
    }
  }
}
```

### DataBrowser Integration

When DataBrowser receives `model_name=agenda`:
1. Check the model registry — not found
2. Check the views registry (wc-views Setting) — found
3. Query via raw SQL: `SELECT * FROM agenda` with pagination, sort, filter
4. Render in db.list with standard toolbar
5. Click a row → read `source_model` + `source_id` → open that record's detail pane

### Column Handling

VIEWs should define common columns for display. Non-common fields go in a `detail_text` column — a text concatenation of model-specific fields.

```sql
-- Common columns (sortable, filterable)
icon, title, status, purpose, dt_due, impact, contact_id

-- Non-common (displayed as text, not sortable per-field)
COALESCE(t.summary, '') AS detail_text  -- for touches
COALESCE(a.description->>'en', '') AS detail_text  -- for actions
```

### Detail Pane Behavior

Every VIEW row carries `source_model` and `source_id`. When the user clicks a row:
- `source_model = 'touch'` → open touch detail (db.detail or app mode)
- `source_model = 'action'` → open action detail
- The VIEW itself is read-only — edits happen on the source record

## Existing VIEWs

| VIEW | What it merges | Created |
|------|---------------|---------|
| `agenda` | touches (dt_next > 0) + actions (dt_deadline > 0, status=open/in_progress) | 2026-08-18 |

## Rules

1. **VIEWs are read-only.** Never write to a VIEW. Edits go to the source model via `source_model` + `source_id`.
2. **Every VIEW row has `source_model` and `source_id`.** These are required for click-through to the real record.
3. **Common columns use normalized names.** `dt_due` not `dt_next` or `dt_deadline`. `title` not `subject` or `action->>'en'`.
4. **Non-common fields go in `detail_text`.** One text column, displayed but not individually sortable.
5. **VIEWs are registered in the `wc-views` Setting.** DataBrowser reads this to know which VIEW names are valid.
6. **Create VIEWs via migrations.** `RunSQL` with forward and reverse SQL. Always `CREATE OR REPLACE`.

## User-Created VIEWs

Users can create their own VIEWs for cross-model reporting:
- AR aging: invoices with balance > 0 joined with customer contact info
- Sales pipeline: proposals + orders by stage with customer names
- Commission: orders × rep assignments × line totals

These would be registered in the `wc-views` Setting by an admin. Alice can suggest VIEWs based on common query patterns she observes.

## Files

| File | What |
|------|------|
| `apps/communications/migrations/0016_create_agenda_view.py` | Agenda VIEW SQL |
| `readmes/topics/architecture/database-views.md` | This document |
