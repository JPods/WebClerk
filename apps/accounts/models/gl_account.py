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
    
    ACCOUNT NUMBER FORMAT:
    Standard format: XXXXX-XXX-XXX (e.g., "10100-000-000")
    - First 5 digits: Account code
    - Middle 3 digits: Department/Division
    - Last 3 digits: Sub-account/Location
    
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
    account_number = models.CharField(
        max_length=50, blank=True, null=True, db_index=True,
        help_text="GL account number (e.g., '10100-000-000')")
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
        if self.account_number and self.name:
            return f"{self.account_number} - {self.name}"
        return f"{self.name or 'GlAccount'} ({self.id})"
    