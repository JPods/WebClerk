from django.db import models
from common.models import BaseModel
from decimal import Decimal

BASE_DECIMAL_DEFAULT = Decimal("0.00")
BASE_INT_DEFAULT = Decimal("0")

class BaseLineModel(BaseModel):
    id = models.BigAutoField(primary_key=True)
    id_transaction = models.BigIntegerField()
    transaction_type = models.CharField(max_length=20)
    id_item = models.BigIntegerField()
    uuid_item = models.CharField(max_length=255, blank=True, null=True)
    ida_item = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    description_text = models.TextField(blank=True, null=True)
    time_lead = models.IntegerField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    quantity_parent = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_ordered = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_actioned = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_remaining = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_packed = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_canceled = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    quantity_is_fixed = models.BooleanField(default=False)
    cost_unit = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    cost_extended = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    cost_extended = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    cost_is_fixed = models.BooleanField(default=False)
    price_unit = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    price_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    price_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    price_extended = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    price_is_fixed = models.BooleanField(default=False)
    price_precision = models.IntegerField(default=2)
    price_manufacturer_suggested_retail = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    tax_sales_rate = models.DecimalField(max_digits=5, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    tax_sales_amount = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    tax_cost_rate = models.DecimalField(max_digits=5, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    tax_cost_amount = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    tax_jurisdiction = models.BigIntegerField(blank=True, null=True)
    tax_code = models.CharField(max_length=40, blank=True, null=True)
    by_created = models.CharField(max_length=50, blank=True, null=True)
    by_updated = models.CharField(max_length=50, blank=True, null=True)
    by_action = models.CharField(max_length=50, blank=True, null=True)
    by_requested = models.CharField(max_length=50, blank=True, null=True)
    transaction_flow_source_type = models.CharField(max_length=50, blank=True, null=True)
    transaction_flow_source_id = models.BigIntegerField(blank=True, null=True)
    transaction_flow_destination_type = models.CharField(max_length=50, blank=True, null=True)
    transaction_flow_destination_id = models.BigIntegerField(blank=True, null=True)
    # dt_created, dt_updated, dt_expected, dt_completed go in metadata['history']

    class Meta:
        abstract = True