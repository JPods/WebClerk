"""
Record manipulation admin functions — update, set, copy, merge, check, fix.

Naming: {verb}_{noun}_{qualifier}
"""
from django.apps import apps
from apps.core.admin_functions import register


# ---------------------------------------------------------------------------
# update_field_bulk — set one field on selected records
# ---------------------------------------------------------------------------
def _update_field_bulk(params: dict) -> dict:
    model_name = params['model']
    ids = params['ids']
    field = params['field']
    value = params['value']

    Model = None
    for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
        try:
            Model = apps.get_model(app_label, model_name)
            break
        except LookupError:
            continue
    if not Model:
        return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}

    qs = Model.objects.filter(id__in=ids)
    count = qs.count()
    qs.update(**{field: value})

    return {'success': True, 'message': f'Updated {field}={value} on {count} records', 'data': {'count': count}}

register(
    name='af_update_field_bulk',
    description='Set a field value on selected records',
    params_schema={
        'model': {'type': 'string', 'required': True, 'help': 'Model name'},
        'ids': {'type': 'array', 'required': True, 'help': 'List of record IDs'},
        'field': {'type': 'string', 'required': True, 'help': 'Field name to update'},
        'value': {'type': 'any', 'required': True, 'help': 'New value'},
    },
    fn=_update_field_bulk,
    category='records',
)


# ---------------------------------------------------------------------------
# set_status_bulk — change status on selected records
# ---------------------------------------------------------------------------
def _set_status_bulk(params: dict) -> dict:
    return _update_field_bulk({
        'model': params['model'],
        'ids': params['ids'],
        'field': 'status',
        'value': params['status'],
    })

register(
    name='af_set_status_bulk',
    description='Change status on selected records',
    params_schema={
        'model': {'type': 'string', 'required': True},
        'ids': {'type': 'array', 'required': True, 'help': 'List of record IDs'},
        'status': {'type': 'string', 'required': True, 'help': 'New status value'},
    },
    fn=_set_status_bulk,
    category='records',
)


# ---------------------------------------------------------------------------
# set_refs_keyword_bulk — add a keyword to refs.keywords on selected records
# ---------------------------------------------------------------------------
def _set_refs_keyword_bulk(params: dict) -> dict:
    from django.db.models import F
    from django.db.models.functions import Coalesce

    model_name = params['model']
    ids = params['ids']
    keyword = params['keyword']
    action = params.get('action', 'add')  # add or remove

    Model = None
    for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
        try:
            Model = apps.get_model(app_label, model_name)
            break
        except LookupError:
            continue
    if not Model:
        return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}

    updated = 0
    for record in Model.objects.filter(id__in=ids):
        refs = record.refs or {}
        keywords = refs.get('keywords', [])
        if action == 'add' and keyword not in keywords:
            keywords.append(keyword)
            refs['keywords'] = keywords
            record.refs = refs
            record.save(update_fields=['refs'])
            updated += 1
        elif action == 'remove' and keyword in keywords:
            keywords.remove(keyword)
            refs['keywords'] = keywords
            record.refs = refs
            record.save(update_fields=['refs'])
            updated += 1

    return {'success': True, 'message': f'{action} keyword "{keyword}" on {updated} records', 'data': {'updated': updated}}

register(
    name='af_set_refs_keyword_bulk',
    description='Add or remove a keyword from refs.keywords on selected records',
    params_schema={
        'model': {'type': 'string', 'required': True},
        'ids': {'type': 'array', 'required': True},
        'keyword': {'type': 'string', 'required': True, 'help': 'Keyword to add or remove'},
        'action': {'type': 'string', 'required': False, 'default': 'add', 'help': '"add" or "remove"'},
    },
    fn=_set_refs_keyword_bulk,
    category='records',
)


# ---------------------------------------------------------------------------
# check_orphans — find records with broken FK references
# ---------------------------------------------------------------------------
def _check_orphans(params: dict) -> dict:
    model_name = params['model']
    fk_field = params['fk_field']
    fk_model = params['fk_model']

    Model = None
    FKModel = None
    for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
        try:
            if not Model:
                Model = apps.get_model(app_label, model_name)
        except LookupError:
            pass
        try:
            if not FKModel:
                FKModel = apps.get_model(app_label, fk_model)
        except LookupError:
            pass

    if not Model:
        return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}
    if not FKModel:
        return {'success': False, 'message': f'FK model not found: {fk_model}', 'data': None}

    # Find IDs that reference non-existent FK records
    fk_ids = set(Model.objects.exclude(**{fk_field: None}).values_list(fk_field, flat=True))
    existing_ids = set(FKModel.objects.filter(id__in=fk_ids).values_list('id', flat=True))
    orphan_fk_ids = fk_ids - existing_ids

    if not orphan_fk_ids:
        return {'success': True, 'message': 'No orphans found', 'data': {'orphan_count': 0}}

    orphan_records = list(Model.objects.filter(**{f'{fk_field}__in': orphan_fk_ids}).values_list('id', flat=True))

    return {
        'success': True,
        'message': f'Found {len(orphan_records)} orphan records referencing {len(orphan_fk_ids)} missing {fk_model} records',
        'data': {'orphan_count': len(orphan_records), 'orphan_ids': orphan_records[:100], 'missing_fk_ids': list(orphan_fk_ids)[:100]},
    }

register(
    name='af_check_orphans',
    description='Find records with broken FK references',
    params_schema={
        'model': {'type': 'string', 'required': True, 'help': 'Model to check'},
        'fk_field': {'type': 'string', 'required': True, 'help': 'FK field name (e.g., customer_id)'},
        'fk_model': {'type': 'string', 'required': True, 'help': 'Referenced model (e.g., customer)'},
    },
    fn=_check_orphans,
    category='records',
)


# ---------------------------------------------------------------------------
# copy_records — duplicate selected records with new IDs
# ---------------------------------------------------------------------------
def _copy_records(params: dict) -> dict:
    model_name = params['model']
    ids = params['ids']

    Model = None
    for app_label in ['core', 'docs', 'transactions', 'products', 'orgs']:
        try:
            Model = apps.get_model(app_label, model_name)
            break
        except LookupError:
            continue
    if not Model:
        return {'success': False, 'message': f'Model not found: {model_name}', 'data': None}

    created_ids = []
    for rid in ids:
        try:
            original = Model.objects.get(id=rid)
            original.pk = None
            original.id = None
            if hasattr(original, 'uuid'):
                original.uuid = None
            if hasattr(original, 'ida'):
                original.ida = ''
            original.save()
            created_ids.append(original.id)
        except Model.DoesNotExist:
            continue

    return {'success': True, 'message': f'Copied {len(created_ids)} records', 'data': {'created_ids': created_ids}}

register(
    name='af_copy_records',
    description='Duplicate selected records with new IDs',
    params_schema={
        'model': {'type': 'string', 'required': True},
        'ids': {'type': 'array', 'required': True, 'help': 'Record IDs to copy'},
    },
    fn=_copy_records,
    category='records',
)
