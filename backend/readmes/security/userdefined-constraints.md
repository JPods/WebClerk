# userdefined Field Security Constraints

**Established:** 2026-09-02
**Applies to:** Every BaseModel record (metadata.userdefined + prefs.userdefined)

## What userdefined Is

Every record has two `userdefined` dicts — one in `metadata` (system-managed) and one
in `prefs` (user-managed). These are catch-all bags for fields that don't match any
declared schema attribute. When a client sends an unknown field name in a save request,
it routes automatically to `prefs.userdefined`.

This is by design — it lets users attach custom fields without schema changes. But
without constraints, it's an attack surface: unbounded keys, unbounded values,
nested structures, unlimited count.

## The Five Constraints

| # | Constraint | Limit | Rationale |
|---|-----------|-------|-----------|
| 1 | **Max key count** | 20 pairs | Prevents stuffing hundreds of keys |
| 2 | **Key name length** | 64 chars | No absurdly long key names |
| 3 | **Value length** | 255 chars (strings) | Bounded storage per field |
| 4 | **Flat scalars only** | `str`, `int`, `float`, `bool`, `None` | No dicts, no lists, no nesting |
| 5 | **No dot-path nesting** | 1 level deep | `prefs.userdefined.key` OK; `prefs.userdefined.key.nested` rejected |

## Where Enforced

Two independent layers — both must pass:

### Layer 1: Pydantic Schema (`common/schemas/envelopes.py`)

`validate_userdefined()` runs as a `@field_validator` on both `MetadataBase` and
`RecordPrefsBase`. Any violation raises a Pydantic `ValidationError`, which
`save_envelope.py` catches and returns as a 400 response.

```python
# Constants
USERDEFINED_MAX_KEYS = 20
USERDEFINED_KEY_MAX_LEN = 64
USERDEFINED_VALUE_MAX_LEN = 255

# Type
UserDefinedValue = Union[str, int, float, bool, None]

# Typed field
userdefined: dict[str, UserDefinedValue] = Field(default_factory=dict)
```

### Layer 2: Runtime Save Gate (`apps/core/services/save_field_assignment.py`)

`_store_unknown_field()` checks all five constraints **before** writing to the object.
If any check fails, the field is rejected with a clear error message in the response —
nothing is written.

```python
UNKNOWN_FIELD_MAX_CHARS = 255
UNKNOWN_FIELD_MAX_KEY_LEN = 64
UNKNOWN_FIELD_MAX_KEYS = 20
```

### Layer 3: Dot-Path Bypass Guard (`save_field_assignment.py` — `assign_fields()`)

The `apply_json_op` function handles dot-notation paths like `prefs.userdefined.color`.
Without a guard, a client could send `prefs.userdefined.color.shade.variant` and
`apply_json_op` would create nested dicts inside userdefined — bypassing the flat-only rule.

The guard intercepts any dot-path containing `userdefined`:
- `prefs.userdefined.color` — allowed (depth 1), then checks scalar/length constraints
- `prefs.userdefined.color.shade` — rejected (depth 2+)
- `metadata.userdefined.x.y.z` — rejected (depth 2+)

## Error Responses

All constraint violations return HTTP 400 with clear messages:

```json
{
  "success": false,
  "message": "Invalid field values",
  "error": {
    "code": "invalid_field",
    "details": ["userdefined['notes'] must be a flat scalar (str/int/float/bool/None), got dict"]
  }
}
```

## What Passes

```json
{
  "custom_ref": "PO-12345",
  "color": "blue",
  "priority": 3,
  "active": true,
  "discount_pct": 12.5,
  "legacy_code": null
}
```

## What Gets Rejected

```json
// Nested dict — REJECTED
{ "address": { "street": "123 Main", "city": "Austin" } }

// List value — REJECTED
{ "tags": ["rush", "fragile"] }

// 21st key — REJECTED (if 20 already exist)
{ "key21": "overflow" }

// 100-char key name — REJECTED
{ "aaaaaa...100 chars...aaa": "val" }

// 300-char string value — REJECTED
{ "notes": "xxx...300 chars...xxx" }

// Dot-path nesting — REJECTED
// (sent as field name "prefs.userdefined.addr.street")
```

## Frontend Path Resolution

The React `getValueByPJPV` lookup checks both explicit schema paths and userdefined:

```typescript
const getValueByPJPV = (data: Record<string, any>, path: string) => {
  return getNestedValue(data, path) ?? getNestedValue(data?.userdefined, path);
};
```

Since userdefined is now flat-only, this lookup is always a single-key dict access —
no recursive path walking needed inside userdefined.

## Files

| File | What it does |
|------|-------------|
| `common/schemas/envelopes.py` | `validate_userdefined()`, constants, `@field_validator` on MetadataBase + RecordPrefsBase |
| `apps/core/services/save_field_assignment.py` | `_store_unknown_field()` runtime gate + dot-path guard in `assign_fields()` |
| `apps/core/services/save_envelope.py` | Calls Pydantic validation after field assignment, before save |
| `tests/test_wcapi_save_deep_merge.py` | Integration test — flat unknown field routes to userdefined |
