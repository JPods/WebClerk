#!/usr/bin/env python
"""
Repair children_active on parent transaction lines.

Scans child transactions (Order→Proposal, Invoice→Order) and rebuilds
the parent's children_active tracker from actual child data.

Usage:
    python check_chain.py          # Dry-run: show what would change
    python check_chain.py --fix    # Apply fixes
"""
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
)

DRY_RUN = '--fix' not in sys.argv


def rebuild_children_active(ParentModel, ParentLineModel, ChildModel, ChildLineModel,
                             parent_fk, child_header_fk, parent_model_name):
    """Rebuild children_active on parent lines from actual child line data."""
    fixes = 0
    # Find all child transactions that have this parent type
    children = ChildModel.objects.filter(parent_model=parent_model_name).select_related()
    
    # Group child lines by parent line id
    parent_line_children = {}  # {parent_line_pk: [{'id': child_line_pk, 'active': qty}, ...]}
    
    for child in children:
        child_lines = ChildLineModel.objects.filter(**{child_header_fk: child.pk})
        for cl in child_lines:
            refs = cl.refs or {}
            source = refs.get('source', {})
            parent_line_id = source.get(f'{parent_model_name}_line_id')
            if not parent_line_id:
                continue
            q = cl.quantity or {}
            active = float(q.get('active', 0) or 0)
            if parent_line_id not in parent_line_children:
                parent_line_children[parent_line_id] = []
            parent_line_children[parent_line_id].append({
                'id': cl.pk,
                'active': active,
                'child_header': child.pk,
            })
    
    for pl_id, child_entries in parent_line_children.items():
        try:
            pl = ParentLineModel.objects.get(pk=pl_id)
        except ParentLineModel.DoesNotExist:
            print(f"  WARNING: Parent line {parent_model_name}line #{pl_id} not found")
            continue
        
        q = dict(pl.quantity or {})
        old_remaining = q.get('remaining', '?')
        old_ca = q.get('children_active', None)
        
        # Build correct children_active
        lines_list = [{'id': c['id'], 'active': c['active']} for c in child_entries]
        children_sum = sum(c['active'] for c in lines_list)
        new_children_active = {'sum': children_sum, 'lines': lines_list}
        
        active = float(q.get('active', 0) or 0)
        new_remaining = max(0.0, active - children_sum)
        
        needs_fix = (old_ca != new_children_active or float(old_remaining or 0) != new_remaining)
        
        if needs_fix:
            child_desc = ', '.join(f'cl#{c["id"]}={c["active"]}' for c in child_entries)
            print(f"  {parent_model_name}line #{pl_id}: active={active}, "
                  f"remaining {old_remaining} → {new_remaining}, "
                  f"children=[{child_desc}]")
            
            if not DRY_RUN:
                q['children_active'] = new_children_active
                q['remaining'] = new_remaining
                pl.quantity = q
                pl._pending_created = True
                pl.save(update_fields=['quantity', 'dt_modified', 'version'])
                print(f"    FIXED ✓")
            else:
                print(f"    (dry run, use --fix to apply)")
            fixes += 1
    
    return fixes


if __name__ == '__main__':
    mode = "DRY RUN" if DRY_RUN else "FIXING"
    print(f"\n=== Rebuild children_active ({mode}) ===\n")
    
    print("--- Orders → Proposal lines ---")
    f1 = rebuild_children_active(
        Proposal, ProposalLine, Order, OrderLine,
        'proposal', 'order', 'proposal')
    
    print("\n--- Invoices → Order lines ---")
    f2 = rebuild_children_active(
        Order, OrderLine, Invoice, InvoiceLine,
        'order', 'invoice', 'order')
    
    total = f1 + f2
    if total == 0:
        print("\nAll parent lines are correct — nothing to fix.")
    else:
        print(f"\n{'Would fix' if DRY_RUN else 'Fixed'} {total} parent lines.")
        if DRY_RUN:
            print("Run with --fix to apply changes.")

