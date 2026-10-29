"""
Log — the one log (Bill, 2026-10-28: "Make a single log model for all logs." Setting holds only
the structure of the application; logs go here).

Thin, as Pending is: CoreModel + RefsMixin, no keywords, health or lifecycle. A log row is
written once and never changed.

- purpose  why the row was written (CoreModel: "Why this record exists"); the log definition's
           list (config.selectlists.purpose), as every model's
- action   what happened (update, delete, viewed, mismatch, drill …)
- user_id  who is responsible: the contact id of the person or agent login whose request
           triggered it (from the acting Actor when the caller names no one — Bill, 2026-10-28);
           a value, not a foreign key, so it outlives the contact
- model_name / record_id  the record it is about
- config   the content (CoreModel: "type-specific content"): name, changes, details (LogConfig)
- refs     refs.actor = {kind, source[, connection_id]}: the kind of actor behind it (user, staff,
           sync, system …) and its channel
- dt_created  when (UTC epoch ms)

Before this, eight places: AuditLog, RefsMismatchLog, APILog, UserDailyLog, SerialLog,
AliceCoachingLog, and Setting rows purpose=alice_log (916 of 1003 Settings).
"""
from __future__ import annotations

import logging

from django.db import models, transaction

from common.models import CoreModel, RefsMixin

logger = logging.getLogger(__name__)


class Log(CoreModel, RefsMixin):
    action = models.CharField(max_length=64, blank=True, db_index=True,
                              help_text="What happened: update, delete, viewed, mismatch, drill …")
    # The id as a value, not a foreign key: a deleted contact never erases who acted (C-8).
    user_id = models.BigIntegerField(null=True, blank=True, db_index=True,
                                     help_text="Who: the contact id of a person or an agent login")
    model_name = models.CharField(max_length=64, blank=True, default='',
                                  help_text="The record this is about …")
    record_id = models.BigIntegerField(null=True, blank=True, help_text="… and its id")

    class Meta:
        db_table = 'logs'
        indexes = [
            models.Index(fields=['purpose', 'dt_created']),
            models.Index(fields=['model_name', 'record_id']),
            models.Index(fields=['user_id', 'dt_created']),
        ]

    def __str__(self):
        about = f" {self.model_name}#{self.record_id}" if self.model_name else ''
        return f"Log {self.purpose}/{self.action}{about}"

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            from apps.core.services.door import Refused
            raise Refused(409, 'log_append_only',
                          'A log entry is written once and never changed; write a new one.')
        super().save(*args, **kwargs)

    @staticmethod
    def validate_entry(purpose: str) -> None:
        """What every Log row must be, however it is written (Log.write, or wcapi `new`)."""
        if not purpose:
            raise ValueError('A log entry needs a purpose.')

    @staticmethod
    def responsible(user=None, refs: dict | None = None) -> tuple:
        """(user_id, refs) for a new entry: the caller's user, else the acting Actor's login;
        refs.actor names the actor's kind and channel. Captured when the event happens, so an
        entry applied later (a queued audit write) keeps who triggered it."""
        from apps.core.services.door import acting_actor
        actor = acting_actor()
        user_id = getattr(user, 'pk', user)
        if user is not None and getattr(user, 'is_authenticated', True) is False:
            user_id = None
        if user_id is None and actor is not None:
            user_id = actor.user_id
        refs = dict(refs or {})
        if actor is not None and 'actor' not in refs:
            refs['actor'] = {'kind': actor.kind, 'source': actor.source,
                             **({'connection_id': actor.connection.pk} if actor.connection else {})}
        return user_id, refs

    @classmethod
    def write(cls, purpose: str, action: str = '', *, user=None, model_name: str = '',
              record_id=None, name: str = '', changes: dict | None = None,
              details: dict | None = None, refs: dict | None = None) -> 'Log':
        """The one writer. name, changes and details are the entry's content (LogConfig).

        Runs in its own savepoint, so a failed write never leaves a caller's transaction
        aborted; the error is raised to the caller.
        """
        cls.validate_entry(purpose)
        # The code writes the purposes it needs: a new one joins the log's list (select_lists).
        from apps.core.services import select_lists
        if select_lists.unlisted('log', {'purpose': purpose}):
            select_lists.add_value('log', 'purpose', purpose)
        user_id, refs = cls.responsible(user, refs)
        with transaction.atomic():
            return cls.objects.create(
                purpose=purpose, action=action or '', user_id=user_id,
                model_name=model_name or '', record_id=record_id,
                config={k: v for k, v in (('name', name), ('changes', changes),
                                          ('details', details)) if v},
                refs=refs,
            )

    @classmethod
    def write_or_queue(cls, purpose: str, action: str = '', **kwargs) -> None:
        """For a writer inside a business save (an audit, a line's inventory change): the save
        stands whatever happens here (Bill, 2026-10-28). A failed write is reported and queued
        as a Pending (log_write) applied to the log later; who was responsible is captured now."""
        user_id, refs = cls.responsible(kwargs.pop('user', None), kwargs.pop('refs', None))
        entry = {'purpose': purpose, 'action': action, 'user': user_id, 'refs': refs, **kwargs}
        try:
            cls.write(purpose, action, user=user_id, refs=refs, **kwargs)
        except Exception:
            logger.error("Log write failed (%s/%s %s#%s); queued as a Pending", purpose, action,
                         kwargs.get('model_name'), kwargs.get('record_id'), exc_info=True)
            from apps.core.models.pending import Pending
            Pending.queue_log_write(entry)


__all__ = ['Log']
