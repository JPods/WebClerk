"""
Alice invoice service — creates a completed trip Invoice when Natalie posts trip actuals.

The Invoice uses the standard WC3 transaction structure:
  Invoice    — header: customer FK (OrgBase), contact FK (Contact), total, status, refs
  InvoiceLine — line:  item_fk → Item (kind="service"), quantity.active=1, price.unit=fare

invoice_line.item_fk ties the trip back to the pricing Item (products.Item),
giving Alice a full itemized record visible in WebClerk's transaction views.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.utils import timezone

from apps.core.models import Contact
from apps.products.models import Item
from apps.transactions.models import Invoice, InvoiceLine

logger = logging.getLogger(__name__)


def create_trip_invoice(data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a completed Invoice + InvoiceLine for a finished JPods trip.

    Required input keys:
        contact_id           — from price_query response
        origin_station_id    — e.g. "S001"
        destination_station_id — e.g. "S003"
        price                — decimal string from price_query response
        currency             — e.g. "USD"

    Optional input keys:
        item_id              — Item pk from price_query response (preferred)
        network_id           — JPods network (default: "default")
        trip_id              — Natalie's internal trip identifier
        duration_actual_s    — seconds the trip actually took
        price_level          — price level applied
        discount_applied     — discount label if any

    Returns:
        invoice_id, status, total, currency, contact_name, customer_id, trip_id
    """
    contact_id = data.get("contact_id")
    origin = data.get("origin_station_id", "")
    destination = data.get("destination_station_id", "")
    price_str = data.get("price", "0")
    currency = data.get("currency", "USD")
    item_id = data.get("item_id")
    network_id = data.get("network_id", "default")
    trip_id = data.get("trip_id", "")
    duration_actual_s = data.get("duration_actual_s")
    price_level = data.get("price_level", "retail")
    discount_applied = data.get("discount_applied")

    if not origin or not destination:
        return {"error": "origin_station_id and destination_station_id are required"}

    try:
        price = Decimal(str(price_str))
    except Exception:
        return {"error": f"Invalid price value: {price_str!r}"}

    # ── Resolve contact and customer ──────────────────────────────────
    contact = None
    customer = None

    if contact_id:
        try:
            contact = Contact.objects.get(pk=contact_id)
            if contact.customer_id:
                customer = contact.customer
        except Contact.DoesNotExist:
            logger.warning("invoice: contact_id %s not found", contact_id)

    # ── Resolve trip Item ─────────────────────────────────────────────
    item = None
    if item_id:
        try:
            item = Item.objects.get(pk=item_id, kind=Item.KIND_SERVICE)
        except Item.DoesNotExist:
            logger.warning("invoice: item_id %s not found", item_id)

    if item is None:
        # Fall back to SKU lookup
        sku = f"JPODS-{network_id}-{origin}-{destination}".upper()
        item = Item.objects.filter(sku=sku, kind=Item.KIND_SERVICE, is_active=True).first()

    # ── Build Invoice refs ────────────────────────────────────────────
    refs = {
        "trip_id": trip_id,
        "origin_station_id": origin,
        "destination_station_id": destination,
        "duration_actual_s": duration_actual_s,
        "price_level": price_level,
        "discount_applied": discount_applied,
        "network_id": network_id,
        "currency": currency,
        "source": "natalie",
        "dt_trip_created": timezone.now().isoformat(),
    }

    totals = {
        "subtotal": float(price),
        "discount": 0,
        "taxable": float(price),
        "tax": 0,
        "shipping": 0,
        "other": 0,
        "total": float(price),
        "cost": 0,
        "margin": float(price),
        "margin_pc": 100,
        "received": float(price),
        "balance": 0,
    }

    # ── Create Invoice ────────────────────────────────────────────────
    invoice = Invoice(
        customer=customer,
        contact=contact,
        total=price,
        balance=Decimal("0.00"),
        status=Invoice.STATUS_COMPLETE,
        price_level=price_level,
        refs=refs,
        totals=totals,
    )
    invoice.save()

    # ── Create InvoiceLine referencing the Item ───────────────────────
    if item:
        line = InvoiceLine(
            invoice=invoice,
            item_fk=item,
            price_level=price_level,
            item={
                "item_id": item.pk,
                "description": item.name or f"JPods Trip {origin}→{destination}",
                "unit_measure": "trip",
            },
            quantity={
                "active": 1,
                "staged": 1,
                "remaining": 0,
            },
            price={
                "unit": float(price),
                "unit_base": float(price),
                "discount_percent": 0.0,
                "discount_amount": 0.0,
                "extended": float(price),
            },
        )
        line.save()
    else:
        logger.warning(
            "invoice: no Item found for %s→%s (network=%s); invoice created without line",
            origin, destination, network_id,
        )

    logger.info(
        "JPods invoice created: pk=%s contact=%s %s→%s price=%s %s",
        invoice.pk, contact_id, origin, destination, price, currency,
    )

    return {
        "invoice_id": invoice.pk,
        "status": invoice.status,
        "total": str(price),
        "currency": currency,
        "contact_name": contact.get_full_name() if contact else None,
        "customer_id": customer.pk if customer else None,
        "trip_id": trip_id,
    }
