"""
DHL Express REST API carrier implementation.

Endpoints: https://express.api.dhl.com/mydhlapi/

Authentication: Basic Auth (user ID + password from DHL developer portal).

Connection config.credentials:
  user_id         — DHL Express API user ID
  password        — DHL Express API password
  account_number  — DHL Express account number

Connection config.settings:
  label_format    — 'pdf' (default), 'zpl', 'png'
  test_mode       — True = sandbox (express.api.dhl.com/mydhlapi/test/), False = production
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    Address, CarrierBase, Package, Rate,
    Shipment, TrackingEvent, TrackingResult, register_carrier,
)

logger = logging.getLogger(__name__)

PRODUCTION_BASE = 'https://express.api.dhl.com/mydhlapi'
SANDBOX_BASE = 'https://express.api.dhl.com/mydhlapi/test'

DHL_SERVICES = {
    'N': 'DHL Express Domestic',
    'P': 'DHL Express Worldwide',
    'U': 'DHL Express Worldwide (EU)',
    'K': 'DHL Express 9:00',
    'E': 'DHL Express 9:00 (Non-Doc)',
    'T': 'DHL Express 12:00',
    'Y': 'DHL Express 12:00 (Non-Doc)',
    'D': 'DHL Express Worldwide (Doc)',
}


@register_carrier
class DHLCarrier(CarrierBase):
    carrier_code = 'dhl'
    carrier_name = 'DHL Express'

    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self._test_mode = self.settings.get('test_mode', False)
        self._base = SANDBOX_BASE if self._test_mode else PRODUCTION_BASE

    def _auth(self):
        return (self.credentials.get('user_id', ''), self.credentials.get('password', ''))

    def _headers(self) -> Dict[str, str]:
        return {'Content-Type': 'application/json'}

    def get_rates(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        ship_date: Optional[date] = None,
    ) -> List[Rate]:
        url = f'{self._base}/rates'
        ship_dt = (ship_date or date.today()).strftime('%Y-%m-%dT%H:%M:%S GMT+00:00')

        total_weight = sum(p.weight_lbs * 0.453592 for p in packages)  # lbs → kg

        params = {
            'accountNumber': self.credentials.get('account_number', ''),
            'originCountryCode': origin.country or 'US',
            'originPostalCode': origin.zip_code,
            'destinationCountryCode': destination.country or 'US',
            'destinationPostalCode': destination.zip_code,
            'weight': round(max(total_weight, 0.5), 2),
            'length': round(max((packages[0].length_in * 2.54 if packages else 1), 1)),
            'width': round(max((packages[0].width_in * 2.54 if packages else 1), 1)),
            'height': round(max((packages[0].height_in * 2.54 if packages else 1), 1)),
            'plannedShippingDate': ship_dt,
            'isCustomsDeclarable': 'false',
            'unitOfMeasurement': 'metric',
        }

        resp = httpx.get(url, params=params, auth=self._auth(), headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        rates = []
        for product in data.get('products', []):
            code = product.get('productCode', '')
            total = product.get('totalPrice', [{}])
            price_entry = total[0] if total else {}

            rate = Rate(
                carrier='dhl',
                service_code=code,
                service_name=DHL_SERVICES.get(code, product.get('productName', code)),
                base_cost=float(price_entry.get('price', 0)),
                total_cost=float(price_entry.get('price', 0)),
                currency=price_entry.get('priceCurrency', 'USD'),
                transit_days=int(product.get('deliveryCapabilities', {}).get('totalTransitDays', 0) or 0),
                delivery_date=product.get('deliveryCapabilities', {}).get('estimatedDeliveryDateAndTime', ''),
                raw=product,
            )
            rate = self.apply_surcharges(rate)
            rates.append(rate)

        rates.sort(key=lambda r: r.total_cost)
        return rates

    def create_shipment(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        service_code: str,
        ship_date: Optional[date] = None,
        reference: str = '',
    ) -> Shipment:
        url = f'{self._base}/shipments'
        label_fmt = self.settings.get('label_format', 'pdf').upper()
        ship_dt = (ship_date or date.today()).strftime('%Y-%m-%dT%H:%M:%S GMT+00:00')

        pkg_list = []
        for i, pkg in enumerate(packages):
            pkg_list.append({
                'weight': round(max(pkg.weight_lbs * 0.453592, 0.5), 2),
                'dimensions': {
                    'length': round(max(pkg.length_in * 2.54, 1)),
                    'width': round(max(pkg.width_in * 2.54, 1)),
                    'height': round(max(pkg.height_in * 2.54, 1)),
                },
                'customerReferences': [{'value': reference[:35]}] if reference else [],
            })

        payload = {
            'plannedShippingDateAndTime': ship_dt,
            'pickup': {'isRequested': False},
            'productCode': service_code,
            'accounts': [{'typeCode': 'shipper', 'number': self.credentials.get('account_number', '')}],
            'customerDetails': {
                'shipperDetails': _dhl_contact(origin),
                'receiverDetails': _dhl_contact(destination),
            },
            'content': {
                'packages': pkg_list,
                'isCustomsDeclarable': False,
                'description': 'Shipment',
                'unitOfMeasurement': 'metric',
            },
            'outputImageProperties': {
                'imageOptions': [{'typeCode': 'label', 'templateName': 'ECOM26_84_001'}],
            },
        }

        resp = httpx.post(url, json=payload, auth=self._auth(), headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        track_num = data.get('shipmentTrackingNumber', '')
        documents = data.get('documents', [])
        label_b64 = documents[0].get('content', '') if documents else ''

        import base64
        label_bytes = base64.b64decode(label_b64) if label_b64 else b''

        return Shipment(
            carrier='dhl',
            tracking_number=track_num,
            service_code=service_code,
            service_name=DHL_SERVICES.get(service_code, service_code),
            label_format=label_fmt.lower(),
            label_data=label_bytes,
            ship_date=(ship_date or date.today()).isoformat(),
            raw=data,
        )

    def track(self, tracking_number: str) -> TrackingResult:
        url = f'{self._base}/shipments/{tracking_number}/tracking'

        resp = httpx.get(url, auth=self._auth(), headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        shipments = data.get('shipments', [{}])
        shipment = shipments[0] if shipments else {}
        status = shipment.get('status', {})
        scan_events = shipment.get('events', [])

        events = []
        for evt in scan_events:
            loc = evt.get('location', {}).get('address', {})
            events.append(TrackingEvent(
                timestamp=evt.get('timestamp', ''),
                status=evt.get('statusCode', ''),
                description=evt.get('description', ''),
                city=loc.get('addressLocality', ''),
                country=loc.get('countryCode', ''),
            ))

        delivered = status.get('statusCode', '') == 'delivered'

        return TrackingResult(
            carrier='dhl',
            tracking_number=tracking_number,
            status=status.get('description', ''),
            delivered=delivered,
            events=events,
            raw=data,
        )


def _dhl_contact(addr: Address) -> Dict[str, Any]:
    return {
        'postalAddress': {
            'postalCode': addr.zip_code,
            'cityName': addr.city,
            'countryCode': addr.country or 'US',
            'provinceCode': addr.state,
            'addressLine1': addr.street1,
            'addressLine2': addr.street2,
        },
        'contactInformation': {
            'phone': addr.phone or '0000000000',
            'companyName': addr.company or addr.name,
            'fullName': addr.name,
            'email': addr.email,
        },
    }
