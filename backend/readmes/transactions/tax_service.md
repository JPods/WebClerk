# Tax Service

## Overview

The Tax Service (`apps/transactions/services/tax_service.py`) provides a unified interface for calculating sales tax across different tax providers and jurisdictions. It supports external tax APIs (Avalara, TaxJar) as well as built-in tax calculations for simple cases.

## Features

- **Multiple Providers**: Supports Avalara, TaxJar, and built-in calculations
- **Flexible Configuration**: Configurable via Django settings
- **Error Handling**: Fallback to built-in calculation if external providers fail
- **Tax Exemption Support**: Handles customer tax exemptions with certificates

## Configuration

Set the following in Django settings:

```python
TAX_PROVIDER = 'avalara'  # or 'taxjar' or 'builtin'
TAX_PROVIDER_API_KEY = 'your_api_key'
TAX_PROVIDER_URL = 'https://api.avalara.com'  # or TaxJar URL
TAX_PROVIDER_COMPANY_CODE = 'DEFAULT'
```

## Usage

```python
from apps.transactions.services.tax_service import tax_service

result = tax_service.calculate_tax(
    items=[
        {
            'price': 100.00,
            'quantity': 2,
            'tax_code': 'TAXABLE',
            'description': 'Product A'
        }
    ],
    shipping_address={
        'street': '123 Main St',
        'city': 'Anytown',
        'state': 'CA',
        'zip_code': '12345',
        'country': 'US'
    },
    billing_address=None,  # defaults to shipping
    customer_tax_exempt=False,
    tax_exemption_certificate=None
)

# Returns:
{
    'total_tax': Decimal('16.50'),
    'tax_breakdown': [...],
    'tax_rate': Decimal('0.0825'),
    'taxable_amount': Decimal('200.00'),
    'exempt_amount': Decimal('0.00'),
    'warnings': []
}
```

## Recent Fix

**Issue**: `NameError: name 'timezone' is not defined` in `_build_avalara_payload` method.

**Fix**: Added missing import `from django.utils import timezone` at the top of the file.

**Impact**: Ensures Avalara API payloads include the correct transaction date without runtime errors.

## Integration Status

- Tax service is implemented and functional
- Currently not integrated into invoice/order totals calculation
- Manual testing via `calculate_transaction_tax` function available
- UI displays tax fields but shows $0.00 until totals integration is complete

## Testing

See `readmes/transaction_testing.md` for comprehensive testing instructions for transactions including tax calculation.