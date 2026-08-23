wc# Layout Maintenance

Admin tracking for React2025 model layout file progress. Uses a **singleton Setting** record to maintain a central inventory of which models have which layout files, their build status, and who is working on them.

---

## Setting Record

| Field     | Value            |
|-----------|------------------|
| `name`    | `layout_status`  |
| `purpose` | `admin`          |
| `id`      | 113              |

**Lookup:**

```python
# Python
setting = Setting.objects.get(name='layout_status', purpose='admin')
layouts = setting.data['layouts']
```

```typescript
// TypeScript (R25)
const setting = await getRecords('setting', { name: 'layout_status', purpose: 'admin' });
const layouts = setting.data.layouts;
```

---

## Data Schema

`data.layouts` is an array of objects — one per discovered (app, model) pair:

```jsonc
{
  "layouts": [
    {
      "app": "transactions",       // R25 app folder
      "model": "order",            // Model folder name
      "detail_exists": true,       // *Detail.tsx file found
      "list_exists": true,         // *List.tsx file found
      "dialog_exists": false,      // *Dialog.tsx file found
      "panel_exists": false,       // *Panel.tsx file found
      "detail_status": "",         // Workflow status for Detail layout
      "list_status": "",           // Workflow status for List layout
      "dialog_status": "",         // Workflow status for Dialog layout
      "panel_status": "",          // Workflow status for Panel layout
      "assigned_to": ""            // Person currently working on layouts
    }
    // ... 58 more entries
  ]
}
```

### Column Reference

| Column           | Type    | Description |
|------------------|---------|-------------|
| `app`            | string  | App folder under `src/apps/` (e.g. `transactions`, `products`, `orgs`) |
| `model`          | string  | Model folder under `src/apps/{app}/models/` |
| `detail_exists`  | bool    | Whether a `*Detail.tsx` file exists in the model's `pages/` folder |
| `list_exists`    | bool    | Whether a `*List.tsx` file exists |
| `dialog_exists`  | bool    | Whether a `*Dialog.tsx` file exists |
| `panel_exists`   | bool    | Whether a `*Panel.tsx` file exists |
| `detail_status`  | string  | Status of the Detail layout (see status values below) |
| `list_status`    | string  | Status of the List layout |
| `dialog_status`  | string  | Status of the Dialog layout |
| `panel_status`   | string  | Status of the Panel layout |
| `assigned_to`    | string  | Name/handle of who is working on these layouts |

### Suggested Status Values

| Status        | Meaning |
|---------------|---------|
| *(empty)*     | Not started / not tracked |
| `planned`     | Identified for work |
| `in_progress` | Actively being built |
| `review`      | Built, awaiting review |
| `done`        | Complete and standardized |
| `n/a`         | Not needed for this model |

---

## File Inventory (59 Models)

Scanned from `React2025/src/apps/**/models/*/pages/`:

| App | Model | Detail | List | Dialog | Panel |
|-----|-------|:------:|:----:|:------:|:-----:|
| **accounts** | audit | ✓ | ✓ | – | – |
| | currency | ✓ | ✓ | – | – |
| | exchange_rate | ✓ | ✓ | – | – |
| | exchange_transaction | ✓ | ✓ | – | – |
| | gl_account | ✓ | ✓ | – | – |
| | gl_journal | ✓ | ✓ | – | – |
| | ledger | – | ✓ | – | – |
| | tax_jurisdiction | – | ✓ | – | – |
| | term | – | ✓ | – | – |
| **communications** | address | ✓ | ✓ | – | – |
| | domain | ✓ | ✓ | – | – |
| | email | ✓ | ✓ | – | – |
| | phone | ✓ | ✓ | – | – |
| **core** | action | ✓ | ✓ | – | – |
| | api_log | ✓ | ✓ | – | – |
| | contact | ✓ | ✓ | – | – |
| | report | ✓ | ✓ | – | – |
| | setting | ✓ | ✓ | – | – |
| | template | ✓ | ✓ | – | – |
| **docs** | document | ✓ | ✓ | – | – |
| | linkage_entry | – | ✓ | – | – |
| | question_answer | – | ✓ | – | – |
| | tag | – | ✓ | – | – |
| **orgs** | base_org_model | – | ✓ | – | – |
| | customer | ✓ | ✓ | – | ✓ |
| | employee | ✓ | ✓ | – | – |
| | manufacturer | – | ✓ | – | – |
| | organization | – | ✓ | – | – |
| | rep | – | ✓ | – | – |
| | vendor | ✓ | ✓ | – | – |
| **products** | bill_of_material | ✓ | ✓ | – | – |
| | catalog | ✓ | ✓ | – | – |
| | flow | ✓ | ✓ | – | – |
| | item | ✓ | ✓ | – | – |
| | item_xref | ✓ | ✓ | – | – |
| | matrics | ✓ | ✓ | – | – |
| | org_item | ✓ | ✓ | – | – |
| | serial | ✓ | ✓ | – | – |
| | service | ✓ | ✓ | – | – |
| | specification | ✓ | ✓ | – | – |
| | usage | ✓ | ✓ | – | – |
| | variant | ✓ | ✓ | – | – |
| | warehouse | ✓ | ✓ | – | – |
| **support** | campaign | ✓ | ✓ | – | – |
| **sync** | bundle | ✓ | ✓ | – | – |
| **transactions** | inventory_adjustment | – | ✓ | – | – |
| | invoice | ✓ | ✓ | – | – |
| | invoice_line | ✓ | ✓ | – | – |
| | order | ✓ | ✓ | – | – |
| | order_line | ✓ | ✓ | – | – |
| | project | ✓ | ✓ | – | – |
| | proposal | ✓ | ✓ | – | – |
| | proposal_line | ✓ | ✓ | – | – |
| | purchase | ✓ | ✓ | – | – |
| | purchase_line | ✓ | ✓ | – | – |
| | receipt | ✓ | ✓ | – | – |
| | requisition | ✓ | ✓ | – | – |
| | workorder | ✓ | ✓ | – | – |
| | workorder_line | ✓ | ✓ | – | – |

**Totals:** 47 Detail, 59 List, 0 Dialog, 1 Panel

---

## Management Command

```bash
# Preview what would be stored (no DB writes)
python manage.py create_layout_status --dry-run

# Create the singleton record (skip if it already exists)
python manage.py create_layout_status

# Rescan files and replace data (preserves same record ID)
python manage.py create_layout_status --reset
```

**Source:** `apps/core/management/commands/create_layout_status.py`

### What it does

1. Walks `React2025/src/apps/**/models/*/pages/` for `.tsx` files
2. Matches filenames ending in `Detail`, `List`, `Dialog`, or `Panel`
3. Skips `qqq_`-prefixed files (deprecated/experimental)
4. Groups by (app, model) and builds the `data.layouts` array
5. Creates or updates the singleton Setting record (`name=layout_status`, `purpose=admin`)

### When to re-run

- After adding new model layout files
- After renaming or reorganizing model folders
- Periodically to keep the inventory current

> **Note:** `--reset` replaces the `data` payload entirely. Any manually-edited status values (e.g. `detail_status`, `assigned_to`) will be cleared. To preserve manual edits, update the record via the API or Django shell instead of using `--reset`.

---

## Updating Status via API

Use wcapi to update individual layout statuses without re-running the command:

```typescript
// Fetch the setting
const res = await getRecords('setting', { name: 'layout_status', purpose: 'admin' });
const setting = res.data[0];

// Update a specific model's status
const layouts = setting.data.layouts;
const orderLayout = layouts.find(l => l.model === 'order' && l.app === 'transactions');
orderLayout.detail_status = 'done';
orderLayout.list_status = 'review';
orderLayout.assigned_to = 'wj';

// Save back
await saveRecord('setting', { id: setting.id, data: { layouts } });
```

```python
# Django shell
setting = Setting.objects.get(name='layout_status', purpose='admin')
for layout in setting.data['layouts']:
    if layout['model'] == 'order' and layout['app'] == 'transactions':
        layout['detail_status'] = 'done'
        layout['list_status'] = 'review'
        layout['assigned_to'] = 'wj'
        break
setting.save()
```

---

## Layout Standards Reference

Each layout type follows the patterns documented in the project:

| Layout Type | Standard Pattern | Reference |
|-------------|-----------------|-----------|
| **Detail** | `SimpleDetailHeader` → `SimpleDetailToolbar` → Basic Info → `DetailTabs` | [detail-page-standardization-plan.md](detail-page-standardization-plan.md) |
| **List** | Data table with search, pagination, column configuration | [list-search-feature.md](list-search-feature.md) |
| **Dialog** | Modal overlay for quick create/edit or search selection | — |
| **Panel** | Reusable sub-section embedded in detail pages (tabs) | [ui-form-layout-research.md](ui-form-layout-research.md) |

---

## Related

- [Settings Reference](../../webClerk3/readmes/topics/settings/settings_reference.md) — Full Setting model documentation
- [Detail Page Standardization Plan](detail-page-standardization-plan.md) — Layout rules for Detail pages
- [01-architecture.md](01-architecture.md) — Per-model folder structure
