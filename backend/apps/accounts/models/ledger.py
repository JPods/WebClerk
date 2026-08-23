from django.db import models

from common.models import BaseModel
from apps.accounts.choices import LEDGER_MODEL_CHOICES, LEDGER_SOURCE_CHOICES

# build up predefined metadata and refs and prefs
# capture incremental value changes
# move tables into .refs values and changes into metadata

class Ledger(BaseModel):
    
    discount_potential = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, help_text="Discount rate, e.g. 0.02 for 2%")
    dt_discount_due = models.DateTimeField(blank=True, null=True)
    dt_due = models.DateTimeField(blank=True, null=True)
    # Journalizing lock — 0 means editable, non-zero epoch ms means locked
    dt_journaled = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms when journalized. 0=editable, non-zero=locked.")
    dt_recorded = models.DateTimeField(blank=True, null=True)
    dt_applied = models.DateTimeField(blank=True, null=True,
        help_text="When payment was applied (settled). Record remains editable. Non-null = settled.")
    is_cleared = models.BooleanField(default=False)
    is_void = models.BooleanField(default=False)
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
    value_available = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Current unpaid balance (mutable by payments)")
    value_original = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Initial amount when created (immutable)")

    def __str__(self):
        return f"Ledger ({self.id})"

    class Meta:
        db_table = 'ledger'
        indexes = [
            models.Index(fields=['org', 'model_name'], name='idx_ledger_org_model'),
            models.Index(fields=['org', 'dt_due'], name='idx_ledger_org_due'),
        ]
    