from decimal import Decimal
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


def default_shipping() -> Dict[str, Any]:
    """Shipping envelope — tracks packages, carrier, costs, and fulfillment status.

    WC2 lineage: LoadTag (container) + LoadItem (item-in-container).
    WC3: single JSON envelope on transaction header. packages[] replaces LoadTag table,
    each package.items[] replaces LoadItem table.

    Hierarchy: item → package (box) → pallet → shipment.
    A package with type="pallet" contains child package IDs, not items directly.
    """
    return {
        "status": "",                # "" | partial | shipped | delivered
        "carrier": "",               # UPS, FedEx, USPS, freight, etc.
        "carrier_account": "",       # carrier account number (3rd party billing)
        "service": "",               # Ground, 2Day, NextDay, etc.
        "ship_to": {},               # snapshot of shipping address at time of ship
        "packages": [
            # Each package is a LoadTag equivalent:
            # {
            #     "id": "uuid or sequential",
            #     "type": "box",           # box | pallet | container
            #     "parent_id": "",         # pallet ID if this box is on a pallet
            #     "tracking": "",          # carrier tracking number
            #     "status": "packed",      # packed | shipped | delivered
            #     "weight": {
            #         "gross": 0.0,        # total weight (product + tare)
            #         "tare": 0.0,         # packaging weight
            #         "unit": "lbs"
            #     },
            #     "dimensions": {
            #         "length": 0.0, "width": 0.0, "height": 0.0, "unit": "in"
            #     },
            #     "value": 0.0,            # declared value for insurance
            #     "insured": False,
            #     "costs": {
            #         "freight": 0.0,
            #         "fuel_surcharge": 0.0,
            #         "insurance": 0.0,
            #         "handling": 0.0,
            #         "total": 0.0
            #     },
            #     "dt_packed": "",         # ISO 8601 UTC
            #     "dt_shipped": "",        # ISO 8601 UTC
            #     "items": [
            #         # Each item is a LoadItem equivalent:
            #         # {
            #         #     "line_number": 10,       # matches invoice/order line_number
            #         #     "item_id": 0,            # FK to Item
            #         #     "item_ida": "",           # item ida for display
            #         #     "description": "",
            #         #     "qty": 0,
            #         #     "unit_weight": 0.0,
            #         #     "extended_weight": 0.0,
            #         #     "is_dunnage": False,      # packing material, not product
            #         #     "hazmat_class": ""
            #         # }
            #     ],
            #     "child_ids": []          # for pallets: list of box package IDs
            # }
        ],
        "costs": {                   # header-level shipping cost summary
            "freight": 0.0,          # base carrier freight
            "fuel_surcharge": 0.0,
            "insurance": 0.0,
            "handling": 0.0,
            "estimated": 0.0,        # pre-ship estimate
            "actual": 0.0,           # what we paid the carrier
            "customer": 0.0          # what we charge the customer (→ totals.shipping)
        },
        "weight": {                  # header-level weight summary
            "gross": 0.0,
            "unit": "lbs"
        },
        "package_count": 0,
        "dt_shipped": "",            # ISO 8601 UTC — when last package shipped
        "dt_delivered": "",          # ISO 8601 UTC — carrier delivery confirmation
        "notes": ""
    }


class TransactionBaseModel(BaseModel):
    """Abstract Django base for transaction headers.

    Minimal fields only; JSON envelopes and lifecycle come from common.BaseModel.

    Totals: ONE engine — recalculate_totals() in services/totals.py.
    JSON is the source of truth. Denormalized total/balance are indexes into it.
    """

    def update_sell_cost_totals(self, persist: bool = True) -> dict:
        """Recompute all totals from line data using the single totals engine.

        JSON is computed from line data. Display values are projections of JSON.
        Never the reverse.
        """
        from apps.transactions.services.totals import recalculate_totals
        model_name = self._meta.model_name
        # recalculate_totals always persists — persist param is accepted but
        # currently ignored (TODO: add dry_run mode to recalculate_totals)
        result = recalculate_totals(self.pk, model_name)
        self.refresh_from_db(fields=['totals'])
        return result

    STATUS_PLANNED = "planned"
    STATUS_SIGNOFF_REQUEST = "signoff_request"
    STATUS_RELEASED = "released"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_HOLD = "hold"
    STATUS_COMPLETE = "complete"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = TRANSACTION_STATUS_CHOICES

    PARENT_MODEL_CHOICES = TRANSACTION_PARENT_MODEL_CHOICES
    # total and balance removed — read from totals JSON envelope (PJPV)
    # Functional indexes on totals->>'total' and totals->>'balance' handle queries.
    # Counter for the next line_number to assign to new lines (increments by 10)
    line_increment = models.IntegerField(default=10)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PLANNED, db_index=True)
    priority = models.CharField(max_length=32, blank=True, null=True)
    price_level = models.CharField(max_length=50, blank=True, default='retail')
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
    attention = models.CharField(max_length=255, blank=True, null=True)  # optional attention line for mailing
    # company, address_full, email, phone removed — read from contact FK or refs.links (PJPV)
    price_level = models.CharField(max_length=30, blank=True, default='retail')
    terms = models.CharField(max_length=30, blank=True, null=True)  # e.g. retail, wholesale; optional for future use
    terms_fk = models.ForeignKey(
        'transactions.PaymentTerm', on_delete=models.SET_NULL,
        blank=True, null=True,
        db_column='terms_id', related_name='%(class)s_with_terms',
    )

    conditions_id = models.IntegerField(blank=True, null=True)
    conditions_description = models.CharField(max_length=255, blank=True, null=True)

    # Journalizing lock — 0 means editable, non-zero epoch ms means locked (GL has this data)
    dt_journaled = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms when journalized to GL. 0=editable, non-zero=locked.")

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
    shipping = models.JSONField(default=default_shipping, blank=True, null=True)

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

    # ── Read-only properties — replaced scalar shadow fields ────────
    # These read from the JSON envelope or FK relationships.
    # Used by admin list_display and serializers.

    @property
    def total(self):
        t = self.totals if isinstance(self.totals, dict) else {}
        val = t.get('total')
        return Decimal(str(val)) if val is not None else None

    @property
    def balance(self):
        t = self.totals if isinstance(self.totals, dict) else {}
        val = t.get('balance')
        return Decimal(str(val)) if val is not None else None

    @property
    def company(self):
        if self.customer_id:
            return getattr(self.customer, 'display_name', '') if self.customer else ''
        refs = self.refs if isinstance(self.refs, dict) else {}
        links = refs.get('links', {})
        cust = links.get('customer', {})
        return cust.get('display_name', '')

    @property
    def address_full(self):
        refs = self.refs if isinstance(self.refs, dict) else {}
        links = refs.get('links', {})
        for role in ('customer', 'vendor', 'manufacturer'):
            r = links.get(role, {})
            if r.get('address_full'):
                return r['address_full']
        return ''

    @property
    def email(self):
        if self.contact_id and self.contact:
            return self.contact.email or ''
        refs = self.refs if isinstance(self.refs, dict) else {}
        links = refs.get('links', {})
        for role in ('customer', 'vendor', 'manufacturer'):
            r = links.get(role, {})
            if r.get('email'):
                return r['email']
        return ''

    @property
    def phone(self):
        refs = self.refs if isinstance(self.refs, dict) else {}
        links = refs.get('links', {})
        for role in ('customer', 'vendor', 'manufacturer'):
            r = links.get(role, {})
            if r.get('phone'):
                return r['phone']
        return ''

    class Meta:
        abstract = True

