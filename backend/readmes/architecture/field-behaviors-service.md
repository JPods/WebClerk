# Field Behaviors Service — Incremental Correction Path

## What This Is

Field behaviors define how every field renders in the frontend: email gets a mailto link, phone gets a tel link, currency gets dollar formatting, status gets a select dropdown, FK fields get lookup search. The system has three layers:

1. **Service function** (`apps/core/services/field_behaviors.py`) — auto-detects widget type from Django model metadata. Covers ~95% of cases. No database hit.
2. **Setting overrides** (`wc:model` Setting → `config.behaviors`) — stored corrections for the ~5% where auto-detection is wrong. One Setting per model.
3. **Audit command** (`manage.py audit_field_behaviors`) — compares computed vs stored, flags problems.

## The Correction Loop

```
Auto-detect from model metadata
    ↓ flags problems
Audit command (manage.py audit_field_behaviors)
    ↓ admin reviews
Cmd+Shift+click on field label in DataBrowser
    ↓ opens BehaviorOverrideDialog
Save override to wc:model Setting
    ↓ next page load
Field renders with corrected behavior
```

Alice runs the audit in her code_standards scan. Users correct via the dialog. The service function stays authoritative — overrides are exceptions, not replacements.

## Gesture Hierarchy on Field Labels

| Gesture | Action | Who |
|---------|--------|-----|
| Click | Default action (mailto, tel link, etc.) | All users |
| Shift+click | Field help (opens help window) | All users |
| Cmd+Shift+click | Behavior override dialog | Admin/superuser only |

## Widget Type Registry

| Type | Widget | What it does |
|------|--------|-------------|
| `text` | TextField | Plain text input |
| `number` | NumberField | Numeric input |
| `currency` | CurrencyField | Formatted money display/edit |
| `email` | EmailField | Input + mailto link on label |
| `phone` | PhoneField | Input + tel link, auto-format |
| `url` | UrlField | Input + clickable link |
| `address` | AddressField | Multi-line, map link |
| `zip` | ZipField | Zip code with format validation |
| `select` | SelectField | Dropdown from behavior.options |
| `lookup` | LookupField | FK search against behavior.model |
| `boolean` | BooleanField | Checkbox/toggle |
| `date` | DateField | Date picker |
| `timestamp` | TimestampField | Unix timestamp → formatted date |
| `json` | JsonField | Raw JSON editor |
| `json-tree` | JsonTreeField | Expandable tree editor |
| `textarea` | TextareaField | Multi-line text |
| `readonly` | ReadonlyField | Display only |
| `geo` | GeoField | Lat/lng pair with map link |
| `hidden` | HiddenField | Renders nothing |
| `editor` | EditorField | Rich text editor |

## Auto-Detection Rules (in priority order)

1. System fields (id, uuid, dt_created, etc.) → `readonly`
2. EmailField or name='email' → `email` with mailto
3. Name is 'phone'/'number'/'phone_cell' or starts with 'phone' → `phone` with tel
4. Name is 'address_full' → `address` with map
5. Name is 'latitude'/'longitude' → `geo` with map
6. BooleanField → `boolean`
7. DateTimeField/DateField → `date`
8. Name starts with 'dt_' + IntegerField → `timestamp`
9. DecimalField named 'amount'/'total'/'balance'/etc. → `currency`
10. DecimalField/FloatField (not excluded) → `number`
11. JSONField named metadata/prefs/config/refs → `json-tree`, others → `json`
12. FK field → `lookup` (with model_map translation)
13. Name-based selects: status, price_level, kanban_column, type, etc. → `select` with inline options
14. SearchVectorField → `hidden`
15. UUIDField → `readonly`
16. SlugField → `text`
17. IntegerField variants → `number`
18. TextField → `textarea`
19. CharField → `text`

## Audit Command

```bash
python manage.py audit_field_behaviors                # summary
python manage.py audit_field_behaviors --detail       # show every flag
python manage.py audit_field_behaviors --model order  # one model
python manage.py audit_field_behaviors --json         # JSON for Alice
```

### Flag Types

| Flag | Severity | Meaning |
|------|----------|---------|
| UNTYPED | High | Field fell through all detection — needs a rule or override |
| BAD_LOOKUP | High | FK points at model not in MODEL_REGISTRY |
| ORPHAN_OVR | Medium | Override exists for field that no longer exists on model |
| EMPTY_OPTS | Medium | Select field with no options defined |
| OVERRIDE | Info | Stored type differs from computed — verify intentional |
| PHONE_NAME | Info | Field named 'number' detected as phone — verify correct |

## Key Files

| File | What |
|------|------|
| `apps/core/services/field_behaviors.py` | Service: auto-detect + override merge |
| `apps/core/management/commands/audit_field_behaviors.py` | Audit command |
| `apps/core/management/commands/seed_model_definitions.py` | Seeds wc:model Settings (calls service) |
| `apps/core/services/setting_resolver.py` | Resolves behaviors live via `wc:field_behaviors` purpose |
| `React2025/src/components/fields/BaseField.tsx` | Cmd+Shift+click handler |
| `React2025/src/components/fields/BehaviorOverrideDialog.tsx` | Override dialog |
| `React2025/src/components/fields/index.tsx` | Widget registry + renderField() |

## How React Loads Behaviors

1. `useDataBrowser` fetches `Setting(purpose='wc:model', parent_model=X)`
2. Extracts `config.behaviors` — these are computed + overrides merged by the seed command
3. `renderField()` reads `behavior.type` and dispatches to the correct widget component
4. Widget-specific props (options, model, pair) come from the behavior object

## Adding a New Widget Type

1. Create `React2025/src/components/fields/FooField.tsx`
2. Add to `WIDGET_REGISTRY` in `components/fields/index.tsx`
3. Add detection rule in `field_behaviors.py` → `get_field_behaviors()`
4. Run `manage.py audit_field_behaviors` to verify
5. Run `manage.py seed_model_definitions --force` to update stored behaviors

## Consolidated Setting Architecture

Each model has exactly one Setting record (`purpose='wc:model'`, `ida='wc-model-{key}'`).
All model definition lives in `config`:

```
config.schema       — Pydantic schema pointers
config.access       — RBAC roles, query_scope, publish channels
config.behaviors    — field widget types (auto-detected + overrides)
config.field_groups — semantic grouping (identity, financial, etc.)
config.layout       — named layouts (list, detail, form, panel)
config.formatting   — currency, locale, date format
config.defaults     — default values for new records
```

No separate `field_access`, `detail_layout`, `workbench_fields`, or `schema_map` records.
The `setting_resolver` handles legacy purpose names via fallback map.
