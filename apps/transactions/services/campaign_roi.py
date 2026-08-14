"""
Campaign / Ad Source ROI Service — GAP-10

Tracks campaign costs against leads, proposals, orders generated.
Calculates cost per acquisition and ROI.

Campaign data lives in Setting records (purpose='user:campaign').
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
        purpose='user:campaign',
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
    setting = Setting.objects.get(pk=campaign_id, purpose='user:campaign')
    data = setting.config or {}
    spent = _dec(data.get('spent', 0)) + amount
    data['spent'] = str(spent)
    setting.config = data
    setting.save(update_fields=['config'])

    return {'campaign_id': campaign_id, 'total_spent': str(spent)}


def calculate_campaign_roi(campaign_id: int) -> Dict:
    """Calculate ROI metrics for a campaign.

    Scans transactions with source.campaign_id matching this campaign.
    Updates the campaign Setting with current metrics.

    Returns: {campaign_id, name, metrics}
    """
    setting = Setting.objects.get(pk=campaign_id, purpose='user:campaign')
    data = setting.config or {}
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
    setting.config = data
    setting.save(update_fields=['config'])

    return {
        'campaign_id': campaign_id,
        'name': campaign_name,
        'metrics': metrics,
    }


def get_all_campaigns() -> List[Dict]:
    """Get all campaigns with their current metrics.

    Returns: [{campaign_id, name, channel, budget, spent, metrics}]
    """
    settings = Setting.objects.filter(purpose='user:campaign', is_active=True)

    return [{
        'campaign_id': s.pk,
        'name': (s.config or {}).get('name', ''),
        'channel': (s.config or {}).get('channel', ''),
        'budget': (s.config or {}).get('budget', '0'),
        'spent': (s.config or {}).get('spent', '0'),
        'metrics': (s.config or {}).get('metrics', {}),
    } for s in settings]


def link_transaction_to_campaign(model_name: str, record_id: int, campaign_id: int) -> Dict:
    """Link a transaction to a campaign by updating its source JSON.

    Returns: {model_name, record_id, campaign_id}
    """
    setting = Setting.objects.get(pk=campaign_id, purpose='user:campaign')
    campaign_name = (setting.config or {}).get('name', '')

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


def attribute_customer_to_campaign(customer_id: int, campaign_id: int) -> Dict:
    """First-touch attribution: link a customer to a campaign.

    Sets customer.refs.links.campaigns = [{campaign_id, dt}].
    If campaigns list already exists and this campaign is already there, no-op.

    Args:
        customer_id: OrgBase PK (org_type='customer')
        campaign_id: Setting PK (purpose='user:campaign')

    Returns: {customer_id, campaign_id, attributed}
    """
    from apps.orgs.models import OrgBase

    # Verify campaign exists
    Setting.objects.get(pk=campaign_id, purpose='user:campaign')

    customer = OrgBase.objects.get(pk=customer_id)
    refs = customer.refs if isinstance(customer.refs, dict) else {}
    links = refs.get('links', {})
    if not isinstance(links, dict):
        links = {}
    campaigns = links.get('campaigns', [])
    if not isinstance(campaigns, list):
        campaigns = []

    # First-touch: only add if not already attributed to this campaign
    existing_ids = {c.get('campaign_id') for c in campaigns if isinstance(c, dict)}
    if campaign_id in existing_ids:
        return {'customer_id': customer_id, 'campaign_id': campaign_id, 'attributed': False}

    campaigns.append({'campaign_id': campaign_id, 'dt': _now_ms()})
    links['campaigns'] = campaigns
    refs['links'] = links
    customer.refs = refs
    customer.save(update_fields=['refs'])

    return {'customer_id': customer_id, 'campaign_id': campaign_id, 'attributed': True}


def get_campaign_cac(campaign_id: int) -> Dict:
    """Customer Acquisition Cost for a campaign.

    CAC = campaign spend / count of customers attributed to this campaign.
    Queries customers whose refs.links.campaigns contains this campaign_id.

    Returns: {campaign_id, spend, customer_count, cac}
    """
    from apps.orgs.models import OrgBase

    setting = Setting.objects.get(pk=campaign_id, purpose='user:campaign')
    data = setting.config or {}
    spent = _dec(data.get('spent', 0))

    # Query customers with this campaign_id in refs.links.campaigns
    # PostgreSQL jsonb containment: refs -> links -> campaigns @> [{"campaign_id": N}]
    customers = OrgBase.objects.filter(
        org_type='customer',
        is_deleted=False,
        refs__links__campaigns__contains=[{'campaign_id': campaign_id}],
    )
    customer_count = customers.count()

    cac = (spent / customer_count) if customer_count > 0 else Decimal('0')

    return {
        'campaign_id': campaign_id,
        'name': data.get('name', ''),
        'spend': str(spent),
        'customer_count': customer_count,
        'cac': str(cac),
    }


def get_campaign_margin_velocity(campaign_id: int) -> Dict:
    """Margin velocity for a campaign: margin * inventory turns.

    For all orders linked to this campaign (via source.campaign_id),
    calculate total margin and inventory turns from related invoices.
    Margin velocity = margin * turns (not just revenue).

    Returns: {campaign_id, name, order_count, revenue, cost, margin,
              turns, margin_velocity}
    """
    setting = Setting.objects.get(pk=campaign_id, purpose='user:campaign')
    data = setting.config or {}

    # Get orders linked to campaign
    orders = Order.objects.filter(
        source__campaign_id=campaign_id,
        is_deleted=False,
    )
    order_count = orders.count()

    # Get invoices linked to campaign for realized revenue/cost
    invoices = Invoice.objects.filter(
        source__campaign_id=campaign_id,
        is_deleted=False,
    )

    total_revenue = Decimal('0')
    total_cost = Decimal('0')

    for inv in invoices:
        totals = inv.totals if isinstance(inv.totals, dict) else {}
        total_revenue += _dec(totals.get('total', 0))
        total_cost += _dec(totals.get('cost', 0))

    margin = total_revenue - total_cost

    # Inventory turns: revenue / average inventory cost
    # Simplified: if cost > 0, turns = revenue / cost
    turns = (total_revenue / total_cost) if total_cost > 0 else Decimal('0')

    margin_velocity = margin * turns

    return {
        'campaign_id': campaign_id,
        'name': data.get('name', ''),
        'order_count': order_count,
        'revenue': str(total_revenue),
        'cost': str(total_cost),
        'margin': str(margin),
        'turns': str(turns.quantize(Decimal('0.01'))),
        'margin_velocity': str(margin_velocity.quantize(Decimal('0.01'))),
    }
