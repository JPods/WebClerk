# Shared Behaviors — One Source of Truth Per Validation

## The Problem

Multiple models share the same behaviors: assign a contact, validate a status
transition, denormalize display fields into refs.links. When each serializer
implements these inline, the logic drifts. One gets updated, the others don't.
Worse — some bypass the centralized service entirely (scar: Proposal and Order
serializers had hardcoded status lists that skipped the approval gate).

## The Pattern

**Standalone validator functions** in a `behaviors.py` module. Serializers call
them — they never implement the logic inline. The serializer stays thin.

```python
# serializers/behaviors.py
def validate_customer_id(value):
    """Works for any model that assigns a customer."""
    ...

# serializers/proposal_serializer.py
class ProposalSerializer(...):
    def validate_customer_id(self, value):
        return validate_customer_id(value)  # one line, calls the behavior
```

## The Mechanism: refs.links

`refs.links` is the universal relationship cache. Two distinct write patterns:

1. **Org snapshot** — `denormalize_org_links.py` copies display fields
   (display_name, address, email, phone) from OrgBase into
   `refs.links.customer`, `refs.links.vendor`, etc.

2. **ID lists** — signals append record IDs to `refs.links.order_line[]`,
   `refs.links.invoice_line[]`, etc.

Both patterns should validate and populate through the same behaviors module.

## Where This Applies

### Transaction ↔ Customer/Vendor (implemented)
```
behaviors.py: validate_customer_id, validate_vendor_id,
              validate_customer_vendor_different,
              validate_status_transition
```
Used by: Proposal, Order, Invoice, Purchase, WorkOrder serializers.

### Contact ↔ Org (same pattern, not yet implemented)
A Contact links to one or more Orgs (Customer, Vendor, Rep). The behaviors:
- Validate org exists and is active
- Denormalize org display fields into contact.refs.links
- Validate role assignment (a contact can be customer + vendor but not
  duplicate roles on the same org)

### Communication ↔ Contact (same pattern)
Address, Email, Phone link to a Contact. The behaviors:
- Validate contact exists
- Normalize the communication data (phone format, address standardize)
- Update contact.refs.links with communication summary

### Action ↔ Contact + Project (same pattern)
An Action links to both a Contact (who) and a Project (what). The behaviors:
- Validate contact and project exist
- Denormalize display names into action.refs.links
- Same status transition validation via service

### Touch ↔ Contact (same pattern)
A Touch records an interaction with a Contact. The behaviors:
- Validate contact exists
- Link to related Action if applicable
- Update contact.refs.links with latest touch data

### Document (same pattern)
Documents link to parent records (any model). The behaviors:
- Validate parent record exists
- Status transitions (draft → active → archived)
- refs.links to parent record

## Behavioral Inventory

| Behavior | Service (exists) | Serializer behavior (status) |
|----------|-----------------|------------------------------|
| Assign customer/vendor | `customer_defaults.py`, `denormalize_org_links.py` | `behaviors.py` — implemented |
| Validate status | `validate_status.py` | `behaviors.py` — implemented |
| Compute totals | `totals_compute.py` + signals | Centralized — no serializer logic needed |
| Apply tax | `tax_resolve.py` + `totals_compute.py` | Centralized — no serializer logic needed |
| Commission | `commission_compute.py` | Centralized — no serializer logic needed |
| Line management | `line_manage.py` + `base_line_serializer.py` | Centralized — `BaseLineSerializer` |
| Contact denormalization | `denormalize_org_links.py` | Service-level — no serializer behavior yet |
| Communication normalization | `format_phone.py`, `format_address.py` | Should move to behaviors pattern |
| Action/Touch contact linking | `action_links.py` | Should move to behaviors pattern |
| Document parent linking | — | Should create behaviors pattern |

## Rules

1. **Never hardcode allowed values in a serializer** — call the service.
2. **Never duplicate validation across serializers** — extract to behaviors.py.
3. **refs.links is the only place for denormalized relationship data** —
   never store display names on scalar fields.
4. **Behaviors are functions, not mixins** — no method resolution order issues,
   testable in isolation, composable.
5. **The serializer is thin** — it validates input, calls behaviors, calls services.
   Business logic lives in services. Validation logic lives in behaviors.
