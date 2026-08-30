# Setting Policy — What Gets a Setting Record and Why

## The Rule

Every model gets exactly **one** Setting record with `purpose='wc:model'`.
All model definition — field behaviors, access roles, layouts, select lists,
defaults, field groups — lives in `config` on that single record.

Non-model features (gantt, databrowser) get their own Setting with `purpose='wc:feature'`.

| Purpose | ida pattern | What it holds | Who writes it |
|---------|-------------|---------------|---------------|
| `wc:model` | `wc-model-{model_key}` | Everything for the model (see config structure below) | `seed_model_definitions` |
| `wc:feature` | varies | Feature-level prefs (gantt colors, databrowser density) | Seed commands, user |
| `wc:company_profile` | `company-profile` | Company name, address, logos, print defaults, receivables | `seed_company_settings` |

## Config Structure (wc:model)

```json
{
  "schema":       { "pydantic_schema": "...", "config_schema": "...", ... },
  "access":       { "roles": { "admin": {...}, "sales": {...}, ... }, "query_scope": {...}, "publish": {...} },
  "behaviors":    { "email": { "type": "email", "action": "mailto" }, "status": { "type": "select", "options": [...] }, ... },
  "field_groups":  [ { "key": "identity", "label": "Identity", "fields": [...] }, ... ],
  "select_lists": { "category": { "choices": [...], "allow_custom": true }, ... },
  "formatting":   { "currency": "USD", "locale": "en-US", "date_format": "short", "number_precision": 2 },
  "default_collapsed": ["system", "dates", "json"],
  "enrichment":   {},
  "layout":       { "active": {...}, "list": { "default": {...} }, "detail": { "default": {...} }, "form": {...}, "panel": [...] },
  "searches":     [],
  "defaults":     {}
}
```

### Key config sections

| Section | What it controls | React consumer |
|---------|-----------------|----------------|
| `behaviors` | Widget type per field (email→mailto, phone→tel, select→dropdown, currency→$, lookup→FK search, etc.) | `useDataBrowser` → `renderField()` → widget registry |
| `access.roles` | Which fields each role (admin, sales, customer, vendor, rep) can view/edit | `setting_resolver` → wcapi query scoping |
| `layout.detail.default` | Header columns, line card, tabs — drives `UiDetail` rendering | `useDetailLayout` |
| `layout.list.default` | Column order, widths, visibility for list views | `useDataBrowser` |
| `field_groups` | How fields are grouped in detail view (Identity, Communication, Financial, etc.) | `useDataBrowser` |
| `select_lists` | Dropdown options per field, merged into behaviors at load time | `useDataBrowser` |
| `formatting` | Currency, locale, date format, number precision | Field widgets |

## Naming Convention

```
Setting.parent_model = canonical model key from MODEL_REGISTRY (via meta.key)
Setting.purpose      = "wc:model"
Setting.ida          = "wc-model-{model_key}"
Setting.scope        = "system" (default), "org", "role", or "user" (for overrides)
```

## How React Loads Model Definitions

1. **Bootstrap** (`useAppBootstrap`) — loads company profile, select lists, payment terms, warehouses, campaigns at startup via `get_app_bootstrap`
2. **Per-model** (`useDataBrowser`) — when a model is selected, fetches `Setting(purpose='wc:model', parent_model=X)` and extracts `config.behaviors`, `config.field_groups`, `config.default_collapsed`, `prefs.defaults`
3. **Detail layout** (`useDetailLayout`) — fetches `Setting(purpose='wc:detail_layout', parent_model=X)` which resolves through `setting_resolver` to `wc:model → config.layout`
4. **Field rendering** (`renderField`) — reads `behavior.type` and dispatches to the correct widget component (18 widget types registered)

## Widget Type Registry

| behavior.type | Widget | What it does |
|---------------|--------|-------------|
| `text` | TextField | Plain text input |
| `number` | NumberField | Numeric input |
| `currency` | CurrencyField | Formatted money display/edit |
| `email` | EmailField | Input + mailto link on label |
| `phone` | PhoneField | Input + tel link, auto-format |
| `url` | UrlField | Input + clickable link |
| `address` | AddressField | Multi-line, map link |
| `zip` | ZipField | Zip code with format validation |
| `select` | SelectField | Dropdown from `behavior.options` |
| `lookup` | LookupField | FK search against `behavior.model` |
| `boolean` | BooleanField | Checkbox/toggle |
| `date` | DateField | Date picker |
| `timestamp` | TimestampField | Unix timestamp → formatted date |
| `json` | JsonField | Raw JSON editor |
| `json-tree` | JsonTreeField | Expandable tree editor |
| `textarea` | TextareaField | Multi-line text |
| `readonly` | ReadonlyField | Display only |
| `geo` | GeoField | Lat/lng pair with map link |

## Seed Command

```bash
python manage.py seed_model_definitions           # create missing, skip existing
python manage.py seed_model_definitions --force    # overwrite all
python manage.py seed_model_definitions --model order  # one model only
python manage.py seed_model_definitions --dry-run  # report only
```

## Rules

1. **One Setting per model.** All definition lives in `wc:model`. No separate `field_access`, `detail_layout`, `workbench_fields`, or `schema_map` records.

2. **Settings are syncable.** Every Setting is a BaseModel record with uuid, version, refs. Syncs between installations via Connection/Bundle.

3. **Alice reads Settings.** Alice's onboarding and coaching reads the `wc:model` Setting to know what the installation has configured.

4. **Seed is idempotent.** Running `seed_model_definitions` again does not overwrite existing records unless `--force` is passed.

5. **No orphan Settings.** Every Setting must have a `parent_model` that exists in MODEL_REGISTRY or is one of: `wc`, `gantt`, `databrowser`.

6. **setting_resolver handles legacy purposes.** Code that requests `wc:detail_layout`, `wc:schema_map`, `wc:enrichment_panels`, `wc:workbench_fields`, `wc:keywords`, `wc:print_layout`, or `wc:db_defaults` will fall through to the matching section in `wc:model`. This allows gradual migration of callers.
