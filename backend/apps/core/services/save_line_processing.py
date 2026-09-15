"""Line processing service for the universal save pipeline.

Extracted from save_view.py — handles line CRUD for header models
(order, invoice, purchase, workorder, proposal), pending inventory
creation, source line adjustment, and refs.links updates.

Part of the save_* service cluster:
  save_field_assignment.py  — field coercion, JSON merge
  save_line_processing.py   — this file
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import models

from apps.core.constants.model_registry import get_model

console_logger = logging.getLogger('console')

HEADER_MODELS = frozenset({'order', 'invoice', 'purchase', 'workorder', 'proposal'})

LINE_MODEL_MAP = {
    'order': ('OrderLine', 'order'),
    'invoice': ('InvoiceLine', 'invoice'),
    'purchase': ('PurchaseLine', 'purchase'),
    'workorder': ('WorkOrderLine', 'workorder'),
    'proposal': ('ProposalLine', 'proposal'),
}


def _normalize_model_key(model_key: str) -> str:
    return model_key.replace('_', '').lower()


def _is_new_line(line_id) -> bool:
    """Detect new lines: null, temp-*, or negative IDs."""
    if line_id is None:
        return True
    if isinstance(line_id, str) and line_id.startswith('temp-'):
        return True
    if isinstance(line_id, (int, float)) and line_id < 0:
        return True
    return False


def _get_fk_descriptors(line_model) -> set:
    """Build set of FK descriptor names to skip during field copy."""
    descriptors = set()
    for f in line_model._meta.get_fields():
        if hasattr(f, 'related_model') and f.related_model is not None:
            descriptors.add(f.name)
    return descriptors


def _copy_line_fields(line_obj, line_data: dict, skip_fields: tuple, fk_descriptors: set):
    """Copy fields from line_data to line_obj, skipping FK descriptors and private fields."""
    for field_name, field_value in line_data.items():
        if field_name in skip_fields:
            continue
        if field_name in fk_descriptors and not isinstance(field_value, models.Model):
            continue
        if field_name.startswith('_'):
            continue
        if hasattr(line_obj, field_name):
            setattr(line_obj, field_name, field_value)


def _derive_item_fk(line_obj, line_data: dict):
    """Set item_fk_id from item envelope if not already set."""
    if getattr(line_obj, 'item_fk_id', None):
        return
    item_env = line_data.get('item') or {}
    if isinstance(item_env, dict):
        _item_id = item_env.get('item_id') or item_env.get('id')
        if _item_id:
            line_obj.item_fk_id = _item_id


def _create_pending(parent, model_key: str, line_obj, line_data: dict):
    """Create pending inventory record for a new line."""
    try:
        from apps.transactions.services.line_manage import LineItemService
        service = LineItemService(create_pending=True)
        service._create_pending_for_new_line(
            parent=parent,
            parent_model_key=model_key,
            line=line_obj,
            line_data=line_data,
        )
    except Exception as e:
        console_logger.error(
            f"[SAVE_LINES] Failed to create pending for line {line_obj.id}: {e}",
            exc_info=True,
        )


def _adjust_source(line_data: dict, norm_model: str, line_obj, adjust_fn):
    """Adjust source line quantity remaining after conversion."""
    try:
        refs = line_data.get('refs') or {}
        source = refs.get('source') or {}
        qty = line_obj.quantity or {}
        line_qty = float(qty.get('active', 0) or qty.get('staged', 0) or 0)
        if line_qty > 0:
            adjust_fn(source, norm_model, line_qty, line_obj)
    except Exception as e:
        console_logger.warning(
            f"[SAVE_LINES] Source line update failed for line {line_obj.id}: {e}"
        )


def _update_refs_links(obj, line_model_name: str, new_line_ids: list[int]):
    """Add new line IDs to parent's refs.links."""
    refs_key = line_model_name.lower().replace('line', '_line')
    try:
        refs = obj.refs or {}
        if not isinstance(refs, dict):
            refs = {}
        links = refs.get('links', {})
        if not isinstance(links, dict):
            links = {}
        line_refs = links.get(refs_key, [])
        if not isinstance(line_refs, list):
            line_refs = []
        for new_id in new_line_ids:
            if {'id': new_id} not in line_refs:
                line_refs.append({'id': new_id})
        links[refs_key] = line_refs
        refs['links'] = links
        obj.refs = refs
        obj.save(update_fields=['refs', 'version', 'dt_modified'])
    except Exception as e:
        console_logger.error(f"[SAVE_LINES] Error updating refs.links: {e}")


def process_lines(
    obj,
    data: dict,
    model_key: str,
    adjust_source_fn=None,
) -> list[int]:
    """Process lines for a header model (order, invoice, etc.).

    Args:
        obj: Parent model instance (already saved).
        data: Full request data dict (must contain 'lines' key).
        model_key: Normalized model key (e.g. 'order').
        adjust_source_fn: Optional callback for source line adjustment.

    Returns:
        List of newly created line IDs.
    """
    norm_model = _normalize_model_key(model_key)
    if norm_model not in HEADER_MODELS:
        return []

    lines_data = data.get('lines')
    if not isinstance(lines_data, list):
        return []

    line_info = LINE_MODEL_MAP.get(norm_model)
    if not line_info:
        console_logger.warning(f"[SAVE_LINES] No line model mapping for {model_key}")
        return []

    line_model_name, fk_field_name = line_info
    LineModel = get_model(line_model_name.lower())
    if not LineModel:
        console_logger.error(f"[SAVE_LINES] Line model {line_model_name} not found")
        return []

    fk_descriptors = _get_fk_descriptors(LineModel)
    skip_fields = ('id', 'model_name', fk_field_name, f'{fk_field_name}_id', 'parent', 'parent_id')
    new_line_ids = []

    for idx, line_data in enumerate(lines_data):
        try:
            line_id = line_data.get('id')

            if _is_new_line(line_id):
                line_obj = LineModel()
                setattr(line_obj, f'{fk_field_name}_id', obj.id)
                _copy_line_fields(line_obj, line_data, skip_fields, fk_descriptors)
                _derive_item_fk(line_obj, line_data)
                line_obj._pending_created = True
                line_obj.save()
                new_line_ids.append(line_obj.id)

                _create_pending(obj, model_key, line_obj, line_data)

                if adjust_source_fn:
                    _adjust_source(line_data, norm_model, line_obj, adjust_source_fn)
            else:
                try:
                    line_obj = LineModel.objects.get(id=line_id)
                    _copy_line_fields(line_obj, line_data, skip_fields, fk_descriptors)
                    _derive_item_fk(line_obj, line_data)
                    line_obj.save()
                except LineModel.DoesNotExist:
                    console_logger.warning(f"[SAVE_LINES] Line ID {line_id} not found, skipping")

        except Exception as e:
            console_logger.error(f"[SAVE_LINES] Error saving line {idx}: {e}", exc_info=True)

    if new_line_ids:
        _update_refs_links(obj, line_model_name, new_line_ids)

        from apps.products.dispatch_pending import dispatch_pending_processing
        dispatch_pending_processing(limit=200, caller='save_line_processing')

    return new_line_ids
