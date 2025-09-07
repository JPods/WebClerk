from django.db import models
from common.models import BaseModel


class Currency(BaseModel):
    """Currency catalog entry with optional external provider link.

    Used for listing active currencies and storing metadata needed for
    formatting and conversion. External updates are fetched via a sync.Connection.
    """

    code = models.CharField(max_length=10, unique=True)  # e.g., USD, EUR
    name = models.CharField(max_length=64, blank=True, null=True)
    symbol = models.CharField(max_length=8, blank=True, null=True)
    precision = models.IntegerField(default=2)
    is_active = models.BooleanField(default=True)

    # Optional default provider connection for updates (e.g., forex API)
    connection = models.ForeignKey('sync.Connection', blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'acct_currencies'
        indexes = [
            models.Index(fields=("code", "is_active"), name="acct_currency_code_active_idx")
        ]

    def __str__(self):
        return f"{self.code} ({self.name or ''})".strip()
