"""
Serial Number Lifecycle Service — GAP-03

PO receiving creates serial records. Invoice shipping assigns to customer
and starts warranty clock. History lives on the serial in config.actions[].

Entry points for wcapi/manage. The lifecycle itself is the Serial model's
(receive, issue_on_invoice, return_from_customer); these only find or create
the serial and shape the response.
"""
from __future__ import annotations
from typing import Dict, List
from django.db import transaction
from apps.products.models.serial import Serial, SerialLog


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

    Returns: {serial_id, serial_number, status}
    """
    with transaction.atomic():
        serial = Serial.objects.create(
            item_id=item_id,
            serial_ida=serial_number,
            model_ida=model_ida,
            site={'warehouse_id': warehouse_id},
        )
        serial.receive(
            vendor_id=vendor_id,
            purchase_id=purchase_id,
            purchase_line_ref=purchase_line_id,
            cost=float(unit_cost or 0),
        )
    return {'serial_id': serial.pk, 'serial_number': serial_number, 'status': serial.status}


def assign_serial_on_ship(
    serial_id: int,
    customer_id: int,
    invoice_id: int = None,
    invoice_line_id: int = None,
    warranty_months: int = 12,
) -> Dict:
    """Assign a serial to a customer when shipping on an invoice. Starts the warranty clock.

    Returns: {serial_id, serial_number, status, warranty}
    """
    with transaction.atomic():
        serial = Serial.objects.get(pk=serial_id)
        if warranty_months:
            serial.warranty = {**(serial.warranty or {}), 'days': warranty_months * 30}
        serial.site = {'customer_id': customer_id}
        serial.issue_on_invoice(customer_id, invoice_id, sales_line_ref=invoice_line_id)
    return {
        'serial_id': serial.pk,
        'serial_number': serial.serial_ida,
        'status': serial.status,
        'warranty': serial.warranty or {},
    }


def return_serial(
    serial_id: int,
    reason: str = '',
    return_to_warehouse_id: int = None,
) -> Dict:
    """Process a serial return (RMA).

    Returns: {serial_id, status}
    """
    with transaction.atomic():
        serial = Serial.objects.get(pk=serial_id)
        serial.site = {'warehouse_id': return_to_warehouse_id}
        serial.return_from_customer(invoice_id=(serial.config or {}).get('invoice_id'), notes=reason)
    return {'serial_id': serial.pk, 'status': serial.status}


def get_serial_history(serial_id: int) -> Dict:
    """Complete history: archived SerialLog rows, then config.actions[].

    Returns: {serial_id, serial_number, model_ida, status, warranty, site, history: [...]}
    """
    serial = Serial.objects.get(pk=serial_id)
    archived = [
        {'action': log.action, 'dt': log.dt, **(log.config or {})}
        for log in SerialLog.objects.filter(serial=serial).order_by('dt')
    ]
    return {
        'serial_id': serial.pk,
        'serial_number': serial.serial_ida,
        'model_ida': serial.model_ida,
        'status': serial.status,
        'warranty': serial.warranty or {},
        'site': serial.site or {},
        'history': archived + list((serial.config or {}).get('actions', [])),
    }


def find_serials_by_customer(customer_id: int) -> List[Dict]:
    """Serials currently issued to a customer.

    Returns: [{serial_id, serial_number, model_ida, status, warranty}]
    """
    serials = Serial.objects.filter(
        config__customer_id=customer_id,
        status='issued',
        )
    return [{
        'serial_id': s.pk,
        'serial_number': s.serial_ida,
        'model_ida': s.model_ida,
        'status': s.status,
        'warranty': s.warranty or {},
    } for s in serials]
