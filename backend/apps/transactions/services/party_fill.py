"""A document takes its party's values when its customer or vendor is set or changed (readme
106 rule 3; Bill, 2026-11-07: "On assigning a customer, the quote reloads with that customer's
values"). The org's values replace the defaulted fields — not only blanks — except a field the
same payload carries, which is the person's; where the org has none, the model's company
default stays. One formula, on the server: the form saves the pick and reloads what the save
returns (server is truth). The client-side fill (applyCustomerDefaults) is gone.

A customer gives a sale its terms, price level, bill-to and ship-to blocks (addresses, emails,
phones — the org's own blocks, else its company and primary contact), attention, ship_via and
sales tax (exempt, or the jurisdiction the org names, else the ship-to ZIP). A vendor gives a
purchase or receipt its terms and its bill-to block; the ship-to stays the company's own.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

#: What each party gives: the document fields and the org fields they come from.
SCALARS = {'customer': ('terms', 'price_level'), 'vendor': ('terms',)}
ROLES = {'customer': ('bill_to', 'ship_to'), 'vendor': ('bill_to',)}
ASPECTS = ('addresses', 'emails', 'phones')
_ZIP = re.compile(r'\b(\d{5})(?:-\d{4})?\s*$')


def take_party(ctx) -> None:
    """The document's before_save: when its customer or vendor changed in this save, take it."""
    obj = ctx.obj
    names = {f.name for f in obj._meta.concrete_fields}
    for party in ('customer', 'vendor'):
        if party in names and party in ctx.changed and getattr(obj, f'{party}_id', None):
            _take(obj, getattr(obj, party), party, ctx.model_key, ctx.data, names)


def _take(obj, org, party: str, model_key: str, data: Dict[str, Any], names: set) -> None:
    from apps.core.services.defaults import model_defaults, named_term
    company = model_defaults(model_key)
    for field in SCALARS[party]:
        if field not in names or field in data:
            continue
        value = getattr(org, field, None) or company.get(field)
        if value:
            setattr(obj, field, named_term(value) if field == 'terms' else value)

    snapshot = org.build_company_snapshot()          # contact-driven: attention, address, phone, email
    blocks = {'bill_to': _block(org, 'bill_to', snapshot)}
    if 'ship_to' in ROLES[party]:
        blocks['ship_to'] = _block(org, 'ship_to', snapshot, fallback=blocks['bill_to'])
    for aspect in ASPECTS:
        if aspect not in names or aspect in data:
            continue
        current = dict(getattr(obj, aspect) or {})
        for role, block in blocks.items():
            current[role] = {**(current.get(role) or {}), **block[aspect]}
        setattr(obj, aspect, current)
    if 'attention' in names and 'attention' not in data:
        obj.attention = blocks['bill_to']['addresses']['attention']
    if 'ship_via' in names and 'ship_via' not in data:      # the org's carrier, else the company's, else as it was
        theirs = (org.config or {}).get('ship_via') if isinstance(org.config, dict) else None
        obj.ship_via = _listed(model_key, 'ship_via', theirs) or company.get('ship_via') or obj.ship_via
    if party == 'customer' and 'finance' in names and 'finance' not in data:
        _tax(obj, org, blocks.get('ship_to', blocks['bill_to'])['addresses'].get('full_address', ''))


def _listed(model_key: str, field: str, value: Any) -> Optional[str]:
    """An org's value in the document list's own spelling (Riverside's config said 'USPS', the
    quote list says 'usps'); none when the list lacks it — the door refuses code writing an
    unlisted value (Bill, 2026-11-04), and a party fill is code. The sweep repairs the org."""
    if not value:
        return None
    from apps.core.services import select_lists
    listed = select_lists.lists(model_key).get(field)
    if not listed:
        return str(value)
    return next((str(v) for v in listed if str(v).lower() == str(value).lower()), None)


def _block(org, role: str, snapshot: Dict[str, Any], fallback: Optional[Dict[str, Dict]] = None) -> Dict[str, Dict]:
    """One party block from the org's own ``<aspect>.<role>``; an empty one from the fallback
    block (a ship-to is the bill-to until split), else from the org's company snapshot."""
    addr = dict((org.addresses or {}).get(role) or {})
    email = dict((org.emails or {}).get(role) or {})
    phone = dict((org.phones or {}).get(role) or {})
    if not (addr.get('company') or addr.get('full_address')):
        addr = dict(fallback['addresses']) if fallback else {
            'contact_id': snapshot.get('contact_id'), 'company': org.company or '',
            'attention': snapshot.get('attention') or '', 'full_address': snapshot.get('full_address') or '',
            'instructions': ''}
    if not email.get('email'):
        email = dict(fallback['emails']) if fallback else {'email': snapshot.get('email') or ''}
    if not phone.get('number'):
        phone = dict(fallback['phones']) if fallback else {'number': snapshot.get('phone') or ''}
    return {
        'addresses': {k: addr.get(k) for k in ('contact_id', 'company', 'attention', 'full_address', 'instructions')},
        'emails': {'email': email.get('email') or ''},
        'phones': {'number': phone.get('number') or ''},
    }


def _tax(obj, org, ship_address: str) -> None:
    """Sales tax from the customer: exempt, else the jurisdiction it names, else the ship-to ZIP
    (one lookup for every case, tax_resolve); the previous customer's jurisdiction never wins."""
    from apps.transactions.services.pricing.tax_resolve import apply_tax_to_finance
    finance = dict(obj.finance or {})
    code = getattr(org, 'tax_exempt_code', '') or ''
    if code and code != 'DoTax':
        finance.update({'sales_tax_rate': 0, 'sales_tax_name': 'Exempt', 'sales_tax_id': 0})
    else:
        probe: Dict[str, Any] = {'sales_tax_id': getattr(org, 'tax_jurisdiction_id', None) or 0}
        match = _ZIP.search(ship_address or '')
        apply_tax_to_finance(probe, zip_code=match.group(1) if match else '', force=True)
        if probe.get('sales_tax_rate') is None:
            return                                   # nothing found: the finance stays as it was
        finance.update(probe)
    obj.finance = finance
