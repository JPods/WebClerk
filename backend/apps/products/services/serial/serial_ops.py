"""Serial number lifecycle services.

Operations: receive, issue, return, reference, warranty check, search.
Every state change logs to SerialLog. Warranty calculated at issue time.

Pattern source: WC2 Srl_IssueSale, Srl_RcvrPO, Srl_SalvageSale, Srl_Transaction, Srl_Reference.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.products.models.serial import Serial, SerialLog
from apps.products.models.item import Item


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_AVAILABLE = 'available'
STATUS_ISSUED = 'issued'
STATUS_PENDING_SALE = 'pending_sale'
STATUS_REFERENCED = 'referenced'
STATUS_RETURNED = 'returned'
STATUS_SCRAPPED = 'scrapped'
STATUS_IN_SERVICE = 'in_service'


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

@transaction.atomic
def receive_serial(
    item_id: int,
    serial_number: str,
    *,
    vendor_id: Optional[int] = None,
    po_id: Optional[int] = None,
    po_line_id: Optional[int] = None,
    model_number: str = '',
    cost: Optional[Decimal] = None,
    warranty_days: int = 0,
    site: Optional[dict] = None,
) -> Serial:
    """Receive a serialized unit on a PO. Creates the serial record as Available."""
    item = Item.objects.get(id=item_id)

    serial = Serial.objects.create(
        item=item,
        item_ida=item.ida or '',
        serial_ida=serial_number,
        model_ida=model_number,
        description=f"{item.name} S/N {serial_number}",
        status=STATUS_AVAILABLE,
        warranty=_build_warranty(warranty_days),
        site=site or {},
        config={
            'cost': float(cost) if cost else 0,
            'dt_received': _now_ms(),
        },
    )

    # Store vendor/PO linkage in refs
    refs_links = serial.refs.get('links', {}) if isinstance(serial.refs, dict) else {}
    if vendor_id:
        refs_links['vendor_id'] = vendor_id
    if po_id:
        refs_links['po_id'] = po_id
    if po_line_id:
        refs_links['po_line_id'] = po_line_id
    if isinstance(serial.refs, dict):
        serial.refs['links'] = refs_links
    else:
        serial.refs = {'links': refs_links}
    serial.save(update_fields=['refs'])

    _log(serial, 'received', config={
        'vendor_id': vendor_id,
        'po_id': po_id,
        'cost': float(cost) if cost else 0,
    })
    return serial


@transaction.atomic
def issue_to_sale(
    serial_id: int,
    *,
    customer_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    invoice_line_id: Optional[int] = None,
    order_id: Optional[int] = None,
    price: Optional[Decimal] = None,
    discount: Optional[Decimal] = None,
) -> Serial:
    """Issue a serial to a sale (invoice/order). Sets warranty start date."""
    serial = Serial.objects.select_for_update().get(id=serial_id)

    serial.status = STATUS_ISSUED
    now = _now_ms()

    # Warranty: calculate end date from today + warranty_days
    warranty = serial.warranty or {}
    warranty_days = warranty.get('days', 0)
    if warranty_days:
        warranty['dt_start'] = now
        warranty['dt_end'] = now + (warranty_days * 86400000)  # ms
        warranty['date_start'] = date.today().isoformat()
        warranty['date_end'] = (date.today() + timedelta(days=warranty_days)).isoformat()
    serial.warranty = warranty

    # Config: sale details
    config = serial.config or {}
    config['dt_issued'] = now
    config['price'] = float(price) if price else 0
    config['discount'] = float(discount) if discount else 0
    serial.config = config

    # Refs: customer and invoice linkage
    refs = serial.refs if isinstance(serial.refs, dict) else {}
    links = refs.get('links', {})
    if customer_id:
        links['customer_id'] = customer_id
    if invoice_id:
        links['invoice_id'] = invoice_id
    if invoice_line_id:
        links['invoice_line_id'] = invoice_line_id
    if order_id:
        links['order_id'] = order_id
    refs['links'] = links
    serial.refs = refs

    serial.save(update_fields=['status', 'warranty', 'config', 'refs'])

    _log(serial, 'issued', config={
        'customer_id': customer_id,
        'invoice_id': invoice_id,
        'price': float(price) if price else 0,
    })
    return serial


@transaction.atomic
def return_from_sale(
    serial_id: int,
    *,
    reason: str = 'Customer return',
    invoice_id: Optional[int] = None,
) -> Serial:
    """Return/salvage a serial from a sale. Resets to Available."""
    serial = Serial.objects.select_for_update().get(id=serial_id)

    serial.status = STATUS_AVAILABLE

    # Clear customer linkage but preserve vendor/PO history
    refs = serial.refs if isinstance(serial.refs, dict) else {}
    links = refs.get('links', {})
    links.pop('customer_id', None)
    links.pop('invoice_id', None)
    links.pop('invoice_line_id', None)
    links.pop('order_id', None)
    refs['links'] = links
    serial.refs = refs

    # Clear warranty active dates (warranty days definition stays)
    warranty = serial.warranty or {}
    warranty.pop('dt_start', None)
    warranty.pop('dt_end', None)
    warranty.pop('date_start', None)
    warranty.pop('date_end', None)
    serial.warranty = warranty

    serial.save(update_fields=['status', 'refs', 'warranty'])

    _log(serial, 'returned', config={
        'reason': reason,
        'from_invoice_id': invoice_id,
    })
    return serial


@transaction.atomic
def reference_existing(
    item_id: int,
    serial_number: str,
    *,
    customer_id: Optional[int] = None,
    document_type: str = '',
    document_id: Optional[int] = None,
    remaining_warranty_days: int = 0,
) -> Serial:
    """Attach a customer-owned serial to a document without a formal receive.
    Used for service/repair scenarios where the serial already exists in the field."""
    item = Item.objects.get(id=item_id)

    # Find or create
    serial, created = Serial.objects.get_or_create(
        item=item,
        serial_ida=serial_number,
        defaults={
            'item_ida': item.ida or '',
            'model_ida': '',
            'description': f"{item.name} S/N {serial_number}",
            'status': STATUS_REFERENCED,
            'warranty': _build_warranty(remaining_warranty_days, start_today=True),
            'config': {'dt_referenced': _now_ms()},
        }
    )

    if not created:
        serial.status = STATUS_REFERENCED
        serial.save(update_fields=['status'])

    # Link to customer and document
    refs = serial.refs if isinstance(serial.refs, dict) else {}
    links = refs.get('links', {})
    if customer_id:
        links['customer_id'] = customer_id
    if document_id:
        links[f'{document_type}_id'] = document_id
    refs['links'] = links
    serial.refs = refs
    serial.save(update_fields=['refs'])

    _log(serial, 'referenced', config={
        'customer_id': customer_id,
        'document_type': document_type,
        'document_id': document_id,
        'remaining_warranty_days': remaining_warranty_days,
    })
    return serial


@transaction.atomic
def change_status(serial_id: int, new_status: str, *, reason: str = '') -> Serial:
    """Generic status change with audit logging."""
    serial = Serial.objects.select_for_update().get(id=serial_id)
    old_status = serial.status
    serial.status = new_status
    serial.save(update_fields=['status'])
    _log(serial, f'status_change:{old_status}→{new_status}', config={'reason': reason})
    return serial


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_by_item(item_id: int, *, status: Optional[str] = None) -> list[Serial]:
    """All serials for an item, optionally filtered by status."""
    qs = Serial.objects.filter(item_id=item_id).order_by('-dt_created')
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def search_by_customer(customer_id: int) -> list[Serial]:
    """Find all serials currently issued to a customer."""
    return list(Serial.objects.filter(
        refs__links__customer_id=customer_id,
        status=STATUS_ISSUED,
    ).order_by('-dt_created'))


def search_by_vendor(vendor_id: int) -> list[Serial]:
    """Find all serials received from a vendor."""
    return list(Serial.objects.filter(
        refs__links__vendor_id=vendor_id,
    ).order_by('-dt_created'))


def search_by_serial_number(serial_number: str) -> list[Serial]:
    """Find serials by serial number (may return multiple if reused across items)."""
    return list(Serial.objects.filter(
        serial_ida__icontains=serial_number,
    ).order_by('-dt_created'))


def get_history(serial_id: int) -> list[SerialLog]:
    """Full event history for a serial unit."""
    return list(SerialLog.objects.filter(serial_id=serial_id).order_by('dt'))


# ---------------------------------------------------------------------------
# Warranty
# ---------------------------------------------------------------------------

def warranty_due(days_ahead: int = 30) -> list[Serial]:
    """Find serials with warranty expiring within N days."""
    now = _now_ms()
    cutoff = now + (days_ahead * 86400000)
    return list(Serial.objects.filter(
        status=STATUS_ISSUED,
        warranty__dt_end__gt=now,
        warranty__dt_end__lte=cutoff,
    ).order_by('warranty__dt_end'))


def warranty_expired() -> list[Serial]:
    """Find issued serials with expired warranty."""
    now = _now_ms()
    return list(Serial.objects.filter(
        status=STATUS_ISSUED,
        warranty__dt_end__gt=0,
        warranty__dt_end__lt=now,
    ).order_by('warranty__dt_end'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_ms() -> int:
    return int(timezone.now().timestamp() * 1000)


def _log(serial: Serial, action: str, config: Optional[dict] = None) -> SerialLog:
    return SerialLog.objects.create(
        serial=serial,
        action=action,
        dt=_now_ms(),
        config=config or {},
    )


def _build_warranty(days: int, start_today: bool = False) -> dict:
    w: dict = {'days': days}
    if start_today and days:
        now = _now_ms()
        w['dt_start'] = now
        w['dt_end'] = now + (days * 86400000)
        w['date_start'] = date.today().isoformat()
        w['date_end'] = (date.today() + timedelta(days=days)).isoformat()
    return w


__all__ = [
    'receive_serial', 'issue_to_sale', 'return_from_sale', 'reference_existing',
    'change_status', 'list_by_item', 'search_by_customer', 'search_by_vendor',
    'search_by_serial_number', 'get_history', 'warranty_due', 'warranty_expired',
    'STATUS_AVAILABLE', 'STATUS_ISSUED', 'STATUS_PENDING_SALE',
    'STATUS_REFERENCED', 'STATUS_RETURNED', 'STATUS_SCRAPPED', 'STATUS_IN_SERVICE',
]
