"""The browser computes a document's totals while it is edited; the server checks them at save.

Bill, 2026-11-08 (readme 107): "have the front end manage calculations until transactions are
saved … The front end and backend calculations must match." The one engine is compute_totals;
the browser carries a mirror of it (frontend totalsCompute.ts), held to it by the fixture
tests/test_totals_fixture.py writes. Two things live here:

``calc_context(obj)`` — what compute_totals reads from outside the document, served on the GET
beside the record so the browser's mirror has the same inputs: the company's tax policy, the
shipping services (for a ship-via priced as a percent of goods) and whether the customer is
exempt. Served, never stored.

``check_preview(ctx)`` — the save payload may carry ``_totals_preview``, the figures the browser
showed. After the save has recomputed, any difference from the stored totals is logged and said
back in the save's messages. The saved figures stand; nothing is refused (guide, not barriers).
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from common.decimals import safe_decimal as _d

logger = logging.getLogger(__name__)

#: Every document that carries totals. A requisition has lines but no totals; cash has neither.
TOTALS_MODELS = ('quote', 'order', 'invoice', 'purchase', 'workorder', 'receipt')

#: What the browser reports back from its preview, and what is compared.
PREVIEW_KEYS = ('amount', 'tax', 'shipping', 'other', 'total')

_SERVICE_KEYS = ('name', 'carrier_code', 'account', 'aliases', 'rate_method', 'rate_percent')


def calc_context(obj) -> Dict[str, Any]:
    from apps.core.models import Setting
    from apps.transactions.services.pricing.totals_compute import _customer_is_exempt, _tax_policy
    setting = Setting.objects.filter(purpose='wc:shipping_service', is_active=True).only('config').first()
    services = ((setting.config or {}).get('service') or []) if setting else []
    return {
        'tax_policy': _tax_policy(),
        'shipping_services': [{k: svc.get(k) for k in _SERVICE_KEYS if svc.get(k) is not None}
                              for svc in services if isinstance(svc, dict)],
        'customer_exempt': _customer_is_exempt(getattr(obj, 'customer_id', None)),
    }


def check_preview(ctx) -> None:
    preview = ctx.data.get('_totals_preview')
    if not isinstance(preview, dict):
        return
    # The totals as the database holds them now: the recompute ran before the after hooks
    # (save.py: _post_persist, then refresh_from_db), and a reprice in this same hook saves
    # lines through their own instances, so the row is read, not the object in hand.
    stored = (type(ctx.obj).objects.filter(pk=ctx.obj.pk).values_list('totals', flat=True).first()
              or getattr(ctx.obj, 'totals', None) or {})
    diffs = [(k, _d(preview[k]), _d(stored.get(k, 0)))
             for k in PREVIEW_KEYS if k in preview and _d(preview[k]) != _d(stored.get(k, 0))]
    if not diffs:
        return
    logger.warning('browser totals differed from the saved %s %s: %s', ctx.model_key, ctx.obj.pk,
                   '; '.join(f'{k} browser {b} saved {s}' for k, b, s in diffs))
    k, b, s = next(((k, b, s) for k, b, s in diffs if k == 'total'), diffs[0])
    ctx.messages.append(
        f"The {k} shown while editing was {b}; the save computed {s}. The saved figures stand.")
