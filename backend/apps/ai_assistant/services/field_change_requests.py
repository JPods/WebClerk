"""
Field Change Request Service — users request field type changes, Alice creates
action records, administrators approve.

Flow:
  1. User pastes element in GetHelpDialog → clicks "Request Change"
  2. This service creates:
     - AliceObservation (category='field_change_request')
     - Action record (project='Field Change Requests', status='open')
  3. Alice adds to her vector store for pattern detection
  4. Administrator reviews the action record → approves or rejects
  5. On approval, Alice (or admin) updates the field_access Setting
  6. Field immediately changes behavior everywhere (DataBrowser, forms, etc.)

The user CANNOT change the field directly. Only request.
"""
from __future__ import annotations

import json
import time
from django.apps import apps as dj_apps


def _now_ms():
    return int(time.time() * 1000)


def request_field_change(
    model: str,
    field: str,
    change_type: str,
    values_source: str = 'static',
    options: list = None,
    query_model: str = '',
    query_field: str = '',
    query_filter: str = '',
    setting_name: str = '',
    reason: str = '',
    field_label: str = '',
    contact_id: int = None,
) -> dict:
    """Process a field change request from a user.

    Creates:
      1. AliceObservation with full request details
      2. Action record for administrator review

    Does NOT change the field — that requires admin approval.

    Returns: {observation_id, action_id, message}
    """
    now = _now_ms()

    # Build the request detail
    request_detail = {
        'model': model,
        'field': field,
        'field_label': field_label,
        'change_type': change_type,
        'values_source': values_source,
        'reason': reason,
        'requested_by': contact_id,
        'dt_requested': now,
    }

    if options:
        request_detail['options'] = options
    if query_model:
        request_detail['query_model'] = query_model
    if query_field:
        request_detail['query_field'] = query_field
    if query_filter:
        request_detail['query_filter'] = query_filter
    if setting_name:
        request_detail['setting_name'] = setting_name

    # Build human-readable description
    if change_type == 'select' and values_source == 'static' and options:
        desc = f'Make {model}.{field} a dropdown with values: {", ".join(options)}'
    elif change_type == 'select' and values_source == 'query':
        desc = f'Make {model}.{field} a dropdown from {query_model}.{query_field}'
        if query_filter:
            desc += f' where {query_filter}'
    elif change_type == 'select' and values_source == 'setting':
        desc = f'Make {model}.{field} a dropdown from Setting "{setting_name}"'
    elif change_type == 'select' and values_source == 'distinct':
        desc = f'Make {model}.{field} a dropdown from distinct values in the data'
    elif change_type == 'lookup':
        desc = f'Make {model}.{field} a lookup to {query_model} (display: {query_field})'
    elif change_type == 'readonly':
        desc = f'Make {model}.{field} read-only (system driven)'
    elif change_type == 'datetime':
        desc = f'Make {model}.{field} a date/time picker'
    else:
        desc = f'Change {model}.{field} to type: {change_type}'

    if reason:
        desc += f'. Reason: {reason}'

    # 1. Create AliceObservation
    observation_id = None
    try:
        AliceObservation = dj_apps.get_model('ai_assistant', 'AliceObservation')
        obs = AliceObservation.objects.create(
            category='field_change_request',
            source='power_user',
            priority=1,
            message=desc,
            detail=json.dumps(request_detail),
            model_name=model,
            contact_id=contact_id,
            dedup_key=f'field_change:{model}:{field}:{change_type}',
        )
        observation_id = obs.pk
    except Exception:
        # AliceObservation model may not exist yet — create via raw SQL
        pass

    # 2. Create Action record for admin review
    Action = dj_apps.get_model('core', 'Action')
    action = Action.objects.create(
        ida=f'FCR-{model}-{field}'[:40],
        project_name='Field Change Requests',
        status='open',
        kanban_column='backlog',
        priority=2,
        difficulty=1,
        action={'en': f'Field change: {model}.{field} → {change_type}'},
        description={'en': desc},
        contact_id=contact_id or 69,  # default to claude
        metadata={
            'field_change_request': request_detail,
            'observation_id': observation_id,
            'requires_approval': True,
            'approved': False,
            'approved_by': None,
            'dt_approved': None,
        },
    )

    # 3. Send agent message to Alice
    try:
        from apps.core.services.agent_bus_bridge import send_to_bus
        send_to_bus(
            'user', 'alice',
            f'Field change request: {model}.{field}',
            body=desc,
            priority=1,
            category='field_change_request',
            context=request_detail,
        )
    except Exception:
        pass

    return {
        'observation_id': observation_id,
        'action_id': action.pk,
        'action_ida': action.ida,
        'message': f'Request submitted. Action {action.ida} created for admin review.',
        'description': desc,
    }


def approve_field_change(action_id: int, contact_id: int) -> dict:
    """Administrator approves a field change request.

    Reads the request from the action's metadata, updates the field_access
    Setting for the model, and marks the action as complete.

    Returns: {success, model, field, change_applied}
    """
    Action = dj_apps.get_model('core', 'Action')
    Setting = dj_apps.get_model('core', 'Setting')

    try:
        action = Action.objects.get(pk=action_id)
    except Action.DoesNotExist:
        return {'error': f'Action {action_id} not found'}

    meta = action.metadata or {}
    request = meta.get('field_change_request')
    if not request:
        return {'error': 'No field change request in this action'}

    if meta.get('approved'):
        return {'error': 'Already approved'}

    model = request['model']
    field = request['field']
    change_type = request['change_type']

    # Update the model definition Setting (wc:model, fallback to legacy wc:field_access)
    setting = Setting.objects.filter(
        parent_model=model,
        purpose='wc:model',
        is_active=True,
    ).first()
    if not setting:
        setting = Setting.objects.filter(
            parent_model=model,
            purpose='wc:field_access',
            is_active=True,
        ).first()

    if not setting:
        return {'error': f'No model definition Setting found for {model}'}

    data = setting.config or {}
    behaviors = data.get('behaviors', data.get('field_behaviors', {}))
    field_def = behaviors.get(field, {})

    # Apply the change
    field_def['type'] = change_type

    if change_type == 'select':
        values_source = request.get('values_source', 'static')
        field_def['options_source'] = values_source

        if values_source == 'static':
            field_def['options'] = request.get('options', [])
        elif values_source == 'query':
            field_def['options_source'] = 'query'
            field_def['options_model'] = request.get('query_model', '')
            field_def['options_field'] = request.get('query_field', '')
            field_def['options_filter'] = request.get('query_filter', '')
        elif values_source == 'setting':
            field_def['options_source'] = 'setting'
            field_def['options_setting'] = request.get('setting_name', '')
        elif values_source == 'distinct':
            field_def['options_source'] = 'distinct'

    elif change_type == 'lookup':
        field_def['lookup_model'] = request.get('query_model', '')
        field_def['lookup_display'] = request.get('query_field', '')

    elif change_type == 'readonly':
        field_def['editable'] = False
        field_def['system_driven'] = True

    elif change_type == 'datetime':
        field_def['type'] = 'datetime'
        field_def['editable'] = True

    behaviors[field] = field_def
    # Write back to correct key based on record format
    if 'behaviors' in data:
        data['behaviors'] = behaviors
    else:
        data['field_behaviors'] = behaviors
    Setting.objects.filter(pk=setting.pk).update(data=data, dt_modified=_now_ms())

    # Mark action as approved and complete
    meta['approved'] = True
    meta['approved_by'] = contact_id
    meta['dt_approved'] = _now_ms()
    action.metadata = meta
    action.status = 'complete'
    action.kanban_column = 'done'
    action.percent_complete = 100
    action.save()

    return {
        'success': True,
        'model': model,
        'field': field,
        'change_type': change_type,
        'action_ida': action.ida,
        'message': f'{model}.{field} changed to {change_type}. Effective immediately.',
    }
