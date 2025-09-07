from django.db import models
from common.models import BaseModel
from decimal import Decimal


class ExchangeRate(BaseModel):
    """Time-windowed FX rate between two currency codes.

    Separate from transactional Exchanges; this stores reference rates
    fetched from an external provider (sync.Connection).
    """

    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    dt_start = models.DateTimeField(blank=True, null=True)
    dt_end = models.DateTimeField(blank=True, null=True)

    currency_base = models.CharField(max_length=10, default='USD')
    currency_target = models.CharField(max_length=10, default='USD')
    rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'))
    precision_convert = models.IntegerField(default=4)
    precision_display = models.IntegerField(default=2)

    # Provenance to the provider that supplied this rate
    connection = models.ForeignKey(
        'sync.Connection',
        db_column='connection_id',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = 'acct_exchange_rates'
        indexes = [
            models.Index(
                fields=("currency_base", "currency_target", "is_active"),
                name="acct_exrate_base_target_active_idx",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["currency_base", "currency_target", "dt_start", "dt_end"],
                name="uniq_acct_exchange_rate_window",
            )
        ]

    def __str__(self):
        return f"{self.currency_base}->{self.currency_target} @ {self.rate}"
