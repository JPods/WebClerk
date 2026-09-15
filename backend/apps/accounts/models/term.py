from django.db import models
from common.models import BaseModel


class Term(BaseModel):
    """
    Payment Terms Configuration
    ===========================
    
    Defines how invoice payments are scheduled and when they're due.
    Used by terms_ledger.compute_schedule() to create Ledger records.
    
    SCHEDULE CALCULATION:
    - Base date: invoice date (default) or dt_begin (if set)
    - Due dates: base_date + days_due (single) or staggered by days_in_period (multi)
    - Shares: 1/period_count per installment
    
    COMMON TERM PATTERNS:
    
    Net 30 (single payment, 30 days):
        period_count=1, days_due=30
        
    2% 10 Net 30 (discount for early payment):
        period_count=1, days_due=30, days_discount=10, discount_rate=2.0
        
    3-Pay 90 Days (3 installments, 30 days apart):
        period_count=3, days_in_period=30
        
    Fixed Date (payments due on specific date):
        dt_begin=2025-12-15, period_count=3, days_in_period=30
        → Due: Jan 14, Feb 13, Mar 15 (from Dec 15 start)
    
    COD / Due on Receipt:
        period_count=1, days_due=0
    """
    
    # Identification
    name = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Term code (e.g., 'N30', '2%', 'COD')")
    description = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Human-readable description (e.g., 'Net 30 Days')")
    approved_by = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Who approved this term for use")
    
    # Schedule Configuration
    period_count = models.IntegerField(
        blank=True, null=True,
        help_text="Number of payment installments (1=single payment)")
    days_due = models.IntegerField(
        blank=True, null=True,
        help_text="Days until payment due (from invoice or dt_begin)")
    days_in_period = models.IntegerField(
        blank=True, null=True,
        help_text="Days between installments (multi-period only)")
    dt_begin = models.DateField(
        blank=True, null=True,
        help_text="Fixed start date for schedule (overrides invoice date)")
    
    # Discount Configuration
    discount_rate = models.FloatField(
        blank=True, null=True,
        help_text="Early payment discount percentage (e.g., 2.0 for 2%)")
    days_discount = models.IntegerField(
        blank=True, null=True,
        help_text="Days within which discount applies")
    
    # Statement Cutoffs (for periodic billing)
    day_cut_off_invoice = models.IntegerField(
        blank=True, null=True,
        help_text="Invoice cutoff day for statement cycles")
    day_cut_off_due = models.IntegerField(
        blank=True, null=True,
        help_text="Due date cutoff day for statement cycles")

    def __str__(self):
        return f"{self.name or 'Term'} ({self.id})"

    class Meta:
        db_table = 'terms'
    