"""Default choice lists for the products domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

ITEM_KIND_CHOICES: Final[ChoiceList] = (
    ("physical", "Physical"),
    ("service", "Service"),
    ("bundle", "Bundle"),
)

INVENTORY_RESERVATION_STATE_CHOICES: Final[ChoiceList] = (
    ("pending", "Pending"),
    ("committed", "Committed"),
    ("canceled", "Canceled"),
    ("expired", "Expired"),
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

DEFAULT_SELECT_LISTS: Final[dict[str, dict[str, ChoiceList]]] = {
    "Item": {
        "kind": ITEM_KIND_CHOICES,
    },
    "InventoryReservation": {
        "state": INVENTORY_RESERVATION_STATE_CHOICES,
    },
    "InventoryMovement": {
        "movement_type": INVENTORY_MOVEMENT_TYPE_CHOICES,
    },
    "InventoryAdjustmentProcessorRun": {
        "run_type": PROCESSOR_RUN_TYPE_CHOICES,
    },
    "ItemXRef": {
        "source": ITEM_XREF_SOURCE_CHOICES,
    },
}
