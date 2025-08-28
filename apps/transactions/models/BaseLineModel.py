from django.db import models
from common.models import BaseModel
from decimal import Decimal
'''
 Google Doc for BaseLineModel schema and design:
 https://docs.google.com/document/d/12C8LHt8x1Bl6spM_iHFC6DK01eIxQzD5_4-3cK9ybow/edit?tab=t.0
 
'''

BASE_DECIMAL_DEFAULT = Decimal("0.00")
BASE_INT_DEFAULT = Decimal("0")

def default_item():
    return {
        "id_num": None,
        "ida_item": "",
        "uuid_item": "",
        "description": "",
        "description_text": "",
        "time_lead": None,
        "locations": [],
        "unit_measure": "",
        "sequence": 0,
        "line_number": 0,
        "is_deleted": False,
        "is_active": True,
        "is_archived": False
    }

def default_quantity(transaction_type=None):
    if transaction_type == "proposal":
        return {
            "is_blanket": False,
            "increment": 0
        }
    elif transaction_type == "order":
        return {
            "shipped": 0
        }
    elif transaction_type == "invoice":
        return {
            "packed": 0
        }
    else:
        # Default structure
        return {
            "placed": None,
            "backlog": None,
            "remaining": None,
            "is_fixed": False,
            "precision": 2
        }

def default_cost():
    return {
        "freight": None,
        "unit": None,
        "extended": None,
        "is_fixed": False,
        "precision": 2
    }

def default_price():
    return {
        "unit": None,
        "discount_percent": None,
        "discount_amount": None,
        "extended": None,
        "margins": None,
        "is_fixed": False,
        "precision": 2,
        "manufacturer_suggested_retail": None
    }

def default_tax():
    return {
        "sales_rate": None,
        "sales": None,
        "cost_rate": None,
        "cost": None,
        "shipping": None
    }


def default_comments():
    return {
        "public": "",
        "process": "",
        "foreign": ""
    }

def default_action():
    return {
        "action_next":{"who":"","when":0,"what":""},
        "created": {"who":"","when":0},
        "requested": {"who":"","when":0},
        "updated": {"who":"","when":0}
    }

def default_physical():
    return {
        "unit": 0,
        "extended": 0,
        "volume":{},
        "hazardous": {}
    }

# tracks the how we got this transaction and where it was resolved
# mostly at the transaction level unless split across multiple entities
def default_transaction_flow():
    return {
        "source": [{"type": "", "id": 0}],
        "destination": [{"type": "", "id": 0}]
    }

def default_source():
    return {
        "campaign_id": 0,
        "catalog_id": None,
        "vendor_id": 0,
        "manufacturer_id": 0
    }

class BaseLineModel(BaseModel):
    parent_id = models.BigIntegerField()  # ForeignKey to parent table (use ForeignKey in concrete models)
    probability = models.IntegerField(blank=True, null=True)  # Only for proposals/requisitions
    type_sale = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    comments = models.JSONField(default=dict, blank=True, null=True)
    item = models.JSONField(default=dict, blank=True, null=True)
    # documents, not lines counts = models.JSONField(default=dict, blank=True, null=True)
    quantity = models.JSONField(default=dict, blank=True, null=True)
    cost = models.JSONField(default=dict, blank=True, null=True)
    price = models.JSONField(default=dict, blank=True, null=True)
    tax = models.JSONField(default=dict, blank=True, null=True)
    action = models.JSONField(default=dict, blank=True, null=True)
    physical = models.JSONField(default=dict, blank=True, null=True)
    flow = models.JSONField(default=dict, blank=True, null=True)
    source = models.JSONField(default=dict, blank=True, null=True)


    class Meta:
        abstract = True

    def populate_json_fields(self):
        """Populate all JSONB fields with their default structures if empty."""
        if not self.item:
            self.item = default_item()
        if not self.quantity:
            self.quantity = default_quantity(transaction_type=self._meta.model_name)
        if not self.cost:
            self.cost = default_cost()
        if not self.price:
            self.price = default_price()
        if not self.tax:
            self.tax = default_tax()
        if not self.action:
            self.action = default_action()
        if not self.physical:
            self.physical = default_physical()
        if not self.flow:
            self.flow = default_transaction_flow()
        if not self.source:
            self.source = default_source()
        self.save()

            #id_transaction = models.BigIntegerField()
    # transaction_type = models.CharField(max_length=20)
    # item_id = models.BigIntegerField()
    # uuid_item = models.CharField(max_length=255, blank=True, null=True)
    # ida_item = models.CharField(max_length=50, blank=True, null=True)
    # description = models.TextField(blank=True, null=True)
    # description_text = models.TextField(blank=True, null=True)
    # sequence = models.BigIntegerField(blank=True, null=True)
    # time_lead = models.IntegerField(blank=True, null=True)
    # location = models.CharField(max_length=255, blank=True, null=True)
    # #quantity_ordered = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    # #quantity_actioned = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    # quantity = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    # quantity_remaining = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    # #quantity_packed = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    # quantity_canceled = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)
    # quantity_is_fixed = models.BooleanField(default=False)
    # cost_unit = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # cost_extended = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # cost_is_fixed = models.BooleanField(default=False)
    # price_unit = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # price_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # price_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # price_extended = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # price_is_fixed = models.BooleanField(default=False)
    # price_precision = models.IntegerField(default=2)
    # price_manufacturer_suggested_retail = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # tax_sales_rate = models.DecimalField(max_digits=5, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # tax_sales_amount = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # tax_cost_rate = models.DecimalField(max_digits=5, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # tax_cost_amount = models.DecimalField(max_digits=12, decimal_places=2, default=BASE_DECIMAL_DEFAULT)
    # tax_jurisdiction = models.BigIntegerField(blank=True, null=True)
    # tax_code = models.CharField(max_length=40, blank=True, null=True)
    # by_created = models.CharField(max_length=50, blank=True, null=True)
    # by_updated = models.CharField(max_length=50, blank=True, null=True)
    # by_action = models.CharField(max_length=50, blank=True, null=True)
    # by_requested = models.CharField(max_length=50, blank=True, null=True)
    # transaction_flow_source_type = models.CharField(max_length=50, blank=True, null=True)
    # transaction_flow_source_id = models.BigIntegerField(blank=True, null=True)
    # transaction_flow_destination_type = models.CharField(max_length=50, blank=True, null=True)
    # transaction_flow_destination_id = models.BigIntegerField(blank=True, null=True)
    # dt_created, dt_updated, dt_expected, dt_completed go in metadata['history']

# The SQL CREATE TABLE statement below should be removed from this Python file.
# Use Django models and migrations to manage your database schema.


