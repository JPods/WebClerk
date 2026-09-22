"""Keep-in-touch metrics for a customer, computed from source records only (Bill, 2026-09-19).

"We should build out this object now. We can amend it and reduce it as needed.
Also, nice to add physical and web based visits."

Everything here is derived from invoices, quotes, orders, ledgers, touches and
user activity; nothing is typed. The result is stored in OrgBase.metrics and
shaped by common.schemas.org_aspects.OrgMetrics.

Bill's proximity hypothesis (WhatIf C-W38-16): over the years, customers of local
resellers will order more and more online and stop by to pick up. Each year's
``channel`` × ``fulfillment`` mix — especially ``online_pickup`` — is how it will show.

Periods are calendar, in UTC. A sale is dated by dt_approved, else dt_created.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps

SIZE_BAND_EDGES = (50, 250, 1000, 5000)          # company setting later; amend as needed
ONLINE_SOURCES = ('web', 'portal', 'online', 'storefront', 'webserving')
DAY_MS = 86_400_000


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _dt_ms(doc) -> int:
    return int(getattr(doc, 'dt_approved', 0) or 0) or int(getattr(doc, 'dt_created', 0) or 0)


def _band(amount: Decimal) -> str:
    lo = 0
    for edge in SIZE_BAND_EDGES:
        if amount < edge:
            return f"{lo}-{edge}"
        lo = edge
    return f"{lo}+"


def _channel(doc) -> str:
    src = (getattr(doc, 'source_name', '') or '').strip().lower()
    if not src:
        return 'unknown'
    return 'online' if any(w in src for w in ONLINE_SOURCES) else 'in_person'


def _fulfillment(doc) -> str:
    """pickup | delivered | shipped from the ship_via registry entry (wc:shipping_service);
    'unknown' when ship_via is empty or names no entry — never guessed."""
    from apps.transactions.services.fulfillment.fulfillment_freight import shipping_service_for
    svc = shipping_service_for(getattr(doc, 'ship_via', '') or '')
    return (svc or {}).get('fulfillment') or 'unknown'


def _empty_year() -> Dict[str, Any]:
    return {
        'count': 0, 'amount': Decimal('0'), 'margin': Decimal('0'),
        'returns_count': 0, 'returns_amount': Decimal('0'),
        'size_bands': defaultdict(lambda: {'count': 0, 'amount': Decimal('0')}),
        'channel': defaultdict(int), 'fulfillment': defaultdict(int), 'online_pickup': 0,
        'quotes': 0, 'quotes_converted': 0,
        'touches': defaultdict(int), 'visits_in': 0, 'visits_out': 0, 'web_days': 0,
    }


def compute_org_metrics(org, now: Optional[datetime] = None) -> Dict[str, Any]:
    """The customer's metrics object (OrgMetrics), from its source records."""
    from common.schemas.org_aspects import OrgMetrics
    now = now or datetime.now(timezone.utc)
    now_ms = _ms(now)
    year0 = _ms(datetime(now.year, 1, 1, tzinfo=timezone.utc))
    month0 = _ms(datetime(now.year, now.month, 1, tzinfo=timezone.utc))
    same_day_last_year = _ms(now.replace(year=now.year - 1)) if not (now.month == 2 and now.day == 29) \
        else _ms(now.replace(year=now.year - 1, day=28))
    last_year0 = _ms(datetime(now.year - 1, 1, 1, tzinfo=timezone.utc))
    d90 = now_ms - 90 * DAY_MS
    d180 = now_ms - 180 * DAY_MS

    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Quote = dj_apps.get_model('transactions', 'Quote')
    Order = dj_apps.get_model('transactions', 'Order')
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Touch = dj_apps.get_model('communications', 'Touch')

    years: Dict[int, Dict[str, Any]] = defaultdict(_empty_year)
    periods = {p: {'count': 0, 'amount': Decimal('0'), 'margin': Decimal('0')}
               for p in ('mtd', 'ytd', 'ytd_last_year', 'last_year', 'last_90', 'prior_90', 'lifetime')}
    sale_days: List[int] = []
    largest = (Decimal('0'), 0)

    for inv in Invoice.objects.filter(customer_id=org.pk).only(
            'totals', 'dt_approved', 'dt_created', 'source_name', 'ship_via'):
        t = inv.totals or {}
        amount = Decimal(str(t.get('amount') or 0))
        margin = Decimal(str(t.get('margin') or 0))
        dt = _dt_ms(inv)
        y = years[datetime.fromtimestamp(dt / 1000, timezone.utc).year] if dt else years[0]
        if amount < 0:                           # a credit memo: a return
            y['returns_count'] += 1
            y['returns_amount'] += -amount
            continue
        if amount == 0:
            continue
        y['count'] += 1
        y['amount'] += amount
        y['margin'] += margin
        band = y['size_bands'][_band(amount)]
        band['count'] += 1
        band['amount'] += amount
        ch, ff = _channel(inv), _fulfillment(inv)
        y['channel'][ch] += 1
        y['fulfillment'][ff] += 1
        if ch == 'online' and ff == 'pickup':
            y['online_pickup'] += 1
        sale_days.append(dt // DAY_MS)
        if amount > largest[0]:
            largest = (amount, dt)
        for name, ok in (('lifetime', True), ('ytd', dt >= year0), ('mtd', dt >= month0),
                         ('ytd_last_year', last_year0 <= dt < same_day_last_year),
                         ('last_year', last_year0 <= dt < year0),
                         ('last_90', dt >= d90), ('prior_90', d180 <= dt < d90)):
            if ok:
                periods[name]['count'] += 1
                periods[name]['amount'] += amount
                periods[name]['margin'] += margin

    # ── Rhythm: this customer's own cadence ──────────────────────────
    days = sorted(set(sale_days))
    gaps = [b - a for a, b in zip(days, days[1:])]
    usual = statistics.median(gaps) if gaps else None
    last_day = days[-1] if days else None
    since = (now_ms // DAY_MS - last_day) if last_day is not None else None
    rhythm = {
        'first_sale_dt': days[0] * DAY_MS if days else None,
        'last_sale_dt': last_day * DAY_MS if last_day is not None else None,
        'days_since_last': since,
        'usual_interval_days': usual,
        'expected_next_dt': (last_day + usual) * DAY_MS if (last_day is not None and usual) else None,
        # Quiet: longer than 1.5 × their own usual interval, once there is a habit to measure.
        'quiet': bool(usual and since is not None and len(days) >= 3 and since > 1.5 * usual),
    }

    # ── Quotes → orders ──────────────────────────────────────────────
    quote_rows = list(Quote.objects.filter(customer_id=org.pk).values_list('pk', 'dt_created'))
    converted = {}
    for parent_id, dt_created in Order.objects.filter(
            parent_model='quote', parent_id__in=[q for q, _ in quote_rows]).values_list('parent_id', 'dt_created'):
        converted.setdefault(parent_id, dt_created)
    to_order_days = []
    for qid, qdt in quote_rows:
        y = years[datetime.fromtimestamp((qdt or 0) / 1000, timezone.utc).year] if qdt else years[0]
        y['quotes'] += 1
        if qid in converted:
            y['quotes_converted'] += 1
            if qdt and converted[qid]:
                to_order_days.append((converted[qid] - qdt) / DAY_MS)

    # ── Payments ─────────────────────────────────────────────────────
    # Settled on time = settled on or before the last instalment's due date. The shared
    # helper reads the schedule from the ledger and the settlement from the document's
    # events; this used Ledger.dt_applied, which nothing ever set (fixed 2026-09-20).
    from apps.accounts.services.terms_ledger import settlement_days
    paid = settlement_days(org.pk, 'invoice')
    on_time = sum(1 for days_late in paid if days_late <= 0)

    # ── Touches and visits ───────────────────────────────────────────
    last_touch = None
    for channel, direction, dt in Touch.objects.filter(org_id=org.pk).values_list(
            'channel', 'direction', 'dt_created'):
        y = years[datetime.fromtimestamp((dt or 0) / 1000, timezone.utc).year] if dt else years[0]
        y['touches'][channel or 'other'] += 1
        if channel == 'visit':
            if direction == 'in':
                y['visits_in'] += 1          # they came to us
            else:
                y['visits_out'] += 1         # we went to them
        if dt and (last_touch is None or dt > last_touch):
            last_touch = dt

    # Web visits: days the customer's own contacts were active (UserDailyLog, filled nightly).
    try:
        UserDailyLog = dj_apps.get_model('core', 'UserDailyLog')
        for log_date in UserDailyLog.objects.filter(user__customer_id=org.pk).values_list('log_date', flat=True):
            years[log_date.year]['web_days'] += 1
    except Exception:                        # a missing link is reported by the empty count, not hidden
        pass

    def money(x):
        return float(Decimal(x).quantize(Decimal('0.01')))

    def pct(a, b):
        return float(((Decimal(a) - Decimal(b)) / Decimal(b) * 100).quantize(Decimal('0.1'))) if b else None

    out_periods = {}
    for name, p in periods.items():
        out_periods[name] = {'count': p['count'], 'amount': money(p['amount']), 'margin': money(p['margin']),
                             'average': money(p['amount'] / p['count']) if p['count'] else 0.0,
                             'margin_per_transaction': money(p['margin'] / p['count']) if p['count'] else 0.0}

    out_years = []
    for year in sorted(k for k in years if k):
        y = years[year]
        out_years.append({
            'year': year, 'count': y['count'], 'amount': money(y['amount']), 'margin': money(y['margin']),
            'returns_count': y['returns_count'], 'returns_amount': money(y['returns_amount']),
            'size_bands': {k: {'count': v['count'], 'amount': money(v['amount'])} for k, v in sorted(y['size_bands'].items())},
            'channel': dict(y['channel']), 'fulfillment': dict(y['fulfillment']),
            'online_pickup': y['online_pickup'],
            'online_pickup_share': round(y['online_pickup'] / y['count'] * 100, 1) if y['count'] else None,
            'quotes': y['quotes'], 'quotes_converted': y['quotes_converted'],
            'touches': dict(y['touches']), 'visits_in': y['visits_in'], 'visits_out': y['visits_out'],
            'web_days': y['web_days'],
        })

    momentum = pct(periods['last_90']['amount'], periods['prior_90']['amount'])
    metrics = {
        'dt_computed': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'periods': out_periods,
        'years': out_years,
        'largest': {'amount': money(largest[0]), 'dt': largest[1] or None},
        'rhythm': rhythm,
        'trend': {
            'ytd_vs_last_year_pct': pct(periods['ytd']['amount'], periods['ytd_last_year']['amount']),
            'momentum_90_pct': momentum,
            'direction': ('growing' if momentum is not None and momentum > 10 else
                          'falling' if momentum is not None and momentum < -10 else
                          'steady' if momentum is not None else None),
        },
        'quotes': {
            'count': len(quote_rows), 'converted': len(converted),
            'conversion_pct': round(len(converted) / len(quote_rows) * 100, 1) if quote_rows else None,
            'days_to_order_avg': round(sum(to_order_days) / len(to_order_days), 1) if to_order_days else None,
        },
        'payments': {
            'invoices_paid': len(paid),
            'on_time_pct': round(on_time / len(paid) * 100, 1) if paid else None,
        },
        'contact': {
            'days_since_last_touch': (now_ms - last_touch) // DAY_MS if last_touch else None,
        },
        'proximity': {'distance_km': None, 'note': 'needs geocoded customer and store addresses'},
        'size_band_edges': list(SIZE_BAND_EDGES),
    }
    return OrgMetrics.model_validate(metrics).model_dump()
