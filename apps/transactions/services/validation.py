from __future__ import annotations

from typing import Dict, List, Optional, Any
from decimal import Decimal

from apps.transactions.models import Proposal, Order, Invoice


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, can_proceed: bool, errors: List[str] = None, warnings: List[str] = None, data: Dict = None):
        self.can_proceed = can_proceed
        self.errors = errors or []
        self.warnings = warnings or []
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'can_proceed': self.can_proceed,
            'errors': self.errors,
            'warnings': self.warnings,
            'data': self.data
        }


def validate_proposal_for_conversion(proposal: Proposal) -> ValidationResult:
    """
    Validate that a proposal can be converted to an order.

    Checks:
    - Status allows conversion
    - Has lines with valid quantities and pricing
    - Customer information is complete
    """
    errors = []
    warnings = []
    data = {'line_count': 0, 'total_amount': 0.0}

    if not proposal:
        return ValidationResult(False, ["Proposal not found"])

    # Status check
    if proposal.status not in ['sent', 'accepted']:
        errors.append(f"Proposal status '{proposal.status}' does not allow conversion")
    elif proposal.status == 'sent':
        warnings.append("Proposal is sent but not yet accepted")

    # Check for lines
    from apps.transactions.models import ProposalLine
    lines = list(ProposalLine.objects.filter(parent=proposal))
    data['line_count'] = len(lines)

    if not lines:
        errors.append("Proposal has no lines to convert")
        return ValidationResult(False, errors, warnings, data)

    # Validate lines
    total_amount = Decimal(0)
    invalid_lines = 0

    for line in lines:
        # Check quantity
        qty = line.quantity or {}
        quantity = qty.get('remaining', qty.get('ordered', 0))
        if quantity <= 0:
            invalid_lines += 1
            continue

        # Check pricing
        price = line.price or {}
        extended = price.get('extended', 0)
        if extended <= 0:
            invalid_lines += 1
            continue

        total_amount += Decimal(str(extended))

    data['total_amount'] = float(total_amount)

    if invalid_lines > 0:
        errors.append(f"{invalid_lines} line(s) have invalid quantity or pricing")

    # Customer check
    if not proposal.customer_id:
        errors.append("Proposal must have a customer assigned")

    can_proceed = len(errors) == 0
    return ValidationResult(can_proceed, errors, warnings, data)


def validate_order_for_invoicing(order: Order) -> ValidationResult:
    """
    Validate that an order can be converted to an invoice.

    Checks:
    - Status allows invoicing
    - Has fulfillable lines
    - Shipping/billing addresses
    """
    errors = []
    warnings = []
    data = {'fulfillable_lines': 0, 'total_amount': 0.0}

    if not order:
        return ValidationResult(False, ["Order not found"])

    # Status check
    if order.status not in ['released', 'in_progress', 'fulfilled']:
        errors.append(f"Order status '{order.status}' does not allow invoicing")
    elif order.status in ['released', 'in_progress']:
        warnings.append("Order is not fully fulfilled - partial invoicing possible")

    # Check for lines
    from apps.transactions.models import OrderLine
    lines = list(OrderLine.objects.filter(parent=order))
    data['line_count'] = len(lines)

    if not lines:
        errors.append("Order has no lines to invoice")
        return ValidationResult(False, errors, warnings, data)

    # Check fulfillable lines
    fulfillable = 0
    total_amount = Decimal(0)

    for line in lines:
        qty = line.quantity or {}
        remaining = qty.get('remaining', qty.get('ordered', 0))
        invoiced = qty.get('invoiced', 0)

        if remaining > invoiced:  # Has quantity to invoice
            fulfillable += 1
            # Estimate amount (simplified)
            price = line.price or {}
            unit_price = price.get('unit', 0)
            qty_to_invoice = remaining - invoiced
            total_amount += Decimal(str(unit_price)) * Decimal(str(qty_to_invoice))

    data['fulfillable_lines'] = fulfillable
    data['total_amount'] = float(total_amount)

    if fulfillable == 0:
        errors.append("No lines have remaining quantity to invoice")

    # Address checks (simplified)
    if not order.customer_id:
        errors.append("Order must have billing customer")

    can_proceed = len(errors) == 0
    return ValidationResult(can_proceed, errors, warnings, data)


def validate_invoice_for_payment(invoice: Invoice) -> ValidationResult:
    """
    Validate that an invoice can receive payments.

    Checks:
    - Status allows payment
    - Has outstanding balance
    - Not overdue if strict
    """
    errors = []
    warnings = []
    data = {'balance': 0.0, 'is_overdue': False}

    if not invoice:
        return ValidationResult(False, ["Invoice not found"])

    # Status check
    if invoice.status in ['paid', 'canceled']:
        errors.append(f"Invoice status '{invoice.status}' does not allow payments")
    elif invoice.status == 'draft':
        warnings.append("Invoice is still in draft status")

    # Balance check
    totals = invoice.totals or {}
    total = totals.get('total', 0)
    received = totals.get('received', 0)
    balance = total - received
    data['balance'] = balance

    if balance <= 0:
        errors.append("Invoice has no outstanding balance")

    # Overdue check (simplified)
    # In real implementation, check against payment terms
    if invoice.status == 'overdue':
        data['is_overdue'] = True
        warnings.append("Invoice is overdue")

    can_proceed = len(errors) == 0
    return ValidationResult(can_proceed, errors, warnings, data)


def validate_transaction_flow(
    source_type: str,
    source_id: int,
    target_type: str
) -> ValidationResult:
    """
    Validate that a transaction can flow to the next stage.

    Args:
        source_type: 'proposal', 'order', 'purchase_order'
        source_id: ID of source transaction
        target_type: 'order', 'invoice', 'payment'
    """
    errors = []
    warnings = []
    data = {}

    # Get source transaction
    source = None
    if source_type == 'proposal':
        source = Proposal.objects.filter(id=source_id).first()
    elif source_type == 'order':
        source = Order.objects.filter(id=source_id).first()
    elif source_type == 'invoice':
        source = Invoice.objects.filter(id=source_id).first()

    if not source:
        return ValidationResult(False, [f"{source_type} {source_id} not found"])

    # Validate based on flow
    if source_type == 'proposal' and target_type == 'order':
        return validate_proposal_for_conversion(source)
    elif source_type == 'order' and target_type == 'invoice':
        return validate_order_for_invoicing(source)
    elif source_type == 'invoice' and target_type == 'payment':
        return validate_invoice_for_payment(source)
    else:
        errors.append(f"Invalid flow: {source_type} -> {target_type}")

    return ValidationResult(False, errors, warnings, data)


__all__ = [
    'ValidationResult',
    'validate_proposal_for_conversion',
    'validate_order_for_invoicing',
    'validate_invoice_for_payment',
    'validate_transaction_flow',
]