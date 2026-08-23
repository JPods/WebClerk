"""
Erosion Service
===============

Detects and records events where value is lost between transaction stages.

Auto-calculated categories:
  - margin:       Invoice margin < linked proposal/order margin
  - discount:     Discount applied at order or invoice stage
  - late_payment: Payment received past due date (carrying cost)

Manual/future categories:
  - fx_loss, return_credit, rework, shipping, bad_debt, price_override, other

Usage:
    from apps.accounts.services.erosion import detect_margin_erosion, detect_late_payment

    # Called after invoice save (inside on_invoice_save or Phase 5 of transaction_save)
    events = detect_margin_erosion(invoice)

    # Called after payment save
    events = detect_late_payment(payment)

    # Summaries
    summary = get_org_erosion_summary(org_id, days=90)
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Margin Erosion ──────────────────────────────────────────────────

def detect_margin_erosion(invoice) -> list:
    """
    Compare invoice margin against its ancestor proposal/order.

    Walks the parent chain: invoice → order → proposal.
    Creates an Erosion record for each stage where margin dropped.

    Returns list of created Erosion records.
    """
    from apps.accounts.models import Erosion
    from django.apps import apps

    results = []
    inv_totals = getattr(invoice, 'totals', {}) or {}
    inv_margin_pc = _safe_decimal(inv_totals.get('margin_pc'))
    inv_margin = _safe_decimal(inv_totals.get('margin'))
    inv_total = _safe_decimal(inv_totals.get('total'))

    if inv_total is None or inv_total <= 0:
        return results

    # Walk the parent chain
    ancestors = _get_ancestor_chain(invoice)

    for ancestor in ancestors:
        anc_totals = getattr(ancestor, 'totals', {}) or {}
        anc_margin_pc = _safe_decimal(anc_totals.get('margin_pc'))
        anc_margin = _safe_decimal(anc_totals.get('margin'))
        anc_total = _safe_decimal(anc_totals.get('total'))

        if anc_margin is None or inv_margin is None:
            continue
        if anc_total is None or anc_total <= 0:
            continue

        # Erosion = ancestor margin - invoice margin (positive means we lost value)
        margin_loss = anc_margin - inv_margin
        if margin_loss <= 0:
            continue  # No erosion or margin improved

        # Percentage points lost
        pct_loss = D('0')
        if anc_margin_pc is not None and inv_margin_pc is not None:
            pct_loss = anc_margin_pc - inv_margin_pc

        anc_model_name = ancestor._meta.model_name

        # Determine category
        category = 'margin'
        # Check if erosion is from discounting
        inv_discount = _safe_decimal(inv_totals.get('discount', 0))
        anc_discount = _safe_decimal(anc_totals.get('discount', 0))
        if inv_discount and anc_discount and inv_discount > anc_discount:
            category = 'discount'

        # Delete any existing auto erosion for this source+parent pair
        Erosion.objects.filter(
            source_model='invoice',
            source_id=invoice.id,
            parent_model=anc_model_name,
            parent_id=ancestor.id,
            is_auto=True,
        ).delete()

        erosion = Erosion.objects.create(
            category=category,
            amount=margin_loss,
            amount_pct=pct_loss / D('100') if pct_loss else None,
            org_id=getattr(invoice, 'customer_id', None),
            contact_id=getattr(invoice, 'contact_id', None),
            source_model='invoice',
            source_id=invoice.id,
            parent_model=anc_model_name,
            parent_id=ancestor.id,
            dt_event=datetime.now(timezone.utc),
            notes=f"Margin dropped ${margin_loss} ({pct_loss}pp) from {anc_model_name} #{ancestor.id}",
            is_auto=True,
        )
        results.append(erosion)
        logger.info(
            "Erosion detected: invoice %s vs %s %s — $%s margin loss",
            invoice.id, anc_model_name, ancestor.id, margin_loss,
        )

    return results


# ─── Late Payment Erosion ────────────────────────────────────────────

def detect_late_payment(payment, daily_rate: D = D('0.0005')) -> Optional['Erosion']:
    """
    If payment arrives after ledger due date, record carrying cost as erosion.

    daily_rate: daily cost of capital (default 0.05% = ~18% annual).
    Only fires if there's a ledger record with dt_due < payment date.

    Returns created Erosion record or None.
    """
    from apps.accounts.models import Erosion, Ledger

    invoice = getattr(payment, 'invoice', None)
    if invoice is None:
        return None

    payment_amount = _safe_decimal(getattr(payment, 'amount', 0))
    if not payment_amount or payment_amount <= 0:
        return None

    dt_paid = getattr(payment, 'dt_payment', None) or getattr(payment, 'dt_created', None)
    if dt_paid is None:
        return None
    if not dt_paid.tzinfo:
        dt_paid = dt_paid.replace(tzinfo=timezone.utc)

    # Find the earliest unpaid ledger due date for this invoice
    earliest_ledger = (
        Ledger.objects
        .filter(invoice_id=invoice.id, model_name='invoice', dt_applied__isnull=True)
        .order_by('dt_due')
        .first()
    )
    if earliest_ledger is None or earliest_ledger.dt_due is None:
        return None

    dt_due = earliest_ledger.dt_due
    if not dt_due.tzinfo:
        dt_due = dt_due.replace(tzinfo=timezone.utc)

    days_late = (dt_paid - dt_due).days
    if days_late <= 0:
        return None  # Paid on time or early

    carrying_cost = payment_amount * daily_rate * days_late

    # Replace existing auto late-payment erosion for this payment
    Erosion.objects.filter(
        source_model='payment',
        source_id=payment.id,
        category='late_payment',
        is_auto=True,
    ).delete()

    erosion = Erosion.objects.create(
        category='late_payment',
        amount=carrying_cost.quantize(D('0.01')),
        org_id=getattr(invoice, 'customer_id', None),
        contact_id=getattr(invoice, 'contact_id', None),
        source_model='payment',
        source_id=payment.id,
        parent_model='invoice',
        parent_id=invoice.id,
        dt_event=dt_paid,
        notes=f"Payment {days_late} days late on ${payment_amount}. "
              f"Carrying cost at {float(daily_rate * 100):.3f}%/day = ${carrying_cost:.2f}",
        is_auto=True,
    )

    logger.info(
        "Late payment erosion: payment %s — %d days late, $%s carrying cost",
        payment.id, days_late, carrying_cost,
    )
    return erosion


# ─── Discount Erosion (standalone) ───────────────────────────────────

def detect_discount_erosion(transaction) -> Optional['Erosion']:
    """
    Record erosion when a discount is applied at the transaction level.
    Separate from margin erosion — captures the raw discount amount.

    Only creates a record if totals.discount > 0.
    """
    from apps.accounts.models import Erosion

    totals = getattr(transaction, 'totals', {}) or {}
    discount = _safe_decimal(totals.get('discount', 0))
    if not discount or discount <= 0:
        return None

    total = _safe_decimal(totals.get('total', 0))
    model_name = transaction._meta.model_name

    # Replace existing auto discount erosion for this transaction
    Erosion.objects.filter(
        source_model=model_name,
        source_id=transaction.id,
        category='discount',
        is_auto=True,
    ).delete()

    pct = (discount / (total + discount)) if total and total > 0 else None

    erosion = Erosion.objects.create(
        category='discount',
        amount=discount,
        amount_pct=pct,
        org_id=getattr(transaction, 'customer_id', None),
        contact_id=getattr(transaction, 'contact_id', None),
        source_model=model_name,
        source_id=transaction.id,
        dt_event=datetime.now(timezone.utc),
        notes=f"Discount of ${discount} applied on {model_name} #{transaction.id}",
        is_auto=True,
    )
    return erosion


# ─── Summary / Reporting ─────────────────────────────────────────────

def get_org_erosion_summary(org_id: int, days: int = 90) -> dict:
    """
    Summarize erosion for an org over the last N days.

    Returns:
        {
            'total': Decimal,
            'by_category': {'margin': Decimal, 'late_payment': Decimal, ...},
            'count': int,
            'period_days': int,
        }
    """
    from apps.accounts.models import Erosion
    from django.db.models import Sum, Count

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    qs = Erosion.objects.filter(
        org_id=org_id,
        dt_event__gte=cutoff,
    )

    # Total
    agg = qs.aggregate(
        total=Sum('amount'),
        count=Count('id'),
    )

    # By category
    by_cat_qs = (
        qs.values('category')
        .annotate(cat_total=Sum('amount'))
        .order_by('-cat_total')
    )
    by_category = {row['category']: row['cat_total'] or D('0') for row in by_cat_qs}

    return {
        'total': agg['total'] or D('0'),
        'count': agg['count'] or 0,
        'by_category': by_category,
        'period_days': days,
    }


# ─── Helpers ─────────────────────────────────────────────────────────

def _safe_decimal(val) -> Optional[D]:
    """Convert value to Decimal, returning None on failure."""
    if val is None:
        return None
    try:
        return D(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _get_ancestor_chain(transaction) -> list:
    """
    Walk parent_id / parent_model chain upward to find ancestor transactions.
    Returns list of ancestor instances (order, proposal, etc.) from nearest to farthest.
    """
    from django.apps import apps

    ancestors = []
    current = transaction
    seen = set()  # (model_name, id) tuples for cycle protection

    for _ in range(5):  # Safety limit — chains shouldn't go deeper than 5
        parent_id = getattr(current, 'parent_id', None)
        parent_model = getattr(current, 'parent_model', None)

        if not parent_id or not parent_model:
            break
        key = (parent_model, parent_id)
        if key in seen:
            break  # Cycle protection
        seen.add(key)

        # Resolve parent model class
        try:
            # parent_model is like 'order', 'proposal' — need to map to app label
            model_cls = _resolve_transaction_model(parent_model)
            if model_cls is None:
                break
            parent_obj = model_cls.objects.filter(pk=parent_id).first()
            if parent_obj is None:
                break
            ancestors.append(parent_obj)
            current = parent_obj
        except Exception as e:
            logger.warning("Failed to resolve parent %s/%s: %s", parent_model, parent_id, e)
            break

    return ancestors


def sync_metadata_erosions(instance) -> int:
    """
    Persist pending erosion annotations from metadata into Erosion records.

    Scans ``metadata.small_stings[]`` and ``metadata.erosions[]`` for entries
    that have no ``erosion_id`` (or ``erosion_id`` is ``None``).  For each one,
    an Erosion row is created and the resulting ``id`` is written back into the
    metadata entry so subsequent saves skip it.

    Called automatically by the save-view post-save pipeline for every
    BaseModel descendant.

    Returns the number of Erosion records created.
    """
    from apps.accounts.models import Erosion

    metadata = getattr(instance, 'metadata', None)
    if not isinstance(metadata, dict):
        return 0

    model_name = instance._meta.model_name
    instance_id = instance.pk
    if not instance_id:
        return 0

    created_count = 0
    dirty = False

    for list_key in ('small_stings', 'erosions'):
        entries = metadata.get(list_key)
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # Skip entries already synced
            if entry.get('erosion_id'):
                continue

            category = entry.get('category', 'other')
            amount = _safe_decimal(entry.get('amount', 0))
            if amount is None or amount <= 0:
                continue

            note = entry.get('note', '')
            dt_ms = entry.get('dt')
            dt_event = None
            if dt_ms and isinstance(dt_ms, (int, float)):
                dt_event = datetime.fromtimestamp(dt_ms / 1000, tz=timezone.utc)

            try:
                erosion = Erosion.objects.create(
                    category=category,
                    amount=amount,
                    org_id=getattr(instance, 'customer_id', None) or getattr(instance, 'org_id', None),
                    contact_id=getattr(instance, 'contact_id', None),
                    source_model=model_name,
                    source_id=instance_id,
                    dt_event=dt_event or datetime.now(timezone.utc),
                    notes=note,
                    is_auto=False,
                )
                entry['erosion_id'] = erosion.id
                dirty = True
                created_count += 1
                logger.info(
                    "Metadata erosion synced: %s #%s → Erosion #%s (%s $%s)",
                    model_name, instance_id, erosion.id, category, amount,
                )
            except Exception as exc:
                logger.error(
                    "Failed to create Erosion from metadata entry on %s #%s: %s",
                    model_name, instance_id, exc,
                )

    # Persist the updated metadata with erosion_ids in a single update
    if dirty:
        try:
            type(instance).objects.filter(pk=instance_id).update(metadata=metadata)
            instance.refresh_from_db(fields=['metadata'])
        except Exception as exc:
            logger.error("Failed to write back erosion_ids to metadata: %s", exc)

    return created_count


def _resolve_transaction_model(model_name: str):
    """Map a model_name string to its Django model class."""
    from django.apps import apps

    # All transaction models live in apps.transactions
    MODEL_MAP = {
        'proposal': 'transactions.Proposal',
        'order': 'transactions.Order',
        'invoice': 'transactions.Invoice',
        'purchase': 'transactions.Purchase',
    }

    dotpath = MODEL_MAP.get(model_name)
    if dotpath:
        app_label, cls_name = dotpath.split('.')
        try:
            return apps.get_model(app_label, cls_name)
        except LookupError:
            return None

    # Fallback: try scanning all models
    for m in apps.get_models():
        if m._meta.model_name == model_name:
            return m
    return None
