# Role-Based Field Exposure

**Established:** 2026-08-06
**Review due:** 2026-11-06

---

## The Rule

Not every role sees every field. Cost data and price data are separated by role.

| Role | Sees prices | Sees costs | Why |
|------|:-----------:|:----------:|-----|
| **Admin** | Yes | Yes | Internal — full visibility |
| **Manager** | Yes | Yes | Internal — full visibility |
| **Sales** | Yes | Yes | Internal — needs both for margin decisions |
| **Warehouse** | No | No | Neither — operational role |
| **Accounting** | Yes | Yes | Internal — view only, but needs full picture |
| **Customer** | Yes (their prices) | No | They see what they pay, never what it costs us |
| **Rep** | Yes | No | They sell — need prices, not costs |
| **Vendor** | No | Yes (their cost to us) | They see what they charge us, never what we sell for |
| **Manufacturer** | No | Yes (their cost to us) | Same as vendor |

---

## What Gets Hidden

### Cost fields — hidden from Customer and Rep roles

These fields are excluded from view lists for customer and rep roles.

| Field | Type | Where it appears |
|-------|------|-----------------|
| `cost` | JSONB envelope | Item, all transaction headers, all transaction lines |
| `margin` | Decimal/JSONB key | Transaction headers (in `sell` envelope) |
| `margin_pct` | Decimal | Item, transaction headers |
| `margin_velocity` | Decimal | Item |
| `annual_turns` | Decimal | Item |
| `margin_floor` | Decimal | Catalog |

**Defined in:** `seed_field_access.py` as `COST_FIELDS` constant.

### Price fields — hidden from Vendor and Manufacturer roles

| Field | Type | Where it appears |
|-------|------|-----------------|
| `price` | JSONB envelope | Item, sell-side transaction lines |
| `sell` | JSONB envelope | Transaction headers |
| `price_level` | CharField | Transaction headers, transaction lines, Catalog |
| `universal_pct` | Decimal | Catalog |

**Defined in:** `seed_field_access.py` as `PRICE_FIELDS` constant.

---

## How It Works

Three layers enforce field exposure:

### 1. seed_field_access.py — defines what each role can see

Each external-facing model gets a `Setting` record (purpose=`field_access`) with
per-role view/edit field lists. The seed uses two constant sets (`COST_FIELDS`,
`PRICE_FIELDS`) to build exclusion lists per role.

- **Customer** — conservative whitelist. Only named fields are visible. Cost and price
  envelopes are excluded by omission.
- **Vendor** — conservative whitelist. Same approach.
- **Rep** — starts from all fields, then subtracts `COST_FIELDS`.
- **Admin/Manager/Sales/Accounting** — see everything (`'*'`).

```bash
./bin/python manage.py seed_field_access          # first run
./bin/python manage.py seed_field_access --force  # update existing
```

### 2. field_projection.py — strips fields from wcapi responses

`filter_response_data(user, model_name, data)` reads the user's role, looks up
the `field_access` Setting for the model, and returns only allowed fields.

Called on every wcapi response. Supports dotted paths for nested JSONB access
(e.g., `sell.total` allows the total inside the sell envelope while hiding
`sell.margin`).

### 3. role_filter.py — scopes queries by ownership

`inject_role_filters(user, model_name)` adds Django Q objects so customers only
see their own records, vendors see theirs, reps see their assigned accounts.
Variable resolution: `$user.org_ids.customer` resolves to the user's linked
customer IDs at query time.

---

## Admin-Only Models

59 of 96 models are admin-only. They do not get `field_access` Settings and are
never exposed outside employees. Examples: Setting, RoleConfig, Audit, GLAccount,
GLJournal, Currency, Warehouse, Tag, Template, Serial, Notification.

If a model is admin-only, it does not appear in portal views and wcapi rejects
queries from non-admin roles.

---

## JSONB Sub-Field Filtering

The current system handles field exposure at the top level. When a field like `cost`
is excluded, the entire JSONB envelope is stripped.

**Edge case not yet built:** When a role needs partial access to a JSONB envelope
(e.g., rep sees `sell.total` but not `sell.margin`), use dotted-path allowlists in
the view field list:

```python
# Instead of:
'view': ['sell']           # all of sell — includes margin

# Use:
'view': ['sell.subtotal', 'sell.shipping', 'sell.tax', 'sell.total']
```

`field_projection.py` already supports dotted paths. This pattern is available
when needed — no additional code required.

---

## Adding a New Role or Changing Visibility

1. Update `COST_FIELDS` or `PRICE_FIELDS` in `seed_field_access.py` if new
   sensitive fields are added to models
2. Update the role's view list in `_build_config()` or add to `OVERRIDES`
3. Run `seed_field_access --force`
4. Verify with: `GET /wcapi/permissions/` as a test user with that role

---

## Review Schedule

**Action:** Review role-based field exposure rules.
**Due:** 2026-11-06 (3 months from establishment).
**What to check:**
- Are the right fields hidden? Has the data model added new cost/price fields?
- Are customers or vendors seeing data they shouldn't?
- Are reps asking for cost data they can't see? If so, is the rule still right?
- Have any admin-only models been promoted to external-facing?

---

## See Also

- [role-based-access-plan.md](role-based-access-plan.md) — Full RBAC architecture
- [pydantic-envelope-schemas.md](pydantic-envelope-schemas.md) — JSONB envelope structure
- `apps/core/management/commands/seed_field_access.py` — the seed
- `apps/core/services/field_projection.py` — response filtering
- `apps/core/services/role_filter.py` — query scoping
