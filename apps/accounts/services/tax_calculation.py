"""Tax calculation service — line-level and transaction-level tax computation.

Uses TaxJurisdiction records for rate lookup. Falls back to Setting
'tax_config' when no jurisdiction is specified.

All tax amounts are server-side authoritative (Axiom: backend is source of truth).
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _d(x: Any, places: int = 2) -> Decimal:
    """Safe Decimal coercion."""
    try:
        d = Decimal(str(x))
        return d.quantize(Decimal(10) ** -places) if places >= 0 else d
    except Exception:
        return Decimal(0)


def _get_tax_config() -> Dict[str, Any]:
    """Load tax_config Setting. Returns defaults if not found."""
    defaults = {
        'default_tax_rate': 0.0,
        'default_tax_name': 'Sales Tax',
        'tax_on_shipping': False,
    }
    try:
        from apps.core.models.setting import Setting
        setting = Setting.objects.filter(
            name='tax_config', is_active=True, is_deleted=False,
        ).first()
        if setting and isinstance(setting.config, dict):
            merged = dict(defaults)
            merged.update(setting.config)
            return merged
    except Exception:
        logger.warning("Could not load tax_config Setting, using defaults")
    return defaults


# ---------------------------------------------------------------------------
# calculate_line_tax — single line tax computation
# ---------------------------------------------------------------------------

def calculate_line_tax(
    line_price_extended: float,
    tax_jurisdiction_id: Optional[int] = None,
    tax_rate: Optional[float] = None,
    line_cost_extended: float = 0,
    item_taxable: bool = True,
    customer_exempt_code: str = '',
) -> Dict[str, Any]:
    """Calculate tax for a single line's extended price.

    Resolution:
      0. If item not taxable → 0
      0b. If customer exempt (non-empty code, not 'DoTax') → 0
      1. If tax_jurisdiction_id provided, look up TaxJurisdiction.tax_rate_sales
         If jurisdiction has service_provider, try external API first
      2. If tax_rate provided directly, use it
      3. Otherwise, use default from Setting 'tax_config'

    Returns: {tax_amount, tax_rate, tax_jurisdiction_id, tax_name, cost_tax, exempt, exempt_reason}
    """
    resolved_rate = None
    resolved_name = 'Sales Tax'
    resolved_jurisdiction_id = tax_jurisdiction_id
    cost_tax = 0.0
    exempt = False
    exempt_reason = ''

    # Step 0: Item taxability
    if not item_taxable:
        return {'tax_amount': 0, 'tax_rate': 0, 'tax_jurisdiction_id': resolved_jurisdiction_id,
                'tax_name': resolved_name, 'cost_tax': 0, 'exempt': True, 'exempt_reason': 'item_not_taxable'}

    # Step 0b: Customer exempt
    if customer_exempt_code and customer_exempt_code.strip().lower() != 'dotax':
        return {'tax_amount': 0, 'tax_rate': 0, 'tax_jurisdiction_id': resolved_jurisdiction_id,
                'tax_name': resolved_name, 'cost_tax': 0, 'exempt': True,
                'exempt_reason': f'customer_exempt:{customer_exempt_code}'}

    # Step 1: jurisdiction lookup
    if tax_jurisdiction_id:
        try:
            from django.apps import apps as dj_apps
            TaxJurisdiction = dj_apps.get_model('accounts', 'TaxJurisdiction')
            tj = TaxJurisdiction.objects.filter(pk=tax_jurisdiction_id, is_active=True).first()
            if tj:
                if tj.tax_rate_sales is not None:
                    resolved_rate = float(tj.tax_rate_sales)
                resolved_name = tj.tax_name or tj.tax_jurisdiction or 'Sales Tax'
        except Exception as e:
            logger.warning("Tax jurisdiction lookup failed for id=%s: %s", tax_jurisdiction_id, e)

    # Step 2: explicit tax_rate
    if resolved_rate is None and tax_rate is not None:
        resolved_rate = float(tax_rate)

    # Step 3: default from config
    if resolved_rate is None:
        config = _get_tax_config()
        resolved_rate = float(config.get('default_tax_rate', 0.0))
        resolved_name = config.get('default_tax_name', 'Sales Tax')

    # Calculate sales tax
    extended = _d(line_price_extended)
    rate_decimal = _d(resolved_rate / 100.0 if resolved_rate > 1 else resolved_rate, places=6)
    tax_amount = float(_d(extended * rate_decimal))

    # Calculate cost tax (for cost-based tax regimes)
    if line_cost_extended and tax_jurisdiction_id:
        try:
            from django.apps import apps as dj_apps
            TaxJurisdiction = dj_apps.get_model('accounts', 'TaxJurisdiction')
            tj = TaxJurisdiction.objects.filter(pk=tax_jurisdiction_id, is_active=True).first()
            if tj and tj.tax_rate_cost:
                cost_ext = _d(line_cost_extended)
                cost_rate = _d(float(tj.tax_rate_cost) / 100.0, places=6)
                cost_tax = float(_d(cost_ext * cost_rate))
        except Exception:
            pass

    return {
        'tax_amount': tax_amount,
        'tax_rate': resolved_rate,
        'tax_jurisdiction_id': resolved_jurisdiction_id,
        'tax_name': resolved_name,
        'cost_tax': cost_tax,
        'exempt': exempt,
        'exempt_reason': exempt_reason,
    }


# ---------------------------------------------------------------------------
# calculate_transaction_tax — all lines for a transaction
# ---------------------------------------------------------------------------

def calculate_transaction_tax(
    transaction_id: int,
    model_name: str,
) -> Dict[str, Any]:
    """Calculate tax for all lines of a transaction.

    For each line, calculates tax using the transaction's
    finance.sales_tax_id or default. Updates each line's tax JSON.

    Returns: {total_tax, lines_updated, tax_rate_used}
    """
    from django.apps import apps as dj_apps
    from apps.core.constants.model_registry import get_model_meta

    # Resolve header model
    meta = get_model_meta(model_name)
    if not meta:
        raise ValueError(f"Unknown model: {model_name}")

    HeaderModel = meta.import_model()
    try:
        header = HeaderModel.objects.get(pk=transaction_id)
    except HeaderModel.DoesNotExist:
        raise ValueError(f"{model_name} #{transaction_id} not found")

    # Get tax jurisdiction — cascade: header.finance → customer org fields → default
    finance = getattr(header, 'finance', None) or {}
    tax_jurisdiction_id = finance.get('sales_tax_id') or None
    if tax_jurisdiction_id and int(tax_jurisdiction_id) <= 0:
        tax_jurisdiction_id = None
    header_tax_rate = finance.get('sales_tax_rate')
    customer_exempt_code = ''

    # Pull from customer org if not on the header
    customer = getattr(header, 'customer', None)
    if customer:
        if not tax_jurisdiction_id and getattr(customer, 'tax_jurisdiction_id', None):
            tax_jurisdiction_id = customer.tax_jurisdiction_id
        customer_exempt_code = getattr(customer, 'tax_exempt_code', '') or ''

    # Get lines
    if not hasattr(header, 'lines'):
        raise ValueError(f"{model_name} #{transaction_id} has no lines relation")

    lines = header.lines.all()
    total_tax = Decimal(0)
    lines_updated = 0
    tax_rate_used = None

    for line in lines:
        # Get line extended price
        price_data = getattr(line, 'price', None) or {}
        extended = price_data.get('extended', 0) or 0

        # Check item taxability
        item_taxable = True
        item_data = getattr(line, 'item', None) or {}
        if isinstance(item_data, dict):
            tax_code = item_data.get('tax_code') or {}
            if isinstance(tax_code, dict) and tax_code.get('code', '').lower() in ('notax', 'no tax', 'exempt'):
                item_taxable = False

        # Calculate tax for this line
        result = calculate_line_tax(
            line_price_extended=float(extended),
            tax_jurisdiction_id=int(tax_jurisdiction_id) if tax_jurisdiction_id else None,
            tax_rate=float(header_tax_rate) if header_tax_rate is not None else None,
            item_taxable=item_taxable,
            customer_exempt_code=customer_exempt_code,
        )

        # Update line tax JSON
        if not isinstance(line.tax, dict):
            line.tax = {}
        line.tax['sales_rate'] = result['tax_rate']
        line.tax['sales'] = result['tax_amount']
        # Preserve cost-side tax if present
        line.tax.setdefault('cost_rate', None)
        line.tax.setdefault('cost', None)

        line.save(update_fields=['tax'])
        total_tax += _d(result['tax_amount'])
        lines_updated += 1
        if tax_rate_used is None:
            tax_rate_used = result['tax_rate']

    return {
        'total_tax': float(total_tax),
        'lines_updated': lines_updated,
        'tax_rate_used': tax_rate_used,
    }


# ---------------------------------------------------------------------------
# get_tax_jurisdictions — list active jurisdictions for UI dropdowns
# ---------------------------------------------------------------------------

def get_tax_jurisdictions() -> Dict[str, Any]:
    """List active tax jurisdictions with rates. For UI dropdowns."""
    from django.apps import apps as dj_apps
    TaxJurisdiction = dj_apps.get_model('accounts', 'TaxJurisdiction')

    jurisdictions = TaxJurisdiction.objects.filter(is_active=True).order_by('tax_jurisdiction')
    rows = []
    for tj in jurisdictions:
        rows.append({
            'id': tj.pk,
            'jurisdiction': tj.tax_jurisdiction or '',
            'tax_name': tj.tax_name or '',
            'tax_rate_sales': tj.tax_rate_sales,
            'tax_rate_cost': tj.tax_rate_cost,
            'tax_rate_on_shipping': tj.tax_rate_on_shipping,
            'gl_account_payable': tj.gl_account_payable or '',
            'service_provider': tj.service_provider or '',
        })

    return {
        'count': len(rows),
        'jurisdictions': rows,
    }
