# Field Behaviors — BehaviorField Reference

BehaviorField renders each field in the DataBrowser detail view based on its
`type` in the model's `field_access` Setting record (`config.field_behaviors`).

Click the label to trigger the action. Shift+click any label opens field-level help.
Shift+hover shows inline tooltip from alice_coaching data.

## Behavior Types

| Type | Label Icon | Click Action | Example Config |
|------|-----------|--------------|----------------|
| `email` | ✉ | Opens `mailto:` link | `{"type": "email"}` |
| `phone` | ☎ | Opens `tel:` link (dials) | `{"type": "phone"}` |
| `address` | 📍 | Opens Google Maps with address | `{"type": "address"}` |
| `geo` | 🗺 | Opens Google Maps with lat/lng | `{"type": "geo", "pair": "longitude"}` |
| `url` | 🔗 | Opens URL in new browser tab | `{"type": "url"}` |
| `path` | 📂 or 🌐 | File path → Finder, URL → browser | `{"type": "path"}` |
| `select` | (green) | Dropdown from options | See Select Sources below |
| `lookup` | (purple) | FK input with model hint | `{"type": "lookup", "model": "customer"}` |
| `currency` | $ prefix | Number with dollar sign | `{"type": "currency"}` |
| `boolean` | checkbox | Toggle on/off | `{"type": "boolean"}` |
| `json` | (span 2) | Editable JSON textarea | `{"type": "json"}` |
| `textarea` | (span 2) | Multi-line text | `{"type": "textarea"}` |
| `timestamp` | (gray) | Read-only formatted date | `{"type": "timestamp"}` |
| `readonly` | (gray) | Read-only display | `{"type": "readonly"}` |
| `number` | | Numeric input | `{"type": "number"}` |
| `text` | | Default text input | `{"type": "text"}` |

## Label Colors

- **Blue** — actionable (email, phone, address, geo, url, path)
- **Green** — select dropdown
- **Purple** — lookup (FK reference)
- **Gray** — readonly / timestamp

## Path Behavior

The `path` type auto-detects the content:

- Starts with `http://` or `https://` → 🌐 opens in browser
- Starts with `/` or `file://` → 📂 opens in Finder
- JSON object with `.file` key → extracts the path first (matches Document.path format)

```json
{"type": "path"}
```

## Select Sources

Select dropdowns can pull options from three sources:

### 1. Static options (defined in Setting)

```json
{
  "type": "select",
  "options": [
    {"value": "draft", "label": "Draft"},
    {"value": "review", "label": "In Review"},
    {"value": "released", "label": "Released"}
  ]
}
```

### 2. From record field (dot-path into the record's own data)

Pull options from an array field on the record itself:

```json
{
  "type": "select",
  "from_field": "refs.keywords"
}
```

This reads `record.refs.keywords` (e.g., `["civil", "mechanical", "quality"]`)
and builds a dropdown where each string is both the value and label.

For arrays of objects, specify which keys to use:

```json
{
  "type": "select",
  "from_field": "config.questions",
  "label_key": "question",
  "value_key": "id"
}
```

This reads `record.config.questions` (array of objects) and builds a dropdown
using each object's `question` field as the display label and `id` as the value.

### 3. From object keys

If the dot-path resolves to an object (not an array), the keys become values
and the values become labels:

```json
{
  "type": "select",
  "from_field": "metadata.status_choices"
}
```

Record data: `{"metadata": {"status_choices": {"draft": "Draft", "review": "In Review"}}}`
Result: dropdown with "Draft" (value=draft), "In Review" (value=review)

## Where Field Behaviors Are Defined

Each model has a `field_access` Setting record:

```
Setting:
  purpose: "field_access"
  name: "field_access:contact"
  config:
    field_behaviors:
      email: {type: "email"}
      phone: {type: "phone"}
      address1: {type: "address"}
      website: {type: "url"}
      status: {type: "select", options: [...]}
      latitude: {type: "geo", pair: "longitude"}
      ...
      _examples: { ... all available types with examples ... }
```

Every field_access Setting now includes an `_examples` key showing all available
behavior types. Copy and adapt for any field.

## Adding a New Behavior to a Model

1. Open the DataBrowser → Settings → find `field_access:<model_name>`
2. Edit `config.field_behaviors`
3. Add or change the field's type (see examples in `_examples`)
4. Save — DataBrowser picks up the change immediately (no restart)

## File: `src/components/common/BehaviorField.tsx`
