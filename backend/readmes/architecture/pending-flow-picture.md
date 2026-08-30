# Pending Records — The Flow Picture

**Established:** 2026-07-25
**Relates to:** pending-compensating-transactions.md, terms-ledgers.md

---

## The Principle

Pending records paint a picture of flows. Users keep them for a long time because they show the history of how money and inventory moved through the business. They are not temporary queue items to be discarded after processing — they are the narrative of the business.

---

## Three Parallel Flows, Same Pattern

| Flow | Model | What it stages | Direction |
|------|-------|---------------|-----------|
| **Money in** | Ledger | Invoice posted, payment applied, discount taken | AR (model_name = invoice) |
| **Money out** | Ledger | Purchase committed, payment made, credit received | AP (model_name = purchase) |
| **Inventory in** | Inventory Pending | Goods received, returned from customer, transferred in | Receipt, return, transfer |
| **Inventory out** | Inventory Pending | Goods shipped, allocated to order, transferred out | Ship, reserve, transfer |
| **Cash application** | Payment Pending | Cash allocated across invoices | Payment → invoice mapping |

### The Rule

> **Never a record lock without a dangling pending.**

If a record is locked, there MUST be a pending record explaining why:
- Why is it locked?
- Who locked it?
- What is it waiting for?
- What happens if it times out?

No orphan locks. The pending record IS the explanation.

---

## AR vs AP on Ledger

No separate `ledger_type` field. The `model_name` discriminates:

| model_name | Direction | Meaning |
|------------|-----------|---------|
| `invoice` | **AR** | Customer owes you |
| `purchase` | **AP** | You owe vendor |
| `adjustment` | Either | Manual entry — `source` field says 'ar' or 'ap' |

The `org_id` tells you who. The `gl_account_id` tells you which GL account. The direction is inherent in the transaction type.

---

## Why Users Keep Pending Records

In WC2, users kept pending records for months or years. They were not trash to clean up — they were the story of the business:

1. **Cash application history** — which payments were applied to which invoices, when, by whom. Auditors need this. Customers dispute this. The pending chain is the evidence.

2. **Inventory movement history** — what moved where, when, triggered by what transaction. Shrinkage investigation starts with pending records. Cycle count variance traces back to pending.

3. **Term schedule history** — Net 30 split into three installments, first two paid on time, third 15 days late with discount lost. The pending/ledger chain shows the whole story.

4. **Lock contention history** — two users tried to edit the same invoice. One got the lock. The other's intent was captured in pending. Both are visible. No lost work.

---

## Pending as Audit Trail

Every pending record has:

| Field | Purpose |
|-------|---------|
| `purpose` | Machine-readable intent (inventory_line_add, ledger_sync, payment_apply) |
| `name` | Human-readable description |
| `data` | JSON payload — everything needed to replay the action |
| `dt_processed` | 0 = still waiting, >0 = when it completed |
| `model_name` | What type of record it affects |
| `record_id` | Which specific record |

The processed pending record is not garbage. It is the receipt that says "this happened, here's when, here's what."

---

## The Flow Picture

```
Customer places order
    │
    ├── Inventory Pending: reserve on_so for each line item
    │       (Item locked until order ships or cancels)
    │
    ├── Proposal converted to Order (conversion pending)
    │
Order ships
    │
    ├── Inventory Pending: move on_so → on_hand → shipped
    │       (Item lock released)
    │
    ├── Order → Invoice (conversion pending)
    │
Invoice posted
    │
    ├── Ledger record(s) created from payment terms
    │       (AR — model_name = 'invoice')
    │
    ├── Ledger Sync Pending: update org balance
    │       (Org locked until sync confirms)
    │
Customer pays (partial)
    │
    ├── Payment Pending: allocate $500 of $1000 to Invoice #42
    │       (Invoice locked during application)
    │
    ├── Ledger.value_available reduced by $500
    │
    ├── Payment Pending stays: shows partial application history
    │
Customer pays (remainder)
    │
    ├── Payment Pending: allocate $500 to Invoice #42
    │
    ├── Ledger.value_available = 0, is_settled = true
    │
    ├── Invoice status → paid
    │
    └── All pending records stay as the complete flow picture
```

---

## AP Flow (Purchases)

```
PO sent to vendor
    │
    ├── Inventory Pending: reserve on_po for each line item
    │
Goods received
    │
    ├── Inventory Pending: move on_po → on_hand
    │
    ├── Receiving Report (GRN) created
    │
Vendor invoice arrives
    │
    ├── Ledger record(s) created from vendor terms
    │       (AP — model_name = 'purchase')
    │
    ├── Ledger Sync Pending: update org balance (payable)
    │
Payment to vendor
    │
    ├── Payment Pending: allocate payment to vendor invoice
    │
    ├── Ledger.value_available = 0, is_settled = true
    │
    └── Flow picture complete — PO → receipt → invoice → payment
```

---

## Alice's Role

Alice monitors pending records:
- **Stale pending** (unprocessed >1 hour) — something failed, needs attention
- **Lock without pending** — orphan lock, investigate
- **Pending without lock** — processed but record wasn't unlocked, fix
- **Flow gaps** — order shipped but no invoice created, customer paid but not applied

These are Alice's coaching signals. She doesn't need to understand accounting — she needs to see when the expected flow didn't happen.

---

## Post or Pend — The Universal Edit Rule

**Shorthand:** Post or Pend.

Every field edit on every transaction follows this rule:

| Record state | What happens on edit |
|-------------|---------------------|
| **Unlocked** | Post now — change takes effect immediately |
| **Locked** | Post to pending — creates a Pending record that needs release/approval |

The `edit_rules.locked_statuses` in the detail_layout Setting determines which statuses lock a record (e.g., completed, cancelled, void, received).

**Why this matters:** Users need to correct records after they're locked (wrong address, wrong price, wrong quantity). They shouldn't be blocked — but they also shouldn't be making unreviewed changes to completed transactions. Post or Pend gives them a path forward without breaking the audit trail.

**UI interaction on detail fields:**

| Modifier | Action |
|----------|--------|
| Click | Select/focus the field |
| Double-click | Inline edit the value |
| Shift+hover | Tooltip help |
| Shift+click | Deep help (field documentation) |
| Cmd+Option+click label | Open field's Setting record — admin edits select list choices, field config |

**For select lists:** Click opens the dropdown (standard). Cmd+Option+click on the *label* opens the Setting where the dropdown choices are defined — admin modifies the list itself, not the value.

**Alice's role in Post or Pend:**
- When a pending record is created from a locked edit, Alice logs it as an observation
- If the same field gets pending edits frequently, Alice flags it — maybe the lock status is wrong, or the workflow needs adjustment
- Posts question/frequency/answer patterns to WC_HQ (see below)

---

## Alice as Help Agent — Question Loop

Alice handles user questions in the help system with a feedback loop:

1. **User asks** — Shift+click or help button triggers a question
2. **Alice answers** — from her vector store (local knowledge) or escalates
3. **Alice logs** — question text, frequency, answer, resolution (solved/escalated/unanswered)
4. **Alice posts to WC_HQ** — question + frequency + answer, so all Alices learn
5. **WC_HQ distributes** — answers flow back to every Alice installation via sync

**The distribution:** Users typically have fewer than 300 unique questions in a heavily skewed 80/20 exponential distribution. The top 20 questions account for 80% of asks. Alice learns those fast. The long tail gets answered by WC_HQ's aggregated knowledge from all installations.

**What Alice tracks per question:**

| Field | Purpose |
|-------|---------|
| `question_text` | Normalized question (stripped of record-specific details) |
| `answer_text` | The answer that resolved it |
| `ask_count` | How many times this question has been asked (this installation) |
| `global_count` | How many times across all WC_HQ installations |
| `model_name` | Which model the question relates to |
| `field_name` | Which field (if field-specific) |
| `resolution` | solved, escalated, unanswered |
| `confidence` | Alice's confidence in the answer (0-100) |

**The economics:** Each Alice installation teaches WC_HQ. WC_HQ teaches every Alice. The marginal cost of answering the 301st question across all installations approaches zero because some other Alice already answered it. This is n² applied to customer support.

---

## Related Readmes

- `pending-compensating-transactions.md` — technical implementation, how to add new domains
- `pending-records-offline-updates.md` — API consumer perspective, conflict resolution
- `terms-ledgers.md` — how payment terms create ledger records
- `ledger-financial-system.md` — ledger model details
- `inventory_flow_testing.md` — inventory pending test scenarios
