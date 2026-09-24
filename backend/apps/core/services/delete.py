"""The delete door — the one path a record is removed through.

Bill, 2026-09-22: *"Having every save, get, delete flow through their own individual
channel creates a maintainable system. There are few places to audit."*

Delete has the same shape as save and a shorter body: resolve, authorize, then let the
record's own guards have their say. Those guards already exist and are good — the
hard-delete rule refuses a journalized or reconciled document, the cash door refuses a
document with money applied and reverses what a delete is allowed to remove, and
``Model.delete()`` overrides carry the rest. What was missing was a single place they
were reached from: admin, commands and sync each called ``obj.delete()`` on their own.

A refusal from a guard is coaching, not a crash: it comes back as ``Refused`` with a code
and the message the guard wrote, so the caller can show it to the person who tried.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from django.db import transaction

from apps.core.services.door import Actor, Refused, resolve_model

console_logger = logging.getLogger('console')


@dataclass
class DeleteResult:
    deleted: bool
    obj_id: Any
    model_key: str

    def payload(self) -> dict:
        return {'deleted': self.deleted, 'id': self.obj_id, 'model_name': self.model_key}


@transaction.atomic
def delete_record(actor: Actor, model_key: str, record_id, *,
                  visible_only: bool = True) -> DeleteResult:
    """Remove one record. The only path that does.

    ``visible_only`` applies the caller's row visibility, so a user cannot delete a record
    they could not see. A system actor sees everything and says so.
    """
    if not model_key or record_id is None:
        raise Refused(400, 'invalid_payload', 'invalid payload',
                      {'model_name': model_key, 'id': record_id})

    model_cls, model_key, _norm = resolve_model(model_key)

    if actor.is_guarded:
        # The role's `delete` flag (wc:model Setting config.access), or superuser for
        # the open-read models.
        from apps.core.services.role_filter import can_delete
        if not can_delete(actor, model_key):
            raise Refused(403, 'delete_not_permitted',
                          f'Your role may not delete {model_key} records.',
                          {'model_name': model_key, 'id': record_id})

    obj = _find(actor, model_cls, model_key, record_id, visible_only)
    if obj is None:
        return DeleteResult(deleted=False, obj_id=record_id, model_key=model_key)

    try:
        obj.delete()
    except Refused:
        raise
    except Exception as e:  # noqa: BLE001
        # A guard refusing is the usual case here: the hard-delete rule, the cash door,
        # a model's own delete(). Their message is written for a person, so it is the
        # answer — not a 500 with the word "failed" in it.
        message = str(e) or f'{model_key} {record_id} cannot be deleted.'
        console_logger.info("[DELETE] Refused on %s #%s: %s", model_key, record_id, message)
        raise Refused(409, 'delete_refused', message,
                      {'model_name': model_key, 'id': record_id}) from e

    console_logger.info("[DELETE] %s #%s deleted by %s", model_key, record_id, actor.describe())
    return DeleteResult(deleted=True, obj_id=record_id, model_key=model_key)


def _find(actor: Actor, model_cls, model_key: str, record_id, visible_only: bool):
    if not actor.is_guarded or not visible_only:
        return model_cls.objects.filter(pk=record_id).first()
    from apps.core.services.record_serialize import visible_queryset
    _cls, qs = visible_queryset(model_key, actor=actor)
    return qs.filter(pk=record_id).first()
