#!/usr/bin/env python
"""
Backfill Item.quantity.on_p from existing active proposals.

Run with: python manage.py shell < tools/backfill_on_p.py
"""

from decimal import Decimal
from django.db import transaction
from apps.transactions.models import Proposal, ProposalLine
from apps.products.models import Item

print("=== Backfilling Item.quantity.on_p from active proposals ===")
print()

# Get all active proposals with their lines
active_proposals = Proposal.objects.filter(
    is_active=True,
    status__in=['planned', 'released', 'in_progress']
).prefetch_related('lines')

print(f"Found {active_proposals.count()} active proposals")

# Aggregate quantities by item_id
item_qty_map = {}  # item_id -> total qty on proposals

for proposal in active_proposals:
    # Get probability from proposal (default 100% if not set)
    probability = 1.0
    prob_raw = getattr(proposal, 'probability', None)
    if prob_raw is None and hasattr(proposal, 'metadata') and isinstance(proposal.metadata, dict):
        prob_raw = proposal.metadata.get('probability')
    if prob_raw is not None:
        try:
            probability = float(prob_raw) / 100.0 if float(prob_raw) > 1.0 else float(prob_raw)
        except (TypeError, ValueError):
            probability = 1.0
    
    for line in proposal.lines.all():
        if not isinstance(line.item, dict):
            continue
        item_id = line.item.get('item_id')
        if not item_id:
            continue
        
        # Get placed quantity
        qty_placed = 0
        if isinstance(line.quantity, dict):
            qty_placed = float(line.quantity.get('placed', 0) or 0)
        
        # Calculate on_p contribution (qty * probability)
        on_p_contribution = qty_placed * probability
        
        if item_id not in item_qty_map:
            item_qty_map[item_id] = Decimal('0')
        item_qty_map[item_id] += Decimal(str(on_p_contribution))
        
        print(f"  Proposal #{proposal.pk}, Line {line.pk}: item_id={item_id}, qty={qty_placed}, prob={probability:.0%} -> on_p +{on_p_contribution}")

print()
print(f"Items to update: {len(item_qty_map)}")

# Update items
updated_count = 0
for item_id, total_on_p in item_qty_map.items():
    try:
        item = Item.objects.get(pk=item_id)
        quantity = item.quantity or {}
        old_on_p = quantity.get('on_p', 0)
        quantity['on_p'] = float(total_on_p)
        
        # Use .update() to avoid triggering full save hooks
        Item.objects.filter(pk=item_id).update(quantity=quantity)
        
        print(f"  Item {item_id} ({item.name[:30]}): on_p {old_on_p} -> {float(total_on_p)}")
        updated_count += 1
    except Item.DoesNotExist:
        print(f"  Item {item_id}: NOT FOUND - skipping")

print()
print(f"=== Done! Updated {updated_count} items ===")
