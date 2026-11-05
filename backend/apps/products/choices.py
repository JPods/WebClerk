"""Default choice lists for the products domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

ITEM_KIND_CHOICES: Final[ChoiceList] = (
    ("physical", "Physical"),
    ("service", "Service"),
    ("bundle", "Bundle"),
)

INVENTORY_MOVEMENT_TYPE_CHOICES: Final[ChoiceList] = (
    ("receipt", "Receipt"),
    ("issue", "Issue"),
    ("adjust", "Adjust"),
)

PENDING_INVENTORY_STATE_CHOICES: Final[ChoiceList] = (
    ("pending", "Pending"),
    ("applied", "Applied"),
    ("canceled", "Canceled"),
)

PROCESSOR_RUN_TYPE_CHOICES: Final[ChoiceList] = (
    ("global", "Global"),
    ("stack", "Stack"),
)

ITEM_XREF_SOURCE_CHOICES: Final[ChoiceList] = (
    ("manufacturer", "Manufacturer"),
    ("wholesaler", "Wholesaler"),
    ("other", "Other"),
)
