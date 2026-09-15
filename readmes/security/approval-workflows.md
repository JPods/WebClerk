# Approval Workflows — SignOff Request Architecture

**Decision date:** 2026-08-25
**Status:** Built — status gate, Action creation, signoff recording, sequential activation
**Industry gap:** #5 from industry-comparison.md

## Design Principle

Approval is a guardrail, not a process. User sovereignty stays intact. Rules are data (Settings), not code. No multi-level chains, no auto-escalation, no conditional branching. One gate per transition. If your org needs 3 approvers, that's a management problem, not a software problem.

## How It Works

### 1. SignOff Request is a Status

`signoff_request` is a value in the transaction status select list, between `planned` and `released`. When approval is required, the transaction goes to `signoff_request` instead of the target status. It's visible in every status-filtered view — no hidden state.

### 2. Rules Live in Settings

Setting `purpose='wc:approval'`, `parent_model='purchase'` (or any transaction type):

```json
{
  "approval": {
    "rules": [
      {
        "name": "Large PO requires manager",
        "trigger": "status_change",
        "from": "planned",
        "to": "released",
        "condition": {"field": "totals.total", "op": ">=", "value": 5000},
        "assigned_to": [
          {"contact_id": 42, "name": "Jane Smith", "role": "manager", "sequence": 1, "status": "active"},
          {"contact_id": 55, "name": "Tom Director", "role": "director", "sequence": 2, "status": "passive"}
        ]
      }
    ]
  }
}
```

Shared rules can use `parent_model='transaction'` — applies to all transaction types.

### 3. The Flow

1. User tries to change Purchase status `planned → released`
2. `validate_transition()` checks `check_approval_required()` — condition matches (total >= $5000)
3. Status redirected to `signoff_request` instead of `released`
4. `create_signoff_action()` creates an Action record:
   - `action_type: 'follow-up'`
   - `priority: '2'` (High — signoff requests block other work)
   - `kanban_column: 'Ready'`
   - `assigned_to`: from the rule, with sequence and active/passive status
5. Transaction `config.signoff` populated:
   ```json
   {
     "required": true,
     "action_id": 31500,
     "rule_name": "Large PO requires manager",
     "blocked_transition": {"from": "planned", "to": "released"},
     "assigned_to": [...],
     "approvals": [],
     "status": "pending"
   }
   ```
6. Sequence 1 approver (active) sees it in their agenda
7. Approver calls `record_signoff()` → their approval captured in `config.signoff.approvals[]`
8. Sequence 2 activated (passive → active), Action `assigned_to` updated
9. All approvers done → `config.signoff.status = 'approved'`
10. User (or system) transitions `signoff_request → released` — guard verifies all approvals complete
11. Rejection at any point → `config.signoff.status = 'rejected'`, can transition back to `planned`

### 4. Signoff Data Captured on Transaction

```json
{
  "config": {
    "signoff": {
      "required": true,
      "action_id": 31500,
      "rule_name": "Large PO requires manager",
      "blocked_transition": {"from": "planned", "to": "released"},
      "assigned_to": [
        {"contact_id": 42, "name": "Jane Smith", "role": "manager", "sequence": 1, "status": "active", "dt_requested": "2026-08-25T14:00:00Z", "dt_response": "2026-08-25T14:30:00Z"},
        {"contact_id": 55, "name": "Tom Director", "role": "director", "sequence": 2, "status": "active", "dt_requested": "2026-08-25T14:30:00Z", "dt_response": ""}
      ],
      "approvals": [
        {
          "contact_id": 42,
          "name": "Jane Smith",
          "status": "approved",
          "dt": "2026-08-25T14:30:00Z"
        }
      ],
      "status": "pending"
    }
  }
}
```

The transaction carries its own audit trail. No separate approval table to query.

## Action Priority Framework

SignOff Request actions are created with priority `2` (High) because they block other work. The priority framework for all Action records:

| Priority | Label | Tooltip | When to Use |
|----------|-------|---------|-------------|
| 1 | Critical | Blocks revenue or customers — act today | System down, customer escalation, payment failure |
| 2 | High | Blocks other people's work — act within 24h | SignOff Requests, approval gates, pending decisions |
| 3 | Normal | Scheduled work — act within the week | Standard tasks, follow-ups, maintenance |
| 4 | Low | Nice to have — act when time allows | Cleanup, optimization, non-urgent improvements |
| 5 | Someday | No deadline — review monthly | Ideas, deferred improvements, research |

This framework should be exposed as a tooltip on the priority field via Shift-for-Help (Shift+hover on priority label).

## Administrative Drag Measurement

Each assignee in `config.signoff.assigned_to` carries:
- `dt_requested` — ISO 8601 UTC, stamped when this approver becomes active
- `dt_response` — ISO 8601 UTC, stamped when this approver signs off (or rejects)

The delta `dt_response - dt_requested` is the administrative drag for that approver. Alice can:
- Report average approval response time by role, person, or transaction type
- Flag approvers who consistently exceed a threshold (e.g., > 48h)
- Identify which rules create the most drag (rule_name → avg response time)
- Surface transactions stuck in `signoff_request` with no response for > N days

This is not about punishing slow approvers — it's about making the cost of approval visible so the org can decide whether the gate is worth the drag.

## Saved Search: SignOff Required

Pre-assigned search in db.list for both Action and Agenda views.

**Parameters:**
- **User scope**: my signoffs (default) | all signoffs | specific user
- **Sort**: oldest first (default — most drag shows first) | newest first
- **Sort field**: `assigned_to[].dt_requested` — age of the request, not the action creation date

Oldest-first default makes administrative drag visible — the signoff that's been sitting longest is at the top.

## Where Everything Lives

| Component | File | Function/Field |
|-----------|------|----------------|
| `signoff_request` status | `apps/transactions/choices.py` | `TRANSACTION_STATUS_CHOICES` |
| Status constant | `base_transaction_model.py` | `STATUS_SIGNOFF_REQUEST` |
| Transition table | `status_guard.py` | `TRANSITIONS` — `signoff_request` added to all types |
| Approval gate check | `status_guard.py` | `check_approval_required()` |
| Condition evaluator | `status_guard.py` | `_evaluate_condition()` |
| Rule loader | `status_guard.py` | `_get_approval_rules()` |
| Action creation | `status_guard.py` | `create_signoff_action()` |
| Signoff recording | `status_guard.py` | `record_signoff()` |
| ValidationResult | `validation.py` | Extended with `redirect_status`, `approval` |

## What's NOT Built (Intentionally)

- **Multi-level approval chains** — sequence in `assigned_to` handles ordered approvals; no separate chain model
- **Auto-escalation** — if the approver is slow, that's visible in the Action agenda; no timer
- **Conditional branching** — one rule, one gate; if rules get complex, simplify the org
- **Approval delegation** — approver reassigns the Action to a delegate; standard Action behavior
