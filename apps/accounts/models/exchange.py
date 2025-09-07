from django.db import models
from common.models import BaseModel
from decimal import Decimal


# def default_exchange():
#     return {
#         "from": "USD",
#         "to": "USD",
#         "rate": 1    
#         }


class Exchange(BaseModel):
    """Represents an exchange/settlement event (transaction), not a rate record.

    Note: Historical FX reference data lives in ExchangeRate. This model can be
    extended later with amounts, fees, references, etc., when we wire
    transaction flows.
    """
    
    name = models.CharField(max_length=255, blank=True, null=True)
    # when is this valid for and must be active
    is_active = models.BooleanField(default=True)
    dt_start = models.DateTimeField(blank=True, null=True)
    dt_end = models.DateTimeField(blank=True, null=True)
    exchange = models.JSONField(default=dict, blank=True, null=True)
    currency_base = models.CharField(max_length=10, default='USD')
    currency_target = models.CharField(max_length=10, default='USD')
    rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'))
    precision_convert = models.IntegerField(default=2)
    precision_display = models.IntegerField(default=2)
    # Link to the provider connection used to retrieve this rate (stub to external API). Uses the same DB column.
    connection = models.ForeignKey('sync.Connection', db_column='connection_id', blank=True, null=True, on_delete=models.SET_NULL)

    # def populate_json_fields(self):
    #     """Populate all JSONB fields with their default structures if empty."""
    #     if not self.exchange:
    #         self.exchange = default_exchange()

    class Meta:
        abstract = True  # Legacy placeholder; use ExchangeTransaction instead

    # Note: removed self-referential alias properties for dt_start/dt_end to avoid masking fields.

    def __str__(self):
        return f"{self.name or 'Exchange'} ({self.id})"