"""
Clone Service — duplicate any record with its children.

Creates a fresh copy with new id/ida, updated timestamps, and cleared
applied actions. Lines are copied with fresh line numbers.

Usage:
    clone_record('order', 42, include_children=True)
    → creates a new order with all lines, fresh dates, status='planned'
"""
from __future__ import annotations

import time
from django.apps import apps as dj_apps
from django.db import transaction


def _now_ms():
    return int(time.time() * 1000)


# Model → (line model name, FK field name on the line)
CHILDREN_MAP = {
    'order': ('OrderLine', 'order'),
    'invoice': ('InvoiceLine', 'invoice'),
    'proposal': ('ProposalLine', 'proposal'),
    'purchase': ('PurchaseLine', 'purchase'),
    'work_order': ('WorkOrderLine', 'workorder'),
}

# Fields to reset on cloned records
RESET_FIELDS = {
    'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
    'is_locked', 'parent_id', 'parent_model',
}

# Fields to clear (set to default) on cloned records
CLEAR_ON_CLONE = {
    'balance': 0,
    'status': 'planned',
    'is_locked': False,
}


def clone_record(model_name: str, record_id: int, include_children: bool = True, contact_id: int = None) -> dict:
    """Clone a record and optionally its child lines.

    Creates a fresh copy with:
    - New id, uuid, ida (auto-generated on save)
    - Current timestamps
    - Status reset to 'planned'
    - Balance reset to 0
    - is_locked = False
    - parent_id/parent_model cleared
    - Commission accrual reset (accrued=False)
    - Lines copied with fresh ids and line numbers

    Args:
        model_name: 'order', 'invoice', 'proposal', 'purchase', 'work_order', or any model
        record_id: PK of the record to clone
        include_children: if True, also clone child lines
        contact_id: who initiated the clone (for audit)

    Returns: {clone_id, clone_ida, model_name, lines_cloned, source_id}
    """
    # Resolve the model
    model_map = {
        'order': ('transactions', 'Order'),
        'invoice': ('transactions', 'Invoice'),
        'proposal': ('transactions', 'Proposal'),
        'purchase': ('transactions', 'Purchase'),
        'work_order': ('transactions', 'WorkOrder'),
        'item': ('products', 'Item'),
        'customer': ('orgs', 'OrgBase'),
        'contact': ('core', 'Contact'),
        'action': ('core', 'Action'),
    }

    if model_name in model_map:
        app, model = model_map[model_name]
        Model = dj_apps.get_model(app, model)
    else:
        # Try to find via model registry
        try:
            from apps.core.constants.model_registry import get_model_meta
            meta = get_model_meta(model_name)
            if meta:
                Model = meta.import_model()
            else:
                return {'error': f'Unknown model: {model_name}'}
        except Exception:
            return {'error': f'Cannot resolve model: {model_name}'}

    try:
        source = Model.objects.get(pk=record_id)
    except Model.DoesNotExist:
        return {'error': f'{model_name} {record_id} not found'}

    lines_cloned = 0

    with transaction.atomic():
        # Clone the header
        clone = Model()

        # Copy all fields except the ones we reset
        for field in source._meta.get_fields():
            if not hasattr(field, 'column'):
                continue  # skip relations without columns
            name = field.name
            if name in RESET_FIELDS:
                continue
            try:
                setattr(clone, name, getattr(source, name))
            except Exception:
                pass

        # Apply resets
        clone.pk = None
        clone.id = None
        if hasattr(clone, 'uuid'):
            clone.uuid = None  # CoreModel.save() generates new uuid
        if hasattr(clone, 'ida'):
            clone.ida = ''  # CoreModel.save() generates new ida

        for field, default in CLEAR_ON_CLONE.items():
            if hasattr(clone, field):
                setattr(clone, field, default)

        # Clear parent link (this is a new record, not a conversion)
        if hasattr(clone, 'parent_id'):
            clone.parent_id = None
        if hasattr(clone, 'parent_model'):
            clone.parent_model = None

        # Reset commission accrual
        if hasattr(clone, 'commission'):
            comm = clone.commission or {}
            if isinstance(comm, dict):
                comm['accrued'] = False
                comm['dt_accrued'] = 0
                clone.commission = comm

        # Clear metadata applied actions, GL postings, shipping
        if hasattr(clone, 'metadata'):
            meta = clone.metadata or {}
            if isinstance(meta, dict):
                meta.pop('gl_accounts', None)
                meta.pop('shipping', None)
                meta.pop('credit_warnings', None)
                meta.pop('eom', None)
                # Keep versioning, flow, history for reference
                meta['cloned_from'] = {
                    'model': model_name,
                    'id': record_id,
                    'ida': getattr(source, 'ida', ''),
                    'dt_cloned': _now_ms(),
                    'cloned_by': contact_id,
                }
                clone.metadata = meta

        # Reset totals
        if hasattr(clone, 'totals'):
            totals = clone.totals or {}
            if isinstance(totals, dict):
                totals['received'] = 0
                totals['balance'] = totals.get('total', 0)
                clone.totals = totals

        clone.save()

        # Clone children (lines)
        if include_children and model_name in CHILDREN_MAP:
            line_model_name, parent_fk = CHILDREN_MAP[model_name]
            LineModel = dj_apps.get_model('transactions', line_model_name)
            source_lines = LineModel.objects.filter(**{f'{parent_fk}_id': record_id}).order_by('line_number')

            for line in source_lines:
                line_clone = LineModel()

                for field in line._meta.get_fields():
                    if not hasattr(field, 'column'):
                        continue
                    name = field.name
                    if name in RESET_FIELDS:
                        continue
                    try:
                        setattr(line_clone, name, getattr(line, name))
                    except Exception:
                        pass

                line_clone.pk = None
                line_clone.id = None
                if hasattr(line_clone, 'uuid'):
                    line_clone.uuid = None
                if hasattr(line_clone, 'ida'):
                    line_clone.ida = ''

                # Set parent FK to the new clone
                setattr(line_clone, f'{parent_fk}_id', clone.pk)

                # Reset line commission accrual
                if hasattr(line_clone, 'commission'):
                    lcomm = line_clone.commission or {}
                    if isinstance(lcomm, dict):
                        lcomm['accrued'] = False
                        lcomm['dt_accrued'] = 0
                        line_clone.commission = lcomm

                line_clone.save()
                lines_cloned += 1

            # Re-price all cloned lines with current pricing
            try:
                from apps.products.services.pricing import apply_line_pricing
                from apps.transactions.services.totals import recalculate_totals

                line_model_key = model_name + '_line'
                customer_id = getattr(clone, 'customer_id', None)
                cloned_lines = LineModel.objects.filter(**{f'{parent_fk}_id': clone.pk})

                for cl in cloned_lines:
                    try:
                        apply_line_pricing(line_model_key, cl.pk, customer_id=customer_id)
                    except Exception:
                        pass  # keep original price if re-pricing fails

                # Recalculate header totals with updated prices
                recalculate_totals(clone.pk, model_name)
            except Exception:
                pass  # totals service may not be available

    # Refresh to get auto-generated ida
    clone.refresh_from_db()

    return {
        'clone_id': clone.pk,
        'clone_ida': getattr(clone, 'ida', ''),
        'model_name': model_name,
        'source_id': record_id,
        'source_ida': getattr(source, 'ida', ''),
        'lines_cloned': lines_cloned,
    }
