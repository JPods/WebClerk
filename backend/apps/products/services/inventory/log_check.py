"""
Inventory log ↔ Pending — the two records of a line's stock change, checked against each other.

Bill, 2026-10-28: "We can save the inventory logs, but … review this at some point to see if it
is redundant of pending or an asset when conducting an audit. Keeping both, there should be a
reasonably easy access service to check the logs against pending."

Two independent records of the same event:
- the Log (purpose inventory): every save of a document line, written by the line signal;
- the Pending (inventory_line_add): the stock movement, written by the line door only when a
  quantity bucket moves; its name is "<line model> <line id>: <reason>".

They are paired by line (document model + "line", line id) and time. What each side holds that
the other does not is the finding: a Log that changed a quantity with no Pending is a change that
never reached the books; a line Pending with no Log is a gap in the log. Saves that moved
nothing have a Log and, rightly, no Pending — counted apart. Pendings do not keep history (the
stock rebuild of 2026-09-22 replaced them; the Log goes back to 2026-05-20), so only a window
both cover is a fair check. If months of checks show nothing but matches, the inventory log is
redundant and can go.

Run: manage.py check_inventory_log [--days N]; or POST /wcapi/_manage/ get_inventory_log_check.
"""
from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from typing import Any

#: A Pending and its Log are written in the same save; their times differ by milliseconds.
PAIR_WINDOW_MS = 10_000
_PENDING_NAME = re.compile(r'^(?P<model>[a-z_]+) (?P<id>\d+): (?P<reason>.*)$')


def _moved(action: str, details: dict) -> bool:
    """Whether the logged save changed a quantity: an add or delete of a non-zero quantity, an
    update with a non-zero delta. An update logged without a delta is counted as a change."""
    if action.endswith('_update'):
        delta = details.get('quantity_delta')
        return delta is None or delta != 0
    qty = details.get('quantity_before') if action.endswith('_delete') else details.get('quantity_after')
    return qty is None or qty != 0


def reconcile_inventory_log(days: int = 30, samples: int = 5) -> dict[str, Any]:
    from apps.core.models import Log, Pending

    since = int(time.time() * 1000) - days * 86_400_000
    pendings: dict[tuple, list] = defaultdict(list)
    for p in Pending.objects.filter(model_name='item', purpose='inventory_line_add',
                                    dt_created__gte=since).values('id', 'name', 'dt_created', 'record_id'):
        m = _PENDING_NAME.match(p['name'] or '')
        if m:
            pendings[(m['model'], int(m['id']))].append({**p, 'reason': m['reason']})

    matched, no_change, log_only = 0, Counter(), defaultdict(list)
    used: set[int] = set()
    for log in Log.objects.filter(purpose='inventory', dt_created__gte=since).order_by(
            'dt_created').values('id', 'action', 'record_id', 'dt_created', 'config'):
        details = (log['config'] or {}).get('details') or {}
        doc = (details.get('document') or {}).get('model', '')
        if not _moved(log['action'], details):
            # Nothing moved, so rightly no Pending — and it must not take one a change made.
            no_change[log['action']] += 1
            continue
        key = (f'{doc}line', details.get('line_id'))
        pair = next((p for p in pendings.get(key, [])
                     if p['id'] not in used and abs(p['dt_created'] - log['dt_created']) <= PAIR_WINDOW_MS), None)
        if pair:
            used.add(pair['id'])
            matched += 1
        else:
            log_only[log['action']].append({'log_id': log['id'], 'item_id': log['record_id'],
                                            'line': key, 'name': (log['config'] or {}).get('name', '')})

    pending_only = defaultdict(list)
    for key, rows in pendings.items():
        for p in rows:
            if p['id'] not in used:
                pending_only[p['reason']].append({'pending_id': p['id'], 'item_id': p['record_id'],
                                                  'line': key})

    n_log_only = sum(len(v) for v in log_only.values())
    n_pending_only = sum(len(v) for v in pending_only.values())
    return {
        'days': days,
        'matched': matched,
        'no_stock_change': dict(no_change),
        'log_only': {k: {'count': len(v), 'samples': v[:samples]} for k, v in sorted(log_only.items())},
        'pending_only': {k: {'count': len(v), 'samples': v[:samples]} for k, v in sorted(pending_only.items())},
        'verdict': ('agree' if not n_log_only and not n_pending_only else
                    f'{n_log_only} logged changes with no Pending, {n_pending_only} Pendings with no log'),
    }
