from __future__ import annotations

from django.db import models
from django.utils import timezone
from common.models import BaseModel
from .item_base_model import ItemLinkedBase
from .warehouse import Warehouse


SERIAL_STATUS_CHOICES = [
    ('available', 'Available'),
    ('received', 'Received'),
    ('reserved', 'Reserved'),
    ('issued', 'Issued'),
    ('returned', 'Returned'),
    ('referenced', 'Referenced'),
    ('warranty', 'Warranty'),
    ('damaged', 'Damaged'),
    ('scrapped', 'Scrapped'),
]


def default_serial_config() -> dict:
    """Config schema for Serial -- carries the transaction context.

    WC2 lineage: fields from ItemSerial that track who holds this unit,
    what document moved it, and what it cost. Full words, no codes.
    """
    return {
        "customer_id": None,
        "vendor_id": None,
        "invoice_id": None,
        "order_id": None,
        "purchase_id": None,
        "sales_line_ref": None,
        "purchase_line_ref": None,
        "cost": 0.0,
        "price": 0.0,
        "discount": 0.0,
        "dt_received": None,
        "dt_shipped": None,
        "days_on_plan": 0,
        "floor_plan": {
            "is_active": False,
            "dt_expires": None,
            "plan_line": None,
        },
    }


class Serial(ItemLinkedBase):
    """One serialized unit of an item.

    WC2 lineage: [ItemSerial] table. Every physical unit with a unique
    serial number gets one record. Status tracks lifecycle from received
    through issued to returned/scrapped. Config carries transaction
    context (who holds it, what document moved it, cost/price at time
    of transaction). SerialLog records every state change with full
    sentence descriptions.
    """

    item_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="Item identifier (copied from parent item for fast lookup)")
    description = models.CharField(max_length=255, blank=True, help_text="Description of this specific unit")

    serial_ida = models.CharField(max_length=120, unique=False, help_text="Serial number as printed on the unit")
    model_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="Model number or variant identifier")
    warranty = models.JSONField(default=dict, blank=True, help_text="Warranty details: days, dt_start, dt_end, terms")
    status = models.CharField(max_length=40, choices=SERIAL_STATUS_CHOICES, default='received', db_index=True)
    site = models.JSONField(default=dict, blank=True, help_text="Current location: warehouse code, bin, zone, geo")
    inventory_layer = models.ForeignKey(
        'products.InventoryLayer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name="serials", db_column='inventorylayer_id',
    )
    config = models.JSONField(default=default_serial_config, blank=True, help_text="Transaction context: customer, vendor, document refs, cost/price, floor plan")
    qr_code = models.CharField(max_length=255, blank=True, db_index=True, help_text="QR or barcode value if different from serial_ida")

    @property
    def ida(self):
        return str(self.pk)

    @property
    def item_ida_value(self):
        return self.item_ida or str(self.pk)

    @property
    def description_value(self):
        return self.description or f"Serial {self.serial_ida} ({self.model_ida}) [{self.status}]"

    def log_action(self, action: str, doc_type: str = '', doc_id: int | None = None, notes: str = ''):
        """Record a state change in SerialLog. Full sentence actions, no codes."""
        SerialLog.objects.create(
            serial=self,
            action=action,
            dt=int(timezone.now().timestamp()),
            config={
                'doc_type': doc_type,
                'doc_id': doc_id,
                'status_before': self.status,
                'notes': notes,
            },
        )

    def receive(self, vendor_id=None, purchase_id=None, purchase_line_ref=None, cost: float = 0.0, warranty_days: int = 0):
        """Receive on purchase order."""
        cfg = self.config or default_serial_config()
        cfg['vendor_id'] = vendor_id
        cfg['purchase_id'] = purchase_id
        cfg['purchase_line_ref'] = purchase_line_ref
        cfg['cost'] = cost
        cfg['dt_received'] = timezone.now().isoformat()
        self.config = cfg
        self.status = 'received'
        if warranty_days:
            self.warranty = {
                'days': warranty_days,
                'dt_start': None,
                'dt_end': None,
            }
        self.save()
        self.log_action('Received on purchase order', doc_type='purchase', doc_id=purchase_id)

    def make_available(self):
        """Put into available inventory after inspection or return processing."""
        cfg = self.config or default_serial_config()
        cfg['customer_id'] = None
        cfg['invoice_id'] = None
        cfg['order_id'] = None
        cfg['sales_line_ref'] = None
        cfg['dt_shipped'] = None
        cfg['days_on_plan'] = 0
        self.config = cfg
        self.status = 'available'
        self.save()
        self.log_action('Made available')

    def reserve_for_order(self, customer_id, order_id, sales_line_ref=None, price: float = 0.0, discount: float = 0.0):
        """Reserve for a sales order (not yet shipped)."""
        cfg = self.config or default_serial_config()
        cfg['customer_id'] = customer_id
        cfg['order_id'] = order_id
        cfg['sales_line_ref'] = sales_line_ref
        cfg['price'] = price
        cfg['discount'] = discount
        self.config = cfg
        self.status = 'reserved'
        self.save()
        self.log_action('Reserved for order', doc_type='order', doc_id=order_id)

    def issue_on_invoice(self, customer_id, invoice_id, sales_line_ref=None, price: float = 0.0, cost: float = 0.0, discount: float = 0.0):
        """Issue (ship) on invoice."""
        now = timezone.now()
        cfg = self.config or default_serial_config()
        cfg['customer_id'] = customer_id
        cfg['invoice_id'] = invoice_id
        cfg['sales_line_ref'] = sales_line_ref
        cfg['price'] = price
        cfg['cost'] = cost
        cfg['discount'] = discount
        cfg['dt_shipped'] = now.isoformat()
        # Calculate days on plan
        dt_received = cfg.get('dt_received')
        if dt_received:
            from datetime import datetime, timezone as tz
            try:
                received = datetime.fromisoformat(dt_received)
                cfg['days_on_plan'] = (now - received).days
            except (ValueError, TypeError):
                pass
        self.config = cfg
        self.status = 'issued'
        # Start warranty
        warranty = self.warranty or {}
        warranty_days = warranty.get('days', 0)
        if warranty_days:
            warranty['dt_start'] = now.isoformat()
            end = now + __import__('datetime').timedelta(days=warranty_days)
            warranty['dt_end'] = end.isoformat()
            self.warranty = warranty
        self.save()
        self.log_action('Issued in invoice', doc_type='invoice', doc_id=invoice_id)

    def return_from_customer(self, invoice_id=None, notes: str = ''):
        """Return from customer. Moves to returned status pending inspection."""
        self.status = 'returned'
        self.save()
        self.log_action('Returned from customer', doc_type='invoice', doc_id=invoice_id, notes=notes)

    def mark_damaged(self, notes: str = ''):
        """Mark as damaged -- not available for sale."""
        self.status = 'damaged'
        self.save()
        self.log_action('Marked as damaged', notes=notes)

    def scrap(self, notes: str = ''):
        """Write off -- end of life for this unit."""
        self.status = 'scrapped'
        self.save()
        self.log_action('Scrapped', notes=notes)

    def reference_to_document(self, doc_type: str, doc_id: int):
        """Link to a document without physical movement."""
        self.status = 'referenced'
        self.save()
        self.log_action(f'Referenced in {doc_type}', doc_type=doc_type, doc_id=doc_id)


class SerialLog(BaseModel):
    """Log of actions / state changes for a serialized unit.

    WC2 lineage: [ItemSerialAction] table. Every state change gets one
    record with a full sentence action description, the document that
    caused it, and the status before the change. Config carries context.
    """

    serial = models.ForeignKey(Serial, on_delete=models.CASCADE, related_name="logs", db_column='serial_id')
    action = models.CharField(max_length=120, db_index=True, help_text="Full sentence: 'Issued in invoice', 'Returned from customer', etc.")
    dt = models.BigIntegerField(db_index=True, help_text="Unix timestamp of the action")
    config = models.JSONField(default=dict, blank=True, help_text="Context: doc_type, doc_id, status_before, notes")

    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return f"{self.action} @ {self.dt}"

    class Meta:
        indexes = [
            models.Index(fields=("serial_id", "dt"), name="seriallog_serial_dt_idx"),
        ]
