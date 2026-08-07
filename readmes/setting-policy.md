# Setting Policy — What Gets a Setting Record and Why

## The Rule

Every model gets exactly two Setting records. Non-model features get one.

| Purpose | What it holds | Who writes it |
|---------|--------------|---------------|
| `field_access` | Field behaviors, select lists, RBAC scope, `.prefs.defaults` | Admin via Alice onboarding, seed commands |
| `workbench_fields` | List layout, detail layout, named views | User via databrowser Save, seed commands |

One additional system-wide Setting:

| `parent_model` | `purpose` | What it holds |
|----------------|-----------|---------------|
| `wc` | `system` | Company name, default org, currency, timezone, locale, tax ID |

Non-model features (gantt, databrowser, dashboard) get:

| `parent_model` | `purpose` | What it holds |
|----------------|-----------|---------------|
| `gantt` | `feature` | Default view, colors, zoom, dependency display |
| `databrowser` | `feature` | Detail width, font size, theme, density |

## Naming Convention

```
Setting.parent_model = singular lowercase model name (payment, order, contact)
Setting.purpose      = one of: field_access, workbench_fields, system, feature
Setting.name         = "{purpose}:{parent_model}" (e.g., "field_access:payment")
```

## What Lives Where Inside a Setting

### `Setting.config` — structure and behavior (admin-managed)

```json
{
  "field_behaviors": {
    "type": { "type": "readonly" },
    "category": { "type": "select", "options": [...], "allow_custom": true },
    "contact": { "type": "lookup", "model": "contact" }
  },
  "select_lists": {
    "category": { "choices": [...], "gl_map": {...}, "default_gl": "EXP-MISC-000", "allow_custom": true },
    "method": { "choices": ["cash", "check", "wire", "ach"], "allow_custom": true }
  },
  "query_scope": { ... }
}
```

### `Setting.prefs` — installation defaults (admin decides, Alice recommends)

```json
{
  "defaults": {
    "type": "expense",
    "method": "visa_3425",
    "category": "Office Supplies"
  }
}
```

### `Setting.config` on workbench_fields — display layouts (user-managed)

```json
{
  "list": [ { "field": "dt_payment", "visible": true, "width": 100, ... } ],
  "detail": [ { "field": "type", "visible": true, "width": 150, ... } ],
  "views": [ { "name": "checkbook", "list": [...], "detail": [...] } ]
}
```

## The Complete Setting Registry

Every model in MODEL_REGISTRY gets a `field_access` and `workbench_fields` Setting.
Created by `seed_field_access` and `seed_alice_layouts` management commands.

### Core models
| parent_model | field_access | workbench_fields |
|-------------|-------------|-----------------|
| contact | field behaviors, salutation select | list/detail layouts |
| customer | prospect/price_level selects | list/detail layouts |
| vendor | selects | list/detail layouts |
| action | status/priority selects | list/detail layouts |
| document | status select | list/detail layouts |
| setting | (self-referencing) | list/detail layouts |

### Transaction models
| parent_model | field_access | workbench_fields |
|-------------|-------------|-----------------|
| order | status/priority selects, defaults | list/detail layouts |
| order_line | field behaviors | list/detail layouts |
| invoice | status select, defaults | list/detail layouts |
| invoice_line | field behaviors | list/detail layouts |
| purchase | status select, defaults | list/detail layouts |
| purchase_line | field behaviors | list/detail layouts |
| payment | type/status/category/method selects, GL map, defaults | checkbook + alice_guess + alpha views |
| proposal | status select | list/detail layouts |

### Product models
| parent_model | field_access | workbench_fields |
|-------------|-------------|-----------------|
| item | type select | list/detail layouts |
| serial | field behaviors | list/detail layouts |

### Account models
| parent_model | field_access | workbench_fields |
|-------------|-------------|-----------------|
| gl_account | type/category selects | list/detail layouts |
| gl_journal | field behaviors | list/detail layouts |
| ledger | field behaviors | list/detail layouts |

### System-wide
| parent_model | purpose | contents |
|-------------|---------|----------|
| wc | system | company identity, currency, timezone, locale |
| gantt | feature | view prefs, colors |
| databrowser | feature | detail_width, font_size, theme |

## Rules

1. **One source of truth per concern.** Field behavior for payment lives in exactly one place: `Setting(payment, field_access)`. Not scattered across code, not duplicated.

2. **Settings are syncable.** Every Setting is a BaseModel record with uuid, version, refs. It syncs between installations via the standard sync mechanism. An admin configures once, syncs to all locations.

3. **Alice reads Settings.** Alice's onboarding and coaching reads the Setting records to know what the installation has configured. She doesn't hardcode — she reads.

4. **Seed commands are idempotent.** Running `seed_field_access` or `seed_alice_layouts` again does not overwrite user customizations unless `--force` is passed.

5. **No orphan Settings.** Every Setting must have a `parent_model` that exists in MODEL_REGISTRY or is one of: `wc`, `gantt`, `databrowser`.
