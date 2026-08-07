"""Batch dashboard counts — one call replaces N×M individual queries.

Usage via manage endpoint:
    POST /wcapi/manage/
    {
        "action": "get_dashboard_counts",
        "params": {
            "models": ["order", "invoice", "proposal"],
            "periods": [
                {"key": "this_mo", "from": 1722470400000, "to": 1725148800000},
                {"key": "last_mo", "from": 1719792000000, "to": 1722470400000}
            ]
        }
    }

Returns:
    {
        "order": {"this_mo": 5, "last_mo": 12},
        "invoice": {"this_mo": 3, "last_mo": 8},
        ...
    }
"""
import logging
from django.apps import apps
from django.utils import timezone

logger = logging.getLogger(__name__)

# Models that can be queried — prevents arbitrary table enumeration
MODEL_REGISTRY = {
    # Transactions
    'order': 'transactions.Order',
    'invoice': 'transactions.Invoice',
    'proposal': 'transactions.Proposal',
    'purchase': 'transactions.Purchase',
    'payment': 'transactions.Payment',
    'receipt': 'transactions.Receipt',
    'workorder': 'transactions.WorkOrder',
    'requisition': 'transactions.Requisition',
    # Products
    'item': 'products.Item',
    'products.Variant': 'products.Variant',
    'products.BillOfMaterial': 'products.BillOfMaterial',
    'products.Catalog': 'products.Catalog',
    'products.Serial': 'products.Serial',
    'products.Specification': 'products.Specification',
    'products.Warehouse': 'products.Warehouse',
    # Orgs
    'contact': 'core.Contact',
    'customer': 'orgs.Customer',
    'vendor': 'orgs.Vendor',
    'manufacturer': 'orgs.Manufacturer',
    'employee': 'orgs.Employee',
    'rep': 'orgs.Rep',
    # Admin
    'action': 'core.Action',
    'setting': 'core.Setting',
    'core.Report': 'core.Report',
    'docs.Document': 'docs.Document',
    'support.Quality': 'support.Quality',
    # Sync
    'sync.Connection': 'sync.Connection',
    'sync.Bundle': 'sync.Bundle',
    'conversion.ConversionProject': 'conversion.ConversionProject',
    # Communications
    'communications.Email': 'communications.Email',
    'communications.Phone': 'communications.Phone',
    'communications.Address': 'communications.Address',
    'communications.Domain': 'communications.Domain',
}


def _resolve_model(name: str):
    """Resolve a model name to a Django model class."""
    app_model = MODEL_REGISTRY.get(name)
    if not app_model:
        return None
    try:
        app_label, model_name = app_model.rsplit('.', 1)
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


def get_dashboard_counts(params: dict) -> dict:
    """Return period counts for multiple models in a single call."""
    model_names = params.get('models', [])
    periods = params.get('periods', [])

    if not model_names or not periods:
        return {}

    # Cap to prevent abuse
    if len(model_names) > 20:
        model_names = model_names[:20]
    if len(periods) > 10:
        periods = periods[:10]

    result = {}
    for name in model_names:
        Model = _resolve_model(name)
        if not Model:
            result[name] = {p['key']: 0 for p in periods}
            continue

        model_counts = {}
        for p in periods:
            key = p.get('key', '')
            dt_from = p.get('from', 0)
            dt_to = p.get('to', 0)
            try:
                qs = Model.objects.filter(
                    dt_created__gte=dt_from,
                    dt_created__lte=dt_to,
                )
                # Exclude soft-deleted if the model has the field
                if hasattr(Model, 'is_deleted'):
                    qs = qs.filter(is_deleted=False)
                model_counts[key] = qs.count()
            except Exception as e:
                logger.warning(f"dashboard_counts: {name}/{key} failed: {e}")
                model_counts[key] = 0

        result[name] = model_counts

    return result
