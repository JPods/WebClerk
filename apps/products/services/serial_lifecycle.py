"""
Serial Number Lifecycle Service — GAP-03

PO receiving creates serial records. Invoice shipping assigns to customer
and starts warranty clock. Full history chain via SerialLog.

All functions single-purpose. Called from wcapi/manage.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from django.db import transaction
from apps.products.models.serial import Serial, SerialLog
import time


def _now_ms():
    return int(time.time() * 1000)


def create_serial_on_receive(
    item_id: int,
    serial_number: str,
    vendor_id: int = None,
    purchase_id: int = None,
    purchase_line_id: int = None,
    unit_cost: str = '0',
    warehouse_id: int = None,
    model_ida: str = '',
) -> Dict:
    """Create a serial record when receiving goods on a PO.

    Sets status to 'available'. Logs the receiving event.

    Returns: {serial_id, serial_number, status}
    """
    now = _now_ms()

    with transaction.atomic():
        serial = Serial.objects.create(
            item_id=item_id,
            serial_ida=serial_number,
            model_ida=model_ida,
            status='available',
            site={'warehouse_id': warehouse_id},
            warranty={},
            data={
                'received_from_vendor_id': vendor_id,
                'received_cost': unit_cost,
            },
            metadata={
                'health': 'active',
                'received_on_po': purchase_id,
                'received_on_po_line': purchase_line_id,
            },
            dt_created=now,
            dt_modified=now,
        )

        SerialLog.objects.create(
            serial=serial,
            action='received',
            dt=now,
            data={
                'purchase_id': purchase_id,
                'purchase_line_id': purchase_line_id,
                'vendor_id': vendor_id,
                'unit_cost': unit_cost,
                'warehouse_id': warehouse_id,
            },
        )

    return {'serial_id': serial.pk, 'serial_number': serial_number, 'status': 'available'}


def assign_serial_on_ship(
    serial_id: int,
    customer_id: int,
    invoice_id: int = None,
    invoice_line_id: int = None,
    warranty_months: int = 12,
) -> Dict:
    """Assign a serial to a customer when shipping on an invoice.

    Changes status to 'sold'. Starts warranty clock.
    Logs the shipping event.

    Returns: {serial_id, serial_number, status, warranty_expires}
    """
    now = _now_ms()
    warranty_expires_ms = now + (warranty_months * 30 * 24 * 60 * 60 * 1000)

    with transaction.atomic():
        serial = Serial.objects.get(pk=serial_id)
        serial.status = 'sold'
        serial.warranty = {
            'months': warranty_months,
            'starts': now,
            'expires': warranty_expires_ms,
        }
        serial.site = {'customer_id': customer_id}
        serial.dt_modified = now

        meta = serial.metadata or {}
        meta['sold_to_customer_id'] = customer_id
        meta['sold_on_invoice'] = invoice_id
        meta['sold_on_invoice_line'] = invoice_line_id
        serial.metadata = meta

        serial.save()

        SerialLog.objects.create(
            serial=serial,
            action='shipped',
            dt=now,
            data={
                'customer_id': customer_id,
                'invoice_id': invoice_id,
                'invoice_line_id': invoice_line_id,
                'warranty_months': warranty_months,
                'warranty_expires': warranty_expires_ms,
            },
        )

    return {
        'serial_id': serial.pk,
        'serial_number': serial.serial_ida,
        'status': 'sold',
        'warranty_expires': warranty_expires_ms,
    }


def return_serial(
    serial_id: int,
    reason: str = '',
    return_to_warehouse_id: int = None,
) -> Dict:
    """Process a serial return (RMA). Changes status back to 'returned'.

    Returns: {serial_id, status}
    """
    now = _now_ms()

    with transaction.atomic():
        serial = Serial.objects.get(pk=serial_id)
        serial.status = 'returned'
        serial.site = {'warehouse_id': return_to_warehouse_id}
        serial.dt_modified = now
        serial.save()

        SerialLog.objects.create(
            serial=serial,
            action='returned',
            dt=now,
            data={'reason': reason, 'warehouse_id': return_to_warehouse_id},
        )

    return {'serial_id': serial.pk, 'status': 'returned'}


def get_serial_history(serial_id: int) -> Dict:
    """Get complete history for a serial number.

    Returns: {serial_id, serial_number, status, warranty, history: [{action, dt, data}]}
    """
    serial = Serial.objects.get(pk=serial_id)
    logs = SerialLog.objects.filter(serial=serial).order_by('dt')

    return {
        'serial_id': serial.pk,
        'serial_number': serial.serial_ida,
        'model_ida': serial.model_ida,
        'status': serial.status,
        'warranty': serial.warranty or {},
        'site': serial.site or {},
        'history': [
            {'action': log.action, 'dt': log.dt, 'data': log.data or {}}
            for log in logs
        ],
    }


def find_serials_by_customer(customer_id: int) -> List[Dict]:
    """Find all serials currently assigned to a customer.

    Returns: [{serial_id, serial_number, model_ida, status, warranty}]
    """
    serials = Serial.objects.filter(
        metadata__sold_to_customer_id=customer_id,
        status='sold',
        is_deleted=False,
    )

    return [{
        'serial_id': s.pk,
        'serial_number': s.serial_ida,
        'model_ida': s.model_ida,
        'status': s.status,
        'warranty': s.warranty or {},
    } for s in serials]
