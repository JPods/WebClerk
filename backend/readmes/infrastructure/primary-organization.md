# Primary Organization

This document defines how wc3 identifies the internal company record that owns the database.

## Recommendation

Use a database-backed `Setting` record as the source of truth, not a hard-coded Python constant.

Why this is the best default:
- It is environment-specific without code edits.
- It is auditable in the database.
- It can be changed in a controlled admin workflow.
- It avoids deploying code just to point a database at a different owning company record.

## Canonical Storage

The primary organization is stored as:

- `Setting.purpose = "db_defaults"`
- `Setting.name = "primary_organization"`
- `Setting.parent_model = "organization"`
- `Setting.data = {"org_id": ..., "org_type": ..., "company": ..., "display_name": ..., "is_active": ...}`

Service file:
- `apps/orgs/services/primary_org.py`

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

Admin file:
- `apps/orgs/admin.py`

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
