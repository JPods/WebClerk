"""
Carrier abstraction — one interface, every carrier.

Each carrier is a Connection record with credentials in config.
The carrier type selects the implementation class. User adds their
API keys in the Connection record and the carrier is live.

No local rate tables. If the API is down, rates are unavailable.
Stale data is worse than no data.

Carrier implementations:
  carriers/ups.py    — UPS REST OAuth 2.0
  carriers/fedex.py  — FedEx REST
  carriers/usps.py   — USPS Ground Advantage
  carriers/dhl.py    — DHL Express

WC2 heritage:
  - Fuel surcharge, handling, insurance as carrier-level config
  - Hundred-weight threshold (>150 lbs)
  - Business-day back-calculation for ship-on-date
  - ASN email pattern
  All live in the Connection config, not in code.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes — carrier-agnostic
# ---------------------------------------------------------------------------

@dataclass
class Address:
    name: str = ''
    company: str = ''
    street1: str = ''
    street2: str = ''
    city: str = ''
    state: str = ''
    zip_code: str = ''
    country: str = 'US'
    phone: str = ''
    email: str = ''
    is_residential: bool = False


@dataclass
class Package:
    weight_lbs: float = 0.0
    length_in: float = 0.0
    width_in: float = 0.0
    height_in: float = 0.0
    declared_value: float = 0.0
    is_hazmat: bool = False
    description: str = ''


@dataclass
class Rate:
    """One rate option returned by get_rates()."""
    carrier: str = ''            # 'ups', 'fedex', 'usps', 'dhl'
    service_code: str = ''       # carrier-specific service code
    service_name: str = ''       # human-readable: "UPS Ground", "FedEx 2Day"
    total_cost: float = 0.0      # all-in cost to customer
    base_cost: float = 0.0       # before surcharges
    fuel_surcharge: float = 0.0
    handling: float = 0.0
    insurance: float = 0.0
    currency: str = 'USD'
    transit_days: int = 0
    delivery_date: Optional[str] = None  # ISO date
    guaranteed: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)  # full API response


@dataclass
class Shipment:
    """Result of create_shipment()."""
    carrier: str = ''
    tracking_number: str = ''
    service_code: str = ''
    service_name: str = ''
    total_cost: float = 0.0
    label_format: str = ''       # 'pdf', 'gif', 'zpl', 'png'
    label_data: bytes = b''      # raw label content
    label_url: str = ''          # if carrier returns a URL instead
    ship_date: str = ''          # ISO date
    delivery_date: str = ''
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackingEvent:
    timestamp: str = ''          # ISO datetime UTC
    status: str = ''             # 'in_transit', 'delivered', 'exception', etc.
    description: str = ''
    location: str = ''
    city: str = ''
    state: str = ''
    zip_code: str = ''
    country: str = ''


@dataclass
class TrackingResult:
    carrier: str = ''
    tracking_number: str = ''
    status: str = ''             # current status
    delivered: bool = False
    delivery_date: str = ''
    events: List[TrackingEvent] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AddressValidation:
    valid: bool = False
    corrected: Optional[Address] = None
    messages: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Base class — every carrier implements this
# ---------------------------------------------------------------------------

class CarrierBase(ABC):
    """Abstract carrier interface.

    Subclasses implement the wire protocol for each carrier's REST API.
    The Connection record's config provides credentials and carrier-specific
    settings (account number, meter number, markup percentage, etc.).
    """

    carrier_code: str = ''       # 'ups', 'fedex', 'usps', 'dhl'
    carrier_name: str = ''       # 'UPS', 'FedEx', 'USPS', 'DHL Express'

    def __init__(self, connection_config: Dict[str, Any]):
        """Initialize with the Connection record's config dict."""
        self.config = connection_config
        self.credentials = connection_config.get('credentials', {})
        self.settings = connection_config.get('settings', {})

    # -- Surcharges (from WC2 carrier-level fields, now in config) ----------

    def apply_surcharges(self, rate: Rate) -> Rate:
        """Apply carrier-level surcharges from Connection config.

        WC2 heritage: fuel_factor, handling_charge, insurance logic.
        These are additive on top of what the API returns.
        """
        s = self.settings

        # Fuel surcharge (percentage of base — some carriers include this,
        # some don't; config.apply_fuel controls whether we add it)
        if s.get('apply_fuel') and s.get('fuel_factor'):
            fuel = rate.base_cost * float(s['fuel_factor'])
            rate.fuel_surcharge += fuel
            rate.total_cost += fuel

        # Handling charge (flat per package)
        handling = float(s.get('handling_charge', 0))
        if handling:
            rate.handling += handling
            rate.total_cost += handling

        # Markup percentage (WC2: FedEx had 10% markup then round to dollar)
        markup_pct = float(s.get('markup_percent', 0))
        if markup_pct:
            markup = rate.total_cost * (markup_pct / 100)
            rate.total_cost += markup

        return rate

    # -- Abstract methods — each carrier implements --------------------------

    @abstractmethod
    def get_rates(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        ship_date: Optional[date] = None,
    ) -> List[Rate]:
        """Get available rates for a shipment.

        Returns multiple Rate objects — one per service level
        (Ground, 2Day, Next Day, etc.). Sorted by cost ascending.
        """
        ...

    @abstractmethod
    def create_shipment(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        service_code: str,
        ship_date: Optional[date] = None,
        reference: str = '',
    ) -> Shipment:
        """Create a shipment and get a label.

        Returns a Shipment with tracking number and label data.
        Label comes back as PDF, GIF, ZPL, or PNG depending on
        config.label_format preference.
        """
        ...

    @abstractmethod
    def track(self, tracking_number: str) -> TrackingResult:
        """Get tracking status and event history."""
        ...

    def validate_address(self, address: Address) -> AddressValidation:
        """Validate and optionally correct an address.

        Default: returns valid=True (no validation). Carriers that
        support address validation override this.
        """
        return AddressValidation(valid=True)

    def cancel_shipment(self, tracking_number: str) -> bool:
        """Cancel/void a shipment. Returns True if successful.

        Default: raises NotImplementedError. Not all carriers support this.
        """
        raise NotImplementedError(f'{self.carrier_name} cancel not implemented')


# ---------------------------------------------------------------------------
# Registry — carrier_code → class
# ---------------------------------------------------------------------------

_CARRIER_REGISTRY: Dict[str, type] = {}


def register_carrier(cls: type) -> type:
    """Decorator to register a carrier implementation."""
    code = getattr(cls, 'carrier_code', '')
    if code:
        _CARRIER_REGISTRY[code] = cls
    return cls


def get_carrier(connection_config: Dict[str, Any]) -> CarrierBase:
    """Instantiate the right carrier from a Connection config.

    The config must have 'carrier_code' (e.g. 'ups', 'fedex').
    """
    code = connection_config.get('carrier_code', '')
    cls = _CARRIER_REGISTRY.get(code)
    if not cls:
        raise ValueError(
            f"Unknown carrier code '{code}'. "
            f"Available: {list(_CARRIER_REGISTRY.keys())}"
        )
    return cls(connection_config)


def available_carriers() -> List[str]:
    """Return list of registered carrier codes."""
    return list(_CARRIER_REGISTRY.keys())
