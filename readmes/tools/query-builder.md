# Query Builder — Draft

**Status:** Implemented — video pending

## Two Search Tiers

### Tier 1: Search Box (98%+ of use)
The search box at the top of db.list does keyword search across all text fields.
Most users never need more than this. It maps to Django's `keyword` filter
which searches `attention`, `ida`, and model-specific search fields.

### Tier 2: Query Builder (power users)
Click **Filter** in the db.list toolbar. Compound, typed, multi-field queries
for when the search box isn't enough.

## Query Builder Features

| Feature | What it does |
|---------|-------------|
| Multi-row rules | WHERE field op value AND/OR field op value |
| Type selector | Text/Number/Date/Boolean/JSON — user overrides auto-detection |
| JSON/array search | Search inside `assigned_to`, `refs`, `metadata`, etc. |
| Saved searches | Store as Setting records, load from dropdown, delete |
| Copy/Paste | Copy rules as JSON, edit externally, paste back |
| Alice intent | Tell Alice what you're looking for — she learns search patterns |

## Type Override

The query builder guesses the field type but gets it wrong sometimes.
Users can change the Type dropdown per row:

- `assigned_to` detected as JSON — switch to **Text** to search by name,
  **Number** to search by contact ID
- `duration` detected wrong — switch to **Number** for numeric comparisons
- Any field — switch to **Date** if it stores epoch timestamps

## Copy/Paste Format

```json
[
  { "field": "assigned_to", "op": "json_contains_text", "value": "Bill", "type": "json" },
  { "field": "status", "op": "eq", "value": "In Progress", "combine": "AND" }
]
```

Copy the draft, clean it up, paste it back. Share queries between users.

## What's Next

- Better type detection from Django model field introspection
- Autocomplete values from existing data
- OR group nesting (parentheses)
- Date range picker for `between` operator
- Alice suggesting queries based on what users search for most
