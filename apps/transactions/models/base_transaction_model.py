from django.db import models
from typing import Callable, Dict, Any
from common.models import BaseModel
from apps.transactions.choices import (
    TRANSACTION_PARENT_TYPE_CHOICES,
    TRANSACTION_STATUS_CHOICES,
)


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


def default_sell() -> Dict[str, Any]:
    """Default sell envelope for transaction header.
    Mirrors cost structure for sell-side aggregates.
    """
    return {
        "line_sum_goods": None,
        "line_sum_tax": None,
        "line_sum_shipping": None,
        "line_sum_handling": None,
        "handling": None,
        "freight": None,
        "tax_rate": None,
        "tax": None,
        "discount": None,
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
    #tax_service_id is used to link to tax engine records.
    return {
        "sales_rate": None,
        "sales": None,
        "cost_rate": None,
        "cost": None,
        "shipping": None,
        "tax_service_id": 0,
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
    Defines JSON_DEFAULT_FACTORIES for transaction-specific fields; BaseModel.save()
    automatically populates them via ensure_json_defaults().
    """

    STATUS_PLANNED = "planned"
    STATUS_RELEASED = "released"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_HOLD = "hold"
    STATUS_COMPLETE = "complete"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = TRANSACTION_STATUS_CHOICES

    PARENT_TYPE_CHOICES = TRANSACTION_PARENT_TYPE_CHOICES
    #denormalized from record.totals.total for indexing and quick queries
    total = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_index=True)
    #denormalized from record.totals.balance for indexing and quick queries
    balance = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PLANNED, db_index=True)
    priority = models.CharField(max_length=32, blank=True, null=True)
    price_level = models.CharField(max_length=50, blank=True, null=True)
    terms = models.CharField(max_length=128, blank=True, null=True, help_text="Payment terms")
    po_number = models.CharField(max_length=128, blank=True, null=True, help_text="Customer PO number")
    customer_id = models.BigIntegerField(default=0, db_index=True)
    manufacturer_id = models.BigIntegerField(default=0, db_index=True)
    vendor_id = models.BigIntegerField(default=0, db_index=True)
    parent_id = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="ID of the parent transaction")
    parent_type = models.CharField(max_length=20, choices=PARENT_TYPE_CHOICES, blank=True, null=True, db_index=True, help_text="Type of the parent transaction")
    cost = models.JSONField(default=dict, blank=True, null=True)  # new: { sell:{...}, cost:{...}, margin:{...} }
    sell = models.JSONField(default=dict, blank=True, null=True)  # new: { sell:{...}, cost:{...}, margin:{...} }
    # Header-level cached totals for quick filtering and reporting. Persisted so
    # services that compute totals can save results for queries and UI display.
    totals = models.JSONField(default=default_totals, blank=True, null=True)
    finance = models.JSONField(default=dict, blank=True, null=True)
    flow = models.JSONField(default=dict, blank=True, null=True)
    source = models.JSONField(default=dict, blank=True, null=True)
    action = models.JSONField(default=dict, blank=True, null=True)

    # Factory functions for transaction-specific JSON fields.
    # BaseModel.save() collects these from the MRO and auto-populates on save.
    JSON_DEFAULT_FACTORIES: Dict[str, Callable[[], Dict[str, Any]]] = {
        "totals": default_totals,
        "cost": default_cost,
        "sell": default_sell,
        "finance": default_finance,
        "flow": default_transaction_flow,
        "source": default_source,
        "action": default_action,
    }

    class Meta:
        abstract = True

