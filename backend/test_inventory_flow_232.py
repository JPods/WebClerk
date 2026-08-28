#!/usr/bin/env python
"""
Test script for inventory flow using Item 232.

Test plan:
1. Create Proposal with 15 units
2. Create Order from Proposal for 11 units  
3. Create Invoice from Order for 9 units
4. Create Purchase for 11 units
5. Create Receipt from Purchase for 7 units
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from django.db import transaction
from apps.products.models import Item, Warehouse
from apps.transactions.models import (
    Proposal, ProposalLine, 
    Order, OrderLine, 
    Invoice, InvoiceLine, 
    Purchase, PurchaseLine, 
    Receipt, ReceiptLine
)
from apps.transactions.services.line_manage import LineItemService
from apps.core.models import Pending


def print_item_state(item_id, label=""):
    item = Item.objects.get(pk=item_id)
    print(f"\n{label} Item {item_id} quantity: {item.quantity}")
    return item.quantity


def print_pending_summary(item_id):
    pendings = Pending.objects.filter(model_name='item', record_id=item_id).order_by('-id')[:5]
    print(f"Latest pending records for Item {item_id}:")
    for p in pendings:
        data = p.data or {}
        type_id = data.get('type_id', '??')
        on_p = data.get('on_p', 0)
        on_so = data.get('on_so', 0)
        on_po = data.get('on_po', 0)
        on_in = data.get('on_in', 0)
        on_r = data.get('on_r', 0)
        print(f"  Pending {p.id}: type={type_id}, on_p={on_p}, on_so={on_so}, on_po={on_po}, on_in={on_in}, on_r={on_r}")


def run_test():
    ITEM_ID = 232
    service = LineItemService(create_pending=True)
    
    print("=" * 60)
    print("INVENTORY FLOW TEST - Item 232")
    print("=" * 60)
    
    # Initial state
    print_item_state(ITEM_ID, "INITIAL STATE:")
    initial_pending_count = Pending.objects.filter(model_name='item', record_id=ITEM_ID).count()
    print(f"Initial pending count: {initial_pending_count}")
    
    # ============================================================
    # STEP 1: Create Proposal with 15 units
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 1: Create Proposal with 15 units")
    print("=" * 60)
    
    proposal = Proposal.objects.create(
        ida='TEST-PROP-232',
        status='draft',
    )
    print(f"Created Proposal ID: {proposal.id}, ida: {proposal.ida}")
    
    # Service determines transaction_type from the transaction object
    proposal_line = service.add_item_to_transaction(
        proposal, ITEM_ID, 15
    )
    print(f"Created ProposalLine ID: {proposal_line.id}, qty: 15")
    print("Expected: Pending with on_p=+15")
    print_pending_summary(ITEM_ID)
    
    # ============================================================
    # STEP 2: Create Order from Proposal for 11 units
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 2: Create Order from Proposal for 11 units")
    print("=" * 60)
    
    order = Order.objects.create(
        ida='TEST-ORD-232',
        status='draft',
        parent_id=proposal.id,  # Link to proposal
    )
    print(f"Created Order ID: {order.id}, ida: {order.ida}, parent_id: {order.parent_id}")
    
    order_line = service.add_item_to_transaction(order, ITEM_ID, 11)
    print(f"Created OrderLine ID: {order_line.id}, qty: 11")
    print("Expected: Pending with on_so=+11")
    print_pending_summary(ITEM_ID)
    
    # ============================================================
    # STEP 3: Create Invoice from Order for 9 units
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 3: Create Invoice from Order for 9 units")
    print("=" * 60)
    
    invoice = Invoice.objects.create(
        ida='TEST-INV-232',
        status='draft',
        parent_id=order.id,  # Link to order
    )
    print(f"Created Invoice ID: {invoice.id}, ida: {invoice.ida}, parent_id: {invoice.parent_id}")
    
    invoice_line = service.add_item_to_transaction(invoice, ITEM_ID, 9)
    print(f"Created InvoiceLine ID: {invoice_line.id}, qty: 9")
    print("Expected: Pending with on_in=+9 (and ideally on_so=-9, on_hand=-9)")
    print_pending_summary(ITEM_ID)
    
    # ============================================================
    # STEP 4: Create Purchase for 11 units
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 4: Create Purchase for 11 units")
    print("=" * 60)
    
    purchase = Purchase.objects.create(
        ida='TEST-PUR-232',
        status='draft',
    )
    print(f"Created Purchase ID: {purchase.id}, ida: {purchase.ida}")
    
    purchase_line = service.add_item_to_transaction(purchase, ITEM_ID, 11)
    print(f"Created PurchaseLine ID: {purchase_line.id}, qty: 11")
    print("Expected: Pending with on_po=+11")
    print_pending_summary(ITEM_ID)
    
    # ============================================================
    # STEP 5: Create Receipt from Purchase for 7 units
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 5: Create Receipt from Purchase for 7 units")
    print("=" * 60)
    
    receipt = Receipt.objects.create(
        ida='TEST-RCP-232',
        source_type='purchase_receipt',
        purchase=purchase,  # Link to purchase
    )
    print(f"Created Receipt ID: {receipt.id}, ida: {receipt.ida}, purchase_id: {receipt.purchase_id}")
    
    receipt_line = service.add_item_to_transaction(receipt, ITEM_ID, 7, warehouse_id=3)
    print(f"Created ReceiptLine ID: {receipt_line.id}, qty: 7")
    print("Expected: Pending with on_r=+7 (and ideally on_po=-7, on_hand=+7)")
    print_pending_summary(ITEM_ID)
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    final_pending_count = Pending.objects.filter(model_name='item', record_id=ITEM_ID).count()
    new_pendings = final_pending_count - initial_pending_count
    
    print(f"\nTransactions created:")
    print(f"  Proposal {proposal.id} -> ProposalLine {proposal_line.id} (qty=15)")
    print(f"  Order {order.id} -> OrderLine {order_line.id} (qty=11)")
    print(f"  Invoice {invoice.id} -> InvoiceLine {invoice_line.id} (qty=9)")
    print(f"  Purchase {purchase.id} -> PurchaseLine {purchase_line.id} (qty=11)")
    print(f"  Receipt {receipt.id} -> ReceiptLine {receipt_line.id} (qty=7)")
    
    print(f"\nPending records created: {new_pendings}")
    print_item_state(ITEM_ID, "FINAL STATE:")
    
    print("\n" + "=" * 60)
    print("EXPECTED PENDING IMPACT (after processing):")
    print("=" * 60)
    print("  on_p:    +15 (proposal)")
    print("  on_so:   +11 (order)")
    print("  on_in:   +9 (invoice tracking)")
    print("  on_po:   +11 (purchase)")
    print("  on_r:    +7 (receipt tracking)")
    print("\nNOTE: Current implementation creates independent pending records.")
    print("Future: Invoice should release on_so, Receipt should release on_po")
    

if __name__ == '__main__':
    run_test()
