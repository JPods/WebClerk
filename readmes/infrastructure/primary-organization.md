# Primary Organization

This document defines how wc3 identifies the internal company record that owns the database.

## Canonical Storage

The primary organization is stored as a database-backed `Setting` record — not a hard-coded Python constant.

- `Setting.purpose = "db_defaults"`
- `Setting.name = "primary_organization"`
- `Setting.parent_model = "organization"`
- `Setting.data = {"org_id": ..., "org_type": ..., "company": ..., "display_name": ..., "is_active": ...}`

Why this is the best default:
- It is environment-specific without code edits.
- It is auditable in the database.
- It can be changed in a controlled admin workflow.
- It avoids deploying code just to point a database at a different owning company record.

Service file: `apps/orgs/services/primary_org.py`

## Security

Changing the primary organization is a security-sensitive action.

Rules:
- Only `superuser` may change it.
- The org must already exist.
- The org must be active.
- The preferred org type is `customer` or `other`.
- The admin workflow should set it from the organization admin, not by manual JSON editing when possible.

## Admin Workflow

In org admin:
- Select exactly one org record.
- Run action: `Mark selected org as primary organization`

Admin file: `apps/orgs/admin.py`

The org list also shows a lightweight `.primary_org` indicator for the active primary record.

## Runtime Access

Use the service helpers instead of querying `Setting` directly:

- `get_primary_org_setting()`
- `get_primary_org_id()`
- `get_primary_org()`
- `set_primary_org()`

## Emergency Override

A Python settings override is supported for break-glass scenarios:

- `WC_PRIMARY_ORG_ID = <int>`

This should be used sparingly. The database `Setting` remains the preferred operational source of truth.

## Item + Primary Org Defaults

Primary org defaults are stored in the setting payload key `data.default_gl_accounts`.

Implementation:
- Payload builder: `apps/orgs/services/primary_org.py`
- Item default resolver: `apps/accounts/services/gl_defaults.py` (`get_item_gl_defaults`)
- Item save seed: `apps/products/models/item.py`

---

## wc3/r25 Startup Bootstrap (Single Read)

Use one startup bootstrap path in r25 to load primary organization defaults once,
then hydrate app state from that result.

### Goals

- One bootstrap call at app startup, not repeated per page.
- Resolve canonical org identity from `org_id`.
- Keep wc2 defaults available for migration, but behind a normalized payload.
- Fail gracefully so login/navigation still works when defaults are unavailable.

### Backend Contract (wcapi Foundation)

1. Read singleton setting: `GET /wcapi/get/` with `model_name=setting`, lookup `purpose=db_defaults`, `name=primary_organization`, `is_active=true`
2. Resolve `data.org_id` to canonical org record: `GET /wcapi/get/` with `model_name=customer`, id=`org_id`
3. Return a single bootstrap object:

```json
{
  "primary_organization": {
    "setting_id": 147,
    "org_id": 2,
    "display_name": "WebClerk",
    "company": "WebClerk",
    "org_type": "customer",
    "is_active": true,
    "wc2defaults": { "...": "legacy keys" }
  },
  "organization": {
    "id": 2,
    "company": "WebClerk",
    "org_type": "customer",
    "is_active": true
  },
  "config": {
    "inventory": {},
    "pricing": {},
    "shipping": {},
    "ui": {},
    "integrations": {}
  }
}
```

### Frontend Runtime Rules (r25)

- Run bootstrap once after auth bootstrap succeeds.
- Store bootstrap payload in app state (Redux/React Query/context), not HTTP cache.
- Expose one selector/hook for app-wide reads (example: `usePrimaryOrgBootstrap()`).
- Pages/components must read from bootstrap state first and avoid direct singleton fetches.

### Error and Fallback Behavior

- If `primary_organization` setting is missing: set bootstrap state to `missing_defaults`, continue app startup with safe defaults, show operator warning in settings/admin surfaces.
- If org lookup by `org_id` fails: keep setting snapshot fields (`display_name`, `company`, `org_type`, `is_active`), mark `organization` as unresolved.
- Retry policy: one immediate retry on transient failure, then backoff/manual refresh action from UI.

---

## wc2defaults Migration

The singleton currently stores a large legacy payload at `data.wc2defaults`. This is transitional config.

### Design Rules

1. **Primary identity keys are canonical** — `org_id` is the source of truth. `display_name`, `company`, `org_type`, `is_active` are snapshots for operator context.
2. **wc2defaults is transitional** — new code should not directly bind to raw wc2 key names; read from normalized wc3 config keys where available.
3. **Every retained default needs an explanation and an owner.**
4. **Unknown keys are not automatically deleted** — first marked as review-needed.

### Governance Model

Each wc2defaults key should have one status: `keep`, `rename`, `remove`, or `defer`.

### Suggested Normalized Namespaces

When migrating keys from wc2defaults, group under clear namespaces:
`pricing.*`, `inventory.*`, `shipping.*`, `commissions.*`, `credit_card.*`, `ui.*`, `sync.*`, `accounting.*`, `print.*`, `integrations.*`

### Migration Phases

1. **Inventory and classify** — Export all wc2defaults keys, add one row per key with status = defer, mark obvious keep/remove/rename items.
2. **Usage scan** — Search backend and frontend for each key and known aliases. Identify runtime read points and remove dead keys.
3. **Compatibility layer** — For renamed keys, implement a mapping function: read new wc3 key first, fallback to wc2 key, optionally write both during transition.
4. **Hardening** — Move secrets out of Setting.data. Add validation for retained keys. Add tests for key defaults and fallback behavior.
5. **Final prune** — Remove keys marked remove. Keep a dated changelog of removed keys.

### Immediate Cleanup Targets

1. **Typo field** — `wc2defaults.explaination` → replace with `explanation` if retained.
2. **Secret-like values** — Keys like `CCVerPassword` should not remain in plaintext defaults. Move sensitive values to environment variables or secret storage.
3. **Legacy host/path fields** — `SharePath`, `ShareServer`, `PathOfStatus`, `jitHelpFolder` likely represent legacy workstation assumptions. Verify live usage before keeping.

---

## Operational Notes

- Keep exactly one active `primary_organization` record per database.
- Update the singleton only through the primary org service where possible.
- Treat `data.wc2defaults` as migration data, not a permanent unbounded config bucket.

## Related Files

- `apps/orgs/services/primary_org.py`
- `apps/core/models/setting.py`
