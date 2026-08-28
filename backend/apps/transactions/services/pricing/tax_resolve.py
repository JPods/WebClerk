"""Tax jurisdiction lookup.

Entry point: ZIP code. User enters a ZIP on a customer or transaction,
the system resolves state and tax rate automatically.

    ZIP → state (via zip_to_state Setting) → tax rate (via us_state_tax_rates Setting)

Three sources for tax rates, checked in priority order:

  1. TaxJurisdiction records (local overrides)
     - For custom jurisdictions, local rates, or non-US tax
     - Takes precedence over Setting when a matching record exists

  2. Setting record (synced from WC_HQ or updated by Alice)
     - 'us_state_tax_rates': state-level rates for all 50 states + DC + territories
     - 'zip_to_state': ZIP prefix (3-digit) → state mapping (~900 entries)
     - WC_HQ publishes updates; Alice can also refresh from state sources

  3. Connection record for external tax service (Avalara/TaxJar/Vertex)
     - Most precise — product-level taxability, multi-jurisdiction
     - Staged as 'conn-tax-service' Connection, activated when needed

WC2 heritage: TaxCalcLine had three modes (StandardSalesTax, ByCost,
WebBased). This replaces all three.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.apps import apps

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ZIP → state resolution
# ---------------------------------------------------------------------------

# Compact US ZIP prefix → state mapping. The first 3 digits of a ZIP code
# identify the state. This covers all ~900 prefixes. Synced from WC_HQ
# via Setting 'zip_to_state', or uses this built-in fallback.
#
# Format: {"006": "PR", "010": "MA", ..., "995": "AK"}

_ZIP_PREFIX_FALLBACK: Dict[str, str] = {
    # This is populated from the Setting record at runtime.
    # If the Setting doesn't exist, we use a minimal hardcoded set
    # covering the most common ranges. Alice or WC_HQ should seed
    # the full 'zip_to_state' Setting on first sync.
}

# ZIP prefix ranges → state (compact representation for fallback)
# Each tuple: (start_prefix, end_prefix, state_code)
_ZIP_RANGES = [
    ('005', '009', 'PR'), ('010', '027', 'MA'), ('028', '029', 'RI'),
    ('030', '038', 'NH'), ('039', '049', 'ME'), ('050', '059', 'VT'),
    ('060', '069', 'CT'), ('070', '089', 'NJ'), ('100', '149', 'NY'),
    ('150', '196', 'PA'), ('197', '199', 'DE'), ('200', '205', 'DC'),
    ('206', '219', 'MD'), ('220', '246', 'VA'), ('247', '268', 'WV'),
    ('270', '289', 'NC'), ('290', '299', 'SC'), ('300', '319', 'GA'),
    ('320', '349', 'FL'), ('350', '369', 'AL'), ('370', '385', 'TN'),
    ('386', '397', 'MS'), ('400', '427', 'KY'), ('430', '459', 'OH'),
    ('460', '479', 'IN'), ('480', '499', 'MI'), ('500', '528', 'IA'),
    ('530', '549', 'WI'), ('550', '567', 'MN'), ('570', '577', 'SD'),
    ('580', '588', 'ND'), ('590', '599', 'MT'), ('600', '629', 'IL'),
    ('630', '658', 'MO'), ('660', '679', 'KS'), ('680', '693', 'NE'),
    ('700', '714', 'LA'), ('716', '729', 'AR'), ('730', '749', 'OK'),
    ('750', '799', 'TX'), ('800', '816', 'CO'), ('820', '831', 'WY'),
    ('832', '838', 'ID'), ('840', '847', 'UT'), ('850', '865', 'AZ'),
    ('870', '884', 'NM'), ('889', '898', 'NV'), ('900', '935', 'CA'),
    ('936', '966', 'HI') if False else ('936', '961', 'CA'),
    ('967', '968', 'HI'), ('970', '979', 'OR'), ('980', '994', 'WA'),
    ('995', '999', 'AK'),
]


def zip_to_state(zip_code: str) -> str:
    """Resolve a US ZIP code to a 2-letter state code.

    Checks Setting 'zip_to_state' first (WC_HQ synced, most complete).
    Falls back to built-in ZIP prefix range table.

    Returns state code (e.g. 'CA') or empty string if not resolved.
    """
    if not zip_code:
        return ''

    # Clean: take first 5 chars, strip non-digits
    clean = ''.join(c for c in str(zip_code)[:5] if c.isdigit())
    if len(clean) < 3:
        return ''

    prefix = clean[:3]

    # Try Setting first
    Setting = apps.get_model('core', 'Setting')
    try:
        setting = Setting.objects.filter(
            name='zip_to_state',
            is_active=True,
        ).first()
        if setting:
            config = getattr(setting, 'config', {}) or {}
            mapping = config.get('mapping', {})
            if prefix in mapping:
                return mapping[prefix]
    except Exception:
        pass

    # Fall back to built-in range table
    for start, end, state in _ZIP_RANGES:
        if start <= prefix <= end:
            return state

    return ''


# ---------------------------------------------------------------------------
# Setting-based lookup (WC_HQ synced or Alice-maintained)
# ---------------------------------------------------------------------------

def _get_rates_from_setting() -> Dict[str, Dict[str, Any]]:
    """Load US state tax rates from the Setting record.

    Setting name: 'us_state_tax_rates'
    Expected config JSON:
        {
            "rates": {
                "CA": {"sales": 7.25, "shipping": 0, "name": "California"},
                "NY": {"sales": 4.0, "shipping": 0, "name": "New York"},
                "TX": {"sales": 6.25, "shipping": 0, "name": "Texas"},
                ...
            },
            "dt_updated": "2026-08-09T00:00:00Z",
            "source": "wchq"
        }

    Returns dict of state_code → rate info, or empty dict.
    """
    Setting = apps.get_model('core', 'Setting')
    try:
        setting = Setting.objects.filter(
            name='us_state_tax_rates',
            is_active=True,
        ).first()
        if not setting:
            return {}
        config = getattr(setting, 'config', {}) or {}
        return config.get('rates', {})
    except Exception:
        return {}


def _lookup_from_setting(state: str) -> Optional[Dict[str, Any]]:
    """Look up tax rate for a state from the Setting record."""
    if not state:
        return None

    rates = _get_rates_from_setting()
    state_upper = state.strip().upper()

    info = rates.get(state_upper)
    if not info:
        return None

    return {
        'id': 0,  # no TaxJurisdiction record — from Setting
        'name': info.get('name', state_upper),
        'tax_name': f"{info.get('name', state_upper)} Sales Tax",
        'sales_rate': float(info.get('sales', 0)),
        'cost_rate': float(info.get('cost', 0)),
        'shipping_rate': float(info.get('shipping', 0)),
        'gl_account_payable': '',
        'service_provider': '',
        'source': 'setting',
    }


# ---------------------------------------------------------------------------
# TaxJurisdiction record lookup (local overrides)
# ---------------------------------------------------------------------------

def _lookup_from_jurisdiction(
    state: str = '',
    jurisdiction_name: str = '',
    jurisdiction_id: int = 0,
) -> Optional[Dict[str, Any]]:
    """Find an active TaxJurisdiction record.

    Priority:
      1. Explicit jurisdiction_id
      2. Explicit jurisdiction_name
      3. State name/abbreviation match
    """
    TaxJurisdiction = apps.get_model('accounts', 'TaxJurisdiction')

    tj = None

    if jurisdiction_id:
        try:
            tj = TaxJurisdiction.objects.get(pk=jurisdiction_id, is_active=True)
        except TaxJurisdiction.DoesNotExist:
            pass

    if not tj and jurisdiction_name:
        tj = TaxJurisdiction.objects.filter(
            tax_jurisdiction__iexact=jurisdiction_name.strip(),
            is_active=True,
        ).first()

    if not tj and state:
        state_clean = state.strip().upper()
        tj = TaxJurisdiction.objects.filter(
            tax_jurisdiction__iexact=state_clean,
            is_active=True,
        ).first()
        if not tj:
            tj = TaxJurisdiction.objects.filter(
                tax_jurisdiction__icontains=state_clean,
                is_active=True,
            ).first()

    if not tj:
        return None

    return {
        'id': tj.pk,
        'name': tj.tax_jurisdiction or '',
        'tax_name': tj.tax_name or '',
        'sales_rate': float(tj.tax_rate_sales or 0),
        'cost_rate': float(tj.tax_rate_cost or 0),
        'shipping_rate': float(tj.tax_rate_on_shipping or 0),
        'gl_account_payable': tj.gl_account_payable or '',
        'service_provider': tj.service_provider or '',
        'source': 'jurisdiction',
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_tax_jurisdiction(
    zip_code: str = '',
    state: str = '',
    jurisdiction_name: str = '',
    jurisdiction_id: int = 0,
) -> Optional[Dict[str, Any]]:
    """Find tax rate — ZIP code is the primary input.

    ZIP → state → rate. User enters ZIP, everything else resolves.

    Priority:
      1. TaxJurisdiction record (local override — takes precedence)
      2. Setting record (WC_HQ synced rates — automatic)

    If zip_code is provided and state is not, state is derived from ZIP.
    """
    # Resolve state from ZIP if not provided
    if zip_code and not state:
        state = zip_to_state(zip_code)

    # Local override first
    result = _lookup_from_jurisdiction(
        state=state,
        jurisdiction_name=jurisdiction_name,
        jurisdiction_id=jurisdiction_id,
    )
    if result:
        result['resolved_state'] = state
        return result

    # Fall back to WC_HQ Setting
    result = _lookup_from_setting(state)
    if result:
        result['resolved_state'] = state
        return result

    return None


def apply_tax_to_finance(
    finance: Dict[str, Any],
    zip_code: str = '',
    state: str = '',
    jurisdiction_name: str = '',
    force: bool = False,
) -> Dict[str, Any]:
    """Apply tax jurisdiction lookup to a transaction's finance envelope.

    ZIP code is the primary input — state is derived if not provided.
    Only fills in tax fields if not already set (unless force=True).
    Called from customer_defaults and from transaction_save.
    """
    existing_id = finance.get('sales_tax_id', 0)
    existing_rate = finance.get('sales_tax_rate')

    if not force and existing_rate is not None and existing_rate != 0:
        return finance

    tj = lookup_tax_jurisdiction(
        zip_code=zip_code,
        state=state,
        jurisdiction_name=jurisdiction_name or finance.get('sales_tax_name', ''),
        jurisdiction_id=existing_id or 0,
    )

    if tj:
        finance['sales_tax_id'] = tj['id']
        finance['sales_tax_name'] = tj['name']
        finance['sales_tax_rate'] = tj['sales_rate']
        finance['cost_tax_rate'] = tj['cost_rate']
        finance['tax_on_shipping_rate'] = tj['shipping_rate']
        if tj.get('gl_account_payable'):
            finance['tax_gl_account'] = tj['gl_account_payable']
        logger.info(
            "Tax applied: %s (%.4f%%) zip=%s state=%s [source=%s]",
            tj['name'], tj['sales_rate'], zip_code,
            tj.get('resolved_state', state), tj.get('source', 'unknown'),
        )
    else:
        logger.debug(
            "No tax rate found for zip=%s state=%s name=%s",
            zip_code, state, jurisdiction_name,
        )

    return finance


def get_tax_connection() -> Optional[Any]:
    """Get the active tax_service Connection record (if configured).

    Connection config expected:
        {
            "provider": "avalara" | "taxjar" | "vertex",
            "credentials": {"api_key": "...", "account_id": "..."},
            "settings": {"test_mode": true, "company_code": "DEFAULT"},
        }
    """
    Connection = apps.get_model("sync", "Connection")
    return Connection.objects.filter(
        type="tax_service",
        is_active=True,
    ).first()
