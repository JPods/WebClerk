"""
UPS REST API carrier implementation.

UPS migrated from XML toolkit to OAuth 2.0 REST APIs in 2023-2024.
Endpoints: https://onlinetools.ups.com/api/

Authentication: OAuth 2.0 client credentials flow.
  1. POST /security/v1/oauth/token with client_id + client_secret
  2. Bearer token in Authorization header for all subsequent calls
  Token TTL: ~4 hours. Cache and refresh.

Connection config.credentials:
  client_id       — UPS developer app client ID
  client_secret   — UPS developer app client secret
  account_number  — UPS shipper account number

Connection config.settings:
  label_format    — 'pdf' (default), 'gif', 'zpl', 'png'
  test_mode       — True = use sandbox (cwu.ups.com), False = production
  fuel_factor     — decimal surcharge (0.0 if UPS includes it in rates)
  handling_charge — flat per-package handling
  markup_percent  — percentage markup on total
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    Address, AddressValidation, CarrierBase, Package, Rate,
    Shipment, TrackingEvent, TrackingResult, register_carrier,
)

logger = logging.getLogger(__name__)

PRODUCTION_BASE = 'https://onlinetools.ups.com'
SANDBOX_BASE = 'https://wwwcie.ups.com'

# UPS service codes → human names
UPS_SERVICES = {
    '01': 'UPS Next Day Air',
    '02': 'UPS 2nd Day Air',
    '03': 'UPS Ground',
    '07': 'UPS Worldwide Express',
    '08': 'UPS Worldwide Expedited',
    '11': 'UPS Standard',
    '12': 'UPS 3 Day Select',
    '13': 'UPS Next Day Air Saver',
    '14': 'UPS Next Day Air Early',
    '54': 'UPS Worldwide Express Plus',
    '59': 'UPS 2nd Day Air A.M.',
    '65': 'UPS Saver',
    '92': 'UPS SurePost Less Than 1 lb',
    '93': 'UPS SurePost 1 lb or Greater',
    '94': 'UPS SurePost BPM',
    '95': 'UPS SurePost Media',
}


@register_carrier
class UPSCarrier(CarrierBase):
    carrier_code = 'ups'
    carrier_name = 'UPS'

    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self._token: str = ''
        self._token_expires: float = 0
        self._test_mode = self.settings.get('test_mode', False)
        self._base = SANDBOX_BASE if self._test_mode else PRODUCTION_BASE

    # -- Auth ---------------------------------------------------------------

    def _get_token(self) -> str:
        """Get or refresh OAuth 2.0 bearer token."""
        if self._token and time.time() < self._token_expires:
            return self._token

        url = f'{self._base}/security/v1/oauth/token'
        resp = httpx.post(
            url,
            data={'grant_type': 'client_credentials'},
            auth=(self.credentials['client_id'], self.credentials['client_secret']),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data['access_token']
        self._token_expires = time.time() + int(data.get('expires_in', 14400)) - 60
        return self._token

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
            'transId': f'wc3-{int(time.time())}',
            'transactionSrc': 'webclerk3',
        }

    # -- Rates --------------------------------------------------------------

    def get_rates(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        ship_date: Optional[date] = None,
    ) -> List[Rate]:
        url = f'{self._base}/api/rating/v1/Shop'
        ship_dt = (ship_date or date.today()).strftime('%Y%m%d')

        payload = {
            'RateRequest': {
                'Request': {'SubVersion': '2403'},
                'Shipment': {
                    'Shipper': {
                        'ShipperNumber': self.credentials.get('account_number', ''),
                        'Address': _ups_address(origin),
                    },
                    'ShipTo': {'Address': _ups_address(destination)},
                    'ShipFrom': {'Address': _ups_address(origin)},
                    'DeliveryTimeInformation': {
                        'PackageBillType': '03',
                        'Pickup': {'Date': ship_dt},
                    },
                    'Package': [_ups_package(p) for p in packages],
                },
            }
        }

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        rates = []
        rated_shipments = data.get('RateResponse', {}).get('RatedShipment', [])
        if not isinstance(rated_shipments, list):
            rated_shipments = [rated_shipments]

        for rs in rated_shipments:
            svc = rs.get('Service', {})
            code = svc.get('Code', '')
            charges = rs.get('TotalCharges', {})
            transit = rs.get('TimeInTransit', {}).get('ServiceSummary', {})

            rate = Rate(
                carrier='ups',
                service_code=code,
                service_name=UPS_SERVICES.get(code, f'UPS Service {code}'),
                base_cost=float(charges.get('MonetaryValue', 0)),
                total_cost=float(charges.get('MonetaryValue', 0)),
                currency=charges.get('CurrencyCode', 'USD'),
                transit_days=int(transit.get('EstimatedArrival', {}).get('BusinessDaysInTransit', 0) or 0),
                delivery_date=transit.get('EstimatedArrival', {}).get('Arrival', {}).get('Date', ''),
                guaranteed=transit.get('Guaranteed', {}).get('Code', '') == 'Y',
                raw=rs,
            )
            rate = self.apply_surcharges(rate)
            rates.append(rate)

        rates.sort(key=lambda r: r.total_cost)
        return rates

    # -- Create shipment + label -------------------------------------------

    def create_shipment(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        service_code: str,
        ship_date: Optional[date] = None,
        reference: str = '',
    ) -> Shipment:
        url = f'{self._base}/api/shipments/v2403/ship'
        label_fmt = self.settings.get('label_format', 'pdf').upper()
        fmt_map = {'PDF': 'PDF', 'GIF': 'GIF', 'ZPL': 'ZPL', 'PNG': 'PNG'}
        label_code = fmt_map.get(label_fmt, 'PDF')

        pkg_list = []
        for p in packages:
            pkg = _ups_package(p)
            pkg['PackageServiceOptions'] = {}
            if p.declared_value:
                pkg['PackageServiceOptions']['DeclaredValue'] = {
                    'CurrencyCode': 'USD',
                    'MonetaryValue': str(round(p.declared_value, 2)),
                }
            pkg_list.append(pkg)

        payload = {
            'ShipmentRequest': {
                'Request': {'SubVersion': '2403'},
                'Shipment': {
                    'Shipper': {
                        'ShipperNumber': self.credentials.get('account_number', ''),
                        'Name': origin.company or origin.name,
                        'Phone': {'Number': origin.phone or '0000000000'},
                        'Address': _ups_address(origin),
                    },
                    'ShipTo': {
                        'Name': destination.company or destination.name,
                        'Phone': {'Number': destination.phone or '0000000000'},
                        'Address': _ups_address(destination),
                    },
                    'ShipFrom': {
                        'Name': origin.company or origin.name,
                        'Phone': {'Number': origin.phone or '0000000000'},
                        'Address': _ups_address(origin),
                    },
                    'Service': {'Code': service_code},
                    'Package': pkg_list,
                    'PaymentInformation': {
                        'ShipmentCharge': [{
                            'Type': '01',
                            'BillShipper': {
                                'AccountNumber': self.credentials.get('account_number', ''),
                            },
                        }],
                    },
                },
                'LabelSpecification': {
                    'LabelImageFormat': {'Code': label_code},
                    'LabelStockSize': {'Height': '6', 'Width': '4'},
                },
            }
        }

        if reference:
            for pkg in payload['ShipmentRequest']['Shipment']['Package']:
                pkg['ReferenceNumber'] = [{'Value': reference[:35]}]

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        ship_result = data.get('ShipmentResponse', {}).get('ShipmentResults', {})
        tracking = ship_result.get('PackageResults', [])
        if isinstance(tracking, dict):
            tracking = [tracking]

        track_num = tracking[0].get('TrackingNumber', '') if tracking else ''
        label_img = tracking[0].get('ShippingLabel', {}).get('GraphicImage', '') if tracking else ''
        charges = ship_result.get('ShipmentCharges', {}).get('TotalCharges', {})

        import base64
        label_bytes = base64.b64decode(label_img) if label_img else b''

        return Shipment(
            carrier='ups',
            tracking_number=track_num,
            service_code=service_code,
            service_name=UPS_SERVICES.get(service_code, service_code),
            total_cost=float(charges.get('MonetaryValue', 0)),
            label_format=label_code.lower(),
            label_data=label_bytes,
            ship_date=(ship_date or date.today()).isoformat(),
            raw=data,
        )

    # -- Tracking -----------------------------------------------------------

    def track(self, tracking_number: str) -> TrackingResult:
        url = f'{self._base}/api/track/v1/details/{tracking_number}'
        params = {'locale': 'en_US', 'returnSignature': 'false'}

        resp = httpx.get(url, params=params, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        pkg = (data.get('trackResponse', {}).get('shipment', [{}])[0]
               .get('package', [{}])[0])
        activities = pkg.get('activity', [])

        events = []
        for act in activities:
            loc = act.get('location', {}).get('address', {})
            events.append(TrackingEvent(
                timestamp=act.get('date', '') + 'T' + act.get('time', ''),
                status=act.get('status', {}).get('type', ''),
                description=act.get('status', {}).get('description', ''),
                city=loc.get('city', ''),
                state=loc.get('stateProvince', ''),
                zip_code=loc.get('postalCode', ''),
                country=loc.get('country', ''),
            ))

        current = pkg.get('currentStatus', {})
        delivered = current.get('type', '') == 'D'

        return TrackingResult(
            carrier='ups',
            tracking_number=tracking_number,
            status=current.get('description', ''),
            delivered=delivered,
            delivery_date=pkg.get('deliveryDate', [{}])[0].get('date', '') if delivered else '',
            events=events,
            raw=data,
        )

    # -- Address validation -------------------------------------------------

    def validate_address(self, address: Address) -> AddressValidation:
        url = f'{self._base}/api/addressvalidation/v1/1'
        payload = {
            'XAVRequest': {
                'AddressKeyFormat': {
                    'AddressLine': [address.street1, address.street2],
                    'PoliticalDivision2': address.city,
                    'PoliticalDivision1': address.state,
                    'PostcodePrimaryLow': address.zip_code,
                    'CountryCode': address.country,
                },
            }
        }

        try:
            resp = httpx.post(url, json=payload, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return AddressValidation(valid=True, messages=[f'Validation unavailable: {e}'])

        xav = data.get('XAVResponse', {})
        valid_indicator = xav.get('ValidAddressIndicator')
        ambiguous = xav.get('AmbiguousAddressIndicator')

        if valid_indicator is not None:
            candidate = xav.get('Candidate', {})
            if isinstance(candidate, list):
                candidate = candidate[0] if candidate else {}
            addr_fmt = candidate.get('AddressKeyFormat', {})
            corrected = Address(
                street1=(addr_fmt.get('AddressLine', [''])[0] if isinstance(addr_fmt.get('AddressLine'), list) else addr_fmt.get('AddressLine', '')),
                city=addr_fmt.get('PoliticalDivision2', ''),
                state=addr_fmt.get('PoliticalDivision1', ''),
                zip_code=addr_fmt.get('PostcodePrimaryLow', ''),
                country=addr_fmt.get('CountryCode', address.country),
            )
            return AddressValidation(valid=True, corrected=corrected)

        if ambiguous is not None:
            return AddressValidation(valid=False, messages=['Address is ambiguous — multiple matches'])

        return AddressValidation(valid=False, messages=['Address not found'])

    # -- Cancel -------------------------------------------------------------

    def cancel_shipment(self, tracking_number: str) -> bool:
        url = f'{self._base}/api/shipments/v2403/void/1Z{tracking_number}'
        resp = httpx.delete(url, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status = data.get('VoidShipmentResponse', {}).get('SummaryResult', {}).get('Status', {})
        return status.get('Code', '') == '1'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ups_address(addr: Address) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        'AddressLine': [addr.street1],
        'City': addr.city,
        'StateProvinceCode': addr.state,
        'PostalCode': addr.zip_code,
        'CountryCode': addr.country or 'US',
    }
    if addr.street2:
        result['AddressLine'].append(addr.street2)
    if addr.is_residential:
        result['ResidentialAddressIndicator'] = ''
    return result


def _ups_package(pkg: Package) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        'PackagingType': {'Code': '02'},  # 02 = Customer Supplied Package
        'PackageWeight': {
            'UnitOfMeasurement': {'Code': 'LBS'},
            'Weight': str(round(max(pkg.weight_lbs, 0.1), 1)),
        },
    }
    if pkg.length_in and pkg.width_in and pkg.height_in:
        result['Dimensions'] = {
            'UnitOfMeasurement': {'Code': 'IN'},
            'Length': str(round(pkg.length_in, 1)),
            'Width': str(round(pkg.width_in, 1)),
            'Height': str(round(pkg.height_in, 1)),
        }
    return result
