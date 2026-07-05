# Layout Save Flow — How DataBrowser Persists Field Order

## The Object We Save

When a user changes column order, widths, or visibility, we save a **Pending** record.
The Pending record carries the change. Celery applies it to the Setting record.

### Pending Record

```json
{
  "model_name": "setting",
  "purpose": "layout_change",
  "name": "layout:contact",
  "data": {
    "target_model": "contact",
    "view": {
      "list": [
        {"field": "ida", "width": 100, "align": "left", "visible": true},
        {"field": "company", "width": 180, "align": "left", "visible": true},
        {"field": "phone", "width": 120, "align": "left", "format": "phone", "visible": true},
        {"field": "is_active", "width": 50, "align": "center", "visible": true}
      ],
      "detail": [
        {"field": "name_first", "width": 120, "align": "left", "visible": true},
        {"field": "name_last", "width": 120, "align": "left", "visible": true}
      ],
      "views": [
        {
          "name": "Bill",
          "list": [{"field": "ida"}, {"field": "company"}],
          "detail": [],
          "listWidths": {}
        }
      ]
    }
  }
}
```

### What Each Part Means

| Field | Purpose |
|-------|---------|
| `model_name` | "setting" — tells Celery what record type to update |
| `purpose` | "layout_change" — Celery filters for these |
| `name` | "layout:contact" — human-readable label |
| `data.target_model` | Which model's Setting to update (e.g. "contact") |
| `data.view` | The full layout state — replaces `Setting.data` |
| `data.view.list` | FieldSpec array — columns shown in the list |
| `data.view.detail` | FieldSpec array — fields shown in detail pane |
| `data.view.views` | Named views the user has saved |

### FieldSpec Object

Each field in `list` or `detail` is a FieldSpec:

```json
{
  "field": "phone",        // field name on the model
  "width": 120,            // column width in pixels
  "align": "left",         // left | center | right
  "format": "phone",       // currency | percent | date | phone | number | json | null
  "visible": true,         // show in list/detail
  "wrap": false,           // true = word-wrap, false = truncate with ellipsis
  "frozen": false,         // sticky column (not yet implemented)
  "summary": null           // sum | avg | count (footer totals)
}
```

## The Flow

```
User changes layout
    ↓
React updates UI immediately (optimistic)
    ↓
React POSTs to /wcapi/save/ → creates NEW Pending record
    ↓
Celery (every 10s) reads Pending where purpose='layout_change' and dt_processed=0
    ↓
Celery applies data.view to Setting where parent_model=data.target_model
    ↓
Celery marks Pending as processed (dt_processed = now)
    ↓
Next time user loads this model, Setting has the new layout
```

## The Setting Record (Target)

Setting #224 for contact model:

```json
{
  "parent_model": "contact",
  "purpose": "workbench_fields",
  "data": {
    "list": [ ...FieldSpec array... ],
    "detail": [ ...FieldSpec array... ],
    "views": [
      {"name": "alice_guess", "list": [...], "detail": [...], "listWidths": {}},
      {"name": "alphabetical", "list": [...], "detail": [...], "listWidths": {}},
      {"name": "Bill", "list": [...], "detail": [...], "listWidths": {}}
    ]
  }
}
```

## Why Pending (Not Direct Save)

1. **No lock conflicts** — creating a new Pending always succeeds
2. **Audit trail** — every layout change is a separate record with timestamp
3. **Serialized** — FIFO processing prevents race conditions
4. **Same pattern** as PendingInventoryAdjustment and PendingPaymentApplication

## Files

| File | Role |
|------|------|
| `React2025/src/hooks/useDataBrowser.ts` | `persistSetting()` — creates the Pending record |
| `React2025/src/api/wcapi.ts` | `saveRecord('pending', {...})` — POSTs to /wcapi/save/ |
| `webClerk3/apps/core/models/pending.py` | Pending model with `.data` JSONField |
| `webClerk3/apps/ai_assistant/tasks.py` | `apply_pending_layouts_task()` — Celery reads & applies |
| `webClerk3/webclerk3_api/settings.py` | Beat schedule — runs every 10s |
| `webClerk3/apps/core/views/save_view.py` | `/wcapi/save/` endpoint |
