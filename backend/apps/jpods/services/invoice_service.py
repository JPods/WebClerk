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
from django.db import transaction

from apps.core.services.door import Actor
from apps.core.services.save import save_record
from apps.transactions.models import Cash, Invoice
from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice

logger = logging.getLogger(__name__)


def create_trip_invoice(data: dict[str, Any]) -> dict[str, Any]:
    """
    Invoice a JPods trip through the door and pay it from the rider's prepaid balance.

    received is never written here: it is the Σ of the applications made from the rider's
    Cash (fix #2). A balance short of the price refuses the trip with coaching.

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

    # ── The rider pays from their prepaid balance (Bill, 2026-09-26) ──
    # received is never claimed: it is the Σ of real applications, from Cash that arrived
    # earlier (fix #2). A short balance refuses the trip with coaching; nothing is written.
    owner = {"customer_id": customer.pk} if customer else {"contact_id": contact.pk if contact else None}
    if not owner.get("customer_id") and not owner.get("contact_id"):
        return {"error": "A trip needs a rider (contact_id) with a prepaid balance"}
    # A rider with no customer org pays from Cash that names no customer either: the
    # application refuses cash whose customer differs from the invoice's (Fable).
    cash_owner = owner if customer else {**owner, "customer_id__isnull": True}
    funds = [c for c in Cash.objects.filter(**cash_owner, available__gt=0).order_by("dt_created", "pk")
             if c.holds_money]
    on_account = sum((Decimal(str(c.available)) for c in funds), Decimal("0"))
    if on_account < price:
        return {"error": f"Prepaid balance {on_account:.2f} {currency} is short of this trip's "
                         f"{price:.2f}: add {price - on_account:.2f} {currency} to ride",
                "code": "insufficient_balance"}

    refs = {
        "trip_id": trip_id,
        "origin_station_id": origin,
        "destination_station_id": destination,
        "duration_actual_s": duration_actual_s,
        "price_level": price_level,
        "discount_applied": discount_applied,
        "network_id": network_id,
        "currency": currency,
        "dispatched_by": "natalie",
        "dt_trip_created": timezone.now().isoformat(),
    }
    line = {
        "item_fk_id": item.pk if item else None,
        "price_level": price_level,
        "item": {"item_id": item.pk if item else None,
                 "description": (item.name if item else "") or f"JPods Trip {origin}→{destination}",
                 "unit_measure": "trip"},
        "quantity": {"active": 1},
        "price": {"unit": float(price), "unit_base": float(price)},
    }
    if not item:
        logger.warning("invoice: no Item found for %s→%s (network=%s)", origin, destination, network_id)

    # One transaction: an application the cash check refuses (stored available above the
    # journal, a customer mismatch) rolls the invoice back and the rider is told why.
    try:
        with transaction.atomic():
            result = save_record(Actor.system(source="jpods"), {
                "model_name": "invoice", **owner, "source_name": "jpods",
                "contact_id": contact.pk if contact else None,
                "price_level": price_level, "refs": refs, "lines": [line],
            })
            invoice = Invoice.objects.get(pk=result.obj_id)
            remaining = price
            for cash in funds:                   # oldest money first
                if remaining <= 0:
                    break
                take = min(Decimal(str(cash.available)), remaining)
                apply_cash_to_invoice(cash.pk, invoice.pk, take, reason=f"JPods trip {trip_id}")
                remaining -= take
            invoice.refresh_from_db()
    except ValueError as e:
        logger.warning("JPods trip %s refused at payment: %s", trip_id, e)
        return {"error": f"The trip could not be paid from the prepaid balance: {e}",
                "code": "payment_refused"}

    logger.info(
        "JPods invoice created: pk=%s contact=%s %s→%s price=%s %s",
        invoice.pk, contact_id, origin, destination, price, currency,
    )

    return {
        "invoice_id": invoice.pk,
        "status": invoice.status,
        "total": str(invoice.total),
        "received": str((invoice.totals or {}).get("received")),
        "currency": currency,
        "contact_name": contact.get_full_name() if contact else None,
        "customer_id": customer.pk if customer else None,
        "trip_id": trip_id,
    }
