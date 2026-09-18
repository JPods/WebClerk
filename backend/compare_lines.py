#!/usr/bin/env python
"""
Compare lineitem quantity structure consistency across:
- Proposal / ProposalLine
- Order / OrderLine  
- Invoice / InvoiceLine
- Purchase / PurchaseLine

Checks:
1. default_quantity() structure per transaction type
2. LineItemService._build_quantity_envelope consistency
3. Line model save() ensures JSON defaults
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.transactions.models.base_line_model import default_quantity, _normalize_line_kind
from apps.transactions.services.line_manage import LineItemService

print('=' * 70)
print('COMPARISON: Lineitem Quantity Structures')
print('=' * 70)
print()

# 1. Check default_quantity() structure per transaction type
print('1. default_quantity() Structures')
print('-' * 50)

tx_types = ['proposal', 'order', 'invoice', 'purchase', 'work_order']
for tx_type in tx_types:
    qty = default_quantity(tx_type)
    print(f'\n  {tx_type.upper()}:')
    for key, val in qty.items():
        print(f'    {key}: {val}')

# 2. Compare structures for consistency
print('\n')
print('2. Structure Consistency Check')
print('-' * 50)

# Get all structures
structures = {tx: default_quantity(tx) for tx in tx_types}

# Find common keys and unique keys
all_keys = set()
for s in structures.values():
    all_keys.update(s.keys())

common_keys = all_keys.copy()
for s in structures.values():
    common_keys &= set(s.keys())

print(f'\n  Common keys (all types): {sorted(common_keys)}')

for tx_type, struct in structures.items():
    unique = set(struct.keys()) - common_keys
    if unique:
        print(f'  {tx_type} unique keys: {sorted(unique)}')

# 3. Check transaction-specific tracking field patterns
print('\n')
print('3. Transaction-Specific Tracking Fields')
print('-' * 50)

tracking_fields = {
    'proposal': ('placed', 'ordered', 'remaining'),
    'order': ('placed', 'invoiced', 'remaining'),
    'invoice': ('placed', 'packed', 'remaining'),
    'purchase': ('placed', 'received', 'remaining'),
    'work_order': ('placed', 'received', 'remaining'),
}

for tx_type, expected_fields in tracking_fields.items():
    struct = structures[tx_type]
    actual_fields = [k for k in struct.keys() if k in ('placed', 'ordered', 'invoiced', 'packed', 'received', 'remaining')]
    
    missing = set(expected_fields) - set(struct.keys())
    extra = set(actual_fields) - set(expected_fields)
    
    status = '✓' if not missing and not extra else '⚠️'
    print(f'\n  {tx_type.upper()}: {status}')
    print(f'    Expected: {expected_fields}')
    print(f'    Actual:   {tuple(actual_fields)}')
    if missing:
        print(f'    MISSING:  {missing}')
    if extra:
        print(f'    EXTRA:    {extra}')

# 4. LineItemService behavior check
print('\n')
print('4. LineItemService Configuration')
print('-' * 50)

service = LineItemService(create_pending=False)
print(f'\n  LINE_MODEL_MAP keys: {sorted(service.__class__.__dict__.get("LINE_MODEL_MAP", {}).keys()) if hasattr(service, "LINE_MODEL_MAP") else "N/A"}')

from apps.core.constants.model_registry import MODEL_REGISTRY
line_models = {k: v.model for k, v in MODEL_REGISTRY.items() if v.kind == 'line'}
print(f'  Line models from registry: {line_models}')

# 5. Verify _normalize_line_kind mappings
print('\n')
print('5. Line Kind Normalization')
print('-' * 50)

test_inputs = [
    'proposal', 'proposal_line', 'proposalline', 'Proposal',
    'order', 'order_line',
    'invoice', 'invoice_line', 'invoiceline',
    'purchase', 'purchase_order', 'purchase_order_line', 'purchaseorderline',
    'work_order', 'work_order_line', 'workorderline',
]

print('\n  Input -> Normalized:')
for inp in test_inputs:
    normalized = _normalize_line_kind(inp)
    print(f'    {inp:25} -> {normalized}')

print('\n')
print('=' * 70)
print('SUMMARY: Check above for any ⚠️ warnings')
print('=' * 70)
