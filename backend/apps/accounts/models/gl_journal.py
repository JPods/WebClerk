import time

from django.db import models

from common.models import BaseModel
from apps.accounts.choices import GL_JOURNAL_SOURCE_CHOICES, GL_JOURNAL_TYPE_CHOICES

# build up predefined metadata and refs and prefs

class GlJournal(BaseModel):
    account = models.CharField(max_length=255, blank=True, null=True)

    credit = models.FloatField(blank=True, null=True)
    debit = models.FloatField(blank=True, null=True)
    source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=GL_JOURNAL_SOURCE_CHOICES,
    )
    type = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=GL_JOURNAL_TYPE_CHOICES,
    )
    # Traceability — which record generated this entry
    source_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    source_model = models.CharField(max_length=100, blank=True, default='')
    # One event inside that record (a workorder line event, an inventory movement): a record
    # can then post and reverse one event without touching the others (Fable review H1).
    event_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    # A reversal names the row it reverses; a row is standing while nothing reverses it.
    reversal_of = models.BigIntegerField(null=True, blank=True, db_index=True)

    # Division and batch grouping (from WC2 GL mining)
    division = models.CharField(max_length=50, blank=True, default='',
        db_index=True, help_text="Department/division code for GL segmentation")
    batch_id = models.CharField(max_length=80, blank=True, default='',
        db_index=True, help_text="Groups journal lines into a single posting batch (e.g., SJ-2026-06)")
    # Journalizing lock — 0 means editable, non-zero epoch ms means locked
    dt_journaled = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms when journalized. 0=editable, non-zero=locked.")
    # The period this row belongs to: its document's dt_created (Bill, 2026-11-27: "dt_created
    # will be best. It is simple. If they need to adjust it, an admin or superuser can adjust
    # it."). dt_journaled says when it was posted; a document posted a week late still reports
    # in its own month. A row with no document carries its own posting time.
    dt_document = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms of the source document's dt_created; the row's reporting period.")
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'gl_journals'
        indexes = [
            models.Index(fields=['batch_id', 'account'], name='glj_batch_acct_idx'),
            models.Index(fields=['division', 'dt_journaled'], name='glj_div_journaled_idx'),
        ]

    def __str__(self):
        return f"{self.account or 'GlJournal'} ({self.id})"

    def save(self, *args, **kwargs):
        # The chart of accounts is the authority: a posting to an account that
        # is not an active GlAccount is refused, never stored.
        from apps.accounts.services.chart import require_account
        require_account(self.account, used_by=f'journal {self.ida or "(new)"} from {self.source_model or "?"} {self.source_id or ""}'.strip())
        # A GL row is posted the moment it is written: the journal has no drafts (the preview
        # writes nothing). dt_journaled stamps when; a row born with one (a seed's posting date)
        # keeps it. The dashboard counts dt_journaled=0 as unposted (dashboard_pending) — wc_demo
        # held 349 such rows on 2026-11-07, every posting ever made.
        if not self.dt_journaled:
            self.dt_journaled = int(time.time() * 1000)
        if not self.dt_document:
            self.dt_document = document_date(self.source_model, self.source_id) or self.dt_journaled
        if self._state.adding:
            self._log_posted()
        return super().save(*args, **kwargs)

    def _log_posted(self) -> None:
        """Who posted this row and when, in comments.process — the place its document logs the
        same act (Bill, 2026-11-26: "All journals should be logged in the journal and the
        originating record"). The person is the one whose door verb is running; our own code (a
        task, a seed, a management command) is the system."""
        from apps.core.services.comment_stamp import append_comment
        from apps.core.services.door import acting_actor
        actor = acting_actor()
        user = getattr(actor, 'user', None) if actor is not None else None
        source = f'{self.source_model} {self.source_id}' if self.source_model else (self.source or 'journal')
        append_comment(self, 'process', f'Posted from {source}.', user=user, source='journalize',
                       data={'dt': self.dt_journaled})


#: The models a GL row's source_model names. A reversal ('invoice_reversal') belongs to the
#: same document, and so to the same period, as the rows it reverses.
_DOCUMENTS = {'invoice': 'Invoice', 'cash': 'Cash', 'receipt': 'Receipt',
              'workorder': 'WorkOrder', 'purchase': 'Purchase'}


def document_date(source_model: str, source_id) -> int:
    """The dt_created of the document a GL row came from, or 0 when it names none we know (a
    manual entry, an adjustment). The one place the journal learns its period."""
    name = _DOCUMENTS.get((source_model or '').removesuffix('_reversal'))
    if not name or not source_id:
        return 0
    from django.apps import apps
    return (apps.get_model('transactions', name).objects.filter(pk=source_id)
            .values_list('dt_created', flat=True).first()) or 0
