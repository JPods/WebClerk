from django.db import models
from common.models import BaseModel

# build up predefined metadata and refs and prefs
# capture incremental value changes
# move tables into .refs values and changes into metadata

class Ledger(BaseModel):
    
    discount_potential = models.FloatField(blank=True, null=True)
    dt_discount_due = models.DateTimeField(blank=True, null=True)
    dt_due = models.DateTimeField(blank=True, null=True)
    dt_posted = models.DateTimeField(blank=True, null=True)
    dt_recorded = models.DateTimeField(blank=True, null=True)
    dt_settled = models.DateTimeField(blank=True, null=True)
    is_settled = models.BooleanField(default=False)
    is_cleared = models.BooleanField(default=False)
    is_void = models.BooleanField(default=False)
    source = models.CharField(max_length=255, blank=True, null=True)
    # Canonical model identifier
    model_name = models.CharField(max_length=255, blank=True, null=True)
    # Strong linkage to parent (e.g., invoice)
    parent_id = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="Parent primary key for fast lookup")
    invoice = models.ForeignKey('transactions.Invoice', blank=True, null=True, on_delete=models.SET_NULL, db_column='invoice_id')
    term = models.ForeignKey('accounts.Term', blank=True, null=True, on_delete=models.SET_NULL, db_column='term_id')
    gl_account_fx_variance = models.ForeignKey('accounts.Gl_account', blank=True, null=True, on_delete=models.SET_NULL, db_column='gl_fx_variance_id', help_text="GL account for FX gain/loss applied to this entry, if any")
    value_available = models.FloatField(blank=True, null=True)
    value_original = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Ledger ({self.id})"

    class Meta:
        db_table = 'ledger'
    