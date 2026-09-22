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
    4 before     pre-save hook, or the report hooks attached to <model>.save_pre
    5 persist    obj.save()
    6 after      org denormalization, lines, contact linking, post-save hook, keywords
    7 result     the record, its messages, and what the caller should be told

Plan and review: Allie ``readmes/assessments/2026-09-22-save-door-steps-1-2.md``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, cast

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.forms.models import model_to_dict

from apps.core.constants.model_registry import (get_model, normalize_table_key,
                                                to_model_name)
from apps.core.models import Contact
from common.models import LINK_DENORMALIZE_FIELDS

console_logger = logging.getLogger('console')
logger = logging.getLogger(__name__)

# Models that hold authority rather than business data: a Connection carries a bearer
# token, a Setting defines layout and policy, a Report can dispatch a command. None has a
# WCAPI_MODEL_POLICIES entry, and an absent policy means unrestricted — so staff only,
# until each has a policy of its own (reproduced 2026-09-15).
STAFF_ONLY_MODELS = ('connection', 'bundle', 'setting', 'report', 'rolebase', 'roleconfig',
                     'modelroleconfig', 'group', 'permission', 'session')
# Header models whose lines carry the transaction endpoint's rights.
TRANSACTION_LINE_MODELS = ('order', 'invoice', 'quote', 'purchase', 'requisition',
                           'workorder', 'receipt', 'delivery')


# ── what the caller is ────────────────────────────────────────────────

@dataclass
class Actor:
    """Who is writing, and in what capacity.

    ``kind`` decides policy, not the door: a ``system`` actor is still audited, still
    validated, still versioned — it is simply permitted more. "No backdoor" and "a
    command may write what a user may not" are only compatible if the second is written
    down rather than assumed from an absence.
    """
    user: Any = None
    kind: str = 'user'          # user | system | sync
    source: str = 'wcapi'       # wcapi | admin | command | task | sync

    @classmethod
    def from_request(cls, request, source: str = 'wcapi') -> 'Actor':
        return cls(user=getattr(request, 'user', None), kind='user', source=source)

    @classmethod
    def system(cls, source: str = 'command') -> 'Actor':
        return cls(user=None, kind='system', source=source)

    @property
    def user_id(self):
        return getattr(self.user, 'id', None)


# ── what the door refuses with ────────────────────────────────────────

class Refused(Exception):
    """A save the door will not make, with the answer the caller should be given.

    One exception, carrying the status and code the response needs, because the codes are
    the contract: tests and the front end both read ``error.code``.
    """

    def __init__(self, status: int, code: str, message: str, details: Any = None,
                 extra: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else message
        self.extra = extra or {}

    def as_error(self) -> Dict[str, Any]:
        return {'code': self.code, 'details': self.details, **self.extra}


@dataclass
class SaveResult:
    """What the door did, in the shape the response is built from."""
    obj: Any
    obj_id: Optional[int]
    model_key: str
    created: bool
    record: Dict[str, Any] = field(default_factory=dict)
    version: Optional[int] = None
    linked: bool = False
    messages: List[str] = field(default_factory=list)
    warning: Optional[str] = None
    sync: Optional[Dict[str, Any]] = None

    def payload(self) -> Dict[str, Any]:
        data = {
            'id': self.obj_id,
            'record': self.record,
            'model_name': self.model_key,
            'version': self.version,
            'linked': self.linked,
        }
        if self.messages:
            data['messages'] = list(self.messages)
        if self.sync:
            data.update(self.sync)
        return data


# ── phase 1: resolve ──────────────────────────────────────────────────

def resolve_model(raw_model_name: str):
    """(model_cls, model_key, norm_key) for a payload's model_name."""
    if not raw_model_name:
        raise Refused(400, 'missing_model_name', 'Missing required field: model_name',
                      'Provide model_name (singular)')
    norm_key = normalize_table_key(raw_model_name)
    model = get_model(norm_key) if norm_key else None
    if not model:
        raise Refused(400, 'unknown_model', f'Unknown model: {raw_model_name}',
                      f'Unknown model: {raw_model_name}')
    model_cls = cast(Type[models.Model], model)
    return model_cls, (to_model_name(model_cls) or raw_model_name), norm_key


def _load_or_new(actor: Actor, model_cls, model_key: str, record_id, expected_version):
    if not record_id:
        obj = model_cls()
        # Training mode (flight simulator): every record the user makes is a qq record.
        prefs = getattr(actor.user, 'prefs', None) or {}
        if isinstance(prefs, dict) and prefs.get('training'):
            obj._training_prefix = 'qq'
        return obj, True

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

    Returns the filtered payload. A ``system`` actor skips the user-facing guards: it has
    no role, no edit filters and no portal to re-price for.
    """
    from apps.core.services import access

    if actor.kind != 'user':
        return dict(data or {})

    user = actor.user

    # Row-level edit rights: wide visibility, narrow edit.
    if is_update and user and getattr(user, 'is_authenticated', False):
        from apps.core.services.role_filter import get_edit_filters
        edit_filters = get_edit_filters(user, model_key)
        if edit_filters:
            from django.db.models import Q
            if not type(obj).objects.filter(pk=obj.pk).filter(Q(**edit_filters)).exists():
                console_logger.info("[SAVE] Edit denied by edit_filters for %s #%s user=%s",
                                    model_key, getattr(obj, 'id', '?'), actor.user_id)
                raise Refused(403, 'edit_filter_denied',
                              'You can only edit records assigned to you.',
                              'Record does not match your edit permissions.')

    # Models that carry authority rather than business data.
    if model_key in STAFF_ONLY_MODELS:
        if not (user and user.is_authenticated and (user.is_superuser or user.is_staff)):
            console_logger.warning("[SAVE] Non-staff write refused on %s by user=%s",
                                   model_key, actor.user_id)
            raise Refused(403, 'staff_only_model', f'Not permitted to write {model_key}.',
                          model_key)

    # Open-read models (Settings): the login's own superuser role writes them.
    if access.is_open_read(model_key) and not access.open_read_can_write(user):
        console_logger.warning("[SAVE] Non-superuser write refused on %s by user=%s",
                               model_key, actor.user_id)
        raise Refused(403, 'superuser_only_model',
                      f'Only a superuser may change {model_key} records.', model_key)

    # A header posted with its lines takes the transaction endpoint's rights, and for a
    # portal customer the server sets the party and re-prices every line.
    server_set_fields: dict = {}
    if model_key in TRANSACTION_LINE_MODELS and data.get('lines'):
        from apps.transactions.views.wcapi import _transaction_save_denial
        lines_payload = data.get('lines') or []
        tx_denial = _transaction_save_denial(user, model_key, data, lines_payload)
        if tx_denial:
            console_logger.warning("[SAVE] Transaction save denied for %s user=%s: %s",
                                   model_key, actor.user_id, tx_denial[1])
            raise Refused(tx_denial[0], 'transaction_denied', tx_denial[1], model_key)
        data['lines'] = lines_payload
        # What the server just set is authoritative: the write policy would strip
        # customer_id for a portal role and leave the order with no customer at all.
        server_set_fields = {k: data[k] for k in ('customer_id', 'contact_id', 'status')
                             if k in data}

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
    from apps.core.utils.model_policies import enforce_write_policy
    data, denied_fields = enforce_write_policy(model_cls, data, user=user)
    if server_set_fields:
        data.update(server_set_fields)
    if denied_fields:
        console_logger.info("[SAVE] Not enumerated as edit for %s, ignored: %s",
                            model_key, ", ".join(denied_fields))
    return data


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


# ── phase 4 and 6: the model's own say ────────────────────────────────

def _before(actor: Actor, obj, model_key: str, data: dict, is_update: bool) -> None:
    """The model's pre-save hook, or the report hooks attached to <model>.save_pre."""
    pre_hook = getattr(obj, 'pre_save_hook', None)
    if callable(pre_hook):
        context = {'model_name': model_key, 'is_update': is_update,
                   'user_id': actor.user_id}
        try:
            result = _call_hook(pre_hook, data, is_update, context)
        except Exception as e:  # noqa: BLE001 — a hook's refusal is the user's answer
            raise Refused(400, 'validation_exception', 'Pre-save validation failed', str(e))
        if result is not None:
            if isinstance(result, tuple):
                ok = bool(result[0])
                msg = str(result[1] if len(result) > 1 else 'Validation failed')
                if not ok:
                    raise Refused(400, 'validation', msg, msg)
            else:
                raise Refused(400, 'validation', str(result), str(result))
        return

    # A blocking report rule stops the save with its own message; anything else is
    # recorded, not raised.
    from apps.core.services.report_hooks import HookBlocked, run_save_hooks
    try:
        pre_result = run_save_hooks(model_key, 'save_pre', obj, changed=set(data or {}),
                                    user=actor.user)
        if pre_result.errors:
            console_logger.warning("[SAVE] save_pre hook problems: %s", pre_result.errors)
    except HookBlocked as blocked:
        raise Refused(400, 'hook_blocked', blocked.message, blocked.message,
                      extra={'report': blocked.report_ida})


def _call_hook(hook, data, is_update, context):
    """The hooks were written with three different signatures over time."""
    try:
        return hook(data, is_update, context)
    except TypeError:
        try:
            return hook(data, is_update)
        except TypeError:
            return hook(data)


def _after(actor: Actor, obj, model_key: str, data: dict, is_update: bool) -> Optional[str]:
    """The model's post-save hook, or the report hooks at <model>.save_post.

    Post-save never blocks: a problem is reported back with the record.
    """
    post_hook = getattr(obj, 'post_save_hook', None)
    if callable(post_hook):
        context = {'model_name': model_key, 'is_update': is_update,
                   'user_id': actor.user_id}
        try:
            return _call_hook(post_hook, data, is_update, context)
        except Exception as e:  # noqa: BLE001
            console_logger.error("[SAVE] Error in post_save_hook: %s", e)
            return f'post_save_hook error: {e}'

    try:
        from apps.core.services.report_hooks import run_save_hooks
        post_result = run_save_hooks(model_key, 'save_post', obj, changed=set(data or {}),
                                     user=actor.user)
        if post_result.set_fields:
            obj.save()
        if post_result.errors:
            note = '; '.join(post_result.errors)
            console_logger.warning("[SAVE] save_post hook problems: %s", note)
            return note
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Error running save_post report hooks: %s", e)
        return f'Post-save hook error: {e}'
    return None


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

    data = _authorize(actor, obj, model_cls, model_key, data, is_update)
    size_warnings = _assign(obj, data, model_cls, model_key, norm_key, is_update)
    _before(actor, obj, model_key, data, is_update)

    # Settings validate in save(); the door is what authorizes them.
    if model_key == 'setting':
        obj._setting_update_authorized = True
        obj._setting_create_authorized = True
    try:
        obj.save()
    except DjangoValidationError as e:
        details = (list(e.message_dict.items()) if hasattr(e, 'message_dict')
                   else list(getattr(e, 'messages', [str(e)])))
        flat = ([f"{k}: {'; '.join(map(str, v))}" for k, v in details]
                if details and isinstance(details[0], tuple) else [str(d) for d in details])
        console_logger.warning("[SAVE] Validation failed on %s: %s", model_key, flat)
        raise Refused(400, 'validation_failed', 'Validation failed', flat)

    linked = _post_persist(actor, obj, data, model_key)
    note = _after(actor, obj, model_key, data, is_update)

    # Keywords are updated synchronously so the response carries the current ones.
    try:
        update_keywords = getattr(obj, 'update_keywords', None)
        if callable(update_keywords):
            update_keywords()
            obj.save(update_fields=['refs', 'metadata', 'version', 'dt_modified'])
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Error updating keywords: %s", e)

    messages = list(size_warnings)
    if note:
        messages.append(note)

    try:
        record = model_to_dict(obj, fields=[f.name for f in obj._meta.concrete_fields])
    except Exception as e:  # noqa: BLE001
        console_logger.warning("[SAVE] Error generating record dict: %s", e)
        record = {'id': getattr(obj, 'id', None)}

    result = SaveResult(
        obj=obj, obj_id=getattr(obj, 'id', None), model_key=model_key, created=created,
        record=record, version=getattr(obj, 'version', None), linked=linked,
        messages=messages,
        warning=_setting_warning(actor, model_key, obj),
        sync=_queue_remote_sync(model_key, getattr(obj, 'id', None)),
    )
    console_logger.info("[SAVE] %s #%s saved by %s actor", model_key, result.obj_id, actor.kind)
    return result


def _saved_search_guard(actor: Actor, model_cls, model_key: str, data: dict, record_id) -> None:
    """A saved search is a global, admin-managed Setting."""
    if model_key != 'setting' or actor.kind != 'user':
        return
    purpose = data.get('purpose')
    if purpose is None and record_id:
        purpose = model_cls.objects.filter(id=record_id).values_list('purpose', flat=True).first()
    if str(purpose or '').strip().lower() != 'search':
        return
    user = actor.user
    is_admin_writer = bool(
        user and getattr(user, 'is_authenticated', False)
        and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)
             or str(getattr(user, 'role', '')).lower() == 'admin'))
    if not is_admin_writer:
        raise Refused(403, 'saved_search_admin_required',
                      'Only admin users can create or update saved searches', None)


def _post_persist(actor: Actor, obj, data: dict, model_key: str) -> bool:
    """What the record's own save leaves for the door: org links, lines, contact links."""
    try:
        from apps.transactions.services.denormalize_org_links import denormalize_org_links
        if denormalize_org_links(obj, model_key):
            obj.save(update_fields=['refs', 'version', 'dt_modified'])
    except Exception:  # noqa: BLE001 — non-transaction models simply return False
        pass

    # A source line's own door writes its release, so nothing is passed here.
    from apps.core.services.save_line_processing import process_lines
    process_lines(obj, data, model_key, adjust_source_fn=None)

    linked = False
    if model_key.lower() in {'email', 'phone', 'address', 'domain'} and actor.user is not None:
        bucket = model_key.lower()
        contact = Contact.objects.filter(pk=getattr(actor.user, 'pk', None)).first() \
            if getattr(actor.user, 'is_authenticated', False) else None
        if contact:
            from apps.core.services.save_contact_linking import link_comm_to_contact
            fields = LINK_DENORMALIZE_FIELDS.get(bucket, ['id']) or ['id']
            linked = link_comm_to_contact(obj, contact, bucket, fields)
            _persist_deferred_contact_refs(obj, contact, bucket)

    if model_key == 'action' and actor.user_id:
        _action_links(obj, data, actor.user_id)
    return linked


def _persist_deferred_contact_refs(obj, contact, bucket: str) -> None:
    if not getattr(contact, '_refs_pending_save', False):
        return
    try:
        contact.save(update_fields=['refs', 'version', 'dt_modified'])
        contact.refresh_from_db()
        from apps.core.services.save_contact_linking import link_obj_to_contact
        if link_obj_to_contact(obj, contact):
            obj.save(update_fields=['refs', 'version', 'dt_modified'])
        from common.refs.links import ensure_bidirectional
        ensure_bidirectional(contact, obj, kind='contact')
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Error saving deferred contact refs: %s", e)
    finally:
        try:
            delattr(contact, '_refs_pending_save')
        except Exception:  # noqa: BLE001
            pass


def _action_links(obj, data: dict, user_id) -> None:
    """An action links to who filed it, schedules from its parents, and pushes its
    children when its own dates move."""
    from apps.core.services.action_links import (append_contact_link,
                                                 auto_schedule_from_parents,
                                                 check_and_reschedule_children)
    try:
        append_contact_link(obj, user_id)
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Failed to append contact link: %s", e)

    try:
        refs_obj = getattr(obj, 'refs', {}) or {}
        if isinstance(refs_obj, dict) and refs_obj.get('parents'):
            scheduled = auto_schedule_from_parents(obj, save=True)
            if scheduled.get('updated'):
                console_logger.info("[SAVE] Auto-scheduled action %s to %s",
                                    obj.id, scheduled.get('dt_start'))
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Failed to auto-schedule action: %s", e)

    try:
        if 'dt_start' in data or 'duration' in data:
            rescheduled = check_and_reschedule_children(obj, save=True)
            if rescheduled:
                console_logger.info("[SAVE] Rescheduled %s children of action %s",
                                    len(rescheduled), obj.id)
    except Exception as e:  # noqa: BLE001
        console_logger.error("[SAVE] Failed to cascade reschedule children: %s", e)


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
