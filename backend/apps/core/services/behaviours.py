"""What a particular model does when it is saved — the branch inside the one flow.

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

A behaviour has two moments:

    before(ctx)   after the payload is assigned and validated, before obj.save()
    after(ctx)    after obj.save(), before the universal tail

Either may raise ``Refused`` to stop the save with a coached message and a code.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

console_logger = logging.getLogger('console')


@dataclass
class SaveContext:
    """What a behaviour is given. One object, so adding a fact later changes no signature."""
    actor: Any
    obj: Any
    data: Dict[str, Any]
    model_key: str
    is_update: bool
    linked: bool = False        # a communication record linked back to its contact

    @property
    def user(self):
        return self.actor.user

    @property
    def user_id(self):
        return self.actor.user_id


class ModelBehaviour:
    """The default: a record that needs nothing of its own. WC2's ``Else SAVE RECORD``."""

    def before(self, ctx: SaveContext) -> None:
        return None

    def after(self, ctx: SaveContext) -> None:
        return None


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

    def before(self, ctx: SaveContext) -> None:
        # Setting.save() calls full_clean() and refuses an unauthorized write; reaching
        # here means the door has already applied the staff and superuser checks.
        ctx.obj._setting_update_authorized = True
        ctx.obj._setting_create_authorized = True

    def after(self, ctx: SaveContext) -> None:
        purpose = getattr(ctx.obj, 'purpose', '')
        if purpose in ('wc:workbench_fields', 'wc:model'):
            stored = getattr(ctx.obj, 'data', {})
            preview = ([f.get('field') if isinstance(f, dict) else f
                        for f in (stored.get('list') or [])[:4]]
                       if isinstance(stored, dict) else '?')
            console_logger.warning("[SAVE] SETTING SAVED id=%s parent_model=%s list=%s",
                                   ctx.obj.id, getattr(ctx.obj, 'parent_model', '?'), preview)


class ActionBehaviour(ModelBehaviour):
    """An action links to whoever filed it, schedules from its parents, and pushes its
    children when its own dates move."""

    def after(self, ctx: SaveContext) -> None:
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

    def after(self, ctx: SaveContext) -> None:
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


def _register_defaults() -> None:
    register('setting', SettingBehaviour())
    register('action', ActionBehaviour())
    for comm in ('email', 'phone', 'address', 'domain'):
        register(comm, CommunicationBehaviour())


_register_defaults()
