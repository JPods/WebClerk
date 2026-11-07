from django.db import models
from common.models import BaseModel


class JournalBatch(BaseModel):
    """The audit record of a posting run — like Order is to OrderLine.

    Each run of a Journalize report (journalize_report.post_selected: the person ticks rows
    and posts) creates one: the model, the ids ticked, every row's answer (config), counts,
    who ran it and when. The dashboard reads these for posting history and exceptions.
    """

    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETE = 'complete'
    STATUS_HAS_EXCEPTIONS = 'has_exceptions'
    STATUS_CHOICES = [
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETE, 'Complete'),
        (STATUS_HAS_EXCEPTIONS, 'Has Exceptions'),
    ]

    TYPE_CHOICES = [                     # one Journalize report per posting model
        ('invoice', 'Invoices'),
        ('cash', 'Cash'),
        ('receipt', 'Receipts'),
        ('workorder', 'Workorders'),
    ]

    # status — inherited from CoreModel
    batch_type = models.CharField(
        max_length=32, choices=TYPE_CHOICES, default='invoice',
    )

    # Period this batch covers (optional — null means all open)
    period_year = models.IntegerField(null=True, blank=True)
    period_month = models.IntegerField(null=True, blank=True)

    # Totals — what posted
    total_debit = models.DecimalField(
        max_digits=18, decimal_places=6, default=0,
    )
    total_credit = models.DecimalField(
        max_digits=18, decimal_places=6, default=0,
    )

    # Counts
    count_posted = models.IntegerField(default=0)
    count_exceptions = models.IntegerField(default=0)
    count_skipped = models.IntegerField(default=0)
    count_absorbed = models.IntegerField(default=0,
        help_text="FX rounding entries auto-absorbed < $2")

    # Timing
    dt_started = models.BigIntegerField(null=True, blank=True)
    dt_completed = models.BigIntegerField(null=True, blank=True)

    # Who ran it
    run_by = models.ForeignKey(
        'core.Contact', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='journal_batches',
    )

    class Meta:
        db_table = 'journal_batches'
        ordering = ['-dt_created']

    def __str__(self):
        return f"JournalBatch {self.ida} ({self.status})"
