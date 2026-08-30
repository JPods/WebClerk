# Select List Management — User Guide

**Built:** 2026-08-26 | **Audience:** All users | **Ref:** selectlist-inheritance.md

## What Select Lists Are

Select lists are the dropdown options on form fields — status, terms, priority,
carrier, unit of measure, etc. Instead of typing free text, users pick from a
curated list. This keeps data clean and consistent.

## Three Ways to Create or Edit Select Lists

### 1. Cmd+click any field label (fastest)

On any form field in the DataBrowser:
- **Mac:** Cmd+click the field label
- **Windows:** Ctrl+click the field label

This opens the behavior editor pre-set to "select" type. Type your options
as `value:label` pairs, one per line:

```
active:Active
hold:On Hold
discontinued:Discontinued
```

Click Save. The field is now a dropdown. Works on any field, any model.

### 2. Select List Browser (/selectlists)

Alice → Coaching Tips → **Open Select Lists**

Browse all select lists across all Settings. Click any list to:
- See its options
- Add, edit, or remove options
- See which Settings share the same list

### 3. Cmd+Shift+click for full behavior editor

This opens the complete field behavior dialog where you can change:
- Widget type (text, select, currency, lookup, etc.)
- Label
- Action (mailto, tel, map)
- Select list options
- Lookup model

Use this when you need to change more than just the options.

## Keyboard Shortcut Summary

| Shortcut | What it does |
|----------|-------------|
| **Cmd/Ctrl+click** label | Quick select list editor — add dropdown options to any field |
| **Shift+click** label | Field help — what this field is for |
| **Cmd+Shift+click** label | Full behavior editor — change widget type, label, action, options |

## Three-Tier Inheritance

Select lists can be customized at three levels. Most specific wins.

### Tier 1 — Model level (all records)

A Setting record for the model provides default select lists.
Example: all items share the same `status` dropdown.

Managed via the Select List Browser or the Setting Parade.

### Tier 2 — Category level (a group of records)

A record can point to a Setting that provides category-specific options.
Example: paint products get `finish` and `base_type` dropdowns that
plumbing products don't have.

Set on the record: `config.selectlist_profile` → a Setting with
category-specific lists.

```json
{
  "config": {
    "selectlist_profile": {
      "id": 4,
      "ida": "paint_selectlists",
      "purpose": "paint category options"
    }
  }
}
```

### Tier 3 — Record level (one specific record)

A single record can carry its own select list directly in its JSON.
Example: one specialty paint has a unique `drying_humidity` dropdown.

```json
{
  "config": {
    "selectlists": {
      "drying_humidity": [
        {"value": "low", "label": "< 40% RH"},
        {"value": "high", "label": "> 60% RH"}
      ]
    }
  }
}
```

### How they merge

For each field, the most specific level wins:
- Record level overrides category
- Category overrides model
- Fields not overridden inherit from the level above

A paint product gets `status` from the model level, `finish` from the
paint category profile, and `drying_humidity` from its own record —
all at the same time.

## Reference Tools

| Tool | Where | What it shows |
|------|-------|---------------|
| **Setting Parade** | Alice → Coaching → Open Setting Parade | Walk through all Settings, see their select lists, field behaviors, layouts |
| **Form Parade** | Alice → Coaching → Open Form Parade | Review all print forms with sample data |
| **Select List Browser** | Alice → Coaching → Open Select Lists | Browse and edit all select lists in one place |

## Where Options Are Stored

Options live in Setting records under `config.selectlists`:

```json
{
  "config": {
    "selectlists": {
      "status": [
        {"value": "active", "label": "Active"},
        {"value": "hold", "label": "On Hold"}
      ],
      "terms": [
        {"value": "N30", "label": "Net 30 days"},
        {"value": "COD", "label": "Cash on Delivery"}
      ]
    }
  }
}
```

When you use Cmd+click to add options to a field, they save to the
model's `wc:model` Setting automatically.

## PJPV Connection

Pydantic schemas can declare `selectlist_key` on select fields:

```python
status: str = Field('', json_schema_extra={
    'widget': 'select',
    'selectlist_key': 'shipping_status'
})
```

This tells the UI which select list to load by default. The three-tier
inheritance still applies — a Setting or record can override the
schema default.
