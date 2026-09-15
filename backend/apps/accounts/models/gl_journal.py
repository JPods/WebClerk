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

    # Division and batch grouping (from WC2 GL mining)
    division = models.CharField(max_length=50, blank=True, default='',
        db_index=True, help_text="Department/division code for GL segmentation")
    batch_id = models.CharField(max_length=80, blank=True, default='',
        db_index=True, help_text="Groups journal lines into a single posting batch (e.g., SJ-2026-06)")
    # Journalizing lock — 0 means editable, non-zero epoch ms means locked
    dt_journaled = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms when journalized. 0=editable, non-zero=locked.")
    note = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'gl_journals'
        indexes = [
            models.Index(fields=['batch_id', 'account'], name='glj_batch_acct_idx'),
            models.Index(fields=['division', 'dt_journaled'], name='glj_div_journaled_idx'),
        ]

    def __str__(self):
        return f"{self.account or 'GlJournal'} ({self.id})"
