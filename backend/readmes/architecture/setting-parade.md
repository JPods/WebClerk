# Setting Parade — PJPV Configuration Review

**Status:** Spec (not yet built) | **Pattern:** FormParade | **Route:** `/setting-parade`

> **Note:** Runtime explanations belong on each Setting record's description field,
> not in docs. This readme is the build spec for the interactive parade feature.

## What It Is

A guided walk through every Setting record that shapes the UI. Same pattern as
FormParade (left list, right preview, bottom feedback) but for configuration
instead of print forms.

Users learn PJPV by **seeing what each Setting does** — not by reading docs.
The parade shows each Setting, renders a live preview of its effect, and
collects feedback (understood / needs work / don't understand).

## Why It Matters

Settings control everything a user sees:
- Which fields appear on a form (field_behaviors, wc:workbench_fields)
- How fields render (widget type, precision, readonly)
- What options appear in dropdowns (selectlists — three-tier inheritance)
- Column layouts in lists (wc:list_column_config)
- Default values for new records (prefs.defaults)

Users who don't understand Settings can't configure their own system.
The Setting parade is the flight simulator for PJPV.

## Layout

```
+---------------------------------------------------------------+
| Setting Parade                          12 settings | 3 reviewed|
+---------------------------------------------------------------+
|                         |                                      |
| FIELD BEHAVIORS         |  [Live preview of selected setting]  |
|   item (wc:model)    *  |                                      |
|   order (wc:model)      |  Setting: item (wc:model)            |
|   invoice (wc:model)    |  Purpose: Field behaviors for items  |
|                         |                                      |
| SELECT LISTS            |  +-- Behaviors ----+-- Selectlists --+
|   paint_selectlists     |  | status: select  | status: 3 opts  |
|   electronics_parts     |  | price: currency | uom: 5 opts     |
|   address_type          |  | weight: number  | finish: 5 opts  |
|                         |  +----------------+------------------+
| LAYOUTS                 |                                      |
|   item list columns     |  Used by: 42 item records            |
|   order list columns    |  Profile refs: 8 records point here  |
|                         |                                      |
| DEFAULTS                |  Three-tier inheritance:              |
|   sales_defaults        |  [model] ← [this setting] ← [record]|
|                         |                                      |
+---------------------------------------------------------------+
| Understood       Needs Work       Don't Understand    Notes: [ ]|
+---------------------------------------------------------------+
```

## Groups

Settings organized by what they control:

| Group | Purpose filter | What it shows |
|-------|---------------|---------------|
| Field Behaviors | `wc:model` | Widget types, labels, readonly flags |
| Select Lists | has `config.selectlists` | Dropdown options per field |
| List Layouts | `wc:list_column_config`, `wc:workbench_fields` | Column order, widths, visibility |
| Defaults | `*_defaults` | Default field values for new records |
| Field Access | `wc:field_access` | Role-based field visibility |

## Right Panel — Live Preview

For each Setting, the right panel shows:

### Field Behaviors (wc:model)
- Table of field → widget type → label → options
- Highlight select fields with their selectlist_key
- Show which PJPV schema this maps to (if any)

### Select Lists
- Options table with value/label columns
- Three-tier indicator: "This is a [model/profile/record] level list"
- Count of records using this as their selectlist_profile
- "Try it" — render an actual select dropdown with these options

### Layouts
- Visual column preview (field names in order, with widths)
- Which model this layout applies to

### Defaults
- Key/value table of default field values
- Which model they apply to

## Feedback

Same pattern as FormParade — per-Setting feedback stored on the Setting record:

```json
// Setting.prefs.parade_feedback
{
  "choice": "understood",     // understood | needs_work | dont_understand
  "notes": "Need to add more finish options",
  "reviewed_by": "bill",
  "reviewed_at": "2026-08-25T14:30:00Z"
}
```

Choices:
- **Understood** — I know what this does and it's correct
- **Needs Work** — I understand it but it needs changes
- **Don't Understand** — I don't know what this controls

The "don't understand" count is the training gap metric.

## Backend Endpoint

```
GET /wcapi/_setting_parade_manifest/
```

Returns grouped Settings with their effect summaries:

```json
{
  "groups": [
    {
      "name": "Field Behaviors",
      "description": "How fields render — widget type, labels, readonly",
      "settings": [
        {
          "id": 1,
          "ida": "item_model",
          "name": "Item Field Behaviors",
          "parent_model": "item",
          "purpose": "wc:model",
          "summary": {
            "behavior_count": 12,
            "selectlist_count": 3,
            "select_fields": ["status", "unit_of_measure", "finish"],
            "record_refs": 42
          },
          "feedback": null
        }
      ]
    }
  ],
  "total_settings": 12,
  "reviewed_count": 3
}
```

```
GET /wcapi/_setting_parade_preview/?setting_id=1
```

Returns the Setting's config rendered as structured preview data
(not HTML — React renders it).

```
POST /wcapi/_setting_parade_feedback/
{
  "setting_id": 1,
  "feedback": "understood",
  "notes": "Looks good"
}
```

Saves feedback to `Setting.prefs.parade_feedback`.

## Connection to Three-Tier Selectlists

The parade is where users learn the inheritance chain:

1. Walk through a model-level Setting → see its selectlists
2. Walk through a category profile Setting → see what it overrides
3. Open a record that uses the profile → see the merged result
4. The "Try it" dropdown shows the final resolved options

This replaces the need for a dedicated selectlist flight sim.

## Files to Create

| File | What |
|------|------|
| `frontend/src/pages/tools/SettingParade.tsx` | Main page (clone FormParade pattern) |
| `frontend/src/pages/tools/SettingParade.css` | Styles |
| `backend/apps/core/views/setting_parade.py` | Manifest + preview + feedback endpoints |
| Route in `protectedRoutesConfig.tsx` | `/setting-parade` |
| Route in `Routes.ts` | `PageRoutes.settingParade` |

## Build Order

1. Backend manifest endpoint — group Settings by purpose, count behaviors/selectlists
2. Frontend page — left list grouped, right panel with structured preview
3. Backend preview endpoint — return Setting config as structured data
4. Feedback flow — save to Setting.prefs.parade_feedback
5. "Try it" interactive select dropdowns in preview panel
6. Three-tier inheritance visualization — show which tier a selectlist lives at
