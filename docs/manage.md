# Management & Operations Guide

(Moved from `README_MANAGE.md` at project root on 2025-09-01.)

Central reference for Django management commands and operational scripts shipped in this repository. Commands are invoked with:

```bash
python manage.py <command> [options]
```

For virtualenv convenience you can also use `./bin/python manage.py ...` if the provided venv is active.

See main documentation map in `README.md` for links to testing and upgrade guides.

## 1. Data / JSON Envelope Telemetry

### storage_load_report

Summarize JSON field size utilization across BaseModel descendants.

```bash
python manage.py storage_load_report --field metadata --limit 100
python manage.py storage_load_report --field refs --order asc --limit 25
python manage.py storage_load_report --json > storage_util.json
```
 
Options:

- `--model app_label.ModelName` restrict scan
- `--field metadata|refs|prefs|comments|contacts|locations|domains|phones|emails|relations|financial|docs|access|data|metrics|gl_accounts` choose envelope/aspect (default metadata)
- `--limit N` sample size per model (default 50)
- `--order asc|desc` order by size (default desc)
- `--json` machine readable output

Use prior to enabling large JSON offload or before migrations altering envelope structure. Org aspect fields (e.g. `contacts`, `financial`) have heuristic soft caps for telemetry; adjust in `storage_load_report` if growth patterns change.

### org_aspect_metrics

Summarize per-aspect item counts and serialized JSON byte sizes for `OrgBase` rows.

```bash
python manage.py org_aspect_metrics --limit 100
python manage.py org_aspect_metrics --json > org_aspects.json
```
Outputs average, p95, and max counts/bytes for each aspect. Use to spot growth trends (e.g., domains approaching limit) and to justify pruning or offload strategies.

Interpretation quick guide:

- avg_count vs p95_count: large gap indicates a few heavy orgs skew distribution.
- p95_bytes near PostgreSQL toast thresholds (hundreds of KB) => consider normalization/offload.
- orgs_with_data significantly lower than total_orgs => aspect is sparse; indexing strategy may be revisited later.

### Aspect validation (service-layer helper)

`OrgBase.validate_aspects(partial=False, data=None)` uses Pydantic schemas (`apps.orgs.pydantic_schemas`) to validate current aspect blobs (or a proposed patch when `partial=True`). Returns `(ok, errors)`.

Example usage in a shell:

```python
from apps.orgs.models import OrgBase
org = OrgBase.objects.first()
ok, errs = org.validate_aspects()
print(ok, errs)
```

For incoming patch payload prior to applying:

```python
payload = {"contacts": [{"name": "Jane Smith", "role": "buyer"}]}
ok, errs = org.validate_aspects(partial=True, data=payload)
if ok:
	# merge & save logic here
	...
else:
	print("Validation errors", errs)
```

### org_validate_aspects

Batch validates existing `OrgBase` rows against the Pydantic snapshot schema.

```bash
python manage.py org_validate_aspects --limit 500
python manage.py org_validate_aspects --ids 10,11,12 --json
python manage.py org_validate_aspects --limit 0 --fail-on-error
```

Options:

- `--limit N` limit rows scanned (0 = all)
- `--ids id1,id2` explicit set of IDs (overrides limit)
- `--json` machine-readable output including invalid row details
- `--fail-on-error` exit code 1 if any invalid rows found (CI gate)

Suggested CI usage (nightly):

```bash
python manage.py org_validate_aspects --limit 0 --fail-on-error --json > org_validate_report.json
```

### API Validation Toggle (Universal)

Two settings control validation inside `/wcapi/save/`:

1. `UNIVERSAL_API_VALIDATE=True` – enable model-provided `api_validate_payload(data, is_update)` hook for *all* registered tables.
2. `ORGS_VALIDATE_API=True` – (legacy/specific) only validates `orgs` via aspect schemas if universal flag is off.

OrgBase implements `api_validate_payload` delegating to its Pydantic aspect schemas:

- Create: full snapshot validation (all aspects + core fields)
- Update: partial patch validation (only provided aspect + core fields present in payload)
- Failure: HTTP 400 `{ "status":"error", "message":"Validation failed", "errors":[ ... ] }`

Other models can opt-in by defining `api_validate_payload(self, data: dict, is_update: bool) -> tuple[bool, list[str]]`.

Leave flags disabled for bulk ingestion; rely on `org_validate_aspects` management command as an offline gate.

### Model Hooks & Async Events

All `BaseModel` descendants expose generalized hook points used by the universal save endpoint (`/wcapi/save/`):

Hook sequence (create or update):

1. `pre_save_hook(self, data)` (synchronous, before `obj.save()`). Return a non-None string to abort with HTTP 400 `{status:error, message:<string>}`.
2. Field assignment & size checks.
3. `api_validate_payload(self, data, is_update)` if validation flags enabled.
4. `obj.save()` (BaseModel version increment, changed_fields tracking, telemetry).
5. `post_save_hook(self, data)` (synchronous). Return a string to append into response `messages`.
6. `tasks.save_post(table_name, data)` (dynamic table-specific synchronous task; best effort).
7. `tasks.save_post_async.delay(table_name, id, version)` (generic async fan-out).

Async fan-out:

- `save_post_async` (Celery task) emits a lightweight event; extend or consume by subscribing to broker messages for downstream indexing, cache invalidation, webhooks, etc.

Scaffolding validation overrides:

- Run `python manage.py scaffold_api_validation --dry-run` to preview additions of `api_validate_payload` stubs to models inheriting `BaseModel` that still use the default implementation.
- Omit `--dry-run` to apply changes in-place.
- Include `--include-hooks` to also scaffold `pre_save_hook` and `post_save_hook` stubs when a model still inherits the BaseModel defaults.

Introspection:

- Run `python manage.py list_model_hooks` to see which models still use default hooks.
- Add `--json` for machine-readable output or `--app <label>` to filter.
- Run `python manage.py profile_api_validation --iterations 100 --json` to profile validation hook latency.

Customizing a model:

```python
class Product(BaseModel):
	name = models.CharField(max_length=120)

	def pre_save_hook(self, data):
		if not data.get('name'):
			return 'name: required'

	def api_validate_payload(self, data, is_update):
		errors = []
		if 'name' in data and len(data['name']) < 3:
			errors.append('name: too short')
		return (not errors, errors)

	def post_save_hook(self, data):
		return 'product saved (hook)'
```

Enable universal validation to enforce custom `api_validate_payload` across all tables: set `UNIVERSAL_API_VALIDATE=True`.

### Hook Reference

| Hook / Task | Scope | Invocation Point | Return / Contract | Failure Handling | Notes |
|-------------|-------|------------------|-------------------|------------------|-------|
| `pre_save_hook(self, data)` | Every `BaseModel` subclass | Before field validation & save | `None` or `str` (abort) | Abort with 400 if string returned | Light, synchronous |
| `api_validate_payload(self, data, is_update)` | Every `BaseModel` subclass | After pre-save, before save | `(ok, errors)` | 400 if not ok | Business validation |
| `validate_aspects(partial, data)` | `OrgBase` only | Indirect via api_validate | `(ok, errors)` | Caller decides | Pydantic schemas |
| `obj.save()` | Django ORM | After validation | Persist / raise | Exception -> 400/500 | Version bump & telemetry |
| `post_save_hook(self, data)` | Every subclass | After save | `None` or message str | Exceptions captured | Keep fast |
| `tasks.save_pre` / `tasks.save_post` | Dynamic Celery | Around save | Best-effort | Exceptions swallowed | Name-based dispatch |
| `tasks.save_post_async` | Celery async | After synchronous post | None | Autoretry (configurable) | Fan-out event |

Settings (related):

- `SAVE_POST_ASYNC_RETRY_ENABLED` (default True): set False (e.g. in tests) to disable retry loop behavior in `save_post_async`.

| Flags: `UNIVERSAL_API_VALIDATE`, `ORGS_VALIDATE_API` | Scope | When Evaluated | Type | Failure Handling | Description |
|------------------------------------------------------|-------|----------------|------|------------------|-------------|
| Settings flags | Global | Each save request | bool | N/A | Control validation activation scope |

Contract Enforcement:
- Test `tests/test_hooks_contract.py` validates hook signatures across all `BaseModel` descendants.

Remediation flow: run command, inspect invalid rows, correct offending aspect JSON (or adjust schemas), re-run until clean.

## 2. Keyword / Search Maintenance

### refresh_keywords

Re-computes `refs.keywords` for models with `metadata.flags.keywords_pending = True`.

```bash
python manage.py refresh_keywords --batch 500
```

## 3. Demo / Fixture Utilities

### demo_data_import_export

Import or export demo dataset for local testing.

```bash
python manage.py demo_data_import_export --export demo.json
python manage.py demo_data_import_export --import demo.json
```

### demo_data_fix_dup_key

Cleans duplicated keys or integrity issues in imported demo data.

```bash
python manage.py demo_data_fix_dup_key --dry-run
```

### audit_base_models

Integrity / consistency checks across BaseModel descendants.

```bash
python manage.py audit_base_models --verbose
```

## 4. Access / Permission Adjustments

### fix_view_edit_PUBLIC

Normalize or repair view/edit access lists embedded in `metadata.access`.

```bash
python manage.py fix_view_edit_PUBLIC --apply
```
Add `--dry-run` first to preview.

## 5. Development Reset / Local Ops

`reset_dev.sh` provides a convenience script to purge and re-seed a dev environment.

```bash
bash common/management/commands/reset_dev.sh
```

## 6. Postman / API Contract Assets

`postman_url_import.json` contains raw Postman definitions (or seed endpoints) for manual / contract test creation.

## 7. Retired / Legacy Commands

The `retired/` subfolder stores deprecated scripts retained for reference.

## 8. Operational Best Practices

- Use telemetry commands (like `storage_load_report`) in CI to track growth trends.
- Schedule keyword refresh off-peak.
- Run `audit_base_models` after schema or size threshold changes.
- Snapshot DB before bulk import / export operations.

## 9. Adding a New Command

1. Create file: `common/management/commands/<name>.py`.
2. Subclass `BaseCommand` and implement `handle()`.
3. Document it here with purpose + usage examples.
4. (Optional) Add tests invoking `call_command` for critical logic.

## 10. Quick Reference Table

| Command | Purpose | Typical Schedule |
|---------|---------|------------------|
| storage_load_report | JSON size telemetry | On-demand / weekly |
| refresh_keywords | Rebuild search keywords | Hourly / daily |
| audit_base_models | Integrity & size audits | After deployments / weekly |
| demo_data_import_export | Import/export demo dataset | Ad hoc |
| demo_data_fix_dup_key | Clean demo data anomalies | After imports |
| fix_view_edit_PUBLIC | Normalize access metadata | Ad hoc |

---
Questions or clarifications: open an issue referencing this file and the command.

