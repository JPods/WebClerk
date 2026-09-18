from django.db import models

from common.models import BaseModel


class Budget(BaseModel):
    """
    One record per GL account per period.

    Users build complexity in their spreadsheets (what-if, formulas,
    scenarios). When they hand it to us, it's a simple number with
    a GL account and a period. Debit and credit, same as GlJournal.

    Arrives via Connection/Bundle import (audit trail on Bundle).
    Past periods lock via dt_journaled (same pattern as GlJournal).

    Alice compares Budget vs actual (GlJournal) per account per period
    — that's the retrospection/forecast accuracy loop.
    """

    period = models.CharField(
        max_length=20, db_index=True,
        help_text="Period label (e.g., 2026-10, w41_2026, q3_2026 — user-defined)")
    dt_period_start = models.BigIntegerField(
        default=0, db_index=True,
        help_text="Period start UTC epoch ms")
    dt_period_end = models.BigIntegerField(
        default=0, db_index=True,
        help_text="Period end UTC epoch ms")
    account_debit = models.CharField(
        max_length=255, db_index=True,
        help_text="GL account being debited (e.g., 6100-SALARY)")
    debit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Debit amount")
    credit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Credit amount — must equal debit for a balanced entry")
    account_credit = models.CharField(
        max_length=255, db_index=True, blank=True, default='',
        help_text="GL account being credited (e.g., 1000-CASH, 2100-ACCRUED-PAYROLL)")
    description = models.CharField(
        max_length=255, blank=True, default='')

    # Link to capital Purchase for depreciation entries
    purchase = models.ForeignKey(
        'transactions.Purchase', null=True, blank=True,
        on_delete=models.SET_NULL, db_column='purchase_id',
        related_name='depreciation_entries',
        help_text="Capital asset Purchase (depreciation entries only)")

    # Link to import Bundle for audit trail
    bundle = models.ForeignKey(
        'sync.Bundle', null=True, blank=True,
        on_delete=models.SET_NULL, db_column='bundle_id',
        related_name='budget_entries',
        help_text="Bundle that imported this entry")

    # Lock — same pattern as GlJournal: 0=editable, non-zero epoch ms=locked
    dt_journaled = models.BigIntegerField(
        default=0, db_index=True,
        help_text="UTC epoch ms when locked. 0=editable, non-zero=locked.")

    class Meta:
        db_table = 'budgets'
        indexes = [
            models.Index(fields=['period', 'account_debit'], name='idx_budget_period_acct_dr'),
            models.Index(fields=['period', 'account_credit'], name='idx_budget_period_acct_cr'),
            models.Index(fields=['dt_period_start', 'dt_period_end'], name='idx_budget_dt_range'),
            models.Index(fields=['period', 'dt_journaled'], name='idx_budget_period_locked'),
        ]

    def __str__(self):
        return f"{self.period} DR:{self.account_debit} {self.debit:+.2f} → CR:{self.account_credit} {self.credit:+.2f}"

    def save(self, *args, **kwargs):
        from apps.accounts.services.chart import require_accounts
        require_accounts((f'budget {self.period}.{f}', getattr(self, f))
                         for f in ('account_debit', 'account_credit') if getattr(self, f))
        return super().save(*args, **kwargs)
