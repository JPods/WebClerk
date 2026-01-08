"""Default choice lists for the transactions domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

TRANSACTION_STATUS_CHOICES: Final[ChoiceList] = (
    ("planned", "Planned"),
    ("released", "Released"),
    ("in_progress", "In Progress"),
    ("hold", "Hold"),
    ("complete", "Complete"),
    ("canceled", "Canceled"),
)

TRANSACTION_PARENT_TYPE_CHOICES: Final[ChoiceList] = (
    ("proposal", "Proposal"),
    ("sales_order", "Sales Order"),
    ("invoice", "Invoice"),
    ("purchase_order", "Purchase Order"),
    ("work_order", "Work Order"),
    ("requisition", "Requisition"),
)

PROJECT_STATUS_CHOICES: Final[ChoiceList] = (
    ("draft", "Draft"),
    ("active", "Active"),
    ("onhold", "On Hold"),
    ("blocked", "Blocked"),
    ("done", "Done"),
    ("canceled", "Canceled"),
)

PROJECT_ATTENTION_CHOICES: Final[ChoiceList] = (
    ("low", "Low"),
    ("normal", "Normal"),
    ("high", "High"),
    ("critical", "Critical"),
)

PAYMENT_GATEWAY_CHOICES: Final[ChoiceList] = (
    ("manual", "Manual"),
    ("stripe", "Stripe"),
    ("paypal", "PayPal"),
)

PAYMENT_STATUS_CHOICES: Final[ChoiceList] = (
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
    ("refunded", "Refunded"),
    ("partially_refunded", "Partially Refunded"),
)

PROJECT_LINK_MODEL_CHOICES: Final[ChoiceList] = (
    ("proposal", "Proposal"),
    ("order", "Order"),
    ("invoice", "Invoice"),
    ("purchase", "Purchase"),
    ("workorder", "WorkOrder"),
    ("requisition", "Requisition"),
)

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "TransactionBaseModel": {
        "status": TRANSACTION_STATUS_CHOICES,
        "parent_type": TRANSACTION_PARENT_TYPE_CHOICES,
    },
    "Project": {
        "status": PROJECT_STATUS_CHOICES,
        "attention": PROJECT_ATTENTION_CHOICES,
    },
    "Payment": {
        "gateway": PAYMENT_GATEWAY_CHOICES,
        "status": PAYMENT_STATUS_CHOICES,
    },
    "ProjectAssociation": {
        "model_code": PROJECT_LINK_MODEL_CHOICES,
    },
}
