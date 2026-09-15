# WCAPI: Settings-Driven CRUD Mixin

This document explains how webClerk3 centralizes view/edit behavior, security, and pagination/search using a single settings-driven mixin.

## Overview

SettingsDrivenCRUDMixin reads per-model policies from Setting(purpose="view_edit") or from apps/core/management/commands/view_edit.json. It drives:

- Role-based field allowlists (view/edit), optional ctx profiles (list/display)
- Embedded relations (fk/reverse) for GET
- Filters, keyword search, ordering, pagination
- Open-query caps (allowed fields, joins, ops, row limits)
- Soft delete with 60-day purge
- Hooks (pre/post save/delete)
- Scopes (role-specific queryset builders)
- Specialty view profiles selected via ?name=compact or X-View-Name

If no policy is found, dev-fallback allows all fields and marks meta.policy_missing=true.

## Key Meta Knobs (setting.data.__meta__)

- relations: { name: { type: fk|reverse, fields: [...], limit: N } }
- ordering: ["-date_joined"]
- search: { fields: [...], keywords?: { type: array|text, field?: "refs__keywords" } }
- filters: { allow: ["company", "is_active", ...] }
- pagination: { page_size, max_page_size }
- query: { allow_fields, allow_ops, allow_joins, max_rows, max_depth }
- soft_delete: { enabled: true, field: "is_active", false_value: false, retention_days: 60 }
- hooks: { pre_save, post_save, pre_delete, post_delete } (dotted paths)
- scopes: { ROLE: "apps.core.scopes.fn" }
- views: { profileName: { ctx, fields?, ordering?, relations?, pagination?, ... } }

Per-role overrides: you can add __meta__ under a specific role block to override defaults.

## Usage

- Standard CRUD endpoint uses RESTModelRouterView with the mixin.
- Detail GET: ctx="display"; List GET: ctx="list".
- Specialty profile: GET /wcapi/<model>?name=compact.
- Soft-deleted rows are excluded automatically when soft_delete.enabled is true.
- Deletes are soft by default (flip is_active or schedule purge); hard delete only if soft delete not enabled.

## Security

- Edits are sanitized to allowed fields per role.
- Filters limited to filters.allow.
- Open-query is locked down by allow_fields/ops/joins and row caps.
- Scopes can constrain records per role/user/org.
- Hooks run in a controlled way; failures are swallowed by default (log recommended).

## Dev Fallback vs Prod

- Dev: policy_missing allowed with all fields for speed.
- Prod (recommended): require policies and fail-closed (configurable via environment and your view wrapper).

## Example (contact)

See apps/core/management/commands/view_edit.json for a full example including relations, search, views.compact, and soft_delete config.