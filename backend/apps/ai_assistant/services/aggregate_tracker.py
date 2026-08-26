"""Alice aggregate tracker — maintains dashboard Sum() values via delta updates.

Replaces scalar shadow field aggregates (Sum('total'), Sum('balance')) with
Alice-managed collections stored in Setting records. Non-critical drift is
acceptable; periodic refresh corrects any accumulation error.

Usage:
    from apps.ai_assistant.services.aggregate_tracker import (
        get_aggregates, refresh_aggregates, apply_delta,
    )

    # Dashboard reads:
    aggs = get_aggregates('invoice')
    total_sum = aggs['total_sum']

    # Signal-driven delta (called from post_save):
    apply_delta('invoice', old_totals, new_totals, status, old_status)

    # Nightly refresh:
    refresh_aggregates('invoice')   # or refresh_all()
"""
import logging
import time

from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Sum, DecimalField, Q
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

logger = logging.getLogger('alice.aggregates')

TRANSACTION_MODELS = ['invoice', 'order', 'proposal', 'purchase', 'workorder']

SETTING_PURPOSE = 'alice:aggregates'


def _get_model(model_name):
    from django.apps import apps
    return apps.get_model('transactions', model_name)


def _now_ms():
    return int(time.time() * 1000)


from common.decimals import safe_decimal as _d  # noqa: E302


def _totals_expr(field):
    """Cast expression for totals->>field as Decimal."""
    return Cast(
        KeyTextTransform(field, 'totals'),
        output_field=DecimalField(max_digits=18, decimal_places=6),
    )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_aggregates(model_name: str) -> dict:
    """Read Alice's cached aggregates for a transaction model.

    Returns the config dict from the Setting, or empty dict if not yet computed.
    """
    from apps.core.models import Setting
    try:
        setting = Setting.objects.get(
            purpose=SETTING_PURPOSE,
            parent_model=model_name,
        )
        return setting.config or {}
    except Setting.DoesNotExist:
        return {}


# ---------------------------------------------------------------------------
# Delta update (called from post_save signal)
# ---------------------------------------------------------------------------

def apply_delta(model_name: str, old_totals: dict, new_totals: dict,
                status: str = '', old_status: str = ''):
    """Apply a delta to Alice's aggregate Setting after a record save.

    Computes the difference between old and new totals and adjusts
    the cached aggregates atomically.
    """
    from apps.core.models import Setting

    old_total = _d(old_totals.get('total'))
    new_total = _d(new_totals.get('total'))
    old_balance = _d(old_totals.get('balance'))
    new_balance = _d(new_totals.get('balance'))

    delta_total = new_total - old_total
    delta_balance = new_balance - old_balance

    if delta_total == 0 and delta_balance == 0 and status == old_status:
        return  # no change

    with transaction.atomic():
        setting, created = Setting.objects.select_for_update().get_or_create(
            purpose=SETTING_PURPOSE,
            parent_model=model_name,
            defaults={
                'name': f'alice:aggregates:{model_name}',
                'scope': 'system',
                'config': {},
            },
        )

        config = setting.config or {}

        # Global totals
        config['total_sum'] = float(_d(config.get('total_sum')) + delta_total)
        config['balance_sum'] = float(_d(config.get('balance_sum')) + delta_balance)

        # Open balance tracking
        was_open = old_balance > 0
        is_open = new_balance > 0
        open_count = int(config.get('open_count', 0))
        open_balance_sum = _d(config.get('open_balance_sum', 0))

        if not was_open and is_open:
            open_count += 1
            open_balance_sum += new_balance
        elif was_open and not is_open:
            open_count = max(0, open_count - 1)
            open_balance_sum -= old_balance
        elif was_open and is_open:
            open_balance_sum += delta_balance

        config['open_count'] = open_count
        config['open_balance_sum'] = float(open_balance_sum)

        # Per-status tracking
        by_status = config.get('by_status', {})
        if old_status and old_status in by_status:
            s = by_status[old_status]
            s['total_sum'] = float(_d(s.get('total_sum')) - old_total)
            s['balance_sum'] = float(_d(s.get('balance_sum')) - old_balance)
            s['count'] = max(0, int(s.get('count', 0)) - 1)
        if status:
            s = by_status.setdefault(status, {'total_sum': 0, 'balance_sum': 0, 'count': 0})
            s['total_sum'] = float(_d(s.get('total_sum')) + new_total)
            s['balance_sum'] = float(_d(s.get('balance_sum')) + new_balance)
            s['count'] = int(s.get('count', 0)) + 1
        config['by_status'] = by_status

        config['dt_last_delta'] = _now_ms()
        setting.config = config
        setting.save(update_fields=['config'])

    logger.debug(
        "Delta applied to %s aggregates: total=%+.2f balance=%+.2f",
        model_name, float(delta_total), float(delta_balance),
    )


# ---------------------------------------------------------------------------
# Full refresh (management command / nightly)
# ---------------------------------------------------------------------------

def refresh_aggregates(model_name: str) -> dict:
    """Full recompute of aggregates from the database. Corrects any drift."""
    from apps.core.models import Setting

    Model = _get_model(model_name)
    qs = Model.objects.filter(is_active=True, is_deleted=False)

    # Global aggregates from JSON paths
    global_aggs = qs.annotate(
        _total=_totals_expr('total'),
        _balance=_totals_expr('balance'),
    ).aggregate(
        total_sum=Sum('_total'),
        balance_sum=Sum('_balance'),
        count=Count('id'),
    )

    # Open balance
    open_aggs = qs.annotate(
        _balance=_totals_expr('balance'),
    ).filter(_balance__gt=0).aggregate(
        open_count=Count('id'),
        open_balance_sum=Sum('_balance'),
    )

    # Per-status breakdown
    from django.db.models import CharField
    status_qs = qs.values('status').annotate(
        total_sum=Sum(Cast(KeyTextTransform('total', 'totals'), output_field=DecimalField(max_digits=18, decimal_places=6))),
        balance_sum=Sum(Cast(KeyTextTransform('balance', 'totals'), output_field=DecimalField(max_digits=18, decimal_places=6))),
        count=Count('id'),
    )
    by_status = {}
    for row in status_qs:
        by_status[row['status']] = {
            'total_sum': float(row['total_sum'] or 0),
            'balance_sum': float(row['balance_sum'] or 0),
            'count': row['count'],
        }

    config = {
        'total_sum': float(global_aggs['total_sum'] or 0),
        'balance_sum': float(global_aggs['balance_sum'] or 0),
        'count': global_aggs['count'],
        'open_count': open_aggs['open_count'] or 0,
        'open_balance_sum': float(open_aggs['open_balance_sum'] or 0),
        'by_status': by_status,
        'dt_computed': _now_ms(),
        'dt_last_delta': _now_ms(),
    }

    with transaction.atomic():
        setting, created = Setting.objects.get_or_create(
            purpose=SETTING_PURPOSE,
            parent_model=model_name,
            defaults={
                'name': f'alice:aggregates:{model_name}',
                'scope': 'system',
            },
        )
        setting.config = config
        setting.save(update_fields=['config'])

    logger.info(
        "Refreshed %s aggregates: total_sum=%.2f balance_sum=%.2f count=%d",
        model_name, config['total_sum'], config['balance_sum'], config['count'],
    )
    return config


def refresh_all() -> dict:
    """Refresh aggregates for all transaction models."""
    results = {}
    for model_name in TRANSACTION_MODELS:
        results[model_name] = refresh_aggregates(model_name)
    return results
