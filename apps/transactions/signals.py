from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps as dj_apps
from django.db import transaction


@receiver(post_save, sender=dj_apps.get_model('transactions', 'Invoice'))
def create_ledgers_for_invoice(sender, instance, created, **kwargs):  # pragma: no cover
    """On invoice creation, create ledger records based on terms.

    Assumptions:
    - Invoice has prefs.payment_terms or a direct Term FK in future.
    - Total amount can be derived; for now, pull from aggregation or invoice.total.total if present.
    """
    if not created:
        return

    # Attempt to locate Term by name from prefs or by id if present
    Term = dj_apps.get_model('accounts', 'Term')
    terms_spec = (getattr(instance, 'prefs', {}) or {}).get('payment_terms') or {}
    term_obj = None
    if isinstance(terms_spec, dict):
        term_id = terms_spec.get('id')
        term_name = terms_spec.get('name')
        if term_id:
            term_obj = Term.objects.filter(id=term_id).first()
        if not term_obj and term_name:
            term_obj = Term.objects.filter(description__iexact=term_name).first()

    if not term_obj:
        return  # no terms, nothing to create

    # Determine total amount
    total_map = getattr(instance, 'total', {}) or {}
    total_val = total_map.get('total') or total_map.get('amount') or 0
    try:
        total = Decimal(str(total_val))
    except Exception:
        total = Decimal('0')
    if total <= 0:
        # Optionally: compute from lines aggregation if available
        from apps.transactions.aggregation import compute_line_aggregate
        agg = compute_line_aggregate(parent_id=getattr(instance, 'id'), model_key='invoice-line')
        total = Decimal(agg.get('total_price_extended', '0'))
        if total <= 0:
            return

    from apps.accounts.services.terms_ledger import create_ledger_records
    create_ledger_records(invoice=instance, total=total, term=term_obj, strategy='records')


# --- Maintain header.refs.links collections for lines ----------------------

def _ensure_link(list_obj, value: int):
    try:
        if isinstance(list_obj, list) and value not in list_obj:
            list_obj.append(value)
    except Exception:
        pass


@receiver(post_save, sender=dj_apps.get_model('transactions', 'InvoiceLine'))
def maintain_invoice_links(sender, instance, created, **kwargs):  # pragma: no cover - simple list update
    header = getattr(instance, 'parent', None)
    if not header:
        return
    refs = getattr(header, 'refs', {}) or {}
    links = refs.setdefault('links', {}) if isinstance(refs, dict) else {}
    ilist = links.setdefault('invoice_line', []) if isinstance(links, dict) else []
    line_id = getattr(instance, 'id', None)
    if isinstance(line_id, int):
        _ensure_link(ilist, line_id)
    header.refs = refs
    # Save minimally; avoid recursive signals on lines by saving header only
    header.save(update_fields=['refs', 'dt_modified', 'version'])


@receiver(post_save, sender=dj_apps.get_model('transactions', 'SalesOrderLine'))
def maintain_sales_order_links(sender, instance, created, **kwargs):  # pragma: no cover
    header = getattr(instance, 'parent', None)
    if not header:
        return
    refs = getattr(header, 'refs', {}) or {}
    links = refs.setdefault('links', {}) if isinstance(refs, dict) else {}
    # Use model-name singular key
    olist = links.setdefault('sales_order_line', []) if isinstance(links, dict) else []
    line_id = getattr(instance, 'id', None)
    if isinstance(line_id, int):
        _ensure_link(olist, line_id)
    header.refs = refs
    header.save(update_fields=['refs', 'dt_modified', 'version'])
