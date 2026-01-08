"""Default choice lists for the products domain."""

from typing import Final, Tuple

Choice = Tuple[str, str]
ChoiceList = Tuple[Choice, ...]

ITEM_KIND_CHOICES: Final[ChoiceList] = (
    ("physical", "Physical"),
    ("service", "Service"),
    ("bundle", "Bundle"),
)

DELIVERY_VISIT_STATUS_CHOICES: Final[ChoiceList] = (
    ("planned", "Planned"),
    ("en_route", "En Route"),
    ("arrived", "Arrived"),
    ("closed", "Closed"),
    ("canceled", "Canceled"),
)

DELIVERY_LINE_STATUS_CHOICES: Final[ChoiceList] = (
    ("planned", "Planned"),
    ("loaded", "Loaded"),
    ("delivered", "Delivered"),
    ("skipped", "Skipped"),
    ("partial", "Partial"),
)

INVENTORY_CHECK_STATUS_CHOICES: Final[ChoiceList] = (
    ("planned", "Planned"),
    ("in_progress", "In Progress"),
    ("completed", "Completed"),
    ("canceled", "Canceled"),
)

INVENTORY_RESERVATION_STATE_CHOICES: Final[ChoiceList] = (
    ("pending", "Pending"),
    ("committed", "Committed"),
    ("canceled", "Canceled"),
    ("expired", "Expired"),
)

ORG_ITEM_AVAILABILITY_CHOICES: Final[ChoiceList] = (
    ("enabled", "Enabled"),
    ("paused", "Paused"),
    ("retired", "Retired"),
)

ORG_ITEM_INVENTORY_FREQUENCY_CHOICES: Final[ChoiceList] = (
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("30d", "Every 30 Days"),
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
    "DeliveryVisit": {
        "status": DELIVERY_VISIT_STATUS_CHOICES,
    },
    "DeliveryLine": {
        "status": DELIVERY_LINE_STATUS_CHOICES,
    },
    "InventoryCheck": {
        "status": INVENTORY_CHECK_STATUS_CHOICES,
    },
    "InventoryReservation": {
        "state": INVENTORY_RESERVATION_STATE_CHOICES,
    },
    "OrgItem": {
        "availability_state": ORG_ITEM_AVAILABILITY_CHOICES,
        "inventory_frequency": ORG_ITEM_INVENTORY_FREQUENCY_CHOICES,
    },
    "InventoryMovement": {
        "movement_type": INVENTORY_MOVEMENT_TYPE_CHOICES,
    },
    "PendingInventoryAdjustment": {
        "state": PENDING_INVENTORY_STATE_CHOICES,
    },
    "InventoryAdjustmentProcessorRun": {
        "run_type": PROCESSOR_RUN_TYPE_CHOICES,
    },
    "ItemXRef": {
        "source": ITEM_XREF_SOURCE_CHOICES,
    },
}
