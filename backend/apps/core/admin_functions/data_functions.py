"""
Data management admin functions — purge, export, import, seed.

Naming: {verb}_{noun}_{qualifier}
"""
from django.apps import apps
from apps.core.admin_functions import register


# ---------------------------------------------------------------------------
# purge_records_faker — delete seed/faker data
# ---------------------------------------------------------------------------
def _purge_records_faker(params: dict) -> dict:
    model_name = params['model']
    dry_run = params.get('dry_run', False)

    try:
        Model = apps.get_model('docs', model_name) if model_name in ('document', 'question_answer') \
            else apps.get_model('core', model_name)
    except LookupError:
        # Try all apps
        Model = None
        for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
            try:
                Model = apps.get_model(app_label, model_name)
                break
            except LookupError:
                continue
        if not Model:
            return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}

    # Faker data patterns: status contains lorem-ish text, or name is random
    # For documents: ids 1-10 are faker seed data
    max_id = params.get('max_id', 10)
    qs = Model.objects.filter(id__lte=max_id)
    count = qs.count()

    if dry_run:
        return {'success': True, 'message': f'Would delete {count} records (id <= {max_id})', 'data': {'count': count}}

    qs.delete()
    return {'success': True, 'message': f'Deleted {count} records (id <= {max_id})', 'data': {'count': count}}

register(
    name='af_purge_records_faker',
    description='Delete seed/faker data by ID range (default: id <= 10)',
    params_schema={
        'model': {'type': 'string', 'required': True, 'help': 'Model name (e.g., document, contact)'},
        'max_id': {'type': 'integer', 'required': False, 'default': 10, 'help': 'Delete records with id <= this value'},
        'dry_run': {'type': 'boolean', 'required': False, 'default': False, 'help': 'Preview without deleting'},
        'confirm': {'type': 'boolean', 'required': True, 'help': 'Must be true to execute'},
    },
    fn=_purge_records_faker,
    category='data',
    requires_confirmation=True,
    dangerous=True,
)


# ---------------------------------------------------------------------------
# purge_records_empty — delete records with empty/blank name
# ---------------------------------------------------------------------------
def _purge_records_empty(params: dict) -> dict:
    model_name = params['model']
    dry_run = params.get('dry_run', False)

    Model = None
    for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
        try:
            Model = apps.get_model(app_label, model_name)
            break
        except LookupError:
            continue
    if not Model:
        return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}

    if not hasattr(Model, 'name'):
        return {'success': False, 'message': f'{model_name} has no name field', 'data': None}

    qs = Model.objects.filter(name__in=['', None])
    count = qs.count()

    if dry_run:
        return {'success': True, 'message': f'Would delete {count} empty-name records', 'data': {'count': count}}

    qs.delete()
    return {'success': True, 'message': f'Deleted {count} empty-name records', 'data': {'count': count}}

register(
    name='af_purge_records_empty',
    description='Delete records with empty or null name field',
    params_schema={
        'model': {'type': 'string', 'required': True, 'help': 'Model name'},
        'dry_run': {'type': 'boolean', 'required': False, 'default': False},
        'confirm': {'type': 'boolean', 'required': True},
    },
    fn=_purge_records_empty,
    category='data',
    requires_confirmation=True,
    dangerous=True,
)


# ---------------------------------------------------------------------------
# export_records_to_json — dump records as JSON fixture
# ---------------------------------------------------------------------------
def _export_records_to_json(params: dict) -> dict:
    import json
    from django.core import serializers

    model_name = params['model']
    app_label = params.get('app_label', 'docs')
    output_path = params.get('output_path')

    try:
        Model = apps.get_model(app_label, model_name)
    except LookupError:
        return {'success': False, 'message': f'Model not found: {app_label}.{model_name}', 'data': None}

    # Optional filter
    filter_kwargs = params.get('filter', {})
    qs = Model.objects.filter(**filter_kwargs) if filter_kwargs else Model.objects.all()
    count = qs.count()

    data = serializers.serialize('json', qs, indent=2)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(data)
        return {'success': True, 'message': f'Exported {count} {model_name} records to {output_path}', 'data': {'count': count, 'path': output_path}}

    return {'success': True, 'message': f'Exported {count} {model_name} records', 'data': {'count': count, 'json': json.loads(data)}}

register(
    name='af_export_records_to_json',
    description='Export model records as Django JSON fixture',
    params_schema={
        'model': {'type': 'string', 'required': True, 'help': 'Model name (e.g., document)'},
        'app_label': {'type': 'string', 'required': False, 'default': 'docs', 'help': 'Django app label'},
        'output_path': {'type': 'string', 'required': False, 'help': 'File path to save (omit for inline JSON)'},
        'filter': {'type': 'object', 'required': False, 'help': 'Django filter kwargs (e.g., {"status": "published"})'},
    },
    fn=_export_records_to_json,
    category='data',
)


# ---------------------------------------------------------------------------
# import_records_from_json — load records from JSON fixture
# ---------------------------------------------------------------------------
def _import_records_from_json(params: dict) -> dict:
    from django.core.management import call_command
    from io import StringIO

    fixture_path = params['fixture_path']
    out = StringIO()

    try:
        call_command('loaddata', fixture_path, stdout=out, verbosity=1)
        return {'success': True, 'message': f'Loaded fixture: {fixture_path}', 'data': {'output': out.getvalue()}}
    except Exception as e:
        return {'success': False, 'message': f'Failed to load {fixture_path}: {e}', 'data': None}

register(
    name='af_import_records_from_json',
    description='Load records from Django JSON fixture file',
    params_schema={
        'fixture_path': {'type': 'string', 'required': True, 'help': 'Path to fixture JSON file'},
    },
    fn=_import_records_from_json,
    category='data',
)


# ---------------------------------------------------------------------------
# count_records_by_status — tally records grouped by status
# ---------------------------------------------------------------------------
def _count_records_by_status(params: dict) -> dict:
    from django.db.models import Count

    model_name = params['model']
    group_field = params.get('group_by', 'status')

    Model = None
    for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
        try:
            Model = apps.get_model(app_label, model_name)
            break
        except LookupError:
            continue
    if not Model:
        return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}

    counts = Model.objects.values(group_field).annotate(count=Count('id')).order_by('-count')
    result = {row[group_field] or '(null)': row['count'] for row in counts}
    total = sum(result.values())

    return {'success': True, 'message': f'{total} {model_name} records grouped by {group_field}', 'data': result}

register(
    name='af_count_records_by_status',
    description='Count records grouped by a field (default: status)',
    params_schema={
        'model': {'type': 'string', 'required': True, 'help': 'Model name'},
        'group_by': {'type': 'string', 'required': False, 'default': 'status', 'help': 'Field to group by'},
    },
    fn=_count_records_by_status,
    category='data',
)
