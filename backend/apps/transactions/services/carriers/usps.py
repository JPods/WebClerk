"""
USPS REST API carrier implementation.

USPS migrated to OAuth 2.0 REST APIs in 2024 (replacing Web Tools XML).
Endpoints: https://api.usps.com/

Authentication: OAuth 2.0 client credentials.
  POST /oauth2/v3/token with client_id + client_secret

Connection config.credentials:
  client_id       — USPS developer app client ID
  client_secret   — USPS developer app client secret

Connection config.settings:
  label_format    — 'pdf' (default), 'png'
  test_mode       — True = sandbox (apis-cat.usps.com), False = production
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

PRODUCTION_BASE = 'https://api.usps.com'
SANDBOX_BASE = 'https://apis-cat.usps.com'

USPS_SERVICES = {
    'USPS_GROUND_ADVANTAGE': 'USPS Ground Advantage',
    'PRIORITY_MAIL': 'Priority Mail',
    'PRIORITY_MAIL_EXPRESS': 'Priority Mail Express',
    'FIRST_CLASS_MAIL': 'First-Class Mail',
    'MEDIA_MAIL': 'Media Mail',
    'PARCEL_SELECT': 'Parcel Select',
    'LIBRARY_MAIL': 'Library Mail',
}


@register_carrier
class USPSCarrier(CarrierBase):
    carrier_code = 'usps'
    carrier_name = 'USPS'

    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self._token: str = ''
        self._token_expires: float = 0
        self._test_mode = self.settings.get('test_mode', False)
        self._base = SANDBOX_BASE if self._test_mode else PRODUCTION_BASE

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires:
            return self._token

        resp = httpx.post(
            f'{self._base}/oauth2/v3/token',
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
        }

    def get_rates(
        self,
        origin: Address,
        destination: Address,
        packages: List[Package],
        ship_date: Optional[date] = None,
    ) -> List[Rate]:
        url = f'{self._base}/prices/v3/base-rates/search'
        ship_dt = (ship_date or date.today()).isoformat()

        rates = []
        for pkg in packages:
            payload = {
                'originZIPCode': origin.zip_code[:5],
                'destinationZIPCode': destination.zip_code[:5],
                'weight': round(max(pkg.weight_lbs, 0.1), 1),
                'length': round(pkg.length_in or 1),
                'width': round(pkg.width_in or 1),
                'height': round(pkg.height_in or 1),
                'mailClass': 'ALL',
                'processingCategory': 'MACHINABLE',
                'rateIndicator': 'DR',
                'priceType': 'RETAIL',
                'mailingDate': ship_dt,
            }

            try:
                resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning('USPS rate request failed: %s', e)
                continue

            for rate_opt in data.get('rates', []):
                code = rate_opt.get('mailClass', '')
                rate = Rate(
                    carrier='usps',
                    service_code=code,
                    service_name=USPS_SERVICES.get(code, code),
                    base_cost=float(rate_opt.get('price', 0)),
                    total_cost=float(rate_opt.get('price', 0)),
                    currency='USD',
                    transit_days=int(rate_opt.get('deliveryDays', 0) or 0),
                    delivery_date=rate_opt.get('scheduledDeliveryDate', ''),
                    raw=rate_opt,
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
        url = f'{self._base}/labels/v3/label'
        label_fmt = self.settings.get('label_format', 'pdf').upper()
        pkg = packages[0] if packages else Package()

        payload = {
            'imageInfo': {'imageType': label_fmt, 'labelType': '4X6LABEL'},
            'toAddress': _usps_address(destination),
            'fromAddress': _usps_address(origin),
            'packageDescription': {
                'mailClass': service_code,
                'weight': round(max(pkg.weight_lbs, 0.1), 1),
                'processingCategory': 'MACHINABLE',
                'rateIndicator': 'DR',
            },
        }

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        import base64
        label_b64 = data.get('labelImage', '')
        label_bytes = base64.b64decode(label_b64) if label_b64 else b''

        return Shipment(
            carrier='usps',
            tracking_number=data.get('trackingNumber', ''),
            service_code=service_code,
            service_name=USPS_SERVICES.get(service_code, service_code),
            total_cost=float(data.get('postage', 0)),
            label_format=label_fmt.lower(),
            label_data=label_bytes,
            ship_date=(ship_date or date.today()).isoformat(),
            raw=data,
        )

    def track(self, tracking_number: str) -> TrackingResult:
        url = f'{self._base}/tracking/v3/tracking/{tracking_number}'
        params = {'expand': 'DETAIL'}

        resp = httpx.get(url, params=params, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()

        tracking = data.get('trackingNumber', tracking_number)
        summary = data.get('statusSummary', '')
        delivered = 'delivered' in summary.lower()

        events = []
        for evt in data.get('trackingEvents', []):
            events.append(TrackingEvent(
                timestamp=evt.get('eventTimestamp', ''),
                status=evt.get('eventType', ''),
                description=evt.get('eventDescription', ''),
                city=evt.get('eventCity', ''),
                state=evt.get('eventState', ''),
                zip_code=evt.get('eventZIPCode', ''),
                country=evt.get('eventCountry', 'US'),
            ))

        return TrackingResult(
            carrier='usps',
            tracking_number=tracking,
            status=summary,
            delivered=delivered,
            events=events,
            raw=data,
        )

    def validate_address(self, address: Address) -> AddressValidation:
        url = f'{self._base}/addresses/v3/address'
        params = {
            'streetAddress': address.street1,
            'secondaryAddress': address.street2,
            'city': address.city,
            'state': address.state,
            'ZIPCode': address.zip_code,
        }

        try:
            resp = httpx.get(url, params=params, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return AddressValidation(valid=True, messages=[f'Validation unavailable: {e}'])

        addr = data.get('address', {})
        corrected = Address(
            street1=addr.get('streetAddress', address.street1),
            street2=addr.get('secondaryAddress', ''),
            city=addr.get('city', address.city),
            state=addr.get('state', address.state),
            zip_code=addr.get('ZIPCode', address.zip_code),
            country='US',
        )

        return AddressValidation(valid=True, corrected=corrected)


def _usps_address(addr: Address) -> Dict[str, Any]:
    return {
        'streetAddress': addr.street1,
        'secondaryAddress': addr.street2,
        'city': addr.city,
        'state': addr.state,
        'ZIPCode': addr.zip_code[:5],
        'firstName': addr.name.split()[0] if addr.name else '',
        'lastName': ' '.join(addr.name.split()[1:]) if addr.name and ' ' in addr.name else addr.name,
    }
