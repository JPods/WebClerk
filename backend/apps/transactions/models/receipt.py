from django.db import models

from apps.transactions.models.base_transaction_model import (
    TransactionBaseModel, default_totals,
)

# How header landed costs are spread over the receipt's lines.
ALLOCATION_CHOICES = [
    ('value', 'By Value (cost-proportional)'),
    ('weight', 'By Weight'),
    ('quantity', 'By Quantity'),
]


def default_receipt_totals() -> dict:
    """Default totals for a Receipt — the transaction totals plus the AP leaves.

    total = Σ line totals (what we owe); vendor_invoice_amount is the vendor's claim.
    paid  = cash_out applied (the AP mirror of AR 'received').
    balance = total − paid − adjusted.
    """
    return {**default_totals(), "freight": 0, "duty": 0, "handling": 0, "vat": 0, "paid": 0}


def default_receipt_allocations() -> dict:
    """Landed costs are document-level inputs, spread over the lines by the totals
    engine — the AP mirror of a sell document's shipping and other allocations."""
    return {"freight": 0, "duty": 0, "handling": 0, "vat": 0, "method": "value"}


class Receipt(TransactionBaseModel):
    """Receipt header representing a receiving transaction.

    A receipt is created when:
    - Purchase order lines are received (from vendor)
    - Work order lines are completed (manufacturing)
    - Inventory adjustments are made (cycle count, shrinkage, etc.)

    A receipt is a transaction like any other (Bill, 2026-09-19: "more records but
    one uniform behavior"): the base carries the vendor, contact, terms, company
    snapshot, parent pointer, totals, allocations, flow and the journalized lock.
    What is left here is what only a receipt has — where it came from, its landed
    costs and the vendor's claim.

    AP cash flow: Cash (cash_out) applies to Receipt the same way
    Cash (cash_in) applies to Invoice. totals.paid / totals.balance
    mirror Invoice's totals.received / totals.balance.
    """
    # Source type for this receipt
    SOURCE_PURCHASE = 'purchase_receipt'
    SOURCE_WORKORDER = 'workorder_completion'
    SOURCE_ADJUSTMENT = 'inventory_adjustment'
    SOURCE_CHOICES = [
        (SOURCE_PURCHASE, 'Purchase Receipt'),
        (SOURCE_WORKORDER, 'WorkOrder Completion'),
        (SOURCE_ADJUSTMENT, 'Inventory Adjustment'),
    ]
    # The parent model each source receives against. An adjustment has no parent.
    SOURCE_PARENT = {
        SOURCE_PURCHASE: 'purchase',
        SOURCE_WORKORDER: 'workorder',
        SOURCE_ADJUSTMENT: None,
    }
    ALLOCATION_CHOICES = ALLOCATION_CHOICES

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default=SOURCE_PURCHASE,
        db_index=True,
        help_text="Type of receiving transaction"
    )
    dt_received = models.BigIntegerField(
        blank=True, null=True, db_index=True,
        help_text="When the goods arrived (UTC epoch ms — Axiom 14)"
    )
    vendor_invoice_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="The vendor's claim, as billed. Reconciled against totals.total "
                  "(metadata.vendor_claim) — never the total itself."
    )

    # The transaction base carries company, finance, allocations, flow, refs, status,
    # the journalized lock and the rest. A receipt keeps its own totals default, which
    # adds the AP leaves (freight, duty, handling, vat, paid) to the transaction ones,
    # and its own allocations default, which holds the landed costs.
    totals = models.JSONField(default=default_receipt_totals, blank=True, null=True,
        help_text="Σ line totals plus the AP leaves: total, freight, duty, handling, vat, paid, balance")
    allocations = models.JSONField(default=default_receipt_allocations, blank=True, null=True,
        help_text="Landed costs spread over the lines: freight, duty, handling, vat, method")

    class Meta(TransactionBaseModel.Meta):
        db_table = "receipt"
        indexes = [
            models.Index(fields=['source_type', 'dt_received']),
        ]

    # ── Parent — one pointer, the base's (parent_id + parent_model) ──────
    @property
    def parent(self):
        """The purchase or workorder this receipt received against, or None."""
        if not self.parent_id or not self.parent_model:
            return None
        from django.apps import apps as dj_apps
        try:
            model = dj_apps.get_model('transactions', self.parent_model)
        except LookupError:
            return None
        return model.objects.filter(pk=self.parent_id).first()

    def _inherit_from_parent(self):
        """A receipt carries its own vendor, contact and terms — taken from the
        purchase it receives against when they are not set. Without them there is
        no payable ledger, so this runs before every save."""
        if self.SOURCE_PARENT.get(self.source_type) != 'purchase' or not self.parent_id:
            return
        if self.vendor_id and self.terms_fk_id:
            return
        parent = self.parent
        if parent is None:
            return
        for field in ('vendor_id', 'contact_id', 'terms', 'terms_fk_id'):
            if not getattr(self, field, None):
                setattr(self, field, getattr(parent, field, None))

    def _sync_totals_from_allocations(self):
        """Echo the landed-cost inputs into the totals envelope and keep the AP
        balance true. The engine owns total (Σ lines, which include the spread
        landed costs); these leaves are the breakdown behind it."""
        alloc = self.allocations if isinstance(self.allocations, dict) else default_receipt_allocations()
        t = self.totals if isinstance(self.totals, dict) else default_receipt_totals()
        for leaf in ('freight', 'duty', 'handling', 'vat'):
            t[leaf] = float(alloc.get(leaf, 0) or 0)
        t.setdefault('total', 0)
        t.setdefault('paid', 0)
        t['balance'] = float(t.get('total', 0)) - float(t.get('paid', 0)) - float(t.get('adjusted', 0) or 0)
        self.allocations = alloc
        self.totals = t

    def save(self, *args, **kwargs):
        if not self.dt_received:
            from datetime import datetime, timezone as _tz
            self.dt_received = int(datetime.now(_tz.utc).timestamp() * 1000)
        self._inherit_from_parent()      # base save populates the company snapshot
        self._sync_totals_from_allocations()
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"R:{self.ida}" if self.ida else f"R:{self.pk}"


__all__ = ["Receipt", "default_receipt_totals", "default_receipt_allocations", "ALLOCATION_CHOICES"]
