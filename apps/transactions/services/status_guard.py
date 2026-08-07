"""
Status Guard — Transition Validation for Transactions
=====================================================

Single source of truth for:
1. Which status transitions are allowed per transaction type
2. Pre-conditions that must be met before a transition
3. Journalized record protection — no modifications after GL posting

Over-the-counter invoices are a first-class path. Invoice can exist
standalone with no parent order. Guard rails enforce data integrity,
not business process assumptions.

Decision: 2026-08-06. Review due: 2026-11-06.
"""
from __future__ import annotations

from typing import Optional

from django.apps import apps as dj_apps

from apps.transactions.services.validation import ValidationResult


# ─────────────────────────────────────────────────────────────────────────────
# Allowed transitions per transaction type
# ─────────────────────────────────────────────────────────────────────────────

# Terminal statuses — no transitions out
TERMINAL = {'complete', 'canceled', 'paid', 'voided'}

TRANSITIONS = {
    'proposal': {
        'planned':     ['released', 'canceled'],
        'released':    ['sent', 'in_progress', 'hold', 'canceled'],
        'sent':        ['accepted', 'rejected', 'hold', 'canceled'],
        'accepted':    ['converted', 'hold', 'canceled'],
        'rejected':    [],
        'converted':   [],
        'in_progress': ['complete', 'hold', 'canceled'],
        'hold':        ['released', 'sent', 'in_progress', 'canceled'],
        'complete':    [],
        'canceled':    [],
    },
    'order': {
        'planned':     ['released', 'canceled'],
        'released':    ['in_progress', 'hold', 'canceled'],
        'in_progress': ['complete', 'hold', 'canceled'],
        'hold':        ['released', 'in_progress', 'canceled'],
        'complete':    [],
        'canceled':    [],
    },
    'invoice': {
        'planned':     ['released', 'canceled'],
        'released':    ['in_progress', 'hold', 'canceled'],
        'in_progress': ['complete', 'hold', 'canceled'],
        'hold':        ['released', 'in_progress', 'canceled'],
        'complete':    [],
        'canceled':    [],
    },
    'purchase': {
        'planned':     ['released', 'canceled'],
        'released':    ['in_progress', 'hold', 'canceled'],
        'in_progress': ['complete', 'hold', 'canceled'],
        'hold':        ['released', 'in_progress', 'canceled'],
        'complete':    [],
        'canceled':    [],
    },
    'work_order': {
        'planned':     ['released', 'canceled'],
        'released':    ['in_progress', 'hold', 'canceled'],
        'in_progress': ['complete', 'hold', 'canceled'],
        'hold':        ['released', 'in_progress', 'canceled'],
        'complete':    [],
        'canceled':    [],
    },
    'requisition': {
        'planned':     ['released', 'canceled'],
        'released':    ['in_progress', 'hold', 'canceled'],
        'in_progress': ['complete', 'hold', 'canceled'],
        'hold':        ['released', 'in_progress', 'canceled'],
        'complete':    [],
        'canceled':    [],
    },
    'payment': {
        'planned':     ['released', 'canceled'],
        'released':    ['complete', 'canceled'],
        'complete':    [],
        'canceled':    [],
        'voided':      [],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Journalized record protection
# ─────────────────────────────────────────────────────────────────────────────

# Models where journalization locks the record from modification
JOURNALIZABLE_MODELS = {
    'invoice', 'payment', 'purchase',
    'invoice_line', 'purchase_line', 'receipt_line',
}


def is_journalized(instance) -> bool:
    """Check if a record has been journalized (GL posted).

    Journalized records are identified by:
    - metadata.gl_accounts.posted == True (set by journalize.py)
    - is_locked == True (set at the same time)

    For line models, check the parent header.
    """
    # Direct check on the instance
    meta = getattr(instance, 'metadata', None) or {}
    gl = meta.get('gl_accounts', {})
    if gl.get('posted'):
        return True

    # For line models, check the parent
    model_name = instance.__class__.__name__.lower()
    parent_field = None
    if model_name == 'invoiceline':
        parent_field = 'invoice'
    elif model_name == 'purchaseline':
        parent_field = 'purchase'
    elif model_name == 'receiptline':
        parent_field = 'receipt'

    if parent_field:
        parent = getattr(instance, parent_field, None)
        if parent:
            parent_meta = getattr(parent, 'metadata', None) or {}
            parent_gl = parent_meta.get('gl_accounts', {})
            if parent_gl.get('posted'):
                return True

    # Commission check — if this record's commission has been accrued
    commission = getattr(instance, 'commission', None) or {}
    if commission.get('accrued'):
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Pre-condition checks
# ─────────────────────────────────────────────────────────────────────────────

def _get_line_count(instance, model_type: str) -> int:
    """Count lines for a transaction header."""
    line_model_map = {
        'proposal': ('transactions', 'ProposalLine', 'proposal_id'),
        'order': ('transactions', 'OrderLine', 'order_id'),
        'invoice': ('transactions', 'InvoiceLine', 'invoice_id'),
        'purchase': ('transactions', 'PurchaseLine', 'purchase_id'),
        'work_order': ('transactions', 'WorkOrderLine', 'work_order_id'),
        'requisition': ('transactions', 'RequisitionLine', 'requisition_id'),
    }
    entry = line_model_map.get(model_type)
    if not entry:
        return 0
    app, model_name, fk_field = entry
    try:
        LineModel = dj_apps.get_model(app, model_name)
        return LineModel.objects.filter(**{fk_field: instance.pk}).count()
    except Exception:
        return 0


def _has_applied_payments(instance) -> bool:
    """Check if a transaction has payments applied."""
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    model_name = instance.__class__.__name__.lower()
    return GlJournal.objects.filter(
        source_id=instance.pk, source_model=model_name
    ).exists()


def _check_preconditions(instance, model_type: str, from_status: str, to_status: str) -> list[str]:
    """Check pre-conditions for a specific transition. Returns list of error messages."""
    errors = []

    # ── Released requires at least one line ──
    if to_status == 'released' and model_type in ('proposal', 'order', 'invoice', 'purchase', 'work_order', 'requisition'):
        if _get_line_count(instance, model_type) == 0:
            errors.append(f"Cannot release {model_type} with no lines")

    # ── Proposal → released requires customer ──
    if model_type == 'proposal' and to_status == 'released':
        if not getattr(instance, 'customer_id', None):
            errors.append("Proposal must have a customer before release")

    # ── Cancel blocked if payments applied ──
    if to_status == 'canceled':
        if _has_applied_payments(instance):
            errors.append(f"Cannot cancel — has journalized GL entries. Void or credit instead.")

    # ── Order complete requires all lines shipped ──
    if model_type == 'order' and to_status == 'complete':
        try:
            OrderLine = dj_apps.get_model('transactions', 'OrderLine')
            lines = OrderLine.objects.filter(order_id=instance.pk)
            for line in lines:
                qty = line.quantity or {}
                ordered = qty.get('ordered', 0) or 0
                shipped = qty.get('shipped', 0) or 0
                if shipped < ordered:
                    errors.append("Cannot complete order — not all lines are shipped")
                    break
        except Exception:
            pass

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# Main validation entry point
# ─────────────────────────────────────────────────────────────────────────────

def validate_transition(
    instance,
    model_type: str,
    to_status: str,
) -> ValidationResult:
    """Validate a status transition for a transaction.

    Called from wcapi save (when status field changes) and from
    transition action views.

    Args:
        instance: The transaction model instance (current state)
        model_type: 'order', 'invoice', 'proposal', 'purchase',
                    'work_order', 'requisition', 'payment'
        to_status: The requested new status

    Returns:
        ValidationResult with can_proceed, errors, warnings
    """
    errors = []
    warnings = []
    from_status = getattr(instance, 'status', '')

    # ── Journalized lock — no status changes on posted records ──
    if is_journalized(instance):
        return ValidationResult(
            False,
            [f"Cannot change status — {model_type} has been journalized. "
             f"Reverse the journal entry first."],
        )

    # ── Same status — no-op, allow ──
    if from_status == to_status:
        return ValidationResult(True)

    # ── Check transition is allowed ──
    type_transitions = TRANSITIONS.get(model_type, {})
    allowed = type_transitions.get(from_status)

    if allowed is None:
        errors.append(f"Unknown current status '{from_status}' for {model_type}")
        return ValidationResult(False, errors)

    if to_status not in allowed:
        if from_status in TERMINAL:
            errors.append(f"Cannot transition from terminal status '{from_status}'")
        else:
            errors.append(
                f"Cannot transition {model_type} from '{from_status}' to '{to_status}'. "
                f"Allowed: {', '.join(allowed) if allowed else '(none — terminal status)'}"
            )
        return ValidationResult(False, errors)

    # ── Check pre-conditions ──
    precondition_errors = _check_preconditions(instance, model_type, from_status, to_status)
    errors.extend(precondition_errors)

    can_proceed = len(errors) == 0
    return ValidationResult(can_proceed, errors, warnings)


def validate_modification(
    instance,
    model_type: str,
    changed_fields: Optional[set] = None,
) -> ValidationResult:
    """Validate that a record can be modified at all.

    Called from wcapi save before field-level changes are applied.
    Blocks all edits on journalized records (except status transitions,
    which go through validate_transition).

    Args:
        instance: The model instance
        model_type: Model type key
        changed_fields: Set of field names being changed (optional)

    Returns:
        ValidationResult — False if record is locked by journalization
    """
    # Normalize model_type for line models
    check_type = model_type.replace('_line', '').replace('line', '')

    if model_type in JOURNALIZABLE_MODELS or check_type in JOURNALIZABLE_MODELS:
        if is_journalized(instance):
            return ValidationResult(
                False,
                [f"Cannot modify {model_type} — record has been journalized. "
                 f"To correct, reverse the journal entry, make changes, then re-journalize."],
            )

    return ValidationResult(True)


__all__ = [
    'TRANSITIONS',
    'TERMINAL',
    'JOURNALIZABLE_MODELS',
    'is_journalized',
    'validate_transition',
    'validate_modification',
]
