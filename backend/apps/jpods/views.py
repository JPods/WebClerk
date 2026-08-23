"""
JPods Alice API — trip pricing and invoicing endpoints.

    POST /wcapi/jpods/price/    — Natalie asks Alice: what does this trip cost for this person?
    POST /wcapi/jpods/invoice/  — Natalie tells Alice: trip complete, post the invoice.

Authentication: Bearer token checked against the "natalie" Connection record.
During development: token is plaintext in Connection.config["token"].
Before release: encrypt Connection.config and add blockchain audit trail for key changes.
  → Alice action record created by seed_jpods_demo management command (review 2026-05-29).
"""

import logging

from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from common.api_responses import api_response
from apps.sync.models import Connection
from apps.jpods.services.pricing import resolve_price_query
from apps.jpods.services.invoice_service import create_trip_invoice

logger = logging.getLogger(__name__)


class JpodTokenPermission(BasePermission):
    """
    Validates Bearer token against the active 'natalie' Connection record in Alice.
    Token is stored plaintext in Connection.config["token"] during development.
    Replace with encrypted + blockchain-audited key before release.
    """

    def has_permission(self, request, view):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        token = auth[7:].strip()
        return Connection.objects.filter(
            name="natalie",
            status="active",
            config__token=token,
        ).exists()


class PriceQueryView(APIView):
    """
    POST /wcapi/jpods/price/

    Natalie asks Alice what a trip costs for a specific rider before dispatching the pod.
    Alice resolves the Contact, finds their Customer, looks up the pricing rule, applies
    any discounts, and returns the personalized price.

    Body:
        contact_uuid    string  optional  CarryOn UUID (most reliable lookup)
        email           string  optional  rider email
        name            string  optional  "Bill James" (demo name lookup)
        origin_station_id      string  required  e.g. "S001"
        destination_station_id string  required  e.g. "S003"
        network_id      string  optional  default "default"

    Response:
        contact_id, contact_name, customer_id,
        price, currency, price_level, discount_applied, display
    """

    permission_classes = [JpodTokenPermission]

    def post(self, request):
        result = resolve_price_query(request.data)
        if "error" in result:
            return api_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=result["error"],
                error_code="price_query_failed",
            )
        return api_response(data=result)


class InvoiceView(APIView):
    """
    POST /wcapi/jpods/invoice/

    Natalie posts trip actuals to Alice after the pod reaches its destination.
    Alice creates a completed Invoice linked to the Contact and Customer.

    Body:
        contact_id             int     required  from price_query response
        origin_station_id      string  required  e.g. "S001"
        destination_station_id string  required  e.g. "S003"
        price                  string  required  decimal, from price_query response
        currency               string  required  e.g. "USD"
        trip_id                string  optional  Natalie's internal trip ID
        duration_actual_s      int     optional  actual trip duration in seconds
        price_level            string  optional  for record-keeping
        discount_applied       string  optional  discount label
        network_id             string  optional  default "default"

    Response:
        invoice_id, status, total, currency, contact_name, customer_id, trip_id
    """

    permission_classes = [JpodTokenPermission]

    def post(self, request):
        result = create_trip_invoice(request.data)
        if "error" in result:
            return api_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=result["error"],
                error_code="invoice_failed",
            )
        return api_response(
            status_code=status.HTTP_201_CREATED,
            data=result,
        )
