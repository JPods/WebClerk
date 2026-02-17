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
    ("payables", "Accounts Payable"),
    ("inventory", "Inventory"),
    ("sales", "Sales"),
    ("cogs", "Cost of Goods Sold"),
    ("expense", "Expense"),
    ("other", "Other"),
)

GL_ACCOUNT_USAGE_CHOICES: Final[ChoiceList] = (
    ("posting", "Posting"),
    ("reporting", "Reporting"),
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

LEDGER_SOURCE_CHOICES: Final[ChoiceList] = (
    ("invoice", "Invoice"),
    ("payment", "Payment"),
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
    ("payment", "Payment"),
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
    "Ledger": {
        "source": LEDGER_SOURCE_CHOICES,
        "model_name": LEDGER_MODEL_CHOICES,
    },
    "TaxJurisdiction": {
        "service_provider": TAX_SERVICE_PROVIDER_CHOICES,
    },
}
