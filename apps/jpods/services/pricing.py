"""
Alice pricing service — resolves a rider's Contact and Customer, then returns the trip price.

Resolution order for contact lookup:
  1. contact_uuid (most reliable — CarryOn ID)
  2. email
  3. name_first + name_last (demo name lookup)
  4. None → anonymous / walk-up rate

Price lookup:
  Prices live in the standard WC3 Item model (kind="service").
  SKU: JPODS-{NETWORK_ID}-{ORIGIN}-{DESTINATION}  (e.g. JPODS-DEFAULT-S001-S003)

  Customer.price_level maps to Item.price keys:
    demo     → wholesale
    retail   → retail
    employee → sample
  Falls back to retail if no specific-level price is set.

Discounts:
  Applied from customer.financial["discounts"] if present.
  Format: [{"type": "percent", "value": 10, "label": "Demo Pass"}]
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from apps.core.models import Contact
from apps.products.models import Item

logger = logging.getLogger(__name__)

# Maps Customer.price_level → Item.price key
PRICE_LEVEL_KEY: dict[str, str] = {
    "demo":     "wholesale",
    "retail":   "retail",
    "employee": "sample",
}


def resolve_contact(
    contact_uuid: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> Contact | None:
    """Find the Contact for this rider using the best available identifier."""
    if contact_uuid:
        try:
            return Contact.objects.get(uuid=contact_uuid)
        except Contact.DoesNotExist:
            logger.warning("price_query: contact_uuid %s not found", contact_uuid)

    if email:
        try:
            return Contact.objects.get(email=email)
        except Contact.DoesNotExist:
            logger.warning("price_query: email %s not found", email)

    if name:
        parts = name.strip().split(None, 1)
        name_first = parts[0] if parts else ""
        name_last = parts[1] if len(parts) > 1 else ""
        contact = Contact.objects.filter(
            name_first__iexact=name_first,
            name_last__iexact=name_last,
            is_active=True,
        ).first()
        if contact:
            return contact
        logger.warning("price_query: name '%s' not found", name)

    return None


def get_trip_item(
    origin_station_id: str,
    destination_station_id: str,
    network_id: str = "default",
) -> Item | None:
    """Look up the Item for this station pair."""
    sku = f"JPODS-{network_id}-{origin_station_id}-{destination_station_id}".upper()
    return Item.objects.filter(sku=sku, kind=Item.KIND_SERVICE, is_active=True).first()


def get_price(
    item: Item,
    price_level: str,
) -> tuple[Decimal, str]:
    """Extract the price for the given price level from the Item.

    Returns (price, currency).
    Falls back to retail if the level has no price set.
    Raises ValueError if no usable price exists.
    """
    price_data = item.price if isinstance(item.price, dict) else {}
    currency = price_data.get("currency", "USD")

    key = PRICE_LEVEL_KEY.get(price_level, "retail")
    raw = price_data.get(key)

    # Fall back to retail
    if raw is None:
        raw = price_data.get("retail")

    if raw is None:
        raise ValueError(
            f"No price configured on item {item.sku!r} for level '{price_level}'"
        )

    return Decimal(str(raw)), currency


def apply_discounts(base_price: Decimal, customer_financial: dict) -> tuple[Decimal, str | None]:
    """Apply the first active discount from customer.financial['discounts'].

    Returns (final_price, discount_label).
    Currently applies one discount — the first in the list.
    """
    discounts = customer_financial.get("discounts", []) if customer_financial else []
    if not discounts or not isinstance(discounts, list):
        return base_price, None

    discount = discounts[0]
    dtype = discount.get("type", "")
    value = discount.get("value", 0)
    label = discount.get("label", "")

    if dtype == "percent" and value:
        final = base_price * (1 - Decimal(str(value)) / 100)
        return final.quantize(Decimal("0.01")), label

    if dtype == "fixed" and value:
        final = max(Decimal("0.00"), base_price - Decimal(str(value)))
        return final.quantize(Decimal("0.01")), label

    return base_price, None


def resolve_price_query(data: dict[str, Any]) -> dict[str, Any]:
    """
    Main entry point for the price_query endpoint.

    Input dict keys (all optional except origin/destination):
        contact_uuid, email, name,
        origin_station_id, destination_station_id, network_id

    Returns:
        contact_id, contact_name, customer_id,
        price, currency, price_level, discount_applied, display,
        item_id, error (if unresolvable)
    """
    origin = data.get("origin_station_id", "")
    destination = data.get("destination_station_id", "")
    network_id = data.get("network_id", "default")

    if not origin or not destination:
        return {"error": "origin_station_id and destination_station_id are required"}

    contact = resolve_contact(
        contact_uuid=data.get("contact_uuid"),
        email=data.get("email"),
        name=data.get("name"),
    )

    customer = None
    price_level = "retail"
    financial: dict = {}

    if contact and contact.customer_id:
        customer = contact.customer
        price_level = customer.price_level or "retail"
        financial = customer.financial if isinstance(customer.financial, dict) else {}

    item = get_trip_item(origin, destination, network_id)
    if not item:
        sku = f"JPODS-{network_id}-{origin}-{destination}".upper()
        return {"error": f"No trip item found for {origin}→{destination} (SKU: {sku})"}

    try:
        base_price, currency = get_price(item, price_level)
    except ValueError as exc:
        return {"error": str(exc)}

    final_price, discount_label = apply_discounts(base_price, financial)

    display_price = f"{currency} {final_price:.2f}"
    if discount_label:
        display_price += f" ({discount_label})"
    elif price_level != "retail":
        display_price += f" ({price_level} rate)"

    return {
        "contact_id": contact.pk if contact else None,
        "contact_name": contact.get_full_name() if contact else None,
        "customer_id": customer.pk if customer else None,
        "item_id": item.pk,
        "price": str(final_price),
        "currency": currency,
        "price_level": price_level,
        "discount_applied": discount_label,
        "display": display_price,
        "origin_station_id": origin,
        "destination_station_id": destination,
        "network_id": network_id,
    }
