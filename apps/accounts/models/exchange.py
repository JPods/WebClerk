# filepath: /webClerk3/accounts/models/exchange.py
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
    comment = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    # when is this valid for and must be active
    is_active = models.BooleanField(default=True)
    start_dt = models.DateTimeField(blank=True, null=True)
    end_dt = models.DateTimeField(blank=True, null=True)
    exchange = models.JSONField(default=dict, blank=True, null=True)
    currency_base = models.CharField(max_length=10, default='USD')
    currency_target = models.CharField(max_length=10, default='USD')
    rate = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'))
    precision_convert = models.IntegerField(default=2)
    precision_display = models.IntegerField(default=2)
    # link to the connection
    connection_id = models.BigIntegerField(blank=True, null=True)

    # def populate_json_fields(self):
    #     """Populate all JSONB fields with their default structures if empty."""
    #     if not self.exchange:
    #         self.exchange = default_exchange()

    class Meta:
        db_table = 'exchanges'

    def __str__(self):
        return f"{self.name or 'Exchange'} ({self.id})"