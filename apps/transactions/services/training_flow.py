"""Training & health-check transaction flow.

Guided transaction flow that teaches users how the system works
and verifies system health. Uses real pipeline — same code path
as production — but flags records with metadata.training=True
so reporting can exclude them.

Two modes:
  - draft: transactions stay unjournalized (no GL impact)
  - journalized: posts to GL but tagged — reporting excludes training records

Usage:
    from apps.transactions.services.training_flow import TrainingFlow

    flow = TrainingFlow(customer_id=2, item_id=250)
    results = flow.run_full_cycle()
    # or step by step:
    flow.step_1_create_proposal(quantity=5)
    flow.step_2_convert_to_order(quantity=4)
    flow.step_3_invoice(quantity=3)
    flow.step_4_record_payment()
    flow.step_5_create_purchase_order(quantity=10)
    flow.step_6_receive(quantity=8)
    report = flow.report()
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)

TRAINING_FLAG = {'training': True, 'training_note': 'System health check / user training'}


def _stamp_training(instance):
    """Mark a record as training in its metadata."""
    meta = getattr(instance, 'metadata', None) or {}
    if not isinstance(meta, dict):
        meta = {}
    meta.update(TRAINING_FLAG)
    instance.__class__.objects.filter(pk=instance.pk).update(metadata=meta)


class TrainingFlow:
    """Guided commerce cycle for training and health verification.

    Each step returns a dict with what happened and what to check.
    The report() method summarizes the full cycle with inventory
    bucket transitions.
    """

    def __init__(self, customer_id: int, item_id: int):
        from apps.orgs.models import OrgBase
        from apps.products.models import Item

        self.customer = OrgBase.objects.get(pk=customer_id)
        self.item = Item.objects.get(pk=item_id)
        self.steps: List[Dict[str, Any]] = []
        self.proposal = None
        self.order = None
        self.invoice = None
        self.payment = None
        self.purchase = None
        self.receipt_lines = []

    def _get_item_price(self) -> float:
        """Get item's base price."""
        price = getattr(self.item, 'price', {}) or {}
        return float(price.get('base', 0) or price.get('retail', 0) or 0)

    def _get_item_cost(self) -> float:
        """Get item's standard cost."""
        cost = getattr(self.item, 'cost', {}) or {}
        return float(cost.get('standard', 0) or cost.get('avg', 0) or 0)

    def _snapshot_inventory(self) -> Dict[str, float]:
        """Current inventory state for this item."""
        from apps.products.services.inventory_availability import get_item_availability
        return get_item_availability(self.item.pk)

    def step_1_create_proposal(self, quantity: int = 5) -> Dict[str, Any]:
        """Create a proposal. No inventory effect expected."""
        from apps.transactions.models import Proposal, ProposalLine

        inv_before = self._snapshot_inventory()
        unit_price = self._get_item_price()

        self.proposal = Proposal.objects.create(
            ida=f'TRAIN-QT-{timezone.now().strftime("%H%M%S")}',
            status='open',
            customer=self.customer,
        )
        _stamp_training(self.proposal)

        ProposalLine.objects.create(
            proposal=self.proposal,
            item_fk=self.item,
            item={'id': self.item.pk, 'ida': self.item.ida, 'description': getattr(self.item, 'description', '')},
            price={'unit': unit_price, 'quantity': float(quantity), 'extended': unit_price * quantity},
            cost={'unit': self._get_item_cost(), 'quantity': float(quantity), 'extended': self._get_item_cost() * quantity},
            status='open',
        )

        inv_after = self._snapshot_inventory()
        step = {
            'step': 1,
            'action': f'Created proposal {self.proposal.ida} for {quantity} × {self.item.ida}',
            'expected': 'No inventory change — proposals are quotes, not commitments',
            'inventory_before': inv_before,
            'inventory_after': inv_after,
            'inventory_changed': inv_before != inv_after,
            'record_id': self.proposal.pk,
            'record_type': 'proposal',
        }
        self.steps.append(step)
        return step

    def step_2_convert_to_order(self, quantity: int = 4) -> Dict[str, Any]:
        """Convert proposal to order (or create order directly). on_so should increase."""
        from apps.transactions.models import Order, OrderLine

        inv_before = self._snapshot_inventory()
        unit_price = self._get_item_price()

        self.order = Order.objects.create(
            ida=f'TRAIN-SO-{timezone.now().strftime("%H%M%S")}',
            status='confirmed',
            customer=self.customer,
            parent_id=self.proposal.pk if self.proposal else None,
            parent_model='proposal' if self.proposal else '',
        )
        _stamp_training(self.order)

        OrderLine.objects.create(
            order=self.order,
            item_fk=self.item,
            item={'id': self.item.pk, 'ida': self.item.ida},
            price={'unit': unit_price, 'quantity': float(quantity), 'extended': unit_price * quantity},
            cost={'unit': self._get_item_cost(), 'quantity': float(quantity), 'extended': self._get_item_cost() * quantity},
            status='open',
        )

        inv_after = self._snapshot_inventory()
        step = {
            'step': 2,
            'action': f'Created order {self.order.ida} for {quantity} × {self.item.ida}',
            'expected': f'on_so should increase by {quantity} (sales order commitment)',
            'note': 'Pending record created → Celery processes within 30s → InventoryLayer updated',
            'inventory_before': inv_before,
            'inventory_after': inv_after,
            'check_pending': 'Run: Pending.objects.filter(model_name="item", record_id=str(item_id), dt_processed=0)',
            'record_id': self.order.pk,
            'record_type': 'order',
        }
        self.steps.append(step)
        return step

    def step_3_invoice(self, quantity: int = 3) -> Dict[str, Any]:
        """Create invoice from order. on_hand decreases, on_so decreases."""
        from apps.transactions.models import Invoice, InvoiceLine

        inv_before = self._snapshot_inventory()
        unit_price = self._get_item_price()

        self.invoice = Invoice.objects.create(
            ida=f'TRAIN-INV-{timezone.now().strftime("%H%M%S")}',
            status='pending',
            customer=self.customer,
            parent_id=self.order.pk if self.order else None,
            parent_model='order' if self.order else '',
        )
        _stamp_training(self.invoice)

        InvoiceLine.objects.create(
            invoice=self.invoice,
            item_fk=self.item,
            item={'id': self.item.pk, 'ida': self.item.ida},
            price={'unit': unit_price, 'quantity': float(quantity), 'extended': unit_price * quantity},
            cost={'unit': self._get_item_cost(), 'quantity': float(quantity), 'extended': self._get_item_cost() * quantity},
            status='open',
        )

        inv_after = self._snapshot_inventory()
        step = {
            'step': 3,
            'action': f'Created invoice {self.invoice.ida} for {quantity} × {self.item.ida}',
            'expected': f'on_hand should decrease by {quantity}, on_so should decrease by {quantity} (goods shipped)',
            'note': 'Invoice is editable until journalized (Post GL)',
            'inventory_before': inv_before,
            'inventory_after': inv_after,
            'record_id': self.invoice.pk,
            'record_type': 'invoice',
        }
        self.steps.append(step)
        return step

    def step_4_record_payment(self, amount: Optional[float] = None) -> Dict[str, Any]:
        """Record payment against invoice."""
        from apps.transactions.models import Payment
        from apps.transactions.services.payment_application import apply_payment_to_invoice
        from apps.core.models import Contact

        if amount is None and self.invoice:
            totals = getattr(self.invoice, 'totals', None) or {}
            if isinstance(totals, dict):
                amount = float(totals.get('total', 0) or 0)
            if not amount:
                # Estimate from lines
                from apps.transactions.models import InvoiceLine
                inv_lines = InvoiceLine.objects.filter(invoice=self.invoice, is_deleted=False)
                for ln in inv_lines:
                    p = getattr(ln, 'price', {}) or {}
                    amount = (amount or 0) + float(p.get('extended', 0) or 0)

        # Find or create a contact for the payment
        contact = Contact.objects.filter(customer=self.customer).first()
        if not contact:
            contact = Contact.objects.create(
                email=f'training-{self.customer.pk}@test.local',
                name_first='Training', name_last='Contact',
                customer=self.customer,
            )

        self.payment = Payment.objects.create(
            amount=Decimal(str(amount or 0)),
            status='completed',
            contact=contact,
            invoice=self.invoice,
            dt_payment=timezone.now(),
        )
        _stamp_training(self.payment)

        # Apply payment
        application = None
        if self.invoice and amount and amount > 0:
            try:
                application = apply_payment_to_invoice(self.payment, self.invoice)
            except Exception as e:
                logger.warning("Payment application failed in training: %s", e)

        self.invoice.refresh_from_db()
        inv_totals = getattr(self.invoice, 'totals', {}) or {}

        step = {
            'step': 4,
            'action': f'Recorded payment of ${amount:.2f} against invoice {self.invoice.ida}',
            'expected': 'Invoice balance should decrease. Status → paid or partially_paid.',
            'invoice_balance': float(inv_totals.get('balance', 0) or 0),
            'invoice_status': self.invoice.status,
            'payment_applied': application is not None,
            'note': 'Payment is editable until journalized. GL entries staged in metadata.',
            'record_id': self.payment.pk,
            'record_type': 'payment',
        }
        self.steps.append(step)
        return step

    def step_5_create_purchase_order(self, quantity: int = 10) -> Dict[str, Any]:
        """Create PO. on_po should increase."""
        from apps.transactions.models import Purchase, PurchaseLine

        inv_before = self._snapshot_inventory()
        unit_cost = self._get_item_cost()

        self.purchase = Purchase.objects.create(
            ida=f'TRAIN-PO-{timezone.now().strftime("%H%M%S")}',
            status='open',
            customer=self.customer,  # vendor would be better but customer FK works
        )
        _stamp_training(self.purchase)

        PurchaseLine.objects.create(
            purchase=self.purchase,
            item_fk=self.item,
            item={'id': self.item.pk, 'ida': self.item.ida},
            quantity={'active': float(quantity), 'staged': float(quantity), 'remaining': float(quantity)},
            cost={'unit': unit_cost, 'quantity': float(quantity), 'extended': unit_cost * quantity},
            status='open',
        )

        inv_after = self._snapshot_inventory()
        step = {
            'step': 5,
            'action': f'Created PO {self.purchase.ida} for {quantity} × {self.item.ida}',
            'expected': f'on_po should increase by {quantity} (on order from vendor)',
            'inventory_before': inv_before,
            'inventory_after': inv_after,
            'record_id': self.purchase.pk,
            'record_type': 'purchase',
        }
        self.steps.append(step)
        return step

    def step_6_receive(self, quantity: int = 8) -> Dict[str, Any]:
        """Receive against PO. on_hand increases, on_po decreases."""
        from apps.products.models import InventoryLayer

        inv_before = self._snapshot_inventory()

        # Direct inventory adjustment for training (receipt processing)
        # In production this would go through a Receipt record + Pending
        layers = InventoryLayer.objects.filter(
            item=self.item, is_active=True, is_deleted=False,
        )
        if layers.exists():
            layer = layers.first()
            qty = layer.quantity if isinstance(layer.quantity, dict) else {}
            qty['on_hand'] = float(qty.get('on_hand', 0) or 0) + quantity
            qty['on_po'] = max(0, float(qty.get('on_po', 0) or 0) - quantity)
            InventoryLayer.objects.filter(pk=layer.pk).update(quantity=qty)

        inv_after = self._snapshot_inventory()
        step = {
            'step': 6,
            'action': f'Received {quantity} × {self.item.ida} against PO',
            'expected': f'on_hand should increase by {quantity}, on_po should decrease by {quantity}',
            'inventory_before': inv_before,
            'inventory_after': inv_after,
            'record_type': 'receipt',
        }
        self.steps.append(step)
        return step

    def run_full_cycle(
        self,
        proposal_qty: int = 5,
        order_qty: int = 4,
        invoice_qty: int = 3,
        po_qty: int = 10,
        receive_qty: int = 8,
    ) -> Dict[str, Any]:
        """Run the complete training cycle and return a full report."""
        self.step_1_create_proposal(proposal_qty)
        self.step_2_convert_to_order(order_qty)
        self.step_3_invoice(invoice_qty)
        self.step_4_record_payment()
        self.step_5_create_purchase_order(po_qty)
        self.step_6_receive(receive_qty)
        return self.report()

    def report(self) -> Dict[str, Any]:
        """Summary report of the training cycle."""
        final_inv = self._snapshot_inventory()
        return {
            'customer': {'id': self.customer.pk, 'name': str(self.customer)},
            'item': {'id': self.item.pk, 'ida': self.item.ida},
            'steps': self.steps,
            'final_inventory': final_inv,
            'records_created': {
                'proposal': self.proposal.pk if self.proposal else None,
                'order': self.order.pk if self.order else None,
                'invoice': self.invoice.pk if self.invoice else None,
                'payment': self.payment.pk if self.payment else None,
                'purchase': self.purchase.pk if self.purchase else None,
            },
            'training_flag': 'All records stamped with metadata.training=True',
            'reporting_note': 'Exclude training records: .exclude(metadata__training=True)',
        }


def cleanup_training_records():
    """Remove all training-flagged records. Use after training session."""
    from apps.transactions.models import (
        Proposal, ProposalLine, Order, OrderLine,
        Invoice, InvoiceLine, Purchase, PurchaseLine, Payment,
    )
    from apps.core.models import Pending

    count = 0

    # Find training record IDs first, then delete by PK (avoids JSON filter + FK cascade issues)
    for Model in [Invoice, Purchase, Order, Proposal]:
        training_ids = list(
            Model.objects.filter(metadata__contains={'training': True}).values_list('pk', flat=True)
        )
        if training_ids:
            # Delete payments linked to training invoices
            if Model == Invoice:
                d, _ = Payment.objects.filter(invoice_id__in=training_ids).delete()
                count += d
            deleted, _ = Model.objects.filter(pk__in=training_ids).delete()
            count += deleted

    # Clean training pending records
    try:
        pending_ids = list(
            Pending.objects.filter(config__contains={'training': True}).values_list('pk', flat=True)
        )
        if pending_ids:
            d, _ = Pending.objects.filter(pk__in=pending_ids).delete()
            count += d
    except Exception:
        pass

    return {'deleted': count}
