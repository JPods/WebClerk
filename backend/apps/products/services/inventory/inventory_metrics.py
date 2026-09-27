from __future__ import annotations

"""Lightweight aggregation helpers for inventory & reservation operational metrics.

Intended for quick management visibility (command / admin dashboard feed).
Avoids heavy scans – focuses on current state counts & sums.
"""

from typing import Dict, Any
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.metrics import InventoryMetricsSnapshot
from apps.products.models.processor_runs import InventoryAdjustmentProcessorRun


def summarize_inventory_metrics(include_samples: bool = False, sample_limit: int = 5) -> Dict[str, Any]:
    now = timezone.now()
    # Pending inventory adjustments (via Pending model)
    from apps.core.models import Pending
    padj_qs = Pending.objects.filter(model_name='item', purpose__startswith='inventory_')
    padj_processed = padj_qs.exclude(dt_processed=0).count()
    padj_unprocessed = padj_qs.filter(dt_processed=0).count()
    padj_state_counts = {'processed': padj_processed, 'unprocessed': padj_unprocessed}
    padj_state_qty = {}

    # Stack level aggregates
    stacks = InventoryLayer.objects.all()
    stack_count = stacks.count()
    remaining_agg = Decimal('0')
    received_agg = Decimal('0')
    issued_agg = Decimal('0')
    for s in stacks.only('id', 'quantity'):
        q = getattr(s, 'quantity', {}) or {}
        received_agg += Decimal(str(q.get('received', 0) or 0))
        issued_agg += Decimal(str(q.get('issued', 0) or 0)) + Decimal(str(q.get('scrapped', 0) or 0))
        remaining_agg += Decimal(str(q.get('received', 0) or 0)) - (Decimal(str(q.get('issued', 0) or 0)) + Decimal(str(q.get('scrapped', 0) or 0)))

    # Lock statistics
    locked_stack_count = stacks.filter(is_locked=True).count()

    metrics: Dict[str, Any] = {
        'timestamp': now.isoformat(),
        'pending_adjustments': {
            'counts': padj_state_counts,
            'qty': padj_state_qty,
        },
        'stacks': {
            'total': stack_count,
            'locked': locked_stack_count,
            'remaining_total': float(remaining_agg),
            'received_total': float(received_agg),
        },
    }

    # Latest processor runs (global & stack) – lightweight extraction
    try:
        latest_global = (
            InventoryAdjustmentProcessorRun.objects
            .filter(run_type=InventoryAdjustmentProcessorRun.RUN_GLOBAL)
            .order_by('-id')
            .values('id', 'attempted', 'applied', 'skipped_locked', 'still_locked', 'insufficient', 'canceled', 'reserved_conflict_skipped', 'duration_s', 'dt_started', 'dt_finished', 'dry_run')
            .first()
        )
        latest_stack = (
            InventoryAdjustmentProcessorRun.objects
            .filter(run_type=InventoryAdjustmentProcessorRun.RUN_STACK)
            .order_by('-id')
            .values('id', 'stack_id', 'attempted', 'applied', 'insufficient', 'canceled', 'reserved_conflict_skipped', 'duration_s', 'dt_started', 'dt_finished', 'dry_run')
            .first()
        )
        # Cumulative aggregates (lightweight sums)
        agg_global = InventoryAdjustmentProcessorRun.objects.filter(run_type=InventoryAdjustmentProcessorRun.RUN_GLOBAL).aggregate(
            runs=Count('id'), attempted=Sum('attempted'), applied=Sum('applied')
        )
        agg_stack = InventoryAdjustmentProcessorRun.objects.filter(run_type=InventoryAdjustmentProcessorRun.RUN_STACK).aggregate(
            runs=Count('id'), attempted=Sum('attempted'), applied=Sum('applied')
        )
        def _duration_buckets(d):
            if not d or d.get('duration_s') is None:
                return None
            val = float(d['duration_s'])
            bounds = [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5]
            buckets = {str(b): 0 for b in bounds}
            buckets['+Inf'] = 0
            placed = False
            for b in bounds:
                if val <= b:
                    buckets[str(b)] += 1
                    placed = True
                    break
            if not placed:
                buckets['+Inf'] += 1
            return buckets
        metrics['processor_runs'] = {
            'latest_global': latest_global,
            'latest_stack': latest_stack,
            'latest_global_duration_buckets': _duration_buckets(latest_global),
            'latest_stack_duration_buckets': _duration_buckets(latest_stack),
            'cumulative': {
                'global_runs': agg_global.get('runs') or 0,
                'global_attempted': agg_global.get('attempted') or 0,
                'global_applied': agg_global.get('applied') or 0,
                'stack_runs': agg_stack.get('runs') or 0,
                'stack_attempted': agg_stack.get('attempted') or 0,
                'stack_applied': agg_stack.get('applied') or 0,
            }
        }
    except Exception:  # pragma: no cover
        metrics['processor_runs'] = {'latest_global': None, 'latest_stack': None}

    if include_samples:
        sample_padjs = list(
            padj_qs.filter(dt_processed=0)
            .order_by('-dt_created')[:sample_limit]
            .values('id', 'record_id', 'purpose', 'changes', 'dt_created')
        )
        metrics['samples'] = {
            'pending_adjustments': sample_padjs,
        }
    return metrics

__all__ = ['summarize_inventory_metrics']
def snapshot_inventory_metrics(include_samples: bool = False) -> InventoryMetricsSnapshot:
    metrics = summarize_inventory_metrics(include_samples=include_samples)
    def _convert(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        from datetime import datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_convert(v) for v in obj]
        return obj
    snap = InventoryMetricsSnapshot.objects.create(metrics=_convert(metrics))
    return snap

__all__.append('snapshot_inventory_metrics')
