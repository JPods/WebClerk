from django.db import models

from common.models import BaseModel
from apps.accounts.choices import (
    GL_ACCOUNT_CATEGORY_CHOICES,
    GL_ACCOUNT_TYPE_CHOICES,
    GL_ACCOUNT_USAGE_CHOICES,
)

class GlAccount(BaseModel):
    """
    General Ledger Account
    ======================

    Represents an account in the chart of accounts.
    ida is the sole account identifier (e.g., '1000-Cash', '1100-AR', '2000-AP').

    ACCOUNT TYPES:
    - asset: Current Asset, Fixed Asset
    - liability: Current Liability, Long-term Liability
    - equity: Owner's Equity, Retained Earnings
    - revenue: Sales, Income
    - expense: Cost of Sales, Operating Expense
    - contra: Contra accounts (discounts, returns)

    CATEGORIES:
    - cash: Cash and cash equivalents
    - receivables: A/R, notes receivable
    - payables: A/P, accrued liabilities
    - inventory: Inventory accounts
    - sales: Revenue accounts
    - cogs: Cost of goods sold
    - expense: Operating expenses
    """
    
    # Primary identification
    name = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Account name (e.g., 'Cash', 'Accounts Receivable')")
    
    # Classification
    type = models.CharField(
        max_length=255, blank=True, null=True,
        choices=GL_ACCOUNT_TYPE_CHOICES,
        help_text="Account type (asset, liability, equity, revenue, expense)")
    category = models.CharField(
        max_length=255, blank=True, null=True,
        choices=GL_ACCOUNT_CATEGORY_CHOICES,
        help_text="Account category for grouping")
    type_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Product type/category ID for sales/COGS accounts")
    
    # Journal mapping (for default debit/credit accounts)
    account_credit = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Default credit account for journal entries")
    account_debit = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Default debit account for journal entries")
    
    # Usage and status
    used_for = models.CharField(
        max_length=255, blank=True, null=True,
        choices=GL_ACCOUNT_USAGE_CHOICES,
        help_text="Account usage classification")
    division = models.IntegerField(
        blank=True, null=True,
        help_text="Division/department code")
    comment = models.TextField(
        blank=True, null=True,
        help_text="Notes or description")

    class Meta:
        db_table = 'gl_accounts'

    def __str__(self):
        return self.ida or self.name or f'GlAccount ({self.id})'

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    