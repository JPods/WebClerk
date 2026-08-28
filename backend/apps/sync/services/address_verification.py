"""Address Verification Supervisor.

Every WC3 installation can verify addresses and geocode for lat/lng
out of the box — no carrier account required. Nominatim (OpenStreetMap)
provides free address normalization and geocoding worldwide.

Carrier-specific validation is used when available (more precise for
shipping addresses), but the system works without any carrier configured.

Priority:
  1. Preferred carrier (if specified)
  2. Other configured carriers in order (USPS→UPS→FedEx→DHL for US)
  3. Nominatim (always available — free, no API key)

Lat/lng is the critical output: desktop-hosted WC3 installations use
proximity search ("products within 10 miles") for local commerce.
Every verified address gets geocoded.

WC2 heritage: address validation was manual. This replaces the gap.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from django.apps import apps

logger = logging.getLogger(__name__)

# Carrier priority for address validation (US, then non-US)
US_CARRIER_PRIORITY = ['usps', 'ups', 'fedex', 'dhl']
INTL_CARRIER_PRIORITY = ['ups', 'fedex', 'dhl']

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"


# ---------------------------------------------------------------------------
# Nominatim — free address verification + geocoding (always available)
# ---------------------------------------------------------------------------

def _nominatim_verify(address_parts: Dict[str, str]) -> Dict[str, Any]:
    """Verify and geocode an address using OpenStreetMap Nominatim.

    Nominatim does both: structured address lookup (verification) and
    geocoding (lat/lng) in a single call. Free, no API key, worldwide.
    Rate limit: 1 request per second per User-Agent.

    Returns:
        {valid, corrected: {address1, city, state, zip, country},
         latitude, longitude, display_name, match_score, messages}
    """
    try:
        import httpx
    except ImportError:
        return {"valid": False, "messages": ["httpx not installed"]}

    # Structured search gives better results than free-form
    params: Dict[str, str] = {
        "format": "json",
        "limit": "1",
        "addressdetails": "1",
    }

    # Use structured params when we have components
    street = address_parts.get("address1", "")
    city = address_parts.get("city", "")
    state = address_parts.get("state", "")
    postalcode = address_parts.get("zip", "")
    country = address_parts.get("country", "")

    if street or city:
        # Structured search
        if street:
            params["street"] = street
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if postalcode:
            params["postalcode"] = postalcode
        if country:
            params["countrycodes"] = _country_code(country)
    else:
        # Fallback: free-form query
        parts = [street, city, state, postalcode, country]
        query = ", ".join(p for p in parts if p)
        if not query:
            return {"valid": False, "messages": ["empty address"]}
        params["q"] = query

    try:
        resp = httpx.get(
            f"{NOMINATIM_BASE}/search",
            params=params,
            headers={"User-Agent": "WebClerk3/1.0 (address-verification)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"valid": False, "messages": [f"nominatim: {e}"]}

    if not data or not isinstance(data, list) or len(data) == 0:
        return {"valid": False, "messages": ["address not found"]}

    hit = data[0]
    addr = hit.get("address", {})
    lat = float(hit.get("lat", 0))
    lng = float(hit.get("lon", 0))

    # Normalize the returned address components
    corrected = {
        "address1": _build_street(addr),
        "address2": "",
        "city": addr.get("city", "") or addr.get("town", "") or addr.get("village", ""),
        "state": addr.get("state", ""),
        "zip": addr.get("postcode", ""),
        "country": addr.get("country_code", country).upper(),
        "full": hit.get("display_name", ""),
    }

    # Match score based on OSM importance + type
    importance = float(hit.get("importance", 0))
    osm_type = hit.get("type", "")
    if osm_type in ("house", "building", "residential"):
        score = min(int(importance * 100) + 20, 95)
    elif osm_type in ("street", "road"):
        score = min(int(importance * 100), 70)
    else:
        score = min(int(importance * 100), 50)

    return {
        "valid": True,
        "corrected": corrected,
        "latitude": lat,
        "longitude": lng,
        "match_score": score,
        "display_name": hit.get("display_name", ""),
        "osm_type": osm_type,
        "messages": [],
    }


def _build_street(addr: dict) -> str:
    """Build street address from Nominatim address components."""
    house = addr.get("house_number", "")
    road = addr.get("road", "") or addr.get("pedestrian", "") or addr.get("footway", "")
    if house and road:
        return f"{house} {road}"
    return road or house


def _country_code(country: str) -> str:
    """Normalize country to 2-letter code for Nominatim countrycodes param."""
    c = (country or "").strip().upper()
    mapping = {
        "UNITED STATES": "US", "USA": "US",
        "UNITED KINGDOM": "GB", "UK": "GB",
        "CANADA": "CA", "GERMANY": "DE", "FRANCE": "FR",
        "AUSTRALIA": "AU", "JAPAN": "JP", "CHINA": "CN",
    }
    return mapping.get(c, c[:2] if len(c) >= 2 else "US")


# ---------------------------------------------------------------------------
# Carrier validation helpers
# ---------------------------------------------------------------------------

def _get_carrier_connections() -> Dict[str, dict]:
    """Load all active carrier Connection records, keyed by carrier_code."""
    Connection = apps.get_model("sync", "Connection")
    carriers = {}
    for conn in Connection.objects.filter(type="carrier", is_active=True):
        config = getattr(conn, "config", {}) or {}
        code = config.get("carrier_code", "")
        if code:
            carriers[code] = config
    return carriers


def _try_carrier_validation(
    address_payload: Dict[str, Any],
    preferred_carrier: str | None = None,
) -> Dict[str, Any] | None:
    """Try carrier-specific address validation. Returns result or None.

    Carriers give more precise results for shipping addresses (apartment
    numbers, suite corrections, residential vs commercial classification).
    """
    from apps.transactions.services.fulfillment.carriers.base import (
        Address as CarrierAddress,
        get_carrier,
    )

    carrier_configs = _get_carrier_connections()
    if not carrier_configs:
        return None

    carrier_addr = CarrierAddress(
        street1=address_payload.get("address1", "") or address_payload.get("street1", ""),
        street2=address_payload.get("address2", "") or address_payload.get("street2", ""),
        city=address_payload.get("city", ""),
        state=address_payload.get("state", ""),
        zip_code=address_payload.get("zip", "") or address_payload.get("zip_code", ""),
        country=address_payload.get("country", "") or "US",
    )

    country = (address_payload.get("country", "") or "US").upper()
    is_us = country in ("US", "USA", "UNITED STATES", "")
    priority = list(US_CARRIER_PRIORITY if is_us else INTL_CARRIER_PRIORITY)

    if preferred_carrier and preferred_carrier in priority:
        priority.remove(preferred_carrier)
        priority.insert(0, preferred_carrier)

    messages: List[str] = []

    for code in priority:
        if code not in carrier_configs:
            continue
        try:
            carrier = get_carrier(carrier_configs[code])
            validation = carrier.validate_address(carrier_addr)
            corrected_dict = None
            if validation.corrected:
                corrected_dict = {
                    "address1": validation.corrected.street1 or "",
                    "address2": validation.corrected.street2 or "",
                    "city": validation.corrected.city or "",
                    "state": validation.corrected.state or "",
                    "zip": validation.corrected.zip_code or "",
                    "country": validation.corrected.country or "",
                }
            if validation.valid:
                return {
                    "valid": True,
                    "provider": code,
                    "corrected": corrected_dict,
                    "messages": validation.messages,
                    "match_score": 95,
                }
            messages.extend(validation.messages)
        except Exception as e:
            messages.append(f"{code}: {e}")
            logger.info("Carrier %s address validation failed: %s", code, e)

    return None  # No carrier succeeded


# ---------------------------------------------------------------------------
# Result normalization
# ---------------------------------------------------------------------------

def _normalize_result(
    provider: str,
    valid: bool,
    corrected: Optional[Dict[str, str]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    messages: Optional[List[str]] = None,
    match_score: int = 0,
) -> Dict[str, Any]:
    """Build a normalized result dict for apply_validation_result()."""
    result: Dict[str, Any] = {
        "provider": provider,
        "status": "verified" if valid else "not_verified",
        "match_score": match_score,
    }
    if corrected:
        result["normalized"] = corrected
    if latitude is not None:
        result["latitude"] = latitude
    if longitude is not None:
        result["longitude"] = longitude
    if messages:
        result["messages"] = messages
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_verification_connection(name: str | None = None):
    """Get a Connection record for address verification."""
    Connection = apps.get_model("sync", "Connection")
    qs = Connection.objects.filter(type="address_verification")
    if name:
        return qs.filter(name=name).first() or qs.first()
    return qs.first()


def verify_address(
    address_payload: Dict[str, Any],
    preferred_carrier: str | None = None,
) -> Dict[str, Any]:
    """Supervisor: verify address and geocode for lat/lng.

    Three-tier approach:
      1. Carrier validation (if any carriers configured) — most precise
         for shipping addresses (suite/apt correction, residential flag)
      2. Nominatim verification + geocoding — always available, free,
         worldwide. Handles normalization and lat/lng in one call.
      3. Geocode-only fallback — if Nominatim can't verify, still try
         to geocode the original address for lat/lng.

    Every WC3 installation gets address verification out of the box.
    Carrier accounts improve precision but are not required.

    Lat/lng is essential: desktop-hosted local commerce uses proximity
    search to find products within distance of the customer.

    Args:
        address_payload: {address1, address2, city, state, zip, country}
        preferred_carrier: optional carrier_code to try first

    Returns:
        {ok, result: {provider, status, match_score, normalized, latitude,
         longitude, messages}, bundle_id}
    """
    messages: List[str] = []
    corrected: Optional[Dict[str, str]] = None
    provider = "nominatim"
    is_valid = False
    match_score = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # --- Tier 1: Try carrier validation (if configured) -------------------
    carrier_result = _try_carrier_validation(address_payload, preferred_carrier)
    if carrier_result and carrier_result.get("valid"):
        provider = carrier_result["provider"]
        is_valid = True
        corrected = carrier_result.get("corrected")
        match_score = carrier_result.get("match_score", 95)
        messages = carrier_result.get("messages", [])

    # --- Tier 2: Nominatim verification + geocoding -----------------------
    # Always run Nominatim — even if carrier validated, we need lat/lng.
    # If carrier didn't validate, Nominatim is the primary validator.
    address_to_geocode = corrected or {
        "address1": address_payload.get("address1", ""),
        "address2": address_payload.get("address2", ""),
        "city": address_payload.get("city", ""),
        "state": address_payload.get("state", ""),
        "zip": address_payload.get("zip", ""),
        "country": address_payload.get("country", ""),
    }

    nom_result = _nominatim_verify(address_to_geocode)

    if nom_result.get("valid"):
        latitude = nom_result.get("latitude")
        longitude = nom_result.get("longitude")

        # If carrier didn't validate, use Nominatim as the validator
        if not is_valid:
            provider = "nominatim"
            is_valid = True
            corrected = nom_result.get("corrected")
            match_score = nom_result.get("match_score", 60)
        # If carrier did validate, just take the lat/lng
    else:
        # Nominatim couldn't find it either
        nom_msgs = nom_result.get("messages", [])
        messages.extend(nom_msgs)

    # --- Tier 3: Geocode-only fallback ------------------------------------
    # If Nominatim structured search failed, try free-form as last resort
    if latitude is None or longitude is None:
        geo_fallback = _geocode_freeform(address_to_geocode)
        if geo_fallback.get("latitude") is not None:
            latitude = geo_fallback["latitude"]
            longitude = geo_fallback["longitude"]

    # Build final result
    result = _normalize_result(
        provider=provider,
        valid=is_valid,
        corrected=corrected,
        latitude=latitude,
        longitude=longitude,
        messages=messages or (["verified"] if is_valid else ["could not verify"]),
        match_score=match_score,
    )

    bundle_id = _record_bundle(address_payload, result, provider)

    return {"ok": is_valid, "result": result, "bundle_id": bundle_id}


def _geocode_freeform(address_parts: Dict[str, str]) -> Dict[str, Optional[float]]:
    """Last-resort free-form geocode when structured search fails."""
    try:
        import httpx
    except ImportError:
        return {"latitude": None, "longitude": None}

    parts = [
        address_parts.get("address1", ""),
        address_parts.get("city", ""),
        address_parts.get("state", ""),
        address_parts.get("zip", ""),
        address_parts.get("country", ""),
    ]
    query = ", ".join(p for p in parts if p)
    if not query:
        return {"latitude": None, "longitude": None}

    try:
        resp = httpx.get(
            f"{NOMINATIM_BASE}/search",
            params={"q": query, "format": "json", "limit": "1"},
            headers={"User-Agent": "WebClerk3/1.0 (address-verification)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return {
                "latitude": float(data[0].get("lat", 0)),
                "longitude": float(data[0].get("lon", 0)),
            }
    except Exception as e:
        logger.warning("Freeform geocode failed: %s", e)

    return {"latitude": None, "longitude": None}


def _record_bundle(
    payload: Dict[str, Any],
    result: Dict[str, Any],
    provider: str,
) -> Optional[int]:
    """Record verification attempt as a Bundle for audit."""
    try:
        Bundle = apps.get_model("sync", "Bundle")
        conn = get_verification_connection()
        if not conn:
            Connection = apps.get_model("sync", "Connection")
            conn = Connection.objects.filter(type="carrier", is_active=True).first()
        if not conn:
            return None

        from apps.sync.services.email_verification import _mask_config
        cfg = getattr(conn, "config", {}) or {}

        b = Bundle.objects.create(
            connection=conn,
            direction="outbound",
            config=_mask_config(cfg),
            status="ok" if result.get("status") == "verified" else "warning",
            response={**result, "review": {"status": "pending"}},
            duration=0,
            payload={"address": payload},
            size=len(str(payload)) + len(str(result)),
        )
        return getattr(b, "id", None)
    except Exception as e:
        logger.warning("Failed to record address verification bundle: %s", e)
        return None
