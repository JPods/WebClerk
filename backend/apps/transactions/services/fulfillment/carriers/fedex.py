"""
FedEx REST API carrier implementation.

FedEx migrated from SOAP/WSDL to REST APIs in 2023-2024.
Endpoints: https://apis.fedex.com/

Authentication: OAuth 2.0 client credentials flow.
  POST /oauth/token with client_id + client_secret + grant_type
  Bearer token for all subsequent calls.

Connection config.credentials:
  client_id       — FedEx developer app API key
  client_secret   — FedEx developer app secret key
  account_number  — FedEx account number

Connection config.settings:
  label_format    — 'pdf' (default), 'png', 'zpl'
  test_mode       — True = sandbox, False = production
  markup_percent  — WC2 heritage: FedEx had 10% markup then round to dollar
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

PRODUCTION_BASE = 'https://apis.fedex.com'
SANDBOX_BASE = 'https://apis-sandbox.fedex.com'

FEDEX_SERVICES = {
    'FEDEX_GROUND': 'FedEx Ground',
    'GROUND_HOME_DELIVERY': 'FedEx Home Delivery',
    'FEDEX_EXPRESS_SAVER': 'FedEx Express Saver',
    'FEDEX_2_DAY': 'FedEx 2Day',
    'FEDEX_2_DAY_AM': 'FedEx 2Day A.M.',
    'STANDARD_OVERNIGHT': 'FedEx Standard Overnight',
    'PRIORITY_OVERNIGHT': 'FedEx Priority Overnight',
    'FIRST_OVERNIGHT': 'FedEx First Overnight',
    'INTERNATIONAL_ECONOMY': 'FedEx International Economy',
    'INTERNATIONAL_PRIORITY': 'FedEx International Priority',
    'INTERNATIONAL_FIRST': 'FedEx International First',
    'FEDEX_FREIGHT_ECONOMY': 'FedEx Freight Economy',
    'FEDEX_FREIGHT_PRIORITY': 'FedEx Freight Priority',
    'SMART_POST': 'FedEx SmartPost',
}


@register_carrier
class FedExCarrier(CarrierBase):
    carrier_code = 'fedex'
    carrier_name = 'FedEx'

    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self._token: str = ''
        self._token_expires: float = 0
        self._test_mode = self.settings.get('test_mode', False)
        self._base = SANDBOX_BASE if self._test_mode else PRODUCTION_BASE

    # -- Auth ---------------------------------------------------------------

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires:
            return self._token

        resp = httpx.post(
            f'{self._base}/oauth/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': self.credentials['client_id'],
                'client_secret': self.credentials['client_secret'],
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data['access_token']
        self._token_expires = time.time() + int(data.get('expires_in', 3600)) - 60
        return self._token

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
            'X-locale': 'en_US',
        }

    # -- Rates --------------------------------------------------------------

    def get_rates(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        ship_date: Optional[date] = None,
    ) -> List[Rate]:
        url = f'{self._base}/rate/v1/rates/quotes'
        ship_dt = (ship_date or date.today()).isoformat()

        payload = {
            'accountNumber': {'value': self.credentials.get('account_number', '')},
            'requestedShipment': {
                'shipper': {'address': _fedex_address(origin)},
                'recipient': {'address': _fedex_address(destination)},
                'pickupType': 'DROPOFF_AT_FEDEX_LOCATION',
                'rateRequestType': ['ACCOUNT', 'LIST'],
                'shipDateStamp': ship_dt,
                'requestedPackageLineItems': [_fedex_package(p, i) for i, p in enumerate(packages)],
            },
        }

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        rates = []
        for detail in data.get('output', {}).get('rateReplyDetails', []):
            code = detail.get('serviceType', '')
            rated = detail.get('ratedShipmentDetails', [{}])
            # Prefer account rate, fall back to list
            best = rated[0] if rated else {}
            charges = best.get('totalNetCharge', 0)
            transit = detail.get('commit', {})

            rate = Rate(
                carrier='fedex',
                service_code=code,
                service_name=FEDEX_SERVICES.get(code, code),
                base_cost=float(charges),
                total_cost=float(charges),
                currency=best.get('currency', 'USD'),
                transit_days=int(transit.get('transitDays', {}).get('description', '0') or '0'),
                delivery_date=transit.get('dateDetail', {}).get('dayFormat', ''),
                raw=detail,
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
        url = f'{self._base}/ship/v1/shipments'
        label_fmt = self.settings.get('label_format', 'pdf').upper()
        fmt_map = {'PDF': 'PDF', 'PNG': 'PNG', 'ZPL': 'ZPLII'}

        pkg_list = [_fedex_package(p, i) for i, p in enumerate(packages)]
        if reference:
            for pkg in pkg_list:
                pkg['customerReferences'] = [{'customerReferenceType': 'CUSTOMER_REFERENCE', 'value': reference[:35]}]

        payload = {
            'accountNumber': {'value': self.credentials.get('account_number', '')},
            'labelResponseOptions': 'LABEL',
            'requestedShipment': {
                'shipper': {
                    'address': _fedex_address(origin),
                    'contact': {'personName': origin.name, 'phoneNumber': origin.phone or '0000000000', 'companyName': origin.company},
                },
                'recipients': [{
                    'address': _fedex_address(destination),
                    'contact': {'personName': destination.name, 'phoneNumber': destination.phone or '0000000000', 'companyName': destination.company},
                }],
                'pickupType': 'DROPOFF_AT_FEDEX_LOCATION',
                'serviceType': service_code,
                'packagingType': 'YOUR_PACKAGING',
                'shippingChargesPayment': {
                    'paymentType': 'SENDER',
                    'payor': {'responsibleParty': {'accountNumber': {'value': self.credentials.get('account_number', '')}}},
                },
                'labelSpecification': {
                    'labelFormatType': 'COMMON2D',
                    'imageType': fmt_map.get(label_fmt, 'PDF'),
                    'labelStockType': 'PAPER_4X6',
                },
                'requestedPackageLineItems': pkg_list,
            },
        }

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        output = data.get('output', {}).get('transactionShipments', [{}])[0]
        pieces = output.get('pieceResponses', [{}])
        track_num = pieces[0].get('trackingNumber', '') if pieces else output.get('masterTrackingNumber', '')
        label_b64 = pieces[0].get('packageDocuments', [{}])[0].get('encodedLabel', '') if pieces else ''
        charges = output.get('shipmentAdvisoryDetails', {}).get('totalNetCharge', 0)

        import base64
        label_bytes = base64.b64decode(label_b64) if label_b64 else b''

        return Shipment(
            carrier='fedex',
            tracking_number=track_num,
            service_code=service_code,
            service_name=FEDEX_SERVICES.get(service_code, service_code),
            total_cost=float(charges) if charges else 0,
            label_format=label_fmt.lower(),
            label_data=label_bytes,
            ship_date=(ship_date or date.today()).isoformat(),
            raw=data,
        )

    # -- Tracking -----------------------------------------------------------

    def track(self, tracking_number: str) -> TrackingResult:
        url = f'{self._base}/track/v1/trackingnumbers'
        payload = {
            'includeDetailedScans': True,
            'trackingInfo': [{'trackingNumberInfo': {'trackingNumber': tracking_number}}],
        }

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = data.get('output', {}).get('completeTrackResults', [{}])[0]
        track_result = results.get('trackResults', [{}])[0]
        status_detail = track_result.get('latestStatusDetail', {})
        scan_events = track_result.get('scanEvents', [])

        events = []
        for evt in scan_events:
            loc = evt.get('scanLocation', {})
            events.append(TrackingEvent(
                timestamp=evt.get('date', ''),
                status=evt.get('derivedStatus', ''),
                description=evt.get('eventDescription', ''),
                city=loc.get('city', ''),
                state=loc.get('stateOrProvinceCode', ''),
                zip_code=loc.get('postalCode', ''),
                country=loc.get('countryCode', ''),
            ))

        delivered = status_detail.get('code', '') == 'DL'

        return TrackingResult(
            carrier='fedex',
            tracking_number=tracking_number,
            status=status_detail.get('description', ''),
            delivered=delivered,
            delivery_date=track_result.get('estimatedDeliveryTimeWindow', {}).get('window', {}).get('ends', ''),
            events=events,
            raw=data,
        )

    # -- Address validation -------------------------------------------------

    def validate_address(self, address: Address) -> AddressValidation:
        url = f'{self._base}/address/v1/addresses/resolve'
        payload = {
            'addressesToValidate': [{
                'address': _fedex_address(address),
            }],
        }

        try:
            resp = httpx.post(url, json=payload, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return AddressValidation(valid=True, messages=[f'Validation unavailable: {e}'])

        results = data.get('output', {}).get('resolvedAddresses', [])
        if not results:
            return AddressValidation(valid=False, messages=['Address not found'])

        best = results[0]
        classification = best.get('classification', '')
        resolved = best.get('streetLinesToken', [])

        corrected = Address(
            street1=resolved[0] if resolved else address.street1,
            street2=resolved[1] if len(resolved) > 1 else '',
            city=best.get('city', address.city),
            state=best.get('stateOrProvinceCode', address.state),
            zip_code=best.get('postalCode', address.zip_code),
            country=best.get('countryCode', address.country),
            is_residential=classification == 'RESIDENTIAL',
        )

        return AddressValidation(
            valid=True,
            corrected=corrected,
            messages=[f'Classification: {classification}'] if classification else [],
        )

    # -- Cancel -------------------------------------------------------------

    def cancel_shipment(self, tracking_number: str) -> bool:
        url = f'{self._base}/ship/v1/shipments/cancel'
        payload = {
            'accountNumber': {'value': self.credentials.get('account_number', '')},
            'trackingNumber': tracking_number,
        }
        resp = httpx.put(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fedex_address(addr: Address) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        'streetLines': [addr.street1],
        'city': addr.city,
        'stateOrProvinceCode': addr.state,
        'postalCode': addr.zip_code,
        'countryCode': addr.country or 'US',
    }
    if addr.street2:
        result['streetLines'].append(addr.street2)
    if addr.is_residential:
        result['residential'] = True
    return result


def _fedex_package(pkg: Package, index: int = 0) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        'sequenceNumber': index + 1,
        'weight': {'units': 'LB', 'value': round(max(pkg.weight_lbs, 0.1), 1)},
    }
    if pkg.length_in and pkg.width_in and pkg.height_in:
        result['dimensions'] = {
            'length': round(pkg.length_in),
            'width': round(pkg.width_in),
            'height': round(pkg.height_in),
            'units': 'IN',
        }
    if pkg.declared_value:
        result['declaredValue'] = {'amount': round(pkg.declared_value, 2), 'currency': 'USD'}
    return result
