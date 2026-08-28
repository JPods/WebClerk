"""
Pydantic schemas for Shipping Service Setting (purpose='wc:shipping_service').

Setting.config.service[] is the scannable registry — one line per carrier.
Connection.config carries the depth: service levels, rules, credentials.

Same pattern as payment gateway (config.gateway[]).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase


# ── Shipping service entry (Setting-level registry) ─────────────────
#
# Thin. Just enough to identify and display.
# Service levels, weight limits, surcharges, cutoff times —
# all live on Connection.config.

class ShippingServiceEntry(BaseModel):
    """One shipping carrier in the config.service array.

    Thin registry entry. Denormalized from Connection for scanning.
    Manual services (will-call, local delivery): connection_id is null.
    API carriers (FedEx, UPS): connection_id points to a Connection
    with CarrierCredentials and full carrier config.
    """
    name: str                                     # unique key
    type: str = 'manual'                          # manual | api
    carrier_code: str = ''                        # fedex, ups, usps, dhl
    account: str = ''                             # display label
    gl_account: str = ''                          # shipping expense/revenue GL
    is_default: bool = False
    # Connection pointer — denormalized for scanning
    connection_id: Optional[int] = None           # null = manual, no API
    connection_purpose: str = ''                  # Connection.purpose
    connection_status: str = ''                   # Connection.status

    class Config:
        extra = "forbid"


# ── Setting config ──────────────────────────────────────────────────

class ShippingServiceConfig(BaseModel):
    """Setting(purpose='wc:shipping_service').config structure.

    service[] is the scannable registry.
    Origin and dimensional divisor are installation-level.
    """
    service: list[ShippingServiceEntry] = Field(default_factory=list)
    default_origin_zip: str = ''
    default_origin_country: str = 'US'
    dimensional_weight_divisor: int = 139

    class Config:
        extra = "forbid"
