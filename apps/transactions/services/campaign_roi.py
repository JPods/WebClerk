"""
Campaign / Ad Source ROI Service — GAP-10

Tracks campaign costs against leads, proposals, orders generated.
Calculates cost per acquisition and ROI.

Campaign data lives in Setting records (purpose='campaign').
Transaction linkage via source JSON on transaction headers.

All functions single-purpose. Called from wcapi/manage.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from decimal import Decimal
from django.db.models import Sum, Count, Q
from apps.core.models.setting import Setting
from apps.transactions.models import Order, Invoice, Proposal
import time


def _now_ms():
    return int(time.time() * 1000)


def _dec(v) -> Decimal:
    if v is None:
        return Decimal('0')
    return Decimal(str(v))


def create_campaign(
    name: str,
    budget: Decimal = Decimal('0'),
    channel: str = '',
    start_date: int = None,
    end_date: int = None,
    description: str = '',
) -> Dict:
    """Create a campaign as a Setting record.

    Returns: {campaign_id, name}
    """
    now = _now_ms()

    setting = Setting.objects.create(
        name=f'campaign:{name}',
        purpose='campaign',
        parent_model='',
        data={
            'name': name,
            'budget': str(budget),
            'spent': '0',
            'channel': channel,
            'description': description,
            'dt_start': start_date or now,
            'dt_end': end_date,
            'metrics': {
                'leads': 0,
                'proposals': 0,
                'orders': 0,
                'invoices': 0,
                'revenue': '0',
                'cost_per_lead': '0',
                'cost_per_order': '0',
                'roi': '0',
            },
        },
    )

    return {'campaign_id': setting.pk, 'name': name}


def record_campaign_spend(campaign_id: int, amount: Decimal, description: str = '') -> Dict:
    """Record spending against a campaign.

    Returns: {campaign_id, total_spent}
    """
    setting = Setting.objects.get(pk=campaign_id, purpose='campaign')
    data = setting.data or {}
    spent = _dec(data.get('spent', 0)) + amount
    data['spent'] = str(spent)
    setting.data = data
    setting.save(update_fields=['data'])

    return {'campaign_id': campaign_id, 'total_spent': str(spent)}


def calculate_campaign_roi(campaign_id: int) -> Dict:
    """Calculate ROI metrics for a campaign.

    Scans transactions with source.campaign_id matching this campaign.
    Updates the campaign Setting with current metrics.

    Returns: {campaign_id, name, metrics}
    """
    setting = Setting.objects.get(pk=campaign_id, purpose='campaign')
    data = setting.data or {}
    campaign_name = data.get('name', '')

    # Count transactions linked to this campaign
    # Transactions store campaign_id in source JSON
    proposals = Proposal.objects.filter(
        source__campaign_id=campaign_id,
        is_deleted=False,
    )
    orders = Order.objects.filter(
        source__campaign_id=campaign_id,
        is_deleted=False,
    )
    invoices = Invoice.objects.filter(
        source__campaign_id=campaign_id,
        is_deleted=False,
    )

    proposal_count = proposals.count()
    order_count = orders.count()
    invoice_count = invoices.count()

    # Sum revenue from invoices
    total_revenue = Decimal('0')
    for inv in invoices:
        total_revenue += _dec(inv.total)

    spent = _dec(data.get('spent', 0))
    budget = _dec(data.get('budget', 0))

    # Calculate metrics
    cost_per_order = (spent / order_count) if order_count > 0 else Decimal('0')
    roi = ((total_revenue - spent) / spent * 100) if spent > 0 else Decimal('0')

    metrics = {
        'proposals': proposal_count,
        'orders': order_count,
        'invoices': invoice_count,
        'revenue': str(total_revenue),
        'spent': str(spent),
        'budget': str(budget),
        'cost_per_order': str(cost_per_order),
        'roi': str(roi),
    }

    data['metrics'] = metrics
    setting.data = data
    setting.save(update_fields=['data'])

    return {
        'campaign_id': campaign_id,
        'name': campaign_name,
        'metrics': metrics,
    }


def get_all_campaigns() -> List[Dict]:
    """Get all campaigns with their current metrics.

    Returns: [{campaign_id, name, channel, budget, spent, metrics}]
    """
    settings = Setting.objects.filter(purpose='campaign', is_active=True)

    return [{
        'campaign_id': s.pk,
        'name': (s.data or {}).get('name', ''),
        'channel': (s.data or {}).get('channel', ''),
        'budget': (s.data or {}).get('budget', '0'),
        'spent': (s.data or {}).get('spent', '0'),
        'metrics': (s.data or {}).get('metrics', {}),
    } for s in settings]


def link_transaction_to_campaign(model_name: str, record_id: int, campaign_id: int) -> Dict:
    """Link a transaction to a campaign by updating its source JSON.

    Returns: {model_name, record_id, campaign_id}
    """
    setting = Setting.objects.get(pk=campaign_id, purpose='campaign')
    campaign_name = (setting.data or {}).get('name', '')

    MODEL_MAP = {
        'order': Order,
        'invoice': Invoice,
        'proposal': Proposal,
    }

    ModelCls = MODEL_MAP.get(model_name)
    if not ModelCls:
        raise ValueError(f'Unsupported model: {model_name}')

    obj = ModelCls.objects.get(pk=record_id)
    source = obj.source or {}
    source['campaign_id'] = campaign_id
    source['campaign_name'] = campaign_name
    obj.source = source
    obj.dt_modified = _now_ms()
    obj.save(update_fields=['source', 'dt_modified'])

    return {'model_name': model_name, 'record_id': record_id, 'campaign_id': campaign_id}
