"""
Manufacturer Rebate Accrual Service — ORG-07

Calculates rebate earned from manufacturer purchases, updates financial records,
and creates GL journal entries for rebate accrual.

Rebate rate: manufacturer.prefs.rebate_rate_pct
Rebate tracking: manufacturer.financial.manufacturer.rebates
  {earned_ytd, received_ytd, pending}

All functions single-purpose. Called from wcapi/manage.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from decimal import Decimal
from django.apps import apps as dj_apps
from django.db import transaction
import time


def _now_ms():
    return int(time.time() * 1000)


def _dec(v) -> Decimal:
    if v is None:
        return Decimal('0')
    return Decimal(str(v))


def accrue_manufacturer_rebate(
    manufacturer_id: int,
    period_start_ms: Optional[int] = None,
    period_end_ms: Optional[int] = None,
) -> Dict:
    """Calculate rebate earned from purchases in a period.

    Rebate earned = total purchases in period * rebate_rate_pct / 100.
    Updates manufacturer.financial.manufacturer.rebates (earned_ytd, pending).
    Creates GL entries if rebate amount > 0:
      - Debit: ASSET-AR-000 (Rebate Receivable)
      - Credit: REV-MISC-000 (Rebate Income)

    Args:
        manufacturer_id: OrgBase PK where org_type='manufacturer'
        period_start_ms: epoch ms start of period (default: start of current year)
        period_end_ms: epoch ms end of period (default: now)

    Returns: {manufacturer_id, rebate_rate_pct, purchases_total, rebate_earned,
              earned_ytd, pending, gl_entries_created}
    """
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    Purchase = dj_apps.get_model('transactions', 'Purchase')
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    try:
        manufacturer = OrgBase.objects.get(pk=manufacturer_id)
    except OrgBase.DoesNotExist:
        return {'error': f'Manufacturer {manufacturer_id} not found'}

    # Determine rebate rate from prefs
    prefs = manufacturer.prefs if isinstance(manufacturer.prefs, dict) else {}
    rebate_rate_pct = _dec(prefs.get('rebate_rate_pct', 0))

    if rebate_rate_pct <= 0:
        return {
            'manufacturer_id': manufacturer_id,
            'rebate_rate_pct': '0',
            'error': 'No rebate_rate_pct in manufacturer.prefs',
        }

    # Default period: current calendar year
    now = _now_ms()
    if period_start_ms is None:
        import datetime
        jan1 = datetime.datetime(datetime.datetime.utcnow().year, 1, 1)
        period_start_ms = int(jan1.timestamp() * 1000)
    if period_end_ms is None:
        period_end_ms = now

    # Sum purchases for this manufacturer in period
    purchases = Purchase.objects.filter(
        manufacturer_id=manufacturer_id,
        is_deleted=False,
        dt_created__gte=period_start_ms,
        dt_created__lte=period_end_ms,
    )

    # json.path.value — read from totals envelope, never scalar
    purchases_total = Decimal('0')
    for p in purchases:
        totals = p.totals if isinstance(p.totals, dict) else {}
        purchases_total += _dec(totals.get('total', 0))

    rebate_earned = (purchases_total * rebate_rate_pct) / Decimal('100')

    if rebate_earned <= 0:
        return {
            'manufacturer_id': manufacturer_id,
            'rebate_rate_pct': str(rebate_rate_pct),
            'purchases_total': str(purchases_total),
            'rebate_earned': '0',
            'note': 'No purchases in period',
        }

    # Update financial.manufacturer.rebates
    financial = manufacturer.financial if isinstance(manufacturer.financial, dict) else {}
    mfr_block = financial.get('manufacturer', {})
    if not isinstance(mfr_block, dict):
        mfr_block = {}
    rebates = mfr_block.get('rebates', {})
    if not isinstance(rebates, dict):
        rebates = {}

    old_earned_ytd = _dec(rebates.get('earned_ytd', 0))
    old_pending = _dec(rebates.get('pending', 0))

    new_earned_ytd = old_earned_ytd + rebate_earned
    new_pending = old_pending + rebate_earned

    rebates['earned_ytd'] = str(new_earned_ytd)
    rebates['pending'] = str(new_pending)
    mfr_block['rebates'] = rebates
    financial['manufacturer'] = mfr_block
    manufacturer.financial = financial
    manufacturer.save(update_fields=['financial'])

    # Create GL entries
    gl_entries_created = 0
    with transaction.atomic():
        # Debit: Rebate Receivable (asset)
        GlJournal.objects.create(
            account='ASSET-AR-000',
            debit=float(rebate_earned),
            credit=None,
            source='rebate',
            type='accrual',
            source_id=manufacturer_id,
            source_model='orgbase',
        )
        # Credit: Rebate Income (revenue)
        GlJournal.objects.create(
            account='REV-MISC-000',
            debit=None,
            credit=float(rebate_earned),
            source='rebate',
            type='accrual',
            source_id=manufacturer_id,
            source_model='orgbase',
        )
        gl_entries_created = 2

    return {
        'manufacturer_id': manufacturer_id,
        'rebate_rate_pct': str(rebate_rate_pct),
        'purchases_total': str(purchases_total),
        'rebate_earned': str(rebate_earned),
        'earned_ytd': str(new_earned_ytd),
        'pending': str(new_pending),
        'gl_entries_created': gl_entries_created,
    }


def get_rebate_summary() -> List[Dict]:
    """All manufacturers with rebate activity.

    Returns: [{manufacturer_id, name, ida, rebate_rate_pct, earned_ytd,
               received_ytd, pending}]
    """
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')

    manufacturers = OrgBase.objects.filter(
        org_type='manufacturer',
        is_deleted=False,
    )

    results = []
    for mfr in manufacturers:
        financial = mfr.financial if isinstance(mfr.financial, dict) else {}
        mfr_block = financial.get('manufacturer', {})
        if not isinstance(mfr_block, dict):
            mfr_block = {}
        rebates = mfr_block.get('rebates', {})
        if not isinstance(rebates, dict):
            rebates = {}

        prefs = mfr.prefs if isinstance(mfr.prefs, dict) else {}
        rate = prefs.get('rebate_rate_pct', 0)

        earned_ytd = rebates.get('earned_ytd', '0')
        received_ytd = rebates.get('received_ytd', '0')
        pending = rebates.get('pending', '0')

        # Only include manufacturers with rate or activity
        if _dec(rate) > 0 or _dec(earned_ytd) > 0 or _dec(pending) > 0:
            results.append({
                'manufacturer_id': mfr.pk,
                'name': getattr(mfr, 'name', ''),
                'ida': getattr(mfr, 'ida', ''),
                'rebate_rate_pct': str(rate),
                'earned_ytd': str(earned_ytd),
                'received_ytd': str(received_ytd),
                'pending': str(pending),
            })

    return results
