# Leaf Declarations — JSONField Type Classification

**Established:** 2026-08-20
**Scars:** #60 — behavior.type is an assertion, not a suggestion; #61 — declare, don't guess
**Patent:** Provisional draft at `readmes/patents/leaf-declarations-provisional.md`

## The Problem

Django JSONFields serve two fundamentally different purposes:

1. **i18n display fields** — `{"en": "Draft term sheet"}` — language-keyed text that should render as editable text/textarea
2. **Structural envelopes** — `config`, `metadata`, `refs`, `prefs` — nested JSON trees with complex structure

`field_behaviors.py` marked ALL JSONFields as `type: 'json'`. Since `behavior.type` is an assertion that short-circuits auto-detection in `renderField`, i18n display fields rendered as JSON tree widgets — buried at the bottom of the detail pane instead of showing as editable text at the top.

### Why Other Frameworks Don't Hit This

Most frameworks avoid this by never putting display text in JSONFields:
- **django-modeltranslation, django-parler, wagtail** — create separate columns per language (`title_en`, `title_es`). Schema migrations when adding languages, but the ORM sees CharField.
- **Directus, Strapi, Payload CMS** — store field metadata in a configuration database. Works, but a bad config write can break rendering for an entire model.
- **Most applications** — use `CharField` for names, `TextField` for descriptions, `ForeignKey` for assigned_to. One language, one value, one type.

Our approach is architecturally better — one JSONField, any number of languages, no schema migration — but it's the road less traveled. The leaf declaration pattern is required because we chose this road.

## The Solution

**Declare, don't guess.** Every JSONField is classified explicitly in code:

| Type | What it is | How it renders | Examples |
|------|-----------|---------------|----------|
| `i18n` | Language-keyed display value | Extract `[0]`, render as text/textarea | `action`, `description`, `assigned_to` |
| `envelope` | Structural JSON tree | Render as json-tree widget | `config`, `metadata`, `refs`, `prefs` |
| `json` | Generic JSON (fallback) | Render as JSON textarea | anything not classified |

## Architecture

```
field_behaviors.py
    _I18N_FIELDS set    → classifies display fields
    _ENVELOPE_FIELDS set → classifies structural fields
    get_field_behaviors() returns type: 'i18n' | 'json-tree' | 'json'
        ↓
wc:model Setting → config.behaviors
    stores computed types (seed_model_definitions writes these)
        ↓
useDataBrowser.ts → fetches wc:model Setting
    reads config.behaviors
    computes leafDeclarations client-side from behavior types:
        type='i18n'      → {type: 'i18n', extract: '[0]'}
        type='json-tree' → {type: 'envelope'}
        type='json'      → {type: 'json'}
        ↓
GroupedDetailFields → BehaviorField → renderField
    reads behavior.type AND opts.leaf for classification
    i18n → extract [0], render as text, wrap onChange
    envelope → render as json-tree
    no guessing
```

### Why Client-Side Leaf Computation

The leaf declarations are computed client-side from behavior types — not fetched from a separate server endpoint. This is intentional:

1. **No extra API call.** The behaviors are already fetched with the wc:model Setting.
2. **Single source of truth.** The `_I18N_FIELDS` set in `field_behaviors.py` drives both the stored behavior type AND the client leaf map. One place to change.
3. **`get_leaf_declarations()` on the server** exists for future use (API consumers, Alice, non-React clients) but is not the primary delivery path for the DataBrowser.

## Key Files

| File | Role |
|------|------|
| `apps/core/services/field_behaviors.py` | `_I18N_FIELDS`, `_ENVELOPE_FIELDS`, `get_leaf_declarations()`, `get_field_behaviors()` returns `type: 'i18n'` |
| `apps/core/services/setting_resolver.py` | `_compute_behaviors()` includes `leaves` for API consumers |
| `apps/core/views/save_view.py` | Save validation — wraps plain strings in `{"en": value}` for i18n fields |
| `apps/core/management/commands/seed_model_definitions.py` | Stores computed behaviors including i18n types |
| `React2025/src/hooks/useDataBrowser.ts` | Computes `leafDeclarations` from behaviors, stores in state |
| `React2025/src/components/fields/index.tsx` | `renderField` reads `behavior.type` and `opts.leaf` for classification |
| `React2025/src/components/fields/SelectField.tsx` | Handles object values — serializes for comparison, parses on change, Cmd+click multi-select |
| `React2025/src/components/common/BehaviorField.tsx` | Passes `leaf` prop through to renderField |
| `React2025/src/pages/admin/GroupedDetailFields.tsx` | Passes `leafDeclarations` to BehaviorField; Setting field order is primary, groups are fallback |
| `React2025/src/components/common/DataGrid.tsx` | `[0]` resolver: on objects, "first value" not numeric index; column headers show `parent.leaf` not just `.leaf` |

## i18n Extraction Protocol

When `behavior.type === 'i18n'` or `leaf.type === 'i18n'`:

1. **Extract** first value: `Object.values(value)[0]` → the display string
2. **Label** includes key: `action.en` not just `action`
3. **Edit** wraps back: `onChange({...value, [key]: newText})` — language key preserved
4. **Select** widgets get plain string values (the extracted text), not JSON objects. `allow_custom: true` shows current value even when not in option list.
5. **Multi-select** via Cmd+click: comma-separated within the language key: `{"en": "Bill, Claude Code"}`
6. **List columns** use `[0]` notation (e.g., `assigned_to[0]`). The DataGrid resolver interprets `[0]` on objects as "first value", not numeric array index.
7. **Save validation**: if a plain string arrives for an i18n field, the backend wraps it as `{"en": value}` before saving. The i18n structure is never corrupted.

**Future:** Extract by user's language preference first, `[0]` as fallback.

## Adding a New i18n Field

1. Add the field name to `_I18N_FIELDS` in `field_behaviors.py`
2. That's it. The pipeline handles the rest.

The seed command picks up the new type. React computes the leaf. renderField extracts. Save validates. One line of code, five layers of behavior.

## Adding a New Envelope Field

1. Add the field name to `_ENVELOPE_FIELDS` in `field_behaviors.py`
2. Create the Pydantic schema class in `common/schemas/<model>.py`

## Traps We Hit (Read Before Debugging)

These are the specific failure modes we encountered building this system. If you see similar symptoms, check these first.

### Trap 1: behavior.type is an assertion that short-circuits everything

`renderField` checks `behavior.type` before any auto-detection:
```typescript
const typeName = opts?.typeHint || behavior.type || ...auto-detection...
```

If `behavior.type = 'json'`, the field renders as a JSON tree regardless of what the value looks like. The auto-detection never runs. **The fix was not to improve auto-detection — it was to set the right type in the first place.**

This applies to any future field type issue: check `behavior.type` first. If it's wrong, no amount of auto-detection logic will save you.

### Trap 2: Stored overrides outlive the code that created them

`seed_model_definitions` stores computed behaviors in `wc:model` Setting `config.behaviors`. These are database records. When you change `get_field_behaviors()` to return `type: 'i18n'`, the stored `type: 'json'` from the previous seed run is still in the database. **The stored assertion beats the computed truth.**

After any change to field_behaviors classification:
1. Re-run `seed_model_definitions` to update stored behaviors, OR
2. Run the sweep script to update specific types across all Settings

### Trap 3: [0] means different things for arrays and objects

`action[0]` in the DataGrid column spec meant "array index 0". But `{"en": "text"}` is an object, not an array. `obj[0]` is `undefined`. **The fix: when `[0]` is applied to an object, use `Object.values(obj)[0]` instead of `obj[0]`.**

This is in `DataGrid.tsx` line ~641. The reducer now checks if the target is a non-array object and falls back to `Object.values()`.

### Trap 4: The detail pane has two field ordering systems

`config.db.detail` in the Setting specifies field order. `field_groups` from `get_field_groups()` categorizes fields into collapsible sections. **They fought each other.** Fields specified in the Setting got re-sorted into groups, ignoring the Setting order.

The fix: Setting-specified fields render first, ungrouped, in Setting order. Only remaining fields (present in record but not in Setting) get grouped. **The Setting is source of truth for order. Groups are a guideline for the remainder.**

### Trap 5: i18n fields appear twice in the detail pane

A JSON object `{"en": "text"}` can render as:
- The raw object (via the field name `description`) → JSON tree at the bottom
- The flattened dot-path (via `description.en`) → text field somewhere else

If both are in the field list, you get duplicates. The fix: i18n extraction in `renderField` changes the rendered name to `description.en` but operates on the original field name `description`. The field appears once, in its Setting-specified position, with the extracted `.en` value.

## Detail Pane Field Order Rule

The `GroupedDetailFields` component follows this rule:

1. **Primary fields** — fields listed in `config.db.detail` from the wc:model Setting — render first, in Setting order, ungrouped. These are the fields the administrator decided are important.
2. **Grouped fields** — remaining fields present in the record but not in the Setting — render in collapsible sections (Identity, Status, Dates, System, Data) as classified by `get_field_groups()`.
3. **Ungrouped remainder** — fields that don't fit any group — render in an "Other" section.

**The Setting is the source of truth. Groups are guidelines.**

## Principle

> Declare, don't guess. JSONFields serve two fundamentally different purposes
> (display text vs structural trees) but Django gives them the same type. Most
> frameworks solve this by avoiding the problem — separate columns per language,
> or plain text fields. We chose the architecturally correct path (one JSONField,
> any languages) which requires explicit declaration so the UI layer never has to
> inspect values at runtime.
>
> The cost of guessing is invisible until it surfaces as a rendering bug that only
> appears for certain value shapes. The cost of declaring is one line per field.
> Pay the small cost upfront.
