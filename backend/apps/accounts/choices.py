"""Default choice lists for the accounts domain.

These enumerations seed tenant-level settings and keep model defaults
coordinated without hard-coding lists in multiple places. Service teams can
extend or replace them per tenant when synchronizing settings records.
"""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

GL_ACCOUNT_TYPE_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("asset", "Asset"),
    ("liability", "Liability"),
    ("equity", "Equity"),
    ("revenue", "Revenue"),
    ("expense", "Expense"),
    ("contra", "Contra"),
)

GL_ACCOUNT_CATEGORY_CHOICES: Final[ChoiceList] = (
    ("cash", "Cash"),
    ("receivables", "Accounts Receivable"),
    ("prepaid", "Prepaid"),
    ("payables", "Accounts Payable"),
    ("tax", "Tax"),
    ("inventory", "Inventory"),
    ("fixed_assets", "Fixed Assets"),
    ("depreciation", "Depreciation"),
    ("equity", "Equity"),
    ("sales", "Sales"),
    ("contra", "Contra Revenue"),
    ("cogs", "Cost of Goods Sold"),
    ("expense", "Expense"),
    ("payroll", "Payroll"),
    ("other", "Other"),
)

# used_for: how the account is used. The role words (cash, receivables, ...)
# are what the chart actually stores; posting/reporting are the general cases.
# The model validates on save, so a stored value missing here blocks every edit.
GL_ACCOUNT_USAGE_CHOICES: Final[ChoiceList] = (
    ("posting", "Posting"),
    ("reporting", "Reporting (computed, never posted)"),
    ("cash", "Cash"),
    ("receivables", "Receivables"),
    ("payables", "Payables"),
    ("inventory", "Inventory"),
    ("sales", "Sales"),
    ("discounts", "Discounts"),
    ("cogs", "Cost of Goods Sold"),
    ("expense", "Expense"),
    ("tax", "Tax"),
    ("consolidation", "Consolidation"),
    ("other", "Other"),
)

GL_JOURNAL_SOURCE_CHOICES: Final[ChoiceList] = (
    ("manual", "Manual Entry"),
    ("import", "Imported"),
    ("automation", "Automation"),
    ("adjustment", "Adjustment"),
    ("integration", "Integration"),
)

GL_JOURNAL_TYPE_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("general", "General"),
    ("sales", "Sales"),
    ("purchase", "Purchase"),
    ("payroll", "Payroll"),
    ("inventory", "Inventory"),
    ("other", "Other"),
)

EROSION_CATEGORY_CHOICES: Final[ChoiceList] = (
    ("margin", "Margin Erosion"),
    ("discount", "Discount Given"),
    ("fx_loss", "Currency / FX Loss"),
    ("late_payment", "Late Payment Carrying Cost"),
    ("return_credit", "Return / Credit"),
    ("rework", "Rework / Warranty"),
    ("shipping", "Shipping / Freight"),
    ("bad_debt", "Bad Debt Write-Off"),
    ("price_override", "Price Override"),
    ("other", "Other"),
)

EROSION_SOURCE_MODEL_CHOICES: Final[ChoiceList] = (
    ("proposal", "Proposal"),
    ("order", "Order"),
    ("invoice", "Invoice"),
    ("purchase", "Purchase"),
    ("cash", "Cash"),
    ("credit_memo", "Credit Memo"),
    ("action", "Action"),
    ("question_answer", "Question / Answer"),
)

LEDGER_SOURCE_CHOICES: Final[ChoiceList] = (
    ("invoice", "Invoice"),
    ("cash", "Cash"),
    ("journal", "Journal Entry"),
    ("adjustment", "Adjustment"),
    ("import", "Imported"),
    ("other", "Other"),
)

LEDGER_MODEL_CHOICES: Final[ChoiceList] = (
    ("invoice", "Invoice"),
    ("credit_memo", "Credit Memo"),
    ("debit_memo", "Debit Memo"),
    ("purchase", "Purchase"),
    ("cash", "Cash"),
    ("other", "Other"),
)

TAX_SERVICE_PROVIDER_CHOICES: Final[ChoiceList] = (
    ("", "Unspecified"),
    ("avalara", "Avalara"),
    ("taxjar", "TaxJar"),
    ("vertex", "Vertex"),
    ("custom", "Custom"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "GlAccount": {
        "type": GL_ACCOUNT_TYPE_CHOICES,
        "category": GL_ACCOUNT_CATEGORY_CHOICES,
        "used_for": GL_ACCOUNT_USAGE_CHOICES,
    },
    "GlJournal": {
        "source": GL_JOURNAL_SOURCE_CHOICES,
        "type": GL_JOURNAL_TYPE_CHOICES,
    },
    "Erosion": {
        "category": EROSION_CATEGORY_CHOICES,
        "source_model": EROSION_SOURCE_MODEL_CHOICES,
        "parent_model": EROSION_SOURCE_MODEL_CHOICES,
    },
    "Ledger": {
        "source": LEDGER_SOURCE_CHOICES,
        "model_name": LEDGER_MODEL_CHOICES,
    },
    "TaxJurisdiction": {
        "service_provider": TAX_SERVICE_PROVIDER_CHOICES,
    },
}
