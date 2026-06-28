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

    class Meta:
        db_table = 'gl_journals'

    def __str__(self):
        return f"{self.account or 'GlJournal'} ({self.id})"
