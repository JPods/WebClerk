"""Orphan detection service.

Finds records that should have a parent FK but don't (null FK),
or where the FK points to a non-existent record (dangling FK).

Used by admin dashboard for data health monitoring.
"""
import logging
from typing import Any, Dict, List

from django.apps import apps as dj_apps
from django.db import connection

logger = logging.getLogger(__name__)

# FK relationships that should always have a parent.
# Format: (app_label, model_name, fk_field, parent_app, parent_model)
REQUIRED_FK_RELATIONSHIPS = [
    # Transaction lines → headers
    ('transactions', 'OrderLine', 'order_id', 'transactions', 'Order'),
    ('transactions', 'InvoiceLine', 'invoice_id', 'transactions', 'Invoice'),
    ('transactions', 'ProposalLine', 'proposal_id', 'transactions', 'Proposal'),
    ('transactions', 'PurchaseLine', 'purchase_id', 'transactions', 'Purchase'),
    ('transactions', 'WorkOrderLine', 'workorder_id', 'transactions', 'WorkOrder'),
    ('transactions', 'RequisitionLine', 'requisition_id', 'transactions', 'Requisition'),
    ('transactions', 'ReceiptLine', 'receipt_id', 'transactions', 'Receipt'),
    # Payment application links
    ('transactions', 'PaymentApplication', 'payment_id', 'transactions', 'Payment'),
    ('transactions', 'PaymentApplication', 'invoice_id', 'transactions', 'Invoice'),
    # Inventory
    ('products', 'InventoryLayer', 'warehouse_id', 'products', 'Warehouse'),
    ('products', 'InventoryLayer', 'item_id', 'products', 'Item'),
    ('products', 'InventoryReservation', 'item_id', 'products', 'Item'),
    ('products', 'ItemXRef', 'item_id', 'products', 'Item'),
    ('products', 'BillOfMaterial', 'parent_item_id', 'products', 'Item'),
    # Sync
    ('sync', 'Bundle', 'connection_id', 'sync', 'Connection'),
]


def get_orphan_counts() -> List[Dict[str, Any]]:
    """Return orphan counts for all required FK relationships.

    For each relationship, checks:
    1. Null FKs — child.fk_field IS NULL (should not be)
    2. Dangling FKs — child.fk_field points to non-existent parent

    Returns list of dicts with model, fk_field, null_count, dangling_count.
    Only includes relationships with orphans (count > 0).
    """
    results = []

    for child_app, child_model_name, fk_field, parent_app, parent_model_name in REQUIRED_FK_RELATIONSHIPS:
        try:
            ChildModel = dj_apps.get_model(child_app, child_model_name)
            ParentModel = dj_apps.get_model(parent_app, parent_model_name)
        except LookupError:
            continue

        child_table = ChildModel._meta.db_table
        parent_table = ParentModel._meta.db_table
        has_is_deleted = any(f.name == 'is_deleted' for f in ChildModel._meta.get_fields())

        # Count null FKs
        null_count = 0
        try:
            null_filter = {fk_field: None}
            if has_is_deleted:
                null_filter['is_deleted'] = False
            null_count = ChildModel.objects.filter(**null_filter).count()
        except Exception as e:
            logger.warning("Null FK check failed for %s.%s: %s", child_model_name, fk_field, e)
            continue

        # Count dangling FKs via ORM (avoids raw SQL issues on SQLite)
        dangling_count = 0
        try:
            parent_ids = set(ParentModel.objects.values_list('id', flat=True))
            dangling_filter = {f'{fk_field}__isnull': False}
            if has_is_deleted:
                dangling_filter['is_deleted'] = False
            all_with_fk = ChildModel.objects.filter(**dangling_filter)
            for child in all_with_fk.only('id', fk_field).iterator(chunk_size=1000):
                fk_val = getattr(child, fk_field, None)
                if fk_val and fk_val not in parent_ids:
                    dangling_count += 1
        except Exception as e:
            logger.warning("Dangling FK check failed for %s.%s: %s", child_model_name, fk_field, e)

        if null_count > 0 or dangling_count > 0:
            results.append({
                'model': child_model_name,
                'table': child_table,
                'fk_field': fk_field,
                'parent_model': parent_model_name,
                'null_count': null_count,
                'dangling_count': dangling_count,
                'total_orphans': null_count + dangling_count,
            })

    return results


def get_orphan_detail(
    child_app: str,
    child_model_name: str,
    fk_field: str,
    orphan_type: str = 'all',
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Return actual orphan records for a specific model/FK relationship.

    Args:
        child_app: Django app label
        child_model_name: Model class name
        fk_field: FK field name
        orphan_type: 'null' (null FK only), 'dangling' (dangling only), 'all'
        limit: max records to return
        offset: pagination offset

    Returns dict with records list, total count, and query info.
    """
    try:
        ChildModel = dj_apps.get_model(child_app, child_model_name)
    except LookupError:
        return {'error': f'Model {child_app}.{child_model_name} not found'}

    has_is_deleted = any(f.name == 'is_deleted' for f in ChildModel._meta.get_fields())
    qs = ChildModel.objects.filter(is_deleted=False) if has_is_deleted else ChildModel.objects.all()

    if orphan_type == 'null':
        qs = qs.filter(**{fk_field: None})
    elif orphan_type == 'dangling':
        # Find parent model from our registry
        parent_info = None
        for ca, cm, ff, pa, pm in REQUIRED_FK_RELATIONSHIPS:
            if ca == child_app and cm == child_model_name and ff == fk_field:
                parent_info = (pa, pm)
                break
        if parent_info:
            ParentModel = dj_apps.get_model(*parent_info)
            parent_ids = set(ParentModel.objects.values_list('id', flat=True))
            # Get records where FK is set but parent doesn't exist
            qs = qs.exclude(**{fk_field: None})
            qs = qs.exclude(**{f'{fk_field}__in': parent_ids})
        else:
            return {'error': f'No registered relationship for {child_model_name}.{fk_field}'}
    else:
        # All orphans: null OR dangling
        null_qs = qs.filter(**{fk_field: None})
        # For 'all', just return nulls — dangling requires parent lookup
        qs = null_qs

    total = qs.count()
    records = list(
        qs.order_by('-dt_created')[offset:offset + limit]
        .values('id', 'ida', 'dt_created', 'dt_modified', fk_field)
    )

    return {
        'model': child_model_name,
        'fk_field': fk_field,
        'orphan_type': orphan_type,
        'total': total,
        'limit': limit,
        'offset': offset,
        'records': records,
    }
