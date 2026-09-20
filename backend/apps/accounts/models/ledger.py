from django.db import models

from common.models import BaseModel
from apps.accounts.choices import LEDGER_MODEL_CHOICES, LEDGER_SOURCE_CHOICES

# build up predefined metadata and refs and prefs
# capture incremental value changes
# move tables into .refs values and changes into metadata

class Ledger(BaseModel):
    """An instalment: what is owed on a document, and when it comes due.

    Bill, 2026-09-20: *"What is important about ledgers is they support complex terms by
    breaking due dates into parts."* That is the whole job. A document carries one
    balance, and one balance cannot say "half on delivery, half in sixty days, two
    percent if paid in ten". The schedule needs a row per part, each with its own due
    date, so aging can be asked by date instead of inferred.

    A row is therefore the materialized view of the term schedule crossed with the
    applications recorded in the document's ``events[]`` — not a record of its own. It is
    rebuilt when the document's total changes, which is how a projection stays true, and
    giving it its own event log would only duplicate what the document already holds
    (Bill: *"It would be a redundant audit trail"*).

    is_void / is_cleared / dt_applied / dt_journaled were removed on 2026-09-20. Only one
    place assigned them, and only their defaults (dt_journaled=0, dt_applied=None), so no
    row in 125 ever carried a meaningful value — while two were *read*: is_void filtered
    finance charges that could never be excluded, and dt_applied fed a days-average-paid
    metric that therefore scored every customer 0, which reads as "pays exactly on the
    due date" — the best score, given to the customer who never pays.
    Fields that imply a permanence the code does not keep are worse than missing ones
    (Bill: "If ledgers remain temporary, then we should delete the fields").
    """
    
    discount_potential = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, help_text="Discount rate, e.g. 0.02 for 2%")
    dt_discount_due = models.DateTimeField(blank=True, null=True)
    dt_due = models.DateTimeField(blank=True, null=True)
    # Journalizing lock — 0 means editable, non-zero epoch ms means locked
    dt_recorded = models.DateTimeField(blank=True, null=True)
    source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=LEDGER_SOURCE_CHOICES,
    )
    # Canonical model identifier
    model_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=LEDGER_MODEL_CHOICES,
    )
    # Strong linkage to parent (e.g., invoice)
    parent_id = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="Parent primary key for fast lookup")
    # Org linkage for indexed aging queries
    org = models.ForeignKey('orgs.OrgBase', blank=True, null=True, on_delete=models.SET_NULL, db_column='org_id', related_name='ledger_entries', help_text="Org (customer/vendor) for fast aging queries")
    invoice = models.ForeignKey('transactions.Invoice', blank=True, null=True, on_delete=models.SET_NULL, db_column='invoice_id')
    term = models.ForeignKey('accounts.Term', blank=True, null=True, on_delete=models.SET_NULL, db_column='term_id')
    gl_account = models.ForeignKey('accounts.GlAccount', blank=True, null=True, on_delete=models.SET_NULL, db_column='gl_account_id', help_text="GL account for FX gain/loss applied to this entry, if any")
    value_available = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Current unpaid balance (changed as cash is applied)")
    value_original = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Initial amount when created (immutable)")

    def __str__(self):
        return f"Ledger ({self.id})"

    class Meta:
        db_table = 'ledger'
        indexes = [
            models.Index(fields=['org', 'model_name'], name='idx_ledger_org_model'),
            models.Index(fields=['org', 'dt_due'], name='idx_ledger_org_due'),
        ]
    