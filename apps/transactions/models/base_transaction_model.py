from django.db import models
from typing import Callable, Dict, Any
from common.models import BaseModel


def default_prefs() -> Dict[str, Any]:
    return {
        "locale": "",
    }

def default_totals() -> Dict[str, Any]:
    # Header-level searchable totals (designed for frequent filtering).
    # Keep keys flat for common query patterns and indexability.
    return {
        "subtotal": None,   # sum of line extended sell before tax/ship/discount
        "discount": None,   # header discount amount
        "taxable": None,    # subtotal - discount subject to tax
        "tax": None,        # sales tax amount
        "shipping": None,   # shipping/handling charged to customer
        "other": None,      # misc charges
        "total": None,      # grand total customer-facing
        "cost": None,       # total cost (for margin compute)
        "margin": None,     # total - cost
        "margin_pc": None,  # (margin / total)*100 (safe on total>0)
        "received": None,   # payments received (for invoices)
        "balance": None,    # total - received (for invoices)
    }


def default_cost() -> Dict[str, Any]:
    return {
        "line_sum_goods": None,
        "line_sum_tax": None,
        "line_sum_shipping": None,
        "line_sum_handling": None,
        "handling": None,
        "freight": None,
        "tax_rate": None,
        "tax": None,
        "commissions": None,
        "total": None
        }


def default_finance() -> Dict[str, Any]:
    return {
        "sales_tax_id": 0,
        "sales_tax_name": "",
        "sales_tax_rate": None,
        "sales_tax": None,
        "cost_tax_id": 0,
        "cost_tax_name": "",
        "cost_tax_rate": None,
        "cost_tax": None,
        "tax_subtotal": None,
        "tax_pc":None,
        "collection_expense": None,
        "exchange_expense": None
    }


def default_tax() -> Dict[str, Any]:
    # Legacy helper retained for line-model imports; kept minimal.
    return {
        "sales_rate": None,
        "sales": None,
        "cost_rate": None,
        "cost": None,
        "shipping": None,
    }


## QQQ keep separate, move history to .metadata.history
def default_action() -> Dict[str, Any]:
    return {
        "action_next":{"who":"","when":0,"what":""}
    }

# tracks the how we got this transaction and where it was resolved
# mostly at the transaction level unless split across multiple entities
def default_transaction_flow() -> Dict[str, Any]:
    return {
        #QQQ change to parent move to refs??
        "source": [{"type": "", "id": 0}],
        # QQQ add children may be PO
        "children": [{"type": "", "id": 0}]
        # "destination": [{"type": "", "id": 0}]
    }

def default_source() -> Dict[str, Any]:
    return {
        "campaign_id": 0,
        "catalog_id": None,
        "vendor_id": 0,
        "manufacturer_id": 0
    }


class TransactionBaseModel(BaseModel):
    """Abstract Django base for transaction headers.

    Minimal fields only; JSON envelopes and lifecycle come from common.BaseModel.
    """

    STATUS_PLANNED = "planned"
    STATUS_RELEASED = "released"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_HOLD = "hold"
    STATUS_COMPLETE = "complete"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = (
        (STATUS_PLANNED, "Planned"),
        (STATUS_RELEASED, "Released"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_HOLD, "Hold"),
        (STATUS_COMPLETE, "Complete"),
        (STATUS_CANCELED, "Canceled"),
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PLANNED, db_index=True)
    priority = models.CharField(max_length=32, blank=True, null=True)
    price_level = models.CharField(max_length=50, blank=True, null=True)
    id_customer = models.BigIntegerField(default=0, db_index=True)
    id_manufacturer = models.BigIntegerField(default=0, db_index=True)
    id_vendor = models.BigIntegerField(default=0, db_index=True)
    cost = models.JSONField(default=dict, blank=True, null=True)  # new: { sell:{...}, cost:{...}, margin:{...} }
    sell = models.JSONField(default=dict, blank=True, null=True)  # new: { sell:{...}, cost:{...}, margin:{...} }
    finance = models.JSONField(default=dict, blank=True, null=True)
    flow = models.JSONField(default=dict, blank=True, null=True)
    source = models.JSONField(default=dict, blank=True, null=True)
    action = models.JSONField(default=dict, blank=True, null=True)
    
    
    class Meta:
        abstract = True

