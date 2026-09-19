from __future__ import annotations

from typing import Dict, List, Optional, Any
from decimal import Decimal

from apps.transactions.models import Quote, Order, Invoice, Purchase, WorkOrder


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, can_proceed: bool, errors: List[str] = None, warnings: List[str] = None,
                 data: Dict = None, redirect_status: str = None, approval: Dict = None):
        self.can_proceed = can_proceed
        self.errors = errors or []
        self.warnings = warnings or []
        self.data = data or {}
        self.redirect_status = redirect_status  # if set, use this status instead of requested
        self.approval = approval  # approval gate details

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'can_proceed': self.can_proceed,
            'errors': self.errors,
            'warnings': self.warnings,
            'data': self.data,
        }
        if self.redirect_status:
            result['redirect_status'] = self.redirect_status
        if self.approval:
            result['approval'] = self.approval
        return result


def validate_quote_for_conversion(quote: Quote) -> ValidationResult:
    """
    Validate that a quote can be converted to an order.

    Checks:
    - Status allows conversion
    - Has lines with valid quantities and pricing
    - Customer information is complete
    """
    errors = []
    warnings = []
    data = {'line_count': 0, 'total': 0.0}

    if not quote:
        return ValidationResult(False, ["Quote not found"])

    # Status check
    if quote.status not in ['sent', 'accepted']:
        errors.append(f"Quote status '{quote.status}' does not allow conversion")
    elif quote.status == 'sent':
        warnings.append("Quote is sent but not yet accepted")

    # Check for lines
    from apps.transactions.models import QuoteLine
    lines = list(QuoteLine.objects.filter(quote=quote))
    data['line_count'] = len(lines)

    if not lines:
        errors.append("Quote has no lines to convert")
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
        extended = (line.totals or {}).get('amount', 0)
        if extended <= 0:
            invalid_lines += 1
            continue

        total_amount += Decimal(str(extended))

    data['total'] = float(total_amount)

    if invalid_lines > 0:
        errors.append(f"{invalid_lines} line(s) have invalid quantity or pricing")

    # Customer check
    if not quote.customer_id:
        errors.append("Quote must have a customer assigned")

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
    data = {'fulfillable_lines': 0, 'total': 0.0}

    if not order:
        return ValidationResult(False, ["Order not found"])

    # Status check
    if order.status not in ['released', 'in_progress', 'fulfilled']:
        errors.append(f"Order status '{order.status}' does not allow invoicing")
    elif order.status in ['released', 'in_progress']:
        warnings.append("Order is not fully fulfilled - partial invoicing possible")

    # Check for lines
    from apps.transactions.models import OrderLine
    lines = list(OrderLine.objects.filter(order=order))
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
    data['total'] = float(total_amount)

    if fulfillable == 0:
        errors.append("No lines have remaining quantity to invoice")

    # Address checks (simplified)
    if not order.customer_id:
        errors.append("Order must have billing customer")

    can_proceed = len(errors) == 0
    return ValidationResult(can_proceed, errors, warnings, data)


def validate_invoice_for_cash(invoice: Invoice) -> ValidationResult:
    """
    Validate that an invoice can receive cash_entries.

    Checks:
    - Status allows cash
    - Has outstanding balance
    - Not overdue if strict
    """
    errors = []
    warnings = []
    data = {'balance': 0.0, 'is_overdue': False}

    if not invoice:
        return ValidationResult(False, ["Invoice not found"])

    # Status check — workflow only; money state lives in totals.cash_state
    if invoice.status == 'canceled':
        errors.append("Invoice is canceled")
    elif invoice.status == 'draft':
        warnings.append("Invoice is still in draft status")

    # Balance check — read from envelope, don't recompute (PJPV)
    totals = invoice.totals or {}
    balance = totals.get('balance', 0)
    data['balance'] = balance

    if balance == 0:
        errors.append("Invoice has no balance due")

    # Overdue check (simplified)
    # In real implementation, check against cash terms
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
        source_type: 'quote', 'order', 'invoice', 'purchase', 'workorder'
        source_id: ID of source transaction
        target_type: any supported target in transfer matrix
    """
    errors = []
    warnings = []
    data = {}

    # Get source transaction
    source = None
    if source_type == 'quote':
        source = Quote.objects.filter(id=source_id).first()
    elif source_type == 'order':
        source = Order.objects.filter(id=source_id).first()
    elif source_type == 'invoice':
        source = Invoice.objects.filter(id=source_id).first()
    elif source_type == 'purchase':
        source = Purchase.objects.filter(id=source_id).first()
    elif source_type == 'workorder':
        source = WorkOrder.objects.filter(id=source_id).first()

    if not source:
        return ValidationResult(False, [f"{source_type} {source_id} not found"])

    # Validate based on flow
    if source_type == 'quote' and target_type == 'order':
        return validate_quote_for_conversion(source)
    elif source_type == 'order' and target_type == 'invoice':
        return validate_order_for_invoicing(source)
    elif source_type == 'invoice' and target_type == 'cash':
        return validate_invoice_for_cash(source)
    elif target_type in {'quote', 'order', 'invoice', 'purchase', 'workorder'} and source_type in {'quote', 'order', 'invoice', 'purchase', 'workorder'} and source_type != target_type:
        return ValidationResult(True, [], [], {'source_id': source_id})
    else:
        errors.append(f"Invalid flow: {source_type} -> {target_type}")

    return ValidationResult(False, errors, warnings, data)


__all__ = [
    'ValidationResult',
    'validate_quote_for_conversion',
    'validate_order_for_invoicing',
    'validate_invoice_for_cash',
    'validate_transaction_flow',
]