# WC3 Item ID Validation - Implementation Required

> **Status**: ✅ IMPLEMENTED  
> **Updated**: 2026-01-14  
> **Related**: [transaction-calculations.md](./transaction-calculations.md#backend-sync)

---

## Summary

**WC3 has been updated to match the documentation in transaction-calculations.md.**

The `item_id` immutability validation is now implemented as a security backstop in `BaseLineSerializer.validate()`.

---

## What's Documented (transaction-calculations.md)

```
⚠️ Item ID Immutability:
- R25 responsibility: UI prevents users from changing item_id on existing lines
- WC3 safeguard: Backend validates that item_id hasn't changed for any existing line id.
  If violated, rejects the entire save with: "Item_id cannot be changed for any line"
```

---

## Current WC3 State

| File | What's There | item_id Check? |
|------|-------------|----------------|
| `apps/transactions/serializers/line_serializers.py` | `BaseLineSerializer.validate()` - role-based field editing + item_id immutability | ✅ Yes |
| `apps/transactions/services/validation.py` | Flow validations (proposal→order, etc.) | N/A |
| `apps/core/services/wcapi.py` | `save_item()` for WCAPI saves | N/A |

---

## Implementation (Completed)

Added validation to `BaseLineSerializer.validate()` in `line_serializers.py`:

```python
def validate(self, attrs):
    request = self.context.get('request')
    
    # Existing role-based validation...
    
    # NEW: Prevent item_id changes on existing lines
    if self.instance is not None:  # This is an UPDATE
        current_item_id = getattr(self.instance, 'item_id', None)
        new_item_id = attrs.get('item_id') or attrs.get('item', {}).get('item_id')
        
        if new_item_id is not None and new_item_id != current_item_id:
            raise serializers.ValidationError({
                'item_id': 'Item_id cannot be changed for any line. To change the item, please delete this line and add a new line with the correct item.'
            })
    
    return attrs
```

---

## Why This Matters

1. **Defense in Depth**: R25 UI is the primary defense (read-only item fields on saved lines), but malicious API calls could bypass the UI
2. **Data Integrity**: Changing `item_id` on an existing line breaks audit trails and can corrupt linked data (inventory, accounting)
3. **Purchase Orders**: Particularly critical for POs where item changes could affect vendor negotiations and receiving

---

## Testing Checklist

Once implemented, verify:

- [ ] Creating a new line with any `item_id` succeeds
- [ ] Updating an existing line WITHOUT changing `item_id` succeeds
- [ ] Updating an existing line WITH a changed `item_id` returns 400 error
- [ ] Error message matches: `"Item_id cannot be changed for any line..."`
- [ ] Works for all line types: ProposalLine, OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine, RequisitionLine

---

## Changelog

| Date | Status | Notes |
|------|--------|-------|
| 2026-01-14 | Documented | Investigation confirmed validation was missing |
| 2026-01-14 | ✅ Implemented | Added to `BaseLineSerializer.validate()` in `line_serializers.py` |
