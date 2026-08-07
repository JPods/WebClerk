"""
Pydantic schemas for Serial JSON envelopes.

Serial.config carries transaction context (who holds the unit, what document
moved it, cost/price at time of transaction).

Serial actions are defined in Setting.serial and validated here. Full words,
no codes -- WC2 used cryptic 2-letter status codes (Av, Iv, Vo, RTV, PA, PS,
PI, PR). WC3 uses complete words everywhere.

WC2 lineage: [ItemSerial] + [ItemSerialAction] tables.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import MetadataBase, RecordPrefsBase, RefsBase


# -- Serial actions (stored in Setting.serial.config.serial_actions) -------

class SerialAction(BaseModel):
    """One action that can be performed on a serial number.

    Stored in Setting record ida='serial' as config.serial_actions[].
    Each action defines: what it's called, what status it produces,
    what document type triggers it, and whether it's reversible.
    """
    name: str = Field(..., description="Full sentence action name: 'Received on purchase order', 'Issued in invoice'")
    status_result: str = Field(..., description="Status the serial moves to after this action: available, received, reserved, issued, returned, referenced, warranty, damaged, scrapped")
    document_type: str = Field("", description="Document type that triggers this action: order, invoice, purchase, work_order, or empty for manual")
    direction: str = Field("", description="Movement direction: inbound (receiving), outbound (shipping/issuing), internal (status change only), or empty")
    clears_customer: bool = Field(False, description="Whether this action clears customer assignment (returns, voids)")
    clears_vendor: bool = Field(False, description="Whether this action clears vendor assignment")
    starts_warranty: bool = Field(False, description="Whether this action starts the warranty clock")
    ends_warranty: bool = Field(False, description="Whether this action ends warranty tracking")
    captures_cost: bool = Field(False, description="Whether cost should be recorded at time of action")
    captures_price: bool = Field(False, description="Whether price/discount should be recorded at time of action")
    is_reversible: bool = Field(True, description="Whether this action can be undone")
    reverse_action: str = Field("", description="Name of the action that reverses this one")
    requires_document: bool = Field(False, description="Whether a document reference is required")
    notes_required: bool = Field(False, description="Whether notes are required for this action")

    class Config:
        extra = "allow"


class SerialActionList(BaseModel):
    """The full list of serial actions. Stored in Setting.serial.config."""
    serial_actions: list[SerialAction] = Field(default_factory=list)

    class Config:
        extra = "allow"


# -- Serial.config (transaction context on the serial record) ---------------

class FloorPlan(BaseModel):
    is_active: bool = False
    dt_expires: Optional[str] = None
    plan_line: Optional[int] = None

    class Config:
        extra = "allow"


class SerialConfig(BaseModel):
    """Transaction context stored on each Serial record.

    Tracks who holds this unit, what document moved it, and what it
    cost at time of transaction. Updated by lifecycle methods on the
    Serial model (receive, issue_on_invoice, return_from_customer, etc).
    """
    customer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    invoice_id: Optional[int] = None
    order_id: Optional[int] = None
    purchase_id: Optional[int] = None
    sales_line_ref: Optional[int] = None
    purchase_line_ref: Optional[int] = None
    cost: float = 0.0
    price: float = 0.0
    discount: float = 0.0
    dt_received: Optional[str] = None
    dt_shipped: Optional[str] = None
    days_on_plan: int = 0
    floor_plan: FloorPlan = Field(default_factory=FloorPlan)

    class Config:
        extra = "allow"


# -- Serial.metadata -------------------------------------------------------

class SerialMetadata(MetadataBase):
    pass


# -- Serial.prefs ----------------------------------------------------------

class SerialPrefs(RecordPrefsBase):
    pass


# -- Serial.refs -----------------------------------------------------------

class SerialRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


# -- Default serial actions (seeded into Setting.serial) -------------------

DEFAULT_SERIAL_ACTIONS: list[dict] = [
    {
        "name": "Received on purchase order",
        "status_result": "received",
        "document_type": "purchase",
        "direction": "inbound",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": True,
        "captures_price": False,
        "is_reversible": True,
        "reverse_action": "Voided from purchase order",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Made available",
        "status_result": "available",
        "document_type": "",
        "direction": "internal",
        "clears_customer": True,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": False,
        "reverse_action": "",
        "requires_document": False,
        "notes_required": False,
    },
    {
        "name": "Reserved for order",
        "status_result": "reserved",
        "document_type": "order",
        "direction": "outbound",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": True,
        "is_reversible": True,
        "reverse_action": "Removed from order",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Issued in invoice",
        "status_result": "issued",
        "document_type": "invoice",
        "direction": "outbound",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": True,
        "ends_warranty": False,
        "captures_cost": True,
        "captures_price": True,
        "is_reversible": True,
        "reverse_action": "Returned from customer",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Returned from customer",
        "status_result": "returned",
        "document_type": "invoice",
        "direction": "inbound",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": True,
        "reverse_action": "Issued in invoice",
        "requires_document": False,
        "notes_required": True,
    },
    {
        "name": "Removed from order",
        "status_result": "available",
        "document_type": "order",
        "direction": "internal",
        "clears_customer": True,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": False,
        "reverse_action": "",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Removed from invoice",
        "status_result": "available",
        "document_type": "invoice",
        "direction": "internal",
        "clears_customer": True,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": True,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": False,
        "reverse_action": "",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Voided from purchase order",
        "status_result": "available",
        "document_type": "purchase",
        "direction": "internal",
        "clears_customer": False,
        "clears_vendor": True,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": False,
        "reverse_action": "",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Return to vendor",
        "status_result": "available",
        "document_type": "purchase",
        "direction": "outbound",
        "clears_customer": False,
        "clears_vendor": True,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": True,
        "reverse_action": "Received on purchase order",
        "requires_document": True,
        "notes_required": True,
    },
    {
        "name": "Referenced in document",
        "status_result": "referenced",
        "document_type": "",
        "direction": "internal",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": True,
        "reverse_action": "Made available",
        "requires_document": True,
        "notes_required": False,
    },
    {
        "name": "Warranty claim opened",
        "status_result": "warranty",
        "document_type": "",
        "direction": "internal",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": True,
        "reverse_action": "Made available",
        "requires_document": False,
        "notes_required": True,
    },
    {
        "name": "Marked as damaged",
        "status_result": "damaged",
        "document_type": "",
        "direction": "internal",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": False,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": True,
        "reverse_action": "Made available",
        "requires_document": False,
        "notes_required": True,
    },
    {
        "name": "Scrapped",
        "status_result": "scrapped",
        "document_type": "",
        "direction": "internal",
        "clears_customer": False,
        "clears_vendor": False,
        "starts_warranty": False,
        "ends_warranty": True,
        "captures_cost": False,
        "captures_price": False,
        "is_reversible": False,
        "reverse_action": "",
        "requires_document": False,
        "notes_required": True,
    },
]
