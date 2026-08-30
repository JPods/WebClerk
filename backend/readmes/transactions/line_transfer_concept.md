Now lets get the transfer between transactions working

## Save Flow for All Transfers

Every transfer follows the unified save architecture via `POST /wcapi/transaction/save/`.

### Collect-then-Create Pattern (2026-02-21)

```
POST /wcapi/transaction/save/  →  save_transaction_with_lines():
  Phase 1: atomic { save header → save lines (signals suppressed) → collect deltas }
  Phase 2: _create_pending_from_deltas() — one Pending per new line
  Phase 3: update source lines (transfer only)
  Phase 4: single dispatch_pending_processing()
```

**Key rules:**
- **Backend is authoritative** — pending type, transfer detection, and quantity buckets derived server-side
- Lines saved with `_pending_created = True` to suppress `post_save` signal
- Exactly ONE pending record per line — `(invoice_line_id, order_line_id)` pair is stored and duplicates are forbidden
- For transfers (e.g. order→invoice), one Pending captures both the add and the release (`on_in=+qty, on_so=-qty, on_hand=-qty`)
- Celery only **applies** pending deltas to `Item.quantity` — it does not create them
- One dispatch signal after all pending records exist, not per-line

---

## Proposal to Proposal

In a flow from proposal to proposal
1. a null id proposal is created
2. Customer information is not populated from the proposal, price_level is set to "retail"
3. Lines are copied with 
	proposal_line.quantity.staged = proposal_line.quantity.staged
	proposal_line.quantity.active = proposal_line.quantity.staged
	proposal_line.quantity.remaining = proposal_line.quantity.staged

When the customer is selected, the appropriate price_level will be set and the lines recalculate.

**Pending:** One pending per new proposal line (type_id=PP, on_p += staged). No parent-side pending since this is a copy, not a transfer.

---

## Proposal to Order or Invoice

From proposal to order or invoice.
1. a null id order or invoice is created
2. parent_model and parent_id is set.
2. Customer information is populated from the proposal to the order.
3. Line-Items that are copied into order lines.
	Line data is transferred to such as .refs.links.document[], contact, action,....
	Line data having to do with dates are reset
	if quantity.increment = 0;
		order_line.quantity.staged = proposal.quantity.remaining
		order_line.quantity.active = proposal.quantity.remaining
	else;
	If (proposal.quantity.increment < proposal.quantity.remaining) 
		order_line.quantity.staged = proposal.quantity.increment
		order_line.quantity.active = proposal.quantity.increment
	 else
		order_line.quantity.staged = proposal.quantity.remaining
		order_line.quantity.active = proposal.quantity.remaining

	Source proposal line update (children_active tracker):
		children_active.lines.append({"id": order_line.pk, "active": transfer_qty})
		children_active.sum = sum of all children active
		proposal_line.quantity.remaining = proposal_line.quantity.active - children_active.sum

**Pending (inside atomic block):**
1. Child pending: type_id=SO (or IN), on_so += order_line.quantity.staged
2. Parent pending: type_id=PP, on_p -= quantity transferred (proposal transferred)
3. Both pending records saved in current worker; Celery applies after delay

---

## Cross-Type Transfers (Purchase ↔ Sell-Side)
		
In a flow from proposal to purchase, or order to purchase, or invoice to purchase, or purchase to proposal,  or purchase to order, or purchase to invoice
1. a null id purchase is created
2. Customer information is not populated from the proposal, Vendor information will be entered or the reverse from purchase
3. Lines are copied with to (receiving_line is receiving information, original_line is providing information)
	receiving_line.quantity.staged = original_line.quantity.staged
	receiving_line.quantity.active = original_line.quantity.staged
	receiving_line.quantity.remaining = original_line.quantity.staged

**Pending (inside atomic block):**
1. Child pending: type_id matching the new transaction (PO, SO, IN, PP, etc.)
2. Parent pending: delta on the originating line's bucket
3. Saved together in the same atomic block
	
	