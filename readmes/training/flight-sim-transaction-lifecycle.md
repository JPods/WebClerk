# Flight Simulator: Transaction Lifecycle

**Purpose:** Every new user runs this once. Two screens open side by side.

**Screen 1:** Transaction processing (proposal, order, invoice, etc.)
**Screen 2:** Console - db.list collection showing:
- Item record: qqbb200 quantity fields (on_hand, on_po, on_so, available, committed)
- Each transaction as it's created
- Each pending record as it appears and resolves
- GL entries after processing

The console shows quantity at every step, TWICE:
1. After the transaction is saved (pending record exists but hasn't applied)
2. After the pending record applies (quantity changes)

This teaches what pending records do. The gap between "I saved the transaction"
and "the quantity changed" is where understanding lives.

---

## Setup

- Item: qqbb200
- Starting quantity: on_hand=0, on_po=0, on_so=0, available=0
- Console screen showing item.quantity fields in real-time

---

## Step 1: Create Proposal for 15

**Action:** New proposal, add 15x qqbb200, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | 0 |
| on_po | 0 | 0 | 0 |
| on_so | 0 | 0 | 0 |
| available | 0 | 0 | 0 |

**Console shows:** Proposal record appears. No pending record - proposals don't move inventory.
**Lesson:** Proposals are intentions. Nothing moves until conversion.

---

## Step 2: Convert Proposal to Order for 11 (4 remain on proposal)

**Action:** Convert proposal, quantity=11, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | 0 |
| on_po | 0 | 0 | 0 |
| on_so | 0 | 0 | **11** |
| available | 0 | 0 | **-11** |

**Console shows:** Order record appears. Pending record appears (staged). Pending applies - on_so jumps to 11.
**Lesson:** Converting creates the order AND a pending record. The pending record is what moves on_so. Available goes negative - we owe 11 we don't have.
**Also notice:** Proposal still exists with qty=4. Orphaned partials are real.

---

## Step 3: Post Order to Purchase for 11

**Action:** Post order to purchase, quantity=11, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | 0 |
| on_po | 0 | 0 | **11** |
| on_so | 11 | 11 | 11 |
| available | -11 | -11 | **0** |

**Console shows:** Purchase record appears. Pending record stages, then applies. on_po jumps to 11. Available returns to 0 (11 on_po covers 11 on_so).
**Lesson:** Purchasing doesn't give us inventory. It gives us a promise (on_po). Available improves because the promise offsets the commitment.

---

## Step 4: Receive 9 (2 remain on PO)

**Action:** Receive against purchase, quantity=9, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 0 | 0 | **9** |
| on_po | 11 | 11 | **2** |
| on_so | 11 | 11 | 11 |
| available | 0 | 0 | **0** |

**Console shows:** Receipt record appears. Pending stages. Pending applies - on_hand jumps to 9, on_po drops to 2.
**Lesson:** Receiving converts a promise (on_po) into reality (on_hand). We received 9 of the 11 promised. 2 still on_po. Available stays 0: we have 9 in hand + 2 promised = 11, committed 11 on_so.

---

## Step 5: Convert Order to Invoice for 7 (4 remain on SO)

**Action:** Convert order to invoice, quantity=7, save

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 9 | 9 | **2** |
| on_po | 2 | 2 | 2 |
| on_so | 11 | 11 | **4** |
| available | 0 | 0 | **0** |

**Console shows:** Invoice record appears. Pending stages. Pending applies - on_hand drops by 7 (shipped), on_so drops by 7 (fulfilled).
**Lesson:** Invoicing means we shipped the goods. on_hand decreases, on_so decreases. We still owe 4 on the sales order. Available stays 0: 2 in hand + 2 on_po = 4, which matches the 4 still on_so.

---

## Step 6: Pay Invoice with 2% discount and $0.50 write-off

**Action:** Create payment against invoice. Apply 2% early-pay discount. Write off $0.50 as too-trivial-to-collect.

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 2 | 2 | 2 |
| on_po | 2 | 2 | 2 |
| on_so | 4 | 4 | 4 |
| available | 0 | 0 | 0 |

**Console shows:** Payment record appears. Invoice balance goes to 0. Pending record stages payment application. AR ledger: payment amount + discount + write-off = invoice total.
**Lesson:** Payment doesn't touch inventory. It closes the money side. The discount and write-off are separate GL entries - not price changes. The invoice total doesn't change; the payment just has three components.

---

## Step 7: Process GLs

**Action:** Run GL processing

**Console shows:** GL journal entries appear:
- AR debit (from invoice, step 5)
- Revenue credit (from invoice)
- Cash debit (from payment, step 6)
- AR credit (from payment)
- Discount expense debit
- Write-off expense debit

**Lesson:** GL is the accounting record of everything that already happened. It doesn't move inventory or change balances - it records them. Every transaction that touches money has a GL consequence. The discount and write-off get their own expense accounts.

---

## Step 8: Customer Returns 1

**Action:** Create credit memo for 1x qqbb200. Customer returns the item.

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 2 | 2 | **3** |
| on_po | 2 | 2 | 2 |
| on_so | 4 | 4 | 4 |
| available | 0 | 0 | **1** |

**Console shows:** Credit memo record appears. Pending stages return. on_hand increases by 1 (goods came back). AR ledger: credit memo reduces customer balance.
**Lesson:** Returns run the flow backwards. Quantity goes up, money reverses. Same pending mechanism, opposite direction.

---

## Step 9: Scrap the Returned Item

**Action:** Write off / scrap 1x qqbb200. The returned unit is damaged and cannot be resold.

| Field | Before | After save | After pending |
|-------|--------|-----------|---------------|
| on_hand | 3 | 3 | **2** |
| on_po | 2 | 2 | 2 |
| on_so | 4 | 4 | 4 |
| available | 1 | 1 | **0** |

**Console shows:** Inventory adjustment record. Pending stages the write-off. on_hand drops by 1. GL: inventory asset credit, scrap/loss expense debit.
**Lesson:** Scrapping removes inventory permanently. The cost of the item moves from asset (inventory) to expense (loss). The item came back from the customer but it's worthless - the system needs to record both the return AND the disposal as separate events. One is a customer transaction, the other is an internal decision.

---

## Step 10: Refund the Customer

**Action:** Issue refund payment against the credit memo from Step 8.

**Console shows:** Payment record (outbound). Credit memo balance goes to 0. Cash decreases, AR decreases (or goes negative then zeroes). GL: cash credit, AR debit.
**Lesson:** The refund is a payment in reverse - money goes out instead of in. The credit memo is the authority for the refund, just as the invoice was the authority for the original payment. No credit memo = no refund. The audit trail is: return -> credit memo -> refund payment -> GL.

---

## Step 11: Deal with the Orphans

**Action:** Find and cancel the 4 remaining on the original proposal. Find and close the 4 remaining on the sales order. Find and close the 2 remaining on the purchase order.

| Field | Before | After cleanup | 
|-------|--------|--------------|
| on_hand | 2 | 2 |
| on_po | 2 | **0** |
| on_so | 4 | **0** |
| available | 0 | **2** |

**Lesson:** Partial conversions leave orphans. Every open quantity on a transaction is a promise someone needs to keep or explicitly cancel. Closing the orphans releases on_po and on_so back to available. The system doesn't clean these up automatically - that's a business decision, not a system decision. After cleanup, on_hand=2 and available=2 - clean books.

---

## What the Console Screen Shows

A db.list collection view pulling from multiple models simultaneously:

| Section | Model | Key Fields |
|---------|-------|-----------|
| **Item** | item | ida, on_hand, on_po, on_so, available, committed |
| **Transactions** | proposal, order, purchase, receipt, invoice, payment | ida, status, qty, total, balance |
| **Pending** | pending | model_name, status, qty, staged/applied |
| **GL** | ledger | account, debit, credit, source |

Each section updates live as the user works on Screen 1.

---

## Key Takeaways

1. **Proposals don't move anything** - they're intentions
2. **Pending records are the mechanism** - the gap between "saved" and "applied" is where the system works
3. **on_po is a promise, on_hand is reality** - receiving converts one to the other
4. **Invoicing means shipped** - on_hand goes down, on_so goes down
5. **Payment doesn't touch inventory** - it closes the money side only
6. **GL records, it doesn't cause** - journal entries document what already happened
7. **Partial conversions leave orphans** - someone has to deal with them
8. **Returns run backwards** - same pending mechanism, opposite direction
9. **Return and scrap are two events** - return is a customer transaction, scrap is an internal decision. Separate authorities, separate GL entries
10. **Refunds require a credit memo** - no credit memo, no refund. The audit trail is complete
11. **Clean up orphans to clean the books** - canceling orphaned partials releases on_po and on_so back to available
8. **Returns run backwards** - same pending mechanism, opposite direction
