from django.db import models
from django.utils.timezone import now as django_now

from common.models import BaseModel


CLASSIFICATION_CHOICES = [
    ('unknown', 'Unknown'),
    ('business', 'Business'),
    ('personal', 'Personal'),
]

LEDGER_CHOICES = [
    ('post', 'Post'),        # create GL entries when promoted to Payment
    ('skip', 'Skip'),        # already accounted for elsewhere — no GL
    ('review', 'Review'),    # not sure — flag for admin decision
]


class StatementLine(BaseModel):
    """One line from a bank or credit card statement.

    Staging table for statement import → categorize → promote to Payment.
    Alice learns merchant patterns from user corrections.
    """

    class Meta:
        db_table = "statement_lines"
        ordering = ['-dt_transaction']

    # Raw statement data
    dt_transaction = models.DateTimeField(null=True, blank=True, default=django_now,
        help_text="Transaction date from statement")
    description = models.CharField(max_length=500, blank=True,
        help_text="Raw description from statement (merchant name, memo, etc.)")
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
        help_text="Signed amount from statement. Negative=charge, positive=credit/refund.")
    raw_text = models.TextField(blank=True,
        help_text="Full original line from import (CSV row, OFX record, OCR text)")

    # Statement source
    source = models.CharField(max_length=200, blank=True,
        help_text="Bank or card name: chase_visa_3425, wellsfargo_checking, etc.")
    statement_date = models.DateField(null=True, blank=True,
        help_text="Statement period date (month-end)")
    batch_id = models.CharField(max_length=100, blank=True, db_index=True,
        help_text="Import batch ID — groups lines from one import")

    # User classification
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES,
        default='unknown', db_index=True,
        help_text="business, personal, or unknown. User sets, Alice suggests.")
    category = models.CharField(max_length=100, blank=True,
        help_text="Expense category — same select list as Payment.category")
    merchant = models.CharField(max_length=200, blank=True,
        help_text="Resolved merchant name (cleaned from description)")
    ledger = models.CharField(max_length=10, choices=LEDGER_CHOICES,
        default='post', db_index=True,
        help_text="post=hit GL on promote, skip=already ledgered elsewhere, review=admin decides")

    # Links
    contact = models.ForeignKey('core.Contact', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='statement_lines', db_column='contact_id',
        help_text="Resolved vendor/merchant contact")
    vendor = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='statement_lines', db_column='vendor_id',
        help_text="Resolved vendor org")

    # Promotion tracking
    promoted = models.BooleanField(default=False, db_index=True,
        help_text="True = already created a Payment record from this line")
    payment_id = models.BigIntegerField(null=True, blank=True,
        help_text="Payment record ID created from this line")

    def __str__(self):
        return f"{self.dt_transaction:%Y-%m-%d} {self.description[:40]} {self.amount:+.2f}"


__all__ = ["StatementLine"]
