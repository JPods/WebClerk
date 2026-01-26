"""
Test script: Create a Proposal with traced items.

Run with: python manage.py shell < tools/test_proposal_trace.py
Or:       python manage.py runscript tools.test_proposal_trace
"""

from apps.transactions.services.trace_debug import enable_trace, disable_trace
from apps.transactions.services import LineItemService
from apps.transactions.models import Proposal
from apps.products.models import Item
from apps.core.models import Pending

# Enable tracing for our test items
print("\n" + "="*70)
print("  PROPOSAL TEST - Items 249, 250, 251")
print("="*70)

log_path = enable_trace([249, 250, 251])

# Check current item status before
print("\n--- BEFORE: Item Status ---")
for item_id in [249, 250, 251]:
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.ida}): {item.quantity_display}")

# Create a new proposal
proposal = Proposal.objects.create(
    ida="TEST-PROP-001",
    name="Test Proposal for Trace",
)
print(f"\n--- Created Proposal #{proposal.pk} ({proposal.ida}) ---")

# Add items using LineItemService
service = LineItemService()

print("\n--- Adding Items to Proposal ---")
line1 = service.add_item_to_transaction(proposal, item_id=249, quantity=5)
print(f"  Added line {line1.pk}: Item 249, qty=5")

line2 = service.add_item_to_transaction(proposal, item_id=250, quantity=10)
print(f"  Added line {line2.pk}: Item 250, qty=10")

line3 = service.add_item_to_transaction(proposal, item_id=251, quantity=3)
print(f"  Added line {line3.pk}: Item 251, qty=3")

# Check item status after (proposals should NOT affect inventory)
print("\n--- AFTER: Item Status ---")
for item_id in [249, 250, 251]:
    item = Item.objects.get(pk=item_id)
    print(f"  Item #{item_id} ({item.ida}): {item.quantity_display}")

# Check for pending records
pending_count = Pending.objects.filter(
    model_name="item",
    record_id__in=["249", "250", "251"],
    dt_processed=0
).count()
print(f"\nUnprocessed pending records: {pending_count}")
print("(Should be 0 - proposals do NOT create pending inventory records)")

disable_trace()
print(f"\nLog saved to: {log_path}")
print("="*70 + "\n")
