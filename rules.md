# Project Rules & Conventions

Root = webClerk3 (paths in docs/code are relative to this root)

## Git & Versioning

Pushing to dev/main:

1. Add/adjust tests alongside code (tests/ or app/tests/)
2. Ensure automated test + lint pass
3. PR review before merge to main

Baseline contracts = v0.3; breaking changes require version bump + docs.

## Table Naming

No table name should use 'es' pluralization.

- Use 's' plurals: `contacts`, `locations`, `domains`, `phones`, `emails`, `actions`.
- Avoid irregular 'es' forms: not `addresses`, `classes`, `processes`.
- Prefer synonyms to dodge awkward plurals (`location` over `address`).

Field / verbose names may use 'es' if needed; restriction applies to actual table names only.

Baseline rules that require a published exception:

1. Django REST Framework for all endpoints
2. Only json response to endpoints.
3. Standardize response with:
   3.1. { "success": true, "data": ..., "errors": {} }  
        Related data in a json must be noted as data.related{} for consistency.
   3.2. { "success": false, "data": null, "errors": { "message": "...", "help": "https://..." } }. Clear error messages with link to help.
4. jsons for exchanging information, even inputs. Convert all CSV's etc into json outside of WebClerk.
5. always refer to the table_name in its plural and a record in its singular. Drive table_names so they only have plural forms that end in "s" or "es". Minimize "es" endings. No tables ending in e
6. always use table_name for table_name of the primary table being worked and "id" is the id for the primary table record id. For non-primary table_name_id format.
7. Save paths to larger documents. Never save large documents in the database.
8. Limit size of objects that can be stored in JSONBs that might be exposed to the outside (see MAX_METADATA_SIZE = 32000 in common/models.py
9. always put relationships into table_name.refs.links{"related_table_name::[id1,id4,...],"related_table_name2":[]}
10. Settings records for view_edit.  "view_edit" is a keyword that cannot be used for anything except referring to [] of fields by role for table, etc...
11. Break the common Django framework of put, post, add functions with generalized, universal wcapi/relate, wcapi/get, wcapi/save etc... see core/urls.py
11. Use Celery to wrap generalized functions such as wcapi/save for pre/post hooks.
12. ONLY use uuid for communicating between databases with sync records (catalog updates, security issues, defaults, etc.).

## Rate Limiting

- Implement DRF throttling classes for all endpoints.
- Document limits per endpoint.

## Logging & Monitoring

- Log all API requests and errors.
- Integrate Sentry/Prometheus (or equivalents) for alerts.
- Review logs routinely for anomalies.

## Related Data JSON Shape

1. Related data always under `data.related`.

## Performance

1. Optimize queries (select_related / prefetch_related).
2. Always paginate/filter/order list endpoints.
3. Non-critical side-effects go to temp records processed by Celery (e.g., inventory adjustments).

## Deployment

1. API-only backend (gunicorn/nginx etc.).
2. Secrets via environment variables.
3. Ensure pagination/filtering on lists (see Performance).
4. Provide sync records for suggested JS/HTML integration.

## Table Structure

1. Relationships into `table.refs.links.related_table[]`.
2. Store only paths for large documents (no large blobs in DB).

## Business Logic Placement

1. App-specific: app `services/`.
2. Shared: `common/`.
3. Experiments: `sandbox/` (add dated cleanup note).
4. Defaults: `common/defaults/` (data + loader).
5. Background tasks: Celery.

## Version Control Strategy

1. Detect version mismatches (optimistic concurrency) and surface structured error.
2. Serializers / endpoint JSON maintain stable contract.
3. Sync records propagate version issues to remote systems.
4. Error payload example includes `code` and help URL (see API docs).
5. Log + sync mismatches for audit.
6. Provide ≥90 day deprecation window (except security). Weekly sync reminders.

## Frontend Naming

1. Use `*-list` for list/table views.
2. Use `*-details` for detail/edit views.

## Date / Time Handling

1. ISO 8601 in JSON responses.
2. Store all times in UTC.
3. Field/variable names prefixed `dt_`.

## Internationalization

1. Backend strings minimal; additional UI i18n handled client-side.

## API Docs & Deprecation

1. `/endpoint/help/` links to help metadata.
2. Actions record documents deprecations.
3. Provide migration guides (URLs, videos, sync records).
4. Sync endpoints broadcast advance notices.
5. Maintain OpenAPI docs (drf-spectacular).
6. Scheduled dependency scan posts sync record if mismatch.

## Security

1. Enforce HTTPS (prod).
2. Sync functions for attack reports.
3. Sync functions for dependency notifications & updates.
4. Optional automated vulnerability scan distribution.
5. Use Django security middleware.
6. UUID usage limited to sync records.
7. Secrets via env vars only.
8. Sync records broadcast dependency upgrade scripts.

## Data Validation

1. Endpoints supply canonical schema.
2. Sync actions for out-of-compliance remediation.
3. Role-based feedback for UI design.
4. Include field misuse notices even in success responses.

Languages:
Use Django i18n only for backend warnings/errors.
Keep all other content in English to reduce complexity.
Manage UI translations in React if you ever need to expand.


## Timestamp Summary

Always UTC (`timezone.now()`), names prefixed `dt_`; use DateTimeField or ms epoch for JSON.
