"""
customer_defaults.py — Populate transaction header from customer record.

When a user selects a customer on an order (or any sell-side transaction),
auto-populate: company, contact, attention, phone, email, address,
price_level, terms, ship_via, and ship-to from customer defaults.

This is NOT a save — it returns a dict of fields to apply.
The frontend merges these into the edit buffer. Post or Pend applies.
"""
from typing import Any


def get_customer_defaults(customer: Any, contact: Any = None) -> dict:
    """Build a dict of order fields from a customer + optional contact.

    Args:
        customer: OrgBase instance (or dict with same fields)
        contact: Contact instance (or dict), optional — overrides customer contact fields

    Returns:
        dict of field_name: value to merge into the transaction record
    """
    if isinstance(customer, dict):
        c = customer
    else:
        c = {
            'id': getattr(customer, 'id', None),
            'company': getattr(customer, 'company', '') or getattr(customer, 'display_name', ''),
            'ida': getattr(customer, 'ida', ''),
            'phone': getattr(customer, 'phone', ''),
            'email': getattr(customer, 'email', ''),
            'attention': getattr(customer, 'attention', ''),
            'address_full': getattr(customer, 'address_full', ''),
            'price_level': getattr(customer, 'price_level', ''),
            'terms': getattr(customer, 'terms', ''),
            'ship_via': getattr(customer, 'ship_via', ''),
            'config': getattr(customer, 'config', {}) or {},
        }

    # Contact overrides customer-level fields
    if contact:
        if isinstance(contact, dict):
            ct = contact
        else:
            ct = {
                'phone': getattr(contact, 'phone', ''),
                'email': getattr(contact, 'email', ''),
                'attention': getattr(contact, 'display_name', '') or getattr(contact, 'name', ''),
                'address_full': getattr(contact, 'address_full', ''),
            }
    else:
        ct = {}

    defaults = {
        'customer_id': c.get('id'),
        'company': c.get('company', ''),
        'phone': ct.get('phone') or c.get('phone', ''),
        'email': ct.get('email') or c.get('email', ''),
        'attention': ct.get('attention') or c.get('attention', ''),
        'address_full': ct.get('address_full') or c.get('address_full', ''),
        'price_level': c.get('price_level', ''),
        'terms': c.get('terms', ''),
        'ship_via': c.get('ship_via', ''),
    }

    # Ship-to defaults from customer config if present
    ship_to = c.get('config', {}).get('ship_to') or {}
    if ship_to:
        defaults['config'] = {'ship_to': ship_to}

    # Credit data for display
    config = c.get('config', {})
    credit_fields = ['credit_limit', 'credit_available', 'balance_due', 'balance_current',
                     'sales_mtd', 'sales_ytd', 'sales_lifetime', 'avg_pay_days',
                     'last_payment_amount', 'last_sale']
    customer_config = {k: config.get(k) for k in credit_fields if config.get(k) is not None}
    if customer_config:
        defaults['customer_config'] = customer_config

    # Tax jurisdiction lookup — ZIP code drives tax rate assignment.
    # User enters ZIP, system resolves state and tax rate automatically.
    zip_code = ''
    if isinstance(customer, dict):
        zip_code = customer.get('zip', '') or customer.get('zip_code', '')
    else:
        # Try to get ZIP from the customer's primary address
        try:
            addr = getattr(customer, 'addresses', None)
            if addr:
                primary = addr.first()
                if primary:
                    zip_code = getattr(primary, 'zip', '') or ''
        except Exception:
            pass
        if not zip_code:
            # Fall back to parsing from address_full ("City, ST 12345")
            address_full = defaults.get('address_full', '')
            if address_full:
                parts = address_full.strip().split()
                if parts:
                    candidate = parts[-1]
                    if candidate.isdigit() and len(candidate) >= 5:
                        zip_code = candidate

    if zip_code:
        from apps.transactions.services.pricing.tax_resolve import apply_tax_to_finance
        finance = {}
        apply_tax_to_finance(finance, zip_code=zip_code)
        if finance.get('sales_tax_rate'):
            defaults['finance'] = finance

    return defaults
