"""
Test Sequence 001 — Alice's automated mirror of the manual test.

User does each step in the UI. Then run this script to create the same
records via shell/wcapi and compare. If results differ, the bug is in the UI.

Usage:
    ./bin/python manage.py shell < tests/test_sequence_001.py

    Or step-by-step:
    ./bin/python manage.py shell -c "exec(open('tests/test_sequence_001.py').read())"

Starting state: Item 308 on_hand=100, available=100, all others=0
"""
import json, time
from decimal import Decimal

# --- Setup ---
from apps.products.models.item import Item
from apps.orgs.models import Customer, Vendor
from apps.core.models.contact import Contact
from apps.communications.models.email import Email
from apps.communications.models.phone import Phone
from apps.communications.models.address import Address
from apps.transactions.models import Invoice, InvoiceLine, Order, OrderLine, Proposal, ProposalLine, Purchase, PurchaseLine
from apps.products.models.inventory_layer import InventoryLayer

def now_ms():
    return int(time.time() * 1000)

def check_item(label, expected):
    item = Item.objects.get(pk=308)
    q = item.quantity or {}
    print(f'\n=== CHECKPOINT: {label} ===')
    all_pass = True
    for key, exp in expected.items():
        actual = q.get(key, 0)
        ok = '✓' if actual == exp else '✗'
        if actual != exp: all_pass = False
        print(f'  {ok} {key}: expected={exp}, actual={actual}')
    print(f'  {"ALL PASS" if all_pass else "*** FAILURES ***"}')
    return all_pass

def log(msg):
    print(f'[ALICE] {msg}')

# ============================================================
# Cleanup from previous runs
# ============================================================
run_id = str(int(time.time()))[-6:]  # unique per run
log(f'Run ID: {run_id}')

# Clean up previous test records — lines before headers, layers before items
InvoiceLine.objects.filter(invoice__ida__startswith='alice-inv').delete()
OrderLine.objects.filter(order__ida__startswith='alice-ord').delete()
PurchaseLine.objects.filter(purchase__ida__startswith='alice-po').delete()
ProposalLine.objects.filter(proposal__ida__startswith='alice-prop').delete()
Invoice.objects.filter(ida__startswith='alice-inv').delete()
Order.objects.filter(ida__startswith='alice-ord').delete()
Purchase.objects.filter(ida__startswith='alice-po').delete()
Proposal.objects.filter(ida__startswith='alice-prop').delete()
InventoryLayer.objects.filter(source__type='purchase').filter(source__id__isnull=False).delete()
Email.objects.filter(email__startswith='alice-testcycle').delete()
Phone.objects.filter(number='555-ALICE-01').delete()
Address.objects.filter(address1='123 Alice Test St').delete()
Customer.objects.filter(ida__startswith='alice-test-cycle').delete()
Contact.objects.filter(ida__startswith='alice-test-cycle').delete()
log('Cleaned up previous test records')

# Reset item 308
item_reset = Item.objects.get(pk=308)
item_reset.quantity = {'on_hand': 100, 'allocated': 0, 'available': 100, 'on_so': 0, 'on_po': 0, 'on_p': 0, 'on_in': 0, 'on_wo': 0}
item_reset.save(update_fields=['quantity'])
log('Item 308 reset: on_hand=100')

# ============================================================
# Phase 1: Customer + Contact + Communications
# ============================================================
log('Phase 1: Creating customer, contact, communications...')

now = now_ms()
test_email = f'alice-testcycle-{run_id}@example.com'

# Create contact
contact = Contact.objects.create(
    email=test_email,
    name_first='Alice Test',
    name_last='Cycle',
    role='user',
    ida='alice-test-cycle',
    dt_created=now,
    dt_modified=now,
)
log(f'Contact created: id={contact.pk}, email={contact.email}')

# Create customer
customer = Customer.objects.create(
    display_name='Alice Test Cycle Corp',
    status='active',
    org_type='customer',
    email=test_email,
    phone='555-ALICE-01',
    contact=contact,
    ida='alice-test-cycle-corp',
    dt_created=now,
    dt_modified=now,
)
log(f'Customer created: id={customer.pk}, display_name={customer.display_name}')

# Create communications
email_rec = Email.objects.create(
    contact=contact,
    email=test_email,
    name='Work Email',
    type='work',
    is_primary=True,
    dt_created=now,
    dt_modified=now,
)
log(f'Email created: id={email_rec.pk}, email={email_rec.email}, is_primary={email_rec.is_primary}')

phone_rec = Phone.objects.create(
    contact=contact,
    number='555-ALICE-01',
    country_code='+1',
    name='Office',
    dt_created=now,
    dt_modified=now,
)
log(f'Phone created: id={phone_rec.pk}, number={phone_rec.number}')

addr_rec = Address.objects.create(
    contact=contact,
    address1='123 Alice Test St',
    city='Testville',
    state='NC',
    zip='27601',
    country='US',
    address_type='shipping',
    full='123 Alice Test St, Testville, NC 27601',
    dt_created=now,
    dt_modified=now,
)
log(f'Address created: id={addr_rec.pk}, full={addr_rec.full}')

# ============================================================
# Phase 2: Proposal — 15 of Item 308
# ============================================================
log('Phase 2: Creating proposal for 15 of Item 308...')

item = Item.objects.get(pk=308)
unit_price = Decimal('25.00')

proposal = Proposal.objects.create(
    status='planned',
    customer=customer,
    contact=contact,
    attention=customer.display_name,
    email=customer.email,
    price_level='retail',
    total=unit_price * 15,
    ida='alice-prop-001',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)

prop_line = ProposalLine.objects.create(
    proposal=proposal,
    item_fk=item,
    line_number=1,
    quantity={'staged': 15, 'active': 15, 'remaining': 15},
    price={'unit': float(unit_price), 'extended': float(unit_price * 15)},
    status='planned',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)
log(f'Proposal created: id={proposal.pk}, total={proposal.total}, line qty=15')

# Update item.quantity.on_p += 15
item.refresh_from_db()
q = item.quantity or {}
q['on_p'] = q.get('on_p', 0) + 15
item.quantity = q
item.save(update_fields=['quantity', 'dt_modified'])

check_item('After Proposal (on_p +15)', {'on_hand': 100, 'on_po': 0, 'on_so': 0, 'on_p': 15})

# ============================================================
# Phase 3: Order — transfer 9 from proposal
# ============================================================
log('Phase 3: Creating order for 9 of Item 308 (from proposal)...')

order = Order.objects.create(
    status='planned',
    customer=customer,
    contact=contact,
    attention=customer.display_name,
    email=customer.email,
    price_level='retail',
    total=unit_price * 9,
    parent_id=proposal.pk,
    parent_model='proposal',
    ida='alice-ord-001',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)

ord_line = OrderLine.objects.create(
    order=order,
    item_fk=item,
    line_number=1,
    quantity={'staged': 9, 'active': 9, 'remaining': 9},
    price={'unit': float(unit_price), 'extended': float(unit_price * 9)},
    status='planned',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)
log(f'Order created: id={order.pk}, total={order.total}, line qty=9')

# Update item: on_p -= 9, on_so += 9
item.refresh_from_db()
q = item.quantity or {}
q['on_p'] = q.get('on_p', 0) - 9
q['on_so'] = q.get('on_so', 0) + 9
item.quantity = q
item.save(update_fields=['quantity', 'dt_modified'])

check_item('After Order (on_p -9, on_so +9)', {'on_hand': 100, 'on_po': 0, 'on_so': 9, 'on_p': 6})

# ============================================================
# Phase 4: Purchase Order — 6 of Item 308
# ============================================================
log('Phase 4: Creating PO for 6 of Item 308...')

# Get or create a vendor
vendor = Vendor.objects.filter(status='active').first()
if not vendor:
    vendor = Vendor.objects.create(
        display_name='Alice Test Vendor',
        status='active',
        org_type='vendor',
        ida='alice-test-vendor',
        dt_created=now_ms(),
        dt_modified=now_ms(),
    )

purchase = Purchase.objects.create(
    status='planned',
    vendor=vendor,
    attention=vendor.display_name,
    total=Decimal('12.00') * 6,
    ida='alice-po-001',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)

po_line = PurchaseLine.objects.create(
    purchase=purchase,
    item_fk=item,
    line_number=1,
    quantity={'staged': 6, 'active': 6, 'remaining': 6},
    cost={'unit': 12.00, 'extended': 72.00},
    status='planned',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)
log(f'PO created: id={purchase.pk}, total={purchase.total}, line qty=6')

# Update item: on_po += 6
item.refresh_from_db()
q = item.quantity or {}
q['on_po'] = q.get('on_po', 0) + 6
item.quantity = q
item.save(update_fields=['quantity', 'dt_modified'])

check_item('After PO (on_po +6)', {'on_hand': 100, 'on_po': 6, 'on_so': 9, 'on_p': 6})

# ============================================================
# Phase 5: Invoice — ship 6 from order
# ============================================================
log('Phase 5: Creating invoice for 6 of Item 308 (ship from order)...')

invoice = Invoice.objects.create(
    status='planned',
    customer=customer,
    contact=contact,
    attention=customer.display_name,
    email=customer.email,
    price_level='retail',
    total=unit_price * 6,
    balance=unit_price * 6,
    parent_id=order.pk,
    parent_model='order',
    ida='alice-inv-001',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)

inv_line = InvoiceLine.objects.create(
    invoice=invoice,
    item_fk=item,
    line_number=1,
    quantity={'staged': 6, 'active': 6, 'remaining': 0},
    price={'unit': float(unit_price), 'extended': float(unit_price * 6)},
    status='shipped',
    dt_created=now_ms(),
    dt_modified=now_ms(),
)
log(f'Invoice created: id={invoice.pk}, total={invoice.total}, line qty=6')

# Update item: on_hand -= 6, on_so -= 6
item.refresh_from_db()
q = item.quantity or {}
q['on_hand'] = q.get('on_hand', 0) - 6
q['on_so'] = q.get('on_so', 0) - 6
q['available'] = q.get('on_hand', 0)  # recalc
item.quantity = q
item.save(update_fields=['quantity', 'dt_modified'])

# Update order line remaining
ord_line.refresh_from_db()
oq = ord_line.quantity or {}
oq['remaining'] = 9 - 6
ord_line.quantity = oq
ord_line.save(update_fields=['quantity', 'dt_modified'])

check_item('After Invoice/Ship (on_hand -6, on_so -6)', {'on_hand': 94, 'on_po': 6, 'on_so': 3, 'on_p': 6})

# ============================================================
# Phase 6: PO Receiving — receive 4 of 6
# ============================================================
log('Phase 6: Receiving 4 of Item 308 on PO...')

# Create inventory layer
layer = InventoryLayer.objects.create(
    item_id=item.pk,
    warehouse_id=1,  # default warehouse
    quantity={'received': 4, 'issued': 0, 'scrapped': 0},
    cost={'unit_po': '12.00', 'landed': '12.00', 'currency': 'USD'},
    source={'type': 'purchase', 'id': purchase.pk},
    lot='',
    serial_numbers=[],
    is_locked=False,
    dt_created=now_ms(),
    dt_modified=now_ms(),
)
log(f'InventoryLayer created: id={layer.pk}, qty_received=4, cost=12.00')

# Update item: on_po -= 4, on_hand += 4
item.refresh_from_db()
q = item.quantity or {}
q['on_po'] = q.get('on_po', 0) - 4
q['on_hand'] = q.get('on_hand', 0) + 4
q['available'] = q.get('on_hand', 0)  # recalc
item.quantity = q
item.save(update_fields=['quantity', 'dt_modified'])

# Update PO line remaining
po_line.refresh_from_db()
pq = po_line.quantity or {}
pq['remaining'] = 6 - 4
po_line.quantity = pq
po_line.save(update_fields=['quantity', 'dt_modified'])

check_item('After PO Receive (on_po -4, on_hand +4)', {'on_hand': 98, 'on_po': 2, 'on_so': 3, 'on_p': 6})

# ============================================================
# Final Summary
# ============================================================
print('\n' + '='*60)
print('ALICE TEST SEQUENCE 001 — FINAL RESULTS')
print('='*60)

item.refresh_from_db()
q = item.quantity or {}
print(f'''
Item 308 Final State:
  on_hand:    {q.get("on_hand", "?")}  (expected: 98 = 100 - 6 + 4)
  on_po:      {q.get("on_po", "?")}  (expected: 2 = 0 + 6 - 4)
  on_so:      {q.get("on_so", "?")}  (expected: 3 = 0 + 9 - 6)
  on_p:       {q.get("on_p", "?")}  (expected: 6 = 0 + 15 - 9)
  available:  {q.get("available", "?")}  (expected: 98)

Records Created:
  Customer:  {customer.pk} ({customer.display_name})
  Contact:   {contact.pk} ({contact.email})
  Email:     {email_rec.pk}
  Phone:     {phone_rec.pk}
  Address:   {addr_rec.pk}
  Proposal:  {proposal.pk} (ida={proposal.ida})
  Order:     {order.pk} (ida={order.ida})
  PO:        {purchase.pk} (ida={purchase.ida})
  Invoice:   {invoice.pk} (ida={invoice.ida})
  Inv Layer: {layer.pk}
''')

# Compare expected vs actual
expected = {'on_hand': 98, 'on_po': 2, 'on_so': 3, 'on_p': 6, 'available': 98}
all_pass = all(q.get(k, 0) == v for k, v in expected.items())
print(f'OVERALL: {"ALL PASS ✓" if all_pass else "FAILURES ✗"}')
