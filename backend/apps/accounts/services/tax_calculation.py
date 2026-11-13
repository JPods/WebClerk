"""Tax jurisdictions — the list for the form's dropdown.

Tax is calculated in one place: compute_totals (transactions/services/pricing/totals_compute.py),
with the rate resolved by tax_resolve.py. The second calculator that lived here
(calculate_line_tax, with its own tax_config Setting) was removed 2026-11-12 (readme 111).
"""
from typing import Any, Dict


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
