"""
JPods UI API — endpoints for the browser-based trip booking app.

Called by /jpods/trip/ (trip_app.html). All endpoints are relative to /wcapi/jpods/ui/.

Public (no auth):
  GET  ui/contacts/   — list contacts that have a myCarryOn token
  GET  ui/stations/   — available stations and valid route pairs
  POST ui/identify/   — exchange contact_id for myCarryOn token (demo: trust selection)

Protected (myCarryOn Bearer token):
  POST ui/price/      — personalized trip price for the identified rider
  POST ui/travel/     — post invoice + (future) dispatch pod via Natalie

DEMO NOTE: identify/ trusts the contact_id selection without additional verification.
In production, require OTP, biometric, or mycarryon.io credential before returning token.
"""

from __future__ import annotations

import logging
import uuid as uuid_module
from datetime import datetime

from rest_framework.permissions import BasePermission, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Contact
from apps.products.models import Item
from apps.jpods.services.pricing import get_trip_item, get_price, apply_discounts
from apps.jpods.services.invoice_service import create_trip_invoice
from apps.jpods.services.dispatch import dispatch

logger = logging.getLogger(__name__)

# Human-readable station names — update as the network grows
STATION_NAMES = {
    "S001": "Station 1",
    "S002": "Station 2",
    "S003": "Station 3",
    # S097–S100: SketchUp model stations — names are their IDs
}


class MyCarryOnPermission(BasePermission):
    """Validates Bearer token against contact.metadata['myCarryOn']['token'].

    Sets request.jpods_contact on success so views can use the resolved Contact directly.
    """

    def has_permission(self, request, view):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        token = auth[7:].strip()
        # Query by nested JSON key — works on PostgreSQL and SQLite (Django 4.2+)
        contact = Contact.objects.filter(
            metadata__myCarryOn__token=token,
            is_active=True,
        ).first()
        if contact:
            request.jpods_contact = contact
            return True
        return False


# ── Public endpoints ──────────────────────────────────────────────────────────

class ContactsView(APIView):
    """GET /wcapi/jpods/ui/contacts/ — contacts with a myCarryOn entry."""
    permission_classes = [AllowAny]

    def get(self, request):
        contacts = Contact.objects.filter(is_active=True).order_by("name_last", "name_first")
        data = []
        for c in contacts:
            if not (isinstance(c.metadata, dict) and "myCarryOn" in c.metadata):
                continue
            first = c.name_first or ""
            last = c.name_last or ""
            initials = (first[:1] + last[:1]).upper() or "?"
            data.append({
                "id": c.pk,
                "name": c.get_full_name(),
                "initials": initials,
            })
        return Response({"contacts": data})


class IdentifyView(APIView):
    """
    POST /wcapi/jpods/ui/identify/
    Body: {"contact_id": 5}

    Returns the myCarryOn token for the selected contact.
    DEMO ONLY — in production, require OTP / biometric before returning token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        contact_id  = request.data.get("contact_id")
        name_first  = request.data.get("name_first")

        if contact_id:
            try:
                contact = Contact.objects.get(pk=contact_id, is_active=True)
            except Contact.DoesNotExist:
                return Response({"error": "Contact not found"}, status=404)
        elif name_first:
            contact = Contact.objects.filter(
                name_first__iexact=name_first,
                is_active=True,
            ).first()
            if not contact:
                return Response({"error": f"No contact named '{name_first}'"}, status=404)
        else:
            return Response({"error": "contact_id or name_first required"}, status=400)

        mycarryon = (contact.metadata or {}).get("myCarryOn", {})
        token = mycarryon.get("token")
        if not token:
            return Response({"error": "Contact has no myCarryOn token"}, status=404)

        return Response({
            "token": token,
            "contact_id": contact.pk,
            "name": contact.get_full_name(),
            "uuid": mycarryon.get("uuid"),
            "status": mycarryon.get("status", "pending"),
        })


class StationsView(APIView):
    """GET /wcapi/jpods/ui/stations/ — station list and valid route pairs."""
    permission_classes = [AllowAny]

    def get(self, request):
        skus = Item.objects.filter(
            sku__startswith="JPODS-",
            kind=Item.KIND_SERVICE,
            is_active=True,
        ).values_list("sku", flat=True)

        station_ids = set()
        pairs = []

        for sku in skus:
            parts = sku.split("-")
            if len(parts) < 4:
                continue
            # JPODS-{NETWORK}-{ORIGIN}-{DESTINATION} — last two parts always origin/dest
            origin = parts[-2]
            destination = parts[-1]
            station_ids.add(origin)
            station_ids.add(destination)
            pairs.append([origin, destination])

        stations = [
            {"id": sid, "name": STATION_NAMES.get(sid, sid)}
            for sid in sorted(station_ids)
        ]

        return Response({"stations": stations, "pairs": pairs})


# ── Protected endpoints (myCarryOn Bearer token) ──────────────────────────────

class UIPriceView(APIView):
    """
    POST /wcapi/jpods/ui/price/
    Auth: myCarryOn Bearer token

    Body: {"origin_station_id": "S001", "destination_station_id": "S003"}
    Returns personalized price for the authenticated rider.
    """
    permission_classes = [MyCarryOnPermission]

    def post(self, request):
        contact = request.jpods_contact
        origin = request.data.get("origin_station_id", "")
        destination = request.data.get("destination_station_id", "")
        network_id = request.data.get("network_id", "default")

        if not origin or not destination:
            return Response(
                {"error": "origin_station_id and destination_station_id required"},
                status=400,
            )

        customer = contact.customer if contact.customer_id else None
        price_level = (customer.price_level or "retail") if customer else "retail"
        financial = (customer.financial or {}) if customer else {}

        item = get_trip_item(origin, destination, network_id)
        if not item:
            return Response(
                {"error": f"No route from {origin} to {destination}"},
                status=422,
            )

        try:
            base_price, currency = get_price(item, price_level)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=422)

        final_price, discount_label = apply_discounts(base_price, financial)

        display = f"{currency} {final_price:.2f}"
        if discount_label:
            display += f" ({discount_label})"
        elif price_level != "retail":
            display += f" ({price_level} rate)"

        return Response({
            "contact_id": contact.pk,
            "contact_name": contact.get_full_name(),
            "customer_id": customer.pk if customer else None,
            "item_id": item.pk,
            "price": str(final_price),
            "currency": currency,
            "price_level": price_level,
            "discount_applied": discount_label,
            "display": display,
            "origin_station_id": origin,
            "destination_station_id": destination,
            "origin_name": STATION_NAMES.get(origin, origin),
            "destination_name": STATION_NAMES.get(destination, destination),
            "network_id": network_id,
        })


class TravelView(APIView):
    """
    POST /wcapi/jpods/ui/travel/
    Auth: myCarryOn Bearer token

    Body: price response fields (origin, destination, price, item_id, etc.)
    Posts invoice to Alice. Pod dispatch wired when Natalie inbound API is ready.
    """
    permission_classes = [MyCarryOnPermission]

    def post(self, request):
        contact = request.jpods_contact
        origin = request.data.get("origin_station_id", "")
        destination = request.data.get("destination_station_id", "")
        price_str = request.data.get("price", "")
        currency = request.data.get("currency", "USD")
        item_id = request.data.get("item_id")
        price_level = request.data.get("price_level", "retail")
        discount_applied  = request.data.get("discount_applied")
        network_id        = request.data.get("network_id", "default")
        dispatch_target   = request.data.get("dispatch_target", "sketchup")

        if not origin or not destination or not price_str:
            return Response(
                {"error": "origin_station_id, destination_station_id, and price required"},
                status=400,
            )

        trip_id = f"T-{datetime.now().strftime('%Y%m%d')}-{str(uuid_module.uuid4())[:8].upper()}"

        result = create_trip_invoice({
            "contact_id": contact.pk,
            "item_id": item_id,
            "origin_station_id": origin,
            "destination_station_id": destination,
            "price": price_str,
            "currency": currency,
            "trip_id": trip_id,
            "price_level": price_level,
            "discount_applied": discount_applied,
            "network_id": network_id,
        })

        if "error" in result:
            return Response({"error": result["error"]}, status=422)

        # Dispatch to selected network (fire-and-log: failure does not cancel invoice)
        dispatch_result = dispatch(dispatch_target, {
            "trip_id":                trip_id,
            "origin_station_id":      origin,
            "destination_station_id": destination,
            "contact_name":           contact.get_full_name(),
            "price":                  price_str,
            "currency":               currency,
            "network_id":             network_id,
        })

        logger.info(
            "UI travel: %s %s→%s trip=%s invoice=%s",
            contact.get_full_name(), origin, destination, trip_id, result["invoice_id"],
        )

        try:
            price_float = float(price_str)
            display = f"{currency} {price_float:.2f}"
        except (ValueError, TypeError):
            display = f"{currency} {price_str}"

        return Response({
            "trip_id":                trip_id,
            "invoice_id":             result["invoice_id"],
            "status":                 "dispatched",
            "dispatch_target":        dispatch_target,
            "dispatch_ok":            dispatch_result.get("ok", False),
            "dispatch_note":          dispatch_result.get("error") if not dispatch_result.get("ok") else None,
            "contact_name":           contact.get_full_name(),
            "origin_station_id":      origin,
            "destination_station_id": destination,
            "origin_name":            STATION_NAMES.get(origin, origin),
            "destination_name":       STATION_NAMES.get(destination, destination),
            "price":                  price_str,
            "currency":               currency,
            "display":                display,
        }, status=201)
