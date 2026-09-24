"""What a particular model does on a verb — the code hooks, one class per model.

WC2's ``jAcceptButton`` had a ``Case of`` on the table: orders ran ``acceptOrders``,
invoices ``acceptInvoice``, items ``acceptItem``, and everything else fell to the default
``SAVE RECORD``. After the case, unconditionally, came the tail every table got —
keyTags, transaction validate, ``AcceptPostAction``, the sync record, the ``OnSave_<table>``
script — because there was nowhere else a record could be saved from.

This is that case list, dispatched instead of enumerated: a model's behaviour is looked
up by name, so adding a model does not mean editing the door, and the tail after it still
cannot be skipped. Bill, 2026-09-22: *"wc2 is much more crude than inheritance in wc3…
But the single flow creates a manageable path to maintain."* The flow is the door; the
inheritance is here.

Every verb has the same two moments (Bill, 2026-09-24, Channel_Inheritance.png):

    before_<verb>(ctx)   after the payload is authorized and assigned, before the base acts
    after_<verb>(ctx)    after the base succeeded and derived work is flushed

A method that is not defined does nothing: the default class is WC2's ``Else``. A hook
never has to be called — the verb calls it. Either moment may raise ``Refused`` to stop the
verb with a coached message and a code; an after hook may add a note to
``ctx.messages`` for the caller. The user hooks (Report rules) run after the code hook at
each moment — see ``verbs.py``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional

console_logger = logging.getLogger('console')


@dataclass
class HookContext:
    """What a hook is given. One object, so adding a fact later changes no signature."""
    actor: Any
    verb: str
    model_key: str
    obj: Any
    data: Dict[str, Any] = field(default_factory=dict)
    is_update: bool = False
    changed: FrozenSet[str] = frozenset()   # fields whose value this verb changed
    linked: bool = False                    # a communication record linked back to its contact
    messages: List[str] = field(default_factory=list)

    @property
    def user(self):
        return self.actor.user

    @property
    def user_id(self):
        return self.actor.user_id


class ModelBehaviour:
    """The default: a record that needs nothing of its own. WC2's ``Else SAVE RECORD``."""

    def hook(self, moment: str, ctx: HookContext) -> None:
        method = getattr(self, f'{moment}_{ctx.verb}', None)
        if callable(method):
            method(ctx)


_REGISTRY: Dict[str, ModelBehaviour] = {}
_DEFAULT = ModelBehaviour()


def register(model_key: str, behaviour: ModelBehaviour) -> None:
    _REGISTRY[model_key] = behaviour


def behaviour_for(model_key: str) -> ModelBehaviour:
    return _REGISTRY.get(model_key, _DEFAULT)


def registered() -> Dict[str, str]:
    """What the door will branch to — the case list, readable at runtime."""
    return {key: type(b).__name__ for key, b in sorted(_REGISTRY.items())}


# ── the branches ──────────────────────────────────────────────────────

class SettingBehaviour(ModelBehaviour):
    """A Setting is authority, not business data: the door is what authorizes it."""

    def before_save(self, ctx: HookContext) -> None:
        # Setting.save() calls full_clean() and refuses an unauthorized write; reaching
        # here means the door has already applied the staff and superuser checks.
        ctx.obj._setting_update_authorized = True
        ctx.obj._setting_create_authorized = True

    def after_save(self, ctx: HookContext) -> None:
        purpose = getattr(ctx.obj, 'purpose', '')
        if purpose in ('wc:workbench_fields', 'wc:model'):
            stored = getattr(ctx.obj, 'data', {})
            preview = ([f.get('field') if isinstance(f, dict) else f
                        for f in (stored.get('list') or [])[:4]]
                       if isinstance(stored, dict) else '?')
            console_logger.warning("[SAVE] SETTING SAVED id=%s parent_model=%s list=%s",
                                   ctx.obj.id, getattr(ctx.obj, 'parent_model', '?'), preview)


class ActionBehaviour(ModelBehaviour):
    """An action links to whoever filed it and to the documents named in its
    ``_attachments`` signal, schedules from its parents, and pushes its children when its
    own dates move. Its text is written as branch.leaf (``action.en``), never as an
    alternate name (Bill, 2026-09-24)."""

    def after_save(self, ctx: HookContext) -> None:
        pending = ctx.data.get('_attachments')
        if isinstance(pending, list) and pending:
            note = _link_action_attachments(ctx.obj, pending)
            if note:
                ctx.messages.append(note)
        from apps.core.services.action_links import (append_contact_link,
                                                     auto_schedule_from_parents,
                                                     check_and_reschedule_children)
        if ctx.user_id:
            try:
                append_contact_link(ctx.obj, ctx.user_id)
            except Exception as e:  # noqa: BLE001
                console_logger.error("[SAVE] Failed to append contact link: %s", e)

        try:
            refs = getattr(ctx.obj, 'refs', {}) or {}
            if isinstance(refs, dict) and refs.get('parents'):
                scheduled = auto_schedule_from_parents(ctx.obj, save=True)
                if scheduled.get('updated'):
                    console_logger.info("[SAVE] Auto-scheduled action %s to %s",
                                        ctx.obj.id, scheduled.get('dt_start'))
        except Exception as e:  # noqa: BLE001
            console_logger.error("[SAVE] Failed to auto-schedule action: %s", e)

        try:
            if 'dt_start' in ctx.data or 'duration' in ctx.data:
                rescheduled = check_and_reschedule_children(ctx.obj, save=True)
                if rescheduled:
                    console_logger.info("[SAVE] Rescheduled %s children of action %s",
                                        len(rescheduled), ctx.obj.id)
        except Exception as e:  # noqa: BLE001
            console_logger.error("[SAVE] Failed to cascade reschedule children: %s", e)


class CommunicationBehaviour(ModelBehaviour):
    """An email, phone, address or domain saved by a contact links back to them."""

    def after_save(self, ctx: HookContext) -> None:
        from apps.core.models import Contact
        from apps.core.services.save_contact_linking import (link_comm_to_contact,
                                                             link_obj_to_contact)
        from common.models import LINK_DENORMALIZE_FIELDS

        user = ctx.user
        if user is None or not getattr(user, 'is_authenticated', False):
            return
        contact = Contact.objects.filter(pk=getattr(user, 'pk', None)).first()
        if not contact:
            return

        bucket = ctx.model_key.lower()
        fields = LINK_DENORMALIZE_FIELDS.get(bucket, ['id']) or ['id']
        ctx.linked = link_comm_to_contact(ctx.obj, contact, bucket, fields)

        if not getattr(contact, '_refs_pending_save', False):
            return
        try:
            contact.save(update_fields=['refs', 'version', 'dt_modified'])
            contact.refresh_from_db()
            if link_obj_to_contact(ctx.obj, contact):
                ctx.obj.save(update_fields=['refs', 'version', 'dt_modified'])
            from common.refs.links import ensure_bidirectional
            ensure_bidirectional(contact, ctx.obj, kind='contact')
        except Exception as e:  # noqa: BLE001
            console_logger.error("[SAVE] Error saving deferred contact refs: %s", e)
        finally:
            try:
                delattr(contact, '_refs_pending_save')
            except Exception:  # noqa: BLE001
                pass


class PhoneBehaviour(CommunicationBehaviour):
    """A phone number shorter than four digits is refused (moved from Phone.pre_save_hook)."""

    def before_save(self, ctx: HookContext) -> None:
        number = ctx.data.get('number')
        if number and len(str(number)) < 4:
            from apps.core.services.door import Refused
            raise Refused(400, 'validation', 'number: too short', 'number: too short')


class TouchBehaviour(ModelBehaviour):
    """A touch names a known channel and a real org (moved from Touch.pre_save_hook)."""

    def before_save(self, ctx: HookContext) -> None:
        from apps.core.services.door import Refused
        channels = dict(type(ctx.obj).CHANNEL_CHOICES)
        if 'channel' in ctx.data and ctx.data['channel'] not in channels:
            msg = f'channel: must be one of {", ".join(channels.keys())}'
            raise Refused(400, 'validation', msg, msg)
        org_id = ctx.data.get('org_id')
        if org_id:
            from apps.core.serializers.behaviors import validate_org_id
            try:
                validate_org_id(org_id, org_model=ctx.data.get('org_model'))
            except Exception as e:  # noqa: BLE001 — the validator's message is the answer
                msg = str(e.detail[0]) if hasattr(e, 'detail') else str(e)
                raise Refused(400, 'validation', msg, msg)


# ── helpers moved off the models ──────────────────────────────────────

def _link_action_attachments(obj, pending) -> Optional[str]:
    """Attachments named on the payload become LinkageEntry rows (moved from
    Action.post_save_hook)."""
    try:
        from apps.docs.models import LinkageEntry
        from django.db import transaction

        with transaction.atomic():
            # Get or create a group ID for this action's attachments
            existing_entries = LinkageEntry.objects.filter(
                model_name='action',
                record_id=obj.id
            )
            
            if existing_entries.exists():
                # Use existing group
                group_id = existing_entries.first().group_id
                # Remove existing entries for this action
                existing_entries.delete()
            else:
                # Create new group
                group_id = LinkageEntry.next_group_id()

            # Create entry for the action
            LinkageEntry.objects.create(
                group_id=group_id,
                model_name='action',
                record_id=obj.id,
                purpose='attachment',
                name=f'Action {obj.id} attachments',
                role='parent'
            )

            # Create entries for each document
            for doc_id in pending:
                try:
                    doc_id_int = int(doc_id)
                    LinkageEntry.objects.create(
                        group_id=group_id,
                        model_name='document',
                        record_id=doc_id_int,
                        purpose='attachment',
                        name=f'Attachment for Action {obj.id}',
                        role='child'
                    )
                except (ValueError, TypeError):
                    continue

    except Exception as e:
        console_logger.error(f"[SAVE] action Failed to create attachment linkages: {e}")
        return f"Failed to link attachments: {str(e)}"
    return None


def _register_defaults() -> None:
    register('setting', SettingBehaviour())
    register('action', ActionBehaviour())
    for comm in ('email', 'address', 'domain'):
        register(comm, CommunicationBehaviour())
    register('phone', PhoneBehaviour())
    register('touch', TouchBehaviour())


_register_defaults()
