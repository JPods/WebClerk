from __future__ import annotations

from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

import requests
import json


class TaxService:
    """
    Modern tax calculation service supporting external tax providers.

    Supports multiple tax calculation strategies:
    1. External tax service APIs (recommended)
    2. Built-in calculation for simple cases
    3. Configurable tax rules per jurisdiction
    """

    def __init__(self):
        # Check for a tax_service Connection record first (preferred),
        # then fall back to Django settings (legacy).
        from apps.transactions.services.tax_lookup import get_tax_connection
        conn = get_tax_connection()
        if conn:
            config = getattr(conn, 'config', {}) or {}
            self.tax_provider = config.get('provider', 'builtin')
            creds = config.get('credentials', {})
            self.tax_provider_api_key = creds.get('api_key', '')
            self.tax_provider_url = creds.get('url', '') or config.get('settings', {}).get('url', '')
        else:
            self.tax_provider = getattr(settings, 'TAX_PROVIDER', 'builtin')
            self.tax_provider_api_key = getattr(settings, 'TAX_PROVIDER_API_KEY', '')
            self.tax_provider_url = getattr(settings, 'TAX_PROVIDER_URL', '')

    def calculate_tax(
        self,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        billing_address: Optional[Dict[str, Any]] = None,
        customer_tax_exempt: bool = False,
        tax_exemption_certificate: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate tax for a transaction.

        Args:
            items: List of line items with price, quantity, tax_code, etc.
            shipping_address: Shipping address dict
            billing_address: Billing address dict (defaults to shipping)
            customer_tax_exempt: Whether customer is tax exempt
            tax_exemption_certificate: Exemption certificate number

        Returns:
            {
                'total_tax': Decimal,
                'tax_breakdown': List[Dict],
                'tax_rate': Decimal,
                'taxable_amount': Decimal,
                'exempt_amount': Decimal,
                'warnings': List[str]
            }
        """
        if customer_tax_exempt:
            return self._calculate_exempt_tax(items, tax_exemption_certificate)

        billing_address = billing_address or shipping_address

        if self.tax_provider == 'avalara':
            return self._calculate_with_avalara(items, shipping_address, billing_address)
        elif self.tax_provider == 'taxjar':
            return self._calculate_with_taxjar(items, shipping_address, billing_address)
        else:
            return self._calculate_builtin(items, shipping_address, billing_address)

    def _calculate_exempt_tax(
        self,
        items: List[Dict[str, Any]],
        certificate: Optional[str]
    ) -> Dict[str, Any]:
        """Handle tax-exempt customers."""
        total_amount = sum(
            Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 1)))
            for item in items
        )

        return {
            'total_tax': Decimal('0'),
            'tax_breakdown': [],
            'tax_rate': Decimal('0'),
            'taxable_amount': Decimal('0'),
            'exempt_amount': total_amount,
            'warnings': ['Customer is tax exempt'],
            'exemption_certificate': certificate
        }

    def _calculate_with_avalara(
        self,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        billing_address: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate tax using Avalara API."""
        try:
            payload = self._build_avalara_payload(items, shipping_address, billing_address)

            headers = {
                'Authorization': f'Bearer {self.tax_provider_api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                f"{self.tax_provider_url}/api/v2/tax/get",
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            return self._parse_avalara_response(response.json())

        except requests.RequestException as e:
            # Fallback to builtin calculation
            return self._calculate_builtin(items, shipping_address, billing_address, error=str(e))

    def _calculate_with_taxjar(
        self,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        billing_address: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate tax using TaxJar API."""
        try:
            payload = self._build_taxjar_payload(items, shipping_address, billing_address)

            headers = {
                'Authorization': f'Bearer {self.tax_provider_api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                f"{self.tax_provider_url}/v2/taxes",
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            return self._parse_taxjar_response(response.json())

        except requests.RequestException as e:
            # Fallback to builtin calculation
            return self._calculate_builtin(items, shipping_address, billing_address, error=str(e))

    def _calculate_builtin(
        self,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        billing_address: Dict[str, Any],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Built-in tax calculation for simple cases."""
        warnings = []
        if error:
            warnings.append(f"Tax provider error, using built-in calculation: {error}")

        # Determine tax jurisdiction from TaxJurisdiction records
        state = shipping_address.get('state', '').upper()
        zip_code = shipping_address.get('zip_code', '')

        from apps.transactions.services.tax_lookup import lookup_tax_jurisdiction
        tj = lookup_tax_jurisdiction(state=state)
        if tj:
            tax_rate = Decimal(str(tj['sales_rate']))
            # Normalize: if stored as percentage (e.g. 8.25), convert to decimal
            if tax_rate > 1:
                tax_rate = tax_rate / Decimal('100')
        else:
            tax_rate = Decimal('0')
            warnings.append(f"No tax rate configured for state: {state}")

        # Calculate taxable amount
        taxable_amount = Decimal('0')
        exempt_amount = Decimal('0')

        for item in items:
            line_total = (
                Decimal(str(item.get('price', 0))) *
                Decimal(str(item.get('quantity', 1)))
            )

            # Check if item is taxable
            tax_code = item.get('tax_code', 'TAXABLE')
            if tax_code in ['TAXABLE', 'STANDARD']:
                taxable_amount += line_total
            else:
                exempt_amount += line_total

        # Calculate tax
        total_tax = (taxable_amount * tax_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'total_tax': total_tax,
            'tax_breakdown': [{
                'rate': tax_rate,
                'taxable_amount': taxable_amount,
                'tax_amount': total_tax,
                'jurisdiction': f"{state} {zip_code}",
                'description': f"{state} sales tax"
            }] if total_tax > 0 else [],
            'tax_rate': tax_rate,
            'taxable_amount': taxable_amount,
            'exempt_amount': exempt_amount,
            'warnings': warnings
        }

    def _build_avalara_payload(self, items, shipping_address, billing_address) -> Dict:
        """Build payload for Avalara API."""
        return {
            "companyCode": getattr(settings, 'TAX_PROVIDER_COMPANY_CODE', 'DEFAULT'),
            "type": "SalesInvoice",
            "customerCode": "CUSTOMER",
            "date": timezone.now().date().isoformat(),
            "addresses": {
                "shipFrom": self._format_address(billing_address),
                "shipTo": self._format_address(shipping_address)
            },
            "lines": [
                {
                    "number": str(i + 1),
                    "quantity": item.get('quantity', 1),
                    "amount": str(Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 1)))),
                    "taxCode": item.get('tax_code', 'P0000000'),
                    "description": item.get('description', ''),
                }
                for i, item in enumerate(items)
            ]
        }

    def _build_taxjar_payload(self, items, shipping_address, billing_address) -> Dict:
        """Build payload for TaxJar API."""
        return {
            "from_country": billing_address.get('country', 'US'),
            "from_zip": billing_address.get('zip_code', ''),
            "from_state": billing_address.get('state', ''),
            "from_city": billing_address.get('city', ''),
            "from_street": billing_address.get('street', ''),
            "to_country": shipping_address.get('country', 'US'),
            "to_zip": shipping_address.get('zip_code', ''),
            "to_state": shipping_address.get('state', ''),
            "to_city": shipping_address.get('city', ''),
            "to_street": shipping_address.get('street', ''),
            "amount": sum(
                float(Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 1))))
                for item in items
            ),
            "shipping": 0,  # Could be passed separately
            "line_items": [
                {
                    "quantity": int(item.get('quantity', 1)),
                    "unit_price": float(item.get('price', 0)),
                    "product_tax_code": item.get('tax_code', ''),
                }
                for item in items
            ]
        }

    def _format_address(self, address: Dict) -> Dict:
        """Format address for tax provider APIs."""
        return {
            "line1": address.get('street', ''),
            "city": address.get('city', ''),
            "region": address.get('state', ''),
            "country": address.get('country', 'US'),
            "postalCode": address.get('zip_code', '')
        }

    def _parse_avalara_response(self, response: Dict) -> Dict[str, Any]:
        """Parse Avalara API response."""
        total_tax = Decimal(str(response.get('totalTax', 0)))
        tax_details = response.get('lines', [])

        breakdown = []
        for line in tax_details:
            for detail in line.get('details', []):
                breakdown.append({
                    'rate': Decimal(str(detail.get('rate', 0))),
                    'taxable_amount': Decimal(str(line.get('taxableAmount', 0))),
                    'tax_amount': Decimal(str(detail.get('tax', 0))),
                    'jurisdiction': detail.get('jurisdictionName', ''),
                    'description': detail.get('taxName', '')
                })

        return {
            'total_tax': total_tax,
            'tax_breakdown': breakdown,
            'tax_rate': Decimal('0'),  # Would need to calculate weighted average
            'taxable_amount': sum(d['taxable_amount'] for d in breakdown),
            'exempt_amount': Decimal('0'),
            'warnings': []
        }

    def _parse_taxjar_response(self, response: Dict) -> Dict[str, Any]:
        """Parse TaxJar API response."""
        total_tax = Decimal(str(response.get('tax', {}).get('amount_to_collect', 0)))
        breakdown = response.get('tax', {}).get('breakdown', {})

        tax_breakdown = []
        if 'state_tax' in breakdown:
            tax_breakdown.append({
                'rate': Decimal(str(breakdown['state_tax'].get('rate', 0))),
                'taxable_amount': Decimal(str(breakdown.get('taxable_amount', 0))),
                'tax_amount': Decimal(str(breakdown['state_tax'].get('tax_collectable', 0))),
                'jurisdiction': breakdown.get('state_tax_rate', ''),
                'description': 'State sales tax'
            })

        return {
            'total_tax': total_tax,
            'tax_breakdown': tax_breakdown,
            'tax_rate': Decimal('0'),  # Would need to calculate
            'taxable_amount': Decimal(str(breakdown.get('taxable_amount', 0))),
            'exempt_amount': Decimal(str(breakdown.get('exempt_amount', 0))),
            'warnings': []
        }


# Global tax service instance
tax_service = TaxService()


def calculate_transaction_tax(
    transaction,
    items: List[Dict],
    shipping_address: Dict,
    billing_address: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convenience function to calculate tax for a transaction.

    Extracts relevant data from transaction model and calls tax service.
    """
    customer_tax_exempt = getattr(transaction, 'tax_exempt', False)
    exemption_certificate = getattr(transaction, 'tax_exemption_certificate', None)

    return tax_service.calculate_tax(
        items=items,
        shipping_address=shipping_address,
        billing_address=billing_address,
        customer_tax_exempt=customer_tax_exempt,
        tax_exemption_certificate=exemption_certificate
    )


__all__ = [
    'TaxService',
    'tax_service',
    'calculate_transaction_tax',
]