import time
from functools import lru_cache
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List
from django.conf import settings
from apps.transactions.models.line_variants import (
    ProposalLine, SalesOrderLine, InvoiceLine, PurchaseOrderLine, WorkorderLine, RequisitionLine
)
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

LINE_MODEL_MAP = {
    'proposal-line': ProposalLine,
    'sales-order-line': SalesOrderLine,
    'invoice-line': InvoiceLine,
    'purchase-order-line': PurchaseOrderLine,
    'workorder-line': WorkorderLine,
    'requisition-line': RequisitionLine,
}
ALL_MODELS: List[type] = list(LINE_MODEL_MAP.values())


def _cast_decimal(val) -> Decimal:
    if isinstance(val, (int, float, Decimal)):
        try:
            return Decimal(str(val))
        except InvalidOperation:
            return Decimal('0')
    if isinstance(val, str):
        try:
            return Decimal(val)
        except InvalidOperation:
            return Decimal('0')
    return Decimal('0')


DEFAULT_CACHE_TTL_SECONDS = getattr(settings, 'TX_AGGREGATE_TTL_SECONDS', 60)  # fallback if setting not provided

@lru_cache(maxsize=4096)
def _compute_line_aggregate_internal(parent_id: int,
                                     model_key: Optional[str],
                                     window: int,
                                     include_breakdown: bool) -> Dict[str, Any]:
    """Core cached computation.

    window is derived from floor(now / ttl_seconds) so changes when TTL window rolls.
    include_breakdown controls whether breakdown is returned (even when scoped to one model).
    """
    if model_key:
        model = LINE_MODEL_MAP.get(model_key)
        if not model:
            raise ValueError('invalid-model')
        models_to_scan: List[type] = [model]
    else:
        models_to_scan = ALL_MODELS

    total_lines = 0
    total_price_extended = Decimal('0')
    total_cost_extended = Decimal('0')

    breakdown: Dict[str, Dict[str, str | int]] = {}
    for model in models_to_scan:
        qs = model.objects.filter(parent_id=parent_id)
        model_count = qs.count()
        total_lines += model_count
        price_sum = Decimal('0')
        cost_sum = Decimal('0')
        for obj in qs.only('price', 'cost'):
            price_ext = (obj.price or {}).get('extended')
            cost_ext = (obj.cost or {}).get('extended')
            dec_price = _cast_decimal(price_ext)
            dec_cost = _cast_decimal(cost_ext)
            total_price_extended += dec_price
            total_cost_extended += dec_cost
            price_sum += dec_price
            cost_sum += dec_cost
        if include_breakdown or not model_key:
            # always compute per model if requested or unscoped
            key = next((k for k, v in LINE_MODEL_MAP.items() if v is model), None)
            if key:
                breakdown[key] = {
                    'lines': model_count,
                    'price_extended': str(price_sum),
                    'cost_extended': str(cost_sum),
                }

    result = {
        'parent_id': parent_id,
        'total_lines': total_lines,
        'total_price_extended': str(total_price_extended),
        'total_cost_extended': str(total_cost_extended),
    }
    if model_key:
        result['model'] = model_key
    if breakdown:
        result['breakdown'] = breakdown
    return result

def compute_line_aggregate(parent_id: int,
                           model_key: Optional[str] = None,
                           ttl_seconds: Optional[int] = None,
                           include_breakdown: bool = False) -> Dict[str, Any]:
    # allow dynamic default from settings each call (in case reloaded)
    dynamic_default = getattr(settings, 'TX_AGGREGATE_TTL_SECONDS', DEFAULT_CACHE_TTL_SECONDS)
    ttl = max(5, ttl_seconds or dynamic_default)  # guard against very low values
    now = int(time.time())
    window = now // ttl
    data = _compute_line_aggregate_internal(parent_id, model_key, window, include_breakdown)
    data['ttl_seconds'] = ttl
    data['cache_window'] = window  # optional debugging / introspection
    return data


@receiver([post_save, post_delete], sender=ProposalLine)
@receiver([post_save, post_delete], sender=SalesOrderLine)
@receiver([post_save, post_delete], sender=InvoiceLine)
@receiver([post_save, post_delete], sender=PurchaseOrderLine)
@receiver([post_save, post_delete], sender=WorkorderLine)
@receiver([post_save, post_delete], sender=RequisitionLine)
def clear_aggregate_cache(**kwargs):  # pragma: no cover - simple invalidation
    _compute_line_aggregate_internal.cache_clear()
