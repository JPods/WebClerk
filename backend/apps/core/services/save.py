"""The save door — the one path a record is written through.

Bill, 2026-09-22: *"I think everything should flow through this one door including
Django admin. No staff backdoor."* and, of WC2: *"I had one save function similar to the
way wcapi creates one door."*

This is that function, lifted out of ``SaveWcapiView`` so that callers without a request —
a management command, a Celery task, a sync bundle, Django admin — reach the same
authorization, the same validation, the same hooks and the same version check that
``/wcapi/save/`` has always had and nothing else did.

What the caller supplies is an **actor**, not a request: who is writing, and in what
capacity. HTTP builds one from its request; a command builds one directly. The policy
differs by actor; the door does not.

The view above it keeps what is genuinely HTTP: parsing the body, query parameters,
write-through forwarding, and turning the result (or a ``Refused``) into a response.

Phases, in order:
    1 resolve    model key → model class; the record, locked, with its version checked
    2 authorize  staff-only models, open-read models, edit filters, transaction rights,
                 the contact guard, and the role write-field filter
    3 assign     field assignment, envelope validation, model payload validation
    4 before     the model's code hook, then the user hook in <model>.save_pre
    5 persist    obj.save(); the tail every record gets (org links, lines, erosions)
    6 flush      derived work (a document's totals and ledger), so the after hooks see it
    7 after      the model's code hook, then the user hook in <model>.save_post; keywords
    8 result     the record, its messages, and what the caller should be told

Plan and review: Allie ``readmes/assessments/2026-09-22-save-door-steps-1-2.md``.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, cast

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.forms.models import model_to_dict

from apps.core.services import verbs
from apps.core.services.behaviours import HookContext
from apps.core.services.door import Actor, Refused, SaveResult, resolve_model
from apps.core.services.unit_of_work import flush, unit_of_work

console_logger = logging.getLogger('console')
logger = logging.getLogger(__name__)

# Models that hold authority rather than business data: a Connection carries a bearer
# token, a Setting defines layout and policy, a Report can dispatch a command — staff
# only (reproduced 2026-09-15).
STAFF_ONLY_MODELS = ('connection', 'bundle', 'setting', 'report', 'rolebase', 'roleconfig',
                     'modelroleconfig', 'group', 'permission', 'session')
# Header models whose lines carry the transaction endpoint's rights.
TRANSACTION_LINE_MODELS = ('order', 'invoice', 'quote', 'purchase', 'requisition',
                           'workorder', 'receipt', 'delivery')


# ── the record being written ──────────────────────────────────────────

def _load_or_new(actor: Actor, model_cls, model_key: str, record_id, expected_version):
    if not record_id:
        obj = model_cls()
        # Gate 1 on the way in: a published model's record starts unpublished (0); every
        # other record starts where its creator can see it (Bill, 2026-09-23). A payload
        # that names a level, and may write it, overrides this at assign.
        if hasattr(obj, 'security_level'):
            from apps.core.services.access import new_record_level
            obj.security_level = new_record_level(model_key)
        # Training mode (flight simulator): every record the user makes is a qq record.
        prefs = getattr(actor.user, 'prefs', None) or {}
        if isinstance(prefs, dict) and prefs.get('training'):
            obj._training_prefix = 'qq'
        return obj, True

    # A person may change only what they may read: visibility is asked of the read
    # channel, so an unseen record answers exactly like a missing one. The lock is taken on
    # the bare row — the channel's filters can carry DISTINCT, which FOR UPDATE refuses.
    if actor.is_guarded:
        from apps.core.services.record_serialize import visible_queryset
        if not visible_queryset(model_key, actor=actor)[1].filter(pk=record_id).exists():
            raise Refused(404, 'not_found', 'Record not found', 'Record not found')
    try:
        obj = model_cls.objects.select_for_update().get(id=record_id)
    except model_cls.DoesNotExist:  # type: ignore[attr-defined]
        raise Refused(404, 'not_found', 'Record not found', 'Record not found')

    if expected_version is not None:
        current = getattr(obj, 'version', None)
        if current is not None and current != expected_version:
            raise Refused(
                412, 'version_conflict',
                'Record was modified by another user. Reload and try again.',
                {'expected': expected_version, 'current': current})
    return obj, False


# ── phase 2: authorize ────────────────────────────────────────────────

def _authorize(actor: Actor, obj, model_cls, model_key: str, data: dict,
               is_update: bool) -> dict:
    """Everything that can refuse the write, and the field filter that trims it.

    Returns the filtered payload. Only a ``system`` actor skips these guards: a staff
    actor is a person at the admin (Bill: no staff backdoor), and a sync actor is guarded
    by its Connection's role (Bill, 2026-09-23).
    """
    from apps.core.services import access

    if not actor.is_guarded:
        return dict(data or {})

    user = actor.user

    # Create rights: the role's block for this model must say create — the write twin of
    # the delete door's can_delete. A role with no block gets nothing (access.py).
    if not is_update:
        from apps.core.services.role_filter import can_create
        if not can_create(actor, model_key):
            raise Refused(403, 'create_not_permitted',
                          f'Your role may not create {model_key} records.',
                          {'model_name': model_key})

    # Row-level edit rights: wide visibility, narrow edit.
    if is_update:
        from apps.core.services.role_filter import get_edit_filters
        edit_filters = get_edit_filters(actor, model_key)
        if edit_filters:
            from django.db.models import Q
            if not type(obj).objects.filter(pk=obj.pk).filter(Q(**edit_filters)).exists():
                console_logger.info("[SAVE] Edit denied by edit_filters for %s #%s by %s",
                                    model_key, getattr(obj, 'id', '?'), actor.describe())
                raise Refused(403, 'edit_filter_denied',
                              'You can only edit records assigned to you.',
                              'Record does not match your edit permissions.')

    # Models that carry authority rather than business data.
    if model_key in STAFF_ONLY_MODELS:
        if not access.is_admin(actor):
            console_logger.warning("[SAVE] Non-staff write refused on %s by %s",
                                   model_key, actor.describe())
            raise Refused(403, 'staff_only_model', f'Not permitted to write {model_key}.',
                          model_key)

    # Open-read models (Settings): the login's own superuser role writes them.
    if access.is_open_read(model_key) and not actor.may_write_open_read:
        console_logger.warning("[SAVE] Non-superuser write refused on %s by %s",
                               model_key, actor.describe())
        raise Refused(403, 'superuser_only_model',
                      f'Only a superuser may change {model_key} records.', model_key)

    # A header posted with its lines takes the transaction endpoint's rights, and for a
    # portal customer the server sets the party and re-prices every line.
    server_set_fields: dict = {}
    if model_key in TRANSACTION_LINE_MODELS and data.get('lines'):
        from apps.transactions.views.wcapi import _transaction_save_denial
        lines_payload = data.get('lines') or []
        tx_denial = _transaction_save_denial(actor, model_key, data, lines_payload)
        if tx_denial:
            console_logger.warning("[SAVE] Transaction save denied for %s user=%s: %s",
                                   model_key, actor.user_id, tx_denial[1])
            raise Refused(tx_denial[0], 'transaction_denied', tx_denial[1], model_key)
        data['lines'] = lines_payload
        # What the server just set is authoritative: the write policy would strip
        # customer_id for a portal role and leave the order with no customer at all.
        server_set_fields = {k: data[k] for k in ('customer_id', 'contact_id', 'status')
                             if k in data}

    # A rep's transaction carries the rep's own id, set by the server — never chosen by the
    # caller (Bill, 2026-09-23). The customer the rep names must still be one of theirs:
    # the write-scope check refuses anything else.
    if not is_update and model_key in TRANSACTION_LINE_MODELS and actor.role == 'rep':
        rep_ids = actor.context()['org_ids'].get('rep') or []
        if not rep_ids:
            raise Refused(403, 'no_rep_account', 'No rep account is linked to this login.',
                          model_key)
        data['rep_id'] = rep_ids[0]
        server_set_fields['rep_id'] = rep_ids[0]

    # Identity, authority and org scope on a contact.
    if model_key == 'contact':
        from apps.core.views.save_view import _contact_account_denial
        denial = _contact_account_denial(user, obj, data, is_update)
        if denial:
            console_logger.warning("[SAVE] Contact account guard denied %s on contact #%s by user=%s",
                                   denial, getattr(obj, 'id', 'new'), actor.user_id)
            raise Refused(403, 'contact_account_guard',
                          f'Not permitted to change {denial} on this contact.', denial)

    # Role-based write-field filtering. Bill, 2026-09-20: "If it is not enumerated as
    # edit, the back end should never read it as being there regardless of if it is in
    # the payload or not." So it filters the input; it does not refuse the save.
    data, denied_fields = _enumerated_edit(actor, obj, model_key, data)
    if server_set_fields:
        data.update(server_set_fields)
    if denied_fields:
        console_logger.info("[SAVE] Not enumerated as edit for %s, ignored: %s",
                            model_key, ", ".join(denied_fields))
    return data


#: Payload keys that are not fields: the envelope, and the collection the door walks.
PASSTHROUGH_KEYS = frozenset({'model_name', 'id', 'version', 'bulk', 'lines', 'password'})
#: Stamped by the system; never written from a payload by anyone but an admin.
SYSTEM_ONLY_FIELDS = frozenset({'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
                                'is_archived', 'health_rating'})


def _enumerated_edit(actor: Actor, obj, model_key: str, data: dict):
    """Keep only what the role's edit list enumerates — the one field authority.

    Bill, 2026-09-23: the settings.py write lists are retired; the role block's ``edit`` is
    the only answer to "which fields may this role write". A field not enumerated is
    ignored, not refused (2026-09-20). A JSON field keeps only its enumerated leaves.
    A person editing their own contact may also write the self-edit fields.
    """
    from apps.core.services import access
    from apps.core.services.field_projection import filter_data_by_fields
    from apps.core.services.role_filter import get_allowed_fields
    from common.schemas.carrier import read_carrier

    read_carrier(data or {})            # a carrier signal is typed or refused, never a field
    allowed = set(get_allowed_fields(actor, model_key, mode='edit'))
    if model_key == 'contact' and getattr(obj, 'pk', None) and obj.pk == actor.user_id:
        allowed |= set(access.SELF_CONTACT_EDIT)
    admin = access.is_admin(actor)          # an admin may set an ida, as before
    kept: dict = {}
    denied: list = []
    for key, value in (data or {}).items():
        if not isinstance(key, str):
            continue
        if key.startswith('_') or key in PASSTHROUGH_KEYS:
            kept[key] = value
        elif key in SYSTEM_ONLY_FIELDS and not admin:
            denied.append(key)
        elif isinstance(value, dict) and not (key in allowed):
            leaves = filter_data_by_fields({key: value}, allowed).get(key)
            if leaves:
                kept[key] = leaves
            if leaves != value:
                denied.append(key)
        elif key in allowed or f'{key}_id' in allowed:
            kept[key] = value
        else:
            denied.append(key)
    return kept, denied


# ── phase 3: assign and validate ──────────────────────────────────────

def _assign(obj, data: dict, model_cls, model_key: str, norm_key: str,
            is_update: bool) -> List[str]:
    """Set the fields, validate the envelopes. Returns non-fatal size warnings."""
    json_field_names = {f.name for f in obj._meta.get_fields()
                        if hasattr(f, 'attname') and isinstance(f, models.JSONField)}
    # M2M fields cannot be set by setattr — assign_fields uses .set() after the save.
    m2m_field_names = {f.name for f in obj._meta.get_fields()
                       if f.many_to_many or f.one_to_many}

    from apps.core.services.save_field_assignment import assign_fields
    assignment = assign_fields(obj, data, model_cls, json_field_names, m2m_field_names,
                               model_name=model_key)
    # Hashed straight out of the assignment, never held in a local: the value is the
    # user's, and a named variable is one more place it can be read or logged.
    if assignment.get('raw_password') is not None and hasattr(obj, 'set_password'):
        try:
            obj.set_password(assignment['raw_password'])
        except Exception as e:  # noqa: BLE001 — the caller is told which step failed
            raise Refused(400, 'hash_password', 'Failed to hash password', str(e))

    if assignment['field_value_errors']:
        details = [str(e) for e in assignment['field_value_errors']]
        console_logger.error("[SAVE] Field coercion errors for %s: %s", model_key, details)
        raise Refused(400, 'invalid_field', 'Invalid field values', details)

    envelope_fields = set(data.keys()) & {'metadata', 'config', 'refs', 'prefs'}
    if envelope_fields:
        from apps.core.services.save_envelope import validate_and_reject
        envelope_error = validate_and_reject(obj, model_key, envelope_fields)
        if envelope_error:
            raise Refused(400, 'envelope_invalid',
                          f'Envelope validation failed: {envelope_error}', envelope_error)

    universal = getattr(settings, 'UNIVERSAL_API_VALIDATE', False)
    if (universal or (norm_key == 'orgs' and getattr(settings, 'ORGS_VALIDATE_API', False))) \
            and hasattr(obj, 'api_validate_payload'):
        try:
            ok, errors = obj.api_validate_payload(data, is_update)
        except Exception as e:  # noqa: BLE001
            logger.warning("validation_exception model=%s error=%s", model_key, e)
            raise Refused(400, 'validation_exception', 'Validation failed', [str(e)])
        if not ok:
            logger.info("validation_failed model=%s errors=%s", model_key, errors)
            raise Refused(400, 'validation_failed', 'Validation failed', errors)

    _normalize_contact_id(obj, data)
    return assignment['field_size_errors'] or []


def _normalize_contact_id(obj, data: dict) -> None:
    """A contact_id arriving as text is either a number or a name the model resolves."""
    if not hasattr(obj, 'contact_id'):
        return
    cid = getattr(obj, 'contact_id')
    if not isinstance(cid, str):
        return
    s = cid.strip()
    if s.isdigit():
        setattr(obj, 'contact_id', int(s))
        return
    resolved = None
    assigned = data.get('assigned_to') or data.get('assignedTo')
    if isinstance(assigned, list) and assigned and isinstance(assigned[0], dict):
        first = assigned[0]
        aid, name = first.get('id'), first.get('name')
        if isinstance(aid, str) and aid.isdigit():
            resolved = int(aid)
        elif isinstance(name, str) and name.strip().isdigit():
            resolved = int(name.strip())
    setattr(obj, 'contact_id', resolved or 0)


# ── what this save changed ────────────────────────────────────────────

def _snapshot(obj) -> Dict[str, Any]:
    return {f.name: getattr(obj, f.attname, None) for f in obj._meta.concrete_fields}


def _changed(obj, snapshot: Dict[str, Any]) -> frozenset:
    """The fields whose value the payload changed — what ``when_changed`` means. A key
    that arrives with the value it already had is not a change."""
    return frozenset(f.name for f in obj._meta.concrete_fields
                     if getattr(obj, f.attname, None) != snapshot.get(f.name))


# ── the door ──────────────────────────────────────────────────────────

@transaction.atomic
def save_record(actor: Actor, data: dict, *, model_key: Optional[str] = None,
                record_id=None, expected_version=None) -> SaveResult:
    """Write one record. The only path that does.

    ``data`` is the payload as the caller holds it (already parsed; dot-paths and the
    ``record``/``data`` envelopes are the HTTP layer's business). ``model_key`` defaults
    to ``data['model_name']``.

    Raises ``Refused`` with the status and code the caller should answer with.
    """
    model_cls, model_key, norm_key = resolve_model(
        model_key or data.get('model_name') or data.get('model') or '')

    if record_id is None:
        record_id = data.get('id')
    if expected_version is None:
        expected_version = data.get('version')

    _saved_search_guard(actor, model_cls, model_key, data, record_id)

    obj, created = _load_or_new(actor, model_cls, model_key, record_id, expected_version)
    is_update = not created

    with unit_of_work():
        size_warnings, ctx = _write(actor, obj, model_cls, model_key, norm_key,
                                    data, is_update)
    # Derived work — a document's totals — happened once, on the way out of the unit, so
    # what is read back here is what the caller will be told.
    obj.refresh_from_db()

    messages = list(size_warnings) + ctx.messages

    try:
        record = model_to_dict(obj, fields=[f.name for f in obj._meta.concrete_fields])
    except Exception as e:  # noqa: BLE001
        console_logger.warning("[SAVE] Error generating record dict: %s", e)
        record = {'id': getattr(obj, 'id', None)}

    result = SaveResult(
        obj=obj, obj_id=getattr(obj, 'id', None), model_key=model_key, created=created,
        record=record, version=getattr(obj, 'version', None), linked=ctx.linked,
        messages=messages,
        warning=_setting_warning(actor, model_key, obj),
        sync=_queue_remote_sync(model_key, getattr(obj, 'id', None)),
    )
    console_logger.info("[SAVE] %s #%s saved by %s", model_key, result.obj_id, actor.describe())
    return result


def _write(actor: Actor, obj, model_cls, model_key: str, norm_key: str, data: dict,
           is_update: bool):
    """Authorize, assign, before, persist, flush, after — inside one unit of work."""
    data = _authorize(actor, obj, model_cls, model_key, data, is_update)
    snapshot = _snapshot(obj)
    size_warnings = _assign(obj, data, model_cls, model_key, norm_key, is_update)

    # The branch — WC2's `Case of` on the table, dispatched by name — and then the
    # user's hook for this slot. Everything after the base is what every model gets.
    ctx = HookContext(actor=actor, verb='save', model_key=model_key, obj=obj, data=data,
                      is_update=is_update, changed=_changed(obj, snapshot))
    verbs.before(ctx)

    try:
        obj.save()
    except DjangoValidationError as e:
        details = (list(e.message_dict.items()) if hasattr(e, 'message_dict')
                   else list(getattr(e, 'messages', [str(e)])))
        flat = ([f"{k}: {'; '.join(map(str, v))}" for k, v in details]
                if details and isinstance(details[0], tuple) else [str(d) for d in details])
        console_logger.warning("[SAVE] Validation failed on %s: %s", model_key, flat)
        raise Refused(400, 'validation_failed', 'Validation failed', flat)

    _within_scope(actor, obj, model_key)
    ctx.messages += _post_persist(obj, data, model_key)
    flush()
    verbs.after(ctx)

    # Keywords are updated synchronously so the response carries the current ones — but
    # written only if they changed. WC2's tail was `If (Modified record) SAVE RECORD`,
    # a conditional save; ours was unconditional, which is why a plain create came out
    # at version 2 (allie-36's WC2 audit, 2026-09-22).
    try:
        update_keywords = getattr(obj, 'update_keywords', None)
        if callable(update_keywords):
            before = (json.dumps(obj.refs or {}, sort_keys=True, default=str),
                      json.dumps(obj.metadata or {}, sort_keys=True, default=str))
            update_keywords()
            after = (json.dumps(obj.refs or {}, sort_keys=True, default=str),
                     json.dumps(obj.metadata or {}, sort_keys=True, default=str))
            if after != before:
                obj.save(update_fields=['refs', 'metadata', 'version', 'dt_modified'])
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Error updating keywords: %s", e)

    return size_warnings, ctx


def _within_scope(actor: Actor, obj, model_key: str) -> None:
    """A write must land inside the writer's scope (Bill, 2026-09-23).

    The read gates filter rows that exist; on a create there is no row yet, and an update
    was checked only as it was before the change. So after the row is written — inside the
    transaction — it must pass the actor's role and scope, or the whole edit is refused and
    rolled back. A rep takes orders for their own customers; a Connection writes only what
    its scope names. Level is not checked: a new item starts unpublished (0), which is
    staff-only, and its creator may still make it.
    """
    if not actor.is_guarded:
        return
    if model_key == 'contact' and obj.pk == actor.user_id:
        return                              # a person always reaches their own contact
    from apps.core.services.role_filter import inject_role_filters
    if type(obj).objects.filter(pk=obj.pk).filter(inject_role_filters(actor, model_key)).exists():
        return
    console_logger.warning("[SAVE] %s #%s would land outside the scope of %s",
                           model_key, obj.pk, actor.describe())
    raise Refused(403, 'outside_scope',
                  f'That {model_key} would be outside what your role may reach.',
                  {'model_name': model_key})


def _saved_search_guard(actor: Actor, model_cls, model_key: str, data: dict, record_id) -> None:
    """A saved search is a global, admin-managed Setting."""
    if model_key != 'setting' or not actor.is_guarded:
        return
    purpose = data.get('purpose')
    if purpose is None and record_id:
        purpose = model_cls.objects.filter(id=record_id).values_list('purpose', flat=True).first()
    if str(purpose or '').strip().lower() != 'search':
        return
    from apps.core.services.access import is_admin
    if not is_admin(actor):
        raise Refused(403, 'saved_search_admin_required',
                      'Only admin users can create or update saved searches', None)


def _post_persist(obj, data: dict, model_key: str) -> List[str]:
    """The tail every record gets, whatever it is: its org links denormalized, its lines
    processed, and its erosion notes filed. WC2 ran this unconditionally after the case;
    so does this. Returns notes for the caller."""
    try:
        from apps.transactions.services.denormalize_org_links import denormalize_org_links
        if denormalize_org_links(obj, model_key):
            obj.save(update_fields=['refs', 'version', 'dt_modified'])
    except Exception:  # noqa: BLE001 — non-transaction models simply return False
        pass

    # A source line's own door writes its release, so nothing is passed here.
    from apps.core.services.save_line_processing import process_lines
    process_lines(obj, data, model_key, adjust_source_fn=None)
    return _sync_erosions(obj)


def _sync_erosions(obj) -> List[str]:
    """Erosion and small-sting notes written into metadata become Erosion records
    (moved from BaseModel.post_save_hook — every model, so it is the base's work)."""
    meta = getattr(obj, 'metadata', None)
    if not isinstance(meta, dict):
        return []
    pending = any(isinstance(entry, dict) and not entry.get('erosion_id')
                  for key in ('small_stings', 'erosions')
                  for entry in (meta.get(key) if isinstance(meta.get(key), list) else []))
    if not pending:
        return []
    try:
        from apps.accounts.services.value_erosion import sync_metadata_erosions
        count = sync_metadata_erosions(obj)
    except Exception:  # noqa: BLE001 — logged, and the save stands
        logger.exception('[SAVE] erosion sync failed for %s #%s', type(obj).__name__, obj.pk)
        return []
    return [f'{count} erosion record(s) created'] if count else []


def _setting_warning(actor: Actor, model_key: str, obj) -> Optional[str]:
    from apps.core.views.save_view import _setting_edit_warning
    try:
        return _setting_edit_warning(actor.user, model_key, obj)
    except Exception:  # noqa: BLE001 — a coaching note never fails a save
        return None


def _queue_remote_sync(model_key: str, obj_id) -> Optional[Dict[str, Any]]:
    if obj_id is None:
        return None
    try:
        from common.sync_tasks import dispatch_sync_to_remote
        task_id = dispatch_sync_to_remote(model_key.lower(), obj_id)
        if task_id:
            return {'sync_task_id': task_id, 'sync_status': 'queued'}
    except Exception:  # noqa: BLE001 — a queued push never blocks the write
        pass
    return None
