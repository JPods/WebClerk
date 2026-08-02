from django.db import models
from typing import Callable, Dict, Any
from common.models import BaseModel
from apps.transactions.choices import (
    TRANSACTION_PARENT_MODEL_CHOICES,
    TRANSACTION_STATUS_CHOICES,
)
# FK-first: use proper ForeignKey for all entity references.
# .refs JSON is a denormalized cache updated by Celery, not the source of truth.


def default_prefs() -> Dict[str, Any]:
    return {
        "locale": "",
    }

def default_totals() -> Dict[str, Any]:
    # Header-level searchable totals (designed for frequent filtering).
    # Keep keys flat for common query patterns and indexability.
    return {
        "subtotal": 0,      # sum of line extended sell before tax/ship/discount
        "discount": 0,      # header discount amount
        "taxable": 0,       # subtotal - discount subject to tax
        "tax": 0,           # sales tax amount
        "shipping": 0,      # shipping/handling charged to customer
        "other": 0,         # misc charges
        "total": 0,         # grand total customer-facing
        "cost": 0,          # total cost (for margin compute)
        "margin": 0,        # total - cost
        "margin_pc": 0,     # (margin / total)*100 (safe on total>0)
        "received": 0,      # payments received (for invoices)
        "balance": 0,       # total - received (for invoices)
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
        "campaign_name": "",
        "catalog_id": 0,
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
    STATUS_CHOICES = TRANSACTION_STATUS_CHOICES

    PARENT_MODEL_CHOICES = TRANSACTION_PARENT_MODEL_CHOICES
    #denormalized from record.totals.total for indexing and quick queries
    total = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_index=True)
    #denormalized from record.totals.balance for indexing and quick queries
    balance = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_index=True)
    # Counter for the next line_number to assign to new lines (increments by 10)
    line_increment = models.IntegerField(default=10)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PLANNED, db_index=True)
    priority = models.CharField(max_length=32, blank=True, null=True)
    price_level = models.CharField(max_length=50, blank=True, null=True)
    dt_needed = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="Date needed (UTC epoch ms) — when customer needs the order")
    ship_via = models.CharField(max_length=50, blank=True, null=True, help_text="Carrier/shipping method (US Postal, UPS, FedEx, etc.)")
    # Commission orders routed by manufacturer (refs.links.manufacturer[].commission_based=True)
    is_commission = models.BooleanField(default=False, db_index=True, help_text="Order placed by manufacturer for commission")
    # FK-first: proper ForeignKey references to OrgBase and Contact.
    # db_column keeps same column name so existing data is preserved.
    customer = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        blank=True, null=True, db_index=True,
        db_column='customer_id', related_name='%(class)s_as_customer',
    )

    manufacturer = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        blank=True, null=True, db_index=True,
        db_column='manufacturer_id', related_name='%(class)s_as_manufacturer',
    )
    vendor = models.ForeignKey(
        'orgs.OrgBase', on_delete=models.SET_NULL,
        blank=True, null=True, db_index=True,
        db_column='vendor_id', related_name='%(class)s_as_vendor',
    )
    # parent_id is polymorphic (parent_model discriminator) — keep as integer
    parent_id = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="ID of the parent transaction")
    parent_model = models.CharField(max_length=20, choices=PARENT_MODEL_CHOICES, blank=True, null=True, db_index=True, help_text="Model of the parent transaction")

    contact = models.ForeignKey(
        'core.Contact', on_delete=models.SET_NULL,
        blank=True, null=True,
        db_column='contact_id', related_name='%(class)s_as_contact',
    )
    company = models.CharField(max_length=255, blank=True, null=True)  # optional attention line for mailing
    attention = models.CharField(max_length=255, blank=True, null=True)  # optional attention line for mailing
    address_full = models.CharField(max_length=500, blank=True, null=True)  # optional denormalized full address for quick display/search
    email = models.EmailField(blank=True, null=True)  # optional primary email (could be denormalized from emails aspect)
    phone = models.CharField(max_length=50, blank=True, null=True)  # optional primary phone (could be denormalized from phones aspect)
	# New alias property: prefer `company` in code, `display_name` remains the DB column until an explicit migration is performed.
	# Keep `display_name` as the actual DB-backed field for now for smooth migrations; provide a `company` property to use in code.
    price_level = models.CharField(max_length=30, blank=True, null=True)  # e.g. retail, wholesale; optional for future use
    terms = models.CharField(max_length=30, blank=True, null=True)  # e.g. retail, wholesale; optional for future use
    terms_fk = models.ForeignKey(
        'transactions.PaymentTerm', on_delete=models.SET_NULL,
        blank=True, null=True,
        db_column='terms_id', related_name='%(class)s_with_terms',
    )

    conditions_id = models.IntegerField(blank=True, null=True)
    conditions_description = models.CharField(max_length=255, blank=True, null=True)

    cost = models.JSONField(default=dict, blank=True, null=True)  # new: { sell:{...}, cost:{...}, margin:{...} }
    sell = models.JSONField(default=dict, blank=True, null=True)  # new: { sell:{...}, cost:{...}, margin:{...} }
    # Header-level cached totals for quick filtering and reporting. Persisted so
    # services that compute totals can save results for queries and UI display.
    totals = models.JSONField(default=default_totals, blank=True, null=True)
    finance = models.JSONField(default=dict, blank=True, null=True)
    commission = models.JSONField(default=dict, blank=True, null=True)
    flow = models.JSONField(default=dict, blank=True, null=True)
    source = models.JSONField(default=dict, blank=True, null=True)
    # Simple source attribution — one dropdown value, low friction for users.
    # Dropdown options come from bootstrap select list 'source_attribution'.
    # The .source JSON above carries rich campaign data for sophisticated tracking.
    source_name = models.CharField(max_length=80, blank=True, default='', db_index=True,
        help_text="How this transaction originated: Facebook, Referral, Walk-in, Trade Show, etc.")
    # pulled from .refs to track related entities without FK constraints; updated by Celery tasks on save
    actions = models.JSONField(default=dict, blank=True, null=True)
    
    
    # FK columns that must be NULL (not 0) when empty.  Zero would violate
    # the foreign-key constraint; negative values are never valid.
    _FK_COLUMNS = ("customer_id", "vendor_id", "manufacturer_id", "contact_id")

    def save(self, *args, **kwargs):
        # Normalise bad FK values: 0 / negative → None (NULL).
        for col in self._FK_COLUMNS:
            val = getattr(self, col, None)
            if val is not None and int(val) <= 0:
                setattr(self, col, None)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

