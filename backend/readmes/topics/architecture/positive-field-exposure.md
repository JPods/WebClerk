# Positive Field Exposure — Allow Lists, Not Deny Lists

**Established:** 2026-09-04
**Scar:** #81 — Portal RBAC session

## The Principle

**State what you expose. Everything else is denied by omission.**

A `view_fields` list names exactly which fields a role can see. If a field is not on the list, it does not exist for that role. There is no `view_deny` mechanism. There is no wildcard `"*"` for portal roles.

This is the opposite of a deny list, where you name what to hide and everything else passes through. Deny lists fail silently — a new field added to a model is automatically exposed to every role unless someone remembers to add it to every deny list. Allow lists fail safely — a new field is invisible until someone explicitly grants access.

## Why This Matters

1. **Auditable by inspection.** An unsophisticated user can read the list and understand exactly what they are exposing to customers and vendors. No inference required. No cross-referencing against a deny list to figure out what slipped through.

2. **Safe by default.** When a developer adds `cost.landed` to the Item model, it does not appear in any portal view until someone adds it to a role's `view_fields`. With a deny list, the developer must remember to add `cost.landed` to every deny list — and the failure mode is silent data exposure.

3. **Exposure parade.** The list IS the parade of what each role sees. Reviewing the list is reviewing the exposure surface. This creates a natural audit behavior: when you look at the `user_customer` config, you see every field the customer can access. If something shouldn't be there, it's visible. If something is missing, the customer simply doesn't see it.

4. **PJPV compliant.** JSON envelope paths (`totals.total`, `price.retail`, `comments.process`) are first-class entries in the list. The same path that reads the value controls whether the value is visible. One mechanism, one path, one source of truth.

## The Gate Rule

**No filter configured → no gate. The record passes through unchanged.**

Most models have no `view_fields` entry for a portal role. When there is no entry, there is no filter — the full record is returned. Contact, Action, Item catalog — the customer sees everything on the record because there is nothing to hide.

**Filter configured → only the stated scalar and json.path.leaf values pass through.**

The gate only exists for models where internal data coexists with customer-facing data on the same record. Transactions have `cost`, `margin`, `finance` alongside `totals.total` and `status`. The filter names exactly which paths pass. Everything else stops at the gate.

This means the system has two states, not three:
- **Open** — no filter, full record, zero overhead
- **Gated** — explicit paths only, everything else blocked

There is no "partially restricted" middle ground. There is no wildcard that means "everything except these." The gate is either absent or precise.

## How It Works

### Role Defaults (`role_defaults.py`)

Each portal role defines explicit `view_fields` per model:

```python
"user_customer": {
    "models": {
        "invoice": {
            "view_fields": [
                "id", "ida", "status", "dt_created", "dt_modified", "dt_needed",
                "attention", "company", "address_full", "phone", "email",
                "ship_via", "price_level", "priority", "purpose", "source_name",
                "totals", "totals.subtotal", "totals.tax", "totals.total",
                "totals.balance", "totals.received", "totals.shipping",
                "total", "balance", "subtotal",
                "lines", "customer_id",
                "comments", "comments.process",
            ],
        },
    },
}
```

What is NOT on this list: `cost`, `margin`, `margin_pc`, `finance`, `commission`, `sell`, `ledger`. The customer never sees these — not because they are denied, but because they were never granted.

### DB Authority (`ModelRoleConfig`)

The `ModelRoleConfig` table is the live authority. Code defaults in `role_defaults.py` are the seed — they define the initial state. The DB records can be updated without a code deploy.

When code defaults change, run the sync to update DB records. The DB always wins at runtime.

### Layout Filtering (`field_projection.py`)

Setting records contain `config.layout` with column specifications for DataBrowser. When a Setting is returned to a portal user, `filter_setting_layout()` strips any column that references a field not in the user's `view_fields`.

The Setting record is never modified. The filter runs on the response only. Admin users see the full layout. Portal users see the filtered layout. Same record, different projections.

### The Filter Chain

```
Request → authenticate → resolve role
    → get view_fields for (role, model)
    → filter record data (strip disallowed fields from response)
    → filter layout columns (strip disallowed columns from Setting response)
    → return filtered response
```

## What NOT To Do

- **Never use `view_fields: "*"` for portal roles.** Wildcards defeat the entire mechanism. Internal staff roles (admin, employee) can use wildcards because they have full access. Portal roles must enumerate.

- **Never add `view_deny`.** A deny list creates a second mechanism that must be maintained in parallel with the allow list. Two mechanisms for the same concern is one too many.

- **Never filter client-side.** The server strips fields before they reach the wire. A client-side filter is a UI convenience, not a security boundary. The data must never leave the server if the role doesn't allow it.

## The Exposure Parade

The term comes from the idea that every field on the list is marching past the reviewer in a parade. You see each one. You can challenge each one. "Should the customer see `ship_via`?" — it's on the list, so you can ask the question. If `cost.landed` were silently included via a wildcard, you'd never think to ask.

This is the same principle as a government budget line item. You can debate what's in the budget. You can't debate what you can't see.

### Adding a Field to Portal Exposure

1. Add the field path to `view_fields` in `role_defaults.py`
2. Run the DB sync to update `ModelRoleConfig`
3. The field appears in portal views immediately

### Removing a Field from Portal Exposure

1. Remove the field path from `view_fields`
2. Run the DB sync
3. The field disappears from portal views
4. The Setting layout is unchanged — the column spec remains but the filter strips it

## Connection to Divided Sovereignty

This is the enumerated powers principle applied to data access. The customer's portal has limited, enumerated permissions — not unlimited access with specific exceptions carved out. The list of what they can see IS their permission grant. Everything not enumerated is reserved.
