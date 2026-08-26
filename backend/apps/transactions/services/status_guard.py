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
        'planned':          ['signoff_request', 'released', 'canceled'],
        'signoff_request':  ['released', 'planned', 'canceled'],
        'released':         ['sent', 'in_progress', 'hold', 'canceled'],
        'sent':             ['accepted', 'rejected', 'hold', 'canceled'],
        'accepted':         ['converted', 'hold', 'canceled'],
        'rejected':         [],
        'converted':        [],
        'in_progress':      ['complete', 'hold', 'canceled'],
        'hold':             ['released', 'sent', 'in_progress', 'canceled'],
        'complete':         [],
        'canceled':         [],
    },
    'order': {
        'planned':          ['signoff_request', 'released', 'canceled'],
        'signoff_request':  ['released', 'planned', 'canceled'],
        'released':         ['in_progress', 'hold', 'canceled'],
        'in_progress':      ['complete', 'hold', 'canceled'],
        'hold':             ['released', 'in_progress', 'canceled'],
        'complete':         [],
        'canceled':         [],
    },
    'invoice': {
        'planned':          ['signoff_request', 'released', 'canceled'],
        'signoff_request':  ['released', 'planned', 'canceled'],
        'released':         ['in_progress', 'hold', 'canceled'],
        'in_progress':      ['complete', 'hold', 'canceled'],
        'hold':             ['released', 'in_progress', 'canceled'],
        'complete':         [],
        'canceled':         [],
    },
    'purchase': {
        'planned':          ['signoff_request', 'released', 'canceled'],
        'signoff_request':  ['released', 'planned', 'canceled'],
        'released':         ['in_progress', 'hold', 'canceled'],
        'in_progress':      ['complete', 'hold', 'canceled'],
        'hold':             ['released', 'in_progress', 'canceled'],
        'complete':         [],
        'canceled':         [],
    },
    'workorder': {
        'planned':          ['signoff_request', 'released', 'canceled'],
        'signoff_request':  ['released', 'planned', 'canceled'],
        'released':         ['in_progress', 'hold', 'canceled'],
        'in_progress':      ['complete', 'hold', 'canceled'],
        'hold':             ['released', 'in_progress', 'canceled'],
        'complete':         [],
        'canceled':         [],
    },
    'requisition': {
        'planned':          ['signoff_request', 'released', 'canceled'],
        'signoff_request':  ['released', 'planned', 'canceled'],
        'released':         ['in_progress', 'hold', 'canceled'],
        'in_progress':      ['complete', 'hold', 'canceled'],
        'hold':             ['released', 'in_progress', 'canceled'],
        'complete':         [],
        'canceled':         [],
    },
    'payment': {
        'planned':          ['released', 'canceled'],
        'released':         ['complete', 'canceled'],
        'complete':         [],
        'canceled':         [],
        'voided':           [],
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

    Journalized records are identified by dt_journaled != 0.
    For line models, check the parent header.
    """
    # Direct check — dt_journaled non-zero means locked
    dt_j = getattr(instance, 'dt_journaled', 0) or 0
    if dt_j != 0:
        return True

    # For line models, check the parent header
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
            parent_dt_j = getattr(parent, 'dt_journaled', 0) or 0
            if parent_dt_j != 0:
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
        'workorder': ('transactions', 'WorkOrderLine', 'workorder_id'),
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
    if to_status == 'released' and model_type in ('proposal', 'order', 'invoice', 'purchase', 'workorder', 'requisition'):
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
                    'workorder', 'requisition', 'payment'
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

    # ── Approval gate — check if transition requires signoff ──
    approval_result = check_approval_required(instance, model_type, from_status, to_status)
    if approval_result.get('required') and from_status != 'signoff_request':
        # Redirect to signoff_request instead of target status
        warnings.append(
            f"Approval required: {approval_result.get('rule_name', 'approval rule')}. "
            f"Status set to signoff_request pending approval."
        )
        return ValidationResult(
            True, errors, warnings,
            redirect_status='signoff_request',
            approval=approval_result,
        )

    # ── Signoff_request → released: verify all approvals complete ──
    if from_status == 'signoff_request' and to_status not in ('planned', 'canceled'):
        config = getattr(instance, 'config', None) or {}
        signoff = config.get('signoff', {})
        if signoff.get('required') and signoff.get('status') != 'approved':
            errors.append("Cannot proceed — pending approvals not yet complete")
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


# ─────────────────────────────────────────────────────────────────────────────
# Approval gate — Setting-driven signoff rules
# ─────────────────────────────────────────────────────────────────────────────

def _get_approval_rules(model_type: str) -> list:
    """Load approval rules from Setting config.approval for a transaction type.

    Setting purpose: 'wc:approval', parent_model: model_type (e.g. 'purchase').
    Falls back to 'wc:approval' with parent_model='transaction' for shared rules.
    """
    Setting = dj_apps.get_model('core', 'Setting')
    rules = []

    for parent in (model_type, 'transaction'):
        setting = Setting.objects.filter(
            purpose='wc:approval', parent_model=parent, is_active=True,
        ).first()
        if setting and isinstance(setting.config, dict):
            config_rules = setting.config.get('approval', {}).get('rules', [])
            if isinstance(config_rules, list):
                rules.extend(config_rules)

    return rules


def _evaluate_condition(instance, condition: dict) -> bool:
    """Evaluate a simple condition against a transaction instance.

    Condition format: {"field": "totals.total", "op": ">=", "value": 5000}
    Supports dotted field paths into JSON envelopes.
    """
    if not condition:
        return True  # No condition = always applies

    field_path = condition.get('field', '')
    op = condition.get('op', '>=')
    threshold = condition.get('value', 0)

    # Resolve dotted path (e.g., "totals.total")
    parts = field_path.split('.')
    val = instance
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = getattr(val, part, None)
        if val is None:
            return False

    try:
        val = float(val)
        threshold = float(threshold)
    except (TypeError, ValueError):
        return False

    if op == '>=':
        return val >= threshold
    elif op == '>':
        return val > threshold
    elif op == '<=':
        return val <= threshold
    elif op == '<':
        return val < threshold
    elif op == '==':
        return val == threshold
    elif op == '!=':
        return val != threshold
    return False


def check_approval_required(instance, model_type: str, from_status: str, to_status: str) -> dict:
    """Check if a status transition requires approval.

    Returns:
        {'required': False} if no approval needed.
        {'required': True, 'rule_name': str, 'assigned_to': [...]} if approval needed.
    """
    rules = _get_approval_rules(model_type)

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        # Check trigger matches
        if rule.get('trigger') != 'status_change':
            continue
        if rule.get('from', '') and rule['from'] != from_status:
            continue
        if rule.get('to', '') and rule['to'] != to_status:
            continue

        # Check condition
        condition = rule.get('condition')
        if condition and not _evaluate_condition(instance, condition):
            continue

        # Rule matches — approval required
        return {
            'required': True,
            'rule_name': rule.get('name', 'Approval required'),
            'assigned_to': rule.get('assigned_to', []),
            'blocked_transition': {'from': from_status, 'to': to_status},
        }

    return {'required': False}


def create_signoff_action(instance, model_type: str, approval: dict) -> Optional[int]:
    """Create an Action record for signoff approval.

    Populates transaction config.signoff with the approval state.
    Returns the Action ID or None.
    """
    import time
    Action = dj_apps.get_model('core', 'Action')

    from datetime import datetime, timezone as tz

    assigned_to = approval.get('assigned_to', [])
    blocked_transition = approval.get('blocked_transition', {})
    rule_name = approval.get('rule_name', 'Approval required')

    # Stamp dt_requested on active assignees (measures administrative drag)
    now_iso = datetime.now(tz.utc).isoformat()
    for entry in assigned_to:
        if entry.get('status') == 'active':
            entry['dt_requested'] = now_iso
            entry['dt_response'] = ''

    # Create the Action
    action = Action.objects.create(
        action={'en': f'SignOff Request: {rule_name}'},
        description={'en': f'{model_type.title()} #{instance.ida} requires approval to transition '
                     f'from {blocked_transition.get("from", "?")} to {blocked_transition.get("to", "?")}. '
                     f'Rule: {rule_name}'},
        assigned_to=assigned_to,
        kanban_column='Ready',
        action_type='follow-up',
        priority='2',
        status='planned',
    )

    # Write signoff state into transaction config
    config = getattr(instance, 'config', None) or {}
    if not isinstance(config, dict):
        config = {}

    config['signoff'] = {
        'required': True,
        'action_id': action.id,
        'rule_name': rule_name,
        'blocked_transition': blocked_transition,
        'assigned_to': assigned_to,
        'approvals': [],
        'status': 'pending',
    }

    type(instance).objects.filter(pk=instance.pk).update(config=config)

    return action.id


def record_signoff(instance, contact_id: int, contact_name: str, status: str = 'approved') -> dict:
    """Record an individual's signoff on a transaction.

    When all sequential approvers have signed off, config.signoff.status
    changes to 'approved' and the blocked transition can proceed.

    Args:
        instance: transaction instance
        contact_id: who is signing off
        contact_name: display name
        status: 'approved' or 'rejected'

    Returns:
        {'signoff_status': 'pending'|'approved'|'rejected', 'next_sequence': int|None}
    """
    import time
    from datetime import datetime, timezone

    config = getattr(instance, 'config', None) or {}
    signoff = config.get('signoff', {})

    if not signoff.get('required'):
        return {'error': 'No signoff required on this record'}

    approvals = signoff.get('approvals', [])
    assigned_to = signoff.get('assigned_to', [])

    now_iso = datetime.now(timezone.utc).isoformat()

    # Stamp dt_response on the assignee who is responding
    for entry in assigned_to:
        if entry.get('contact_id') == contact_id and not entry.get('dt_response'):
            entry['dt_response'] = now_iso

    # Record this approval
    approvals.append({
        'contact_id': contact_id,
        'name': contact_name,
        'status': status,
        'dt': now_iso,
    })
    signoff['approvals'] = approvals

    if status == 'rejected':
        signoff['status'] = 'rejected'
        signoff['assigned_to'] = assigned_to
        config['signoff'] = signoff
        type(instance).objects.filter(pk=instance.pk).update(config=config)
        return {'signoff_status': 'rejected', 'next_sequence': None}

    # Check if all required approvers have signed off
    approved_ids = {a['contact_id'] for a in approvals if a['status'] == 'approved'}

    # Activate next passive approver in sequence — stamp dt_requested
    next_sequence = None
    all_approved = True
    for entry in assigned_to:
        cid = entry.get('contact_id')
        if cid and cid not in approved_ids:
            all_approved = False
            if entry.get('status') == 'passive':
                entry['status'] = 'active'
                entry['dt_requested'] = now_iso
                entry['dt_response'] = ''
                next_sequence = entry.get('sequence')
                break

    signoff['assigned_to'] = assigned_to

    if all_approved:
        signoff['status'] = 'approved'
    else:
        signoff['status'] = 'pending'

    config['signoff'] = signoff
    type(instance).objects.filter(pk=instance.pk).update(config=config)

    # Update Action assigned_to to reflect activated approvers
    action_id = signoff.get('action_id')
    if action_id:
        try:
            Action = dj_apps.get_model('core', 'Action')
            Action.objects.filter(pk=action_id).update(assigned_to=assigned_to)
        except Exception:
            pass

    return {'signoff_status': signoff['status'], 'next_sequence': next_sequence}


__all__ = [
    'TRANSITIONS',
    'TERMINAL',
    'JOURNALIZABLE_MODELS',
    'is_journalized',
    'validate_transition',
    'validate_modification',
    'check_approval_required',
    'create_signoff_action',
    'record_signoff',
]
